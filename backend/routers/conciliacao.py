"""
Router de Conciliação Bancária
Permite registrar transações do extrato bancário e compará-las
com os lançamentos mensais registrados no sistema.
"""

import os as _os
import tempfile
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models

router = APIRouter(prefix="/api/conciliacao", tags=["conciliacao"])


# ──────────────────────────────────────────────────────────────────
#  Auth — importado do main via dependência injetada
# ──────────────────────────────────────────────────────────────────

from services.auth_utils import get_current_user as _get_user, resolve_empresa_or_403
from routers.auditoria import registrar_auditoria


# ──────────────────────────────────────────────────────────────────
#  Schemas
# ──────────────────────────────────────────────────────────────────

class TransacaoCreate(BaseModel):
    data_transacao: str          # YYYY-MM-DD
    descricao: str
    valor: float                 # sempre positivo
    tipo: str                    # "credito" | "debito"
    categoria: Optional[str] = ""
    observacao: Optional[str] = ""


class TransacaoUpdate(BaseModel):
    status: Optional[str] = None      # "pendente" | "conciliado" | "ignorado"
    categoria: Optional[str] = None
    observacao: Optional[str] = None
    descricao: Optional[str] = None


class TransacaoBulk(BaseModel):
    transacoes: List[TransacaoCreate]


# ──────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────

def _t_to_dict(t: models.TransacaoBancaria) -> dict:
    return {
        "id": t.id,
        "empresa_id": t.empresa_id,
        "data_transacao": t.data_transacao,
        "descricao": t.descricao,
        "valor": t.valor,
        "tipo": t.tipo,
        "categoria": t.categoria or "",
        "status": t.status,
        "observacao": t.observacao or "",
        "criado_em": t.criado_em,
    }


# ──────────────────────────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────────────────────────

@router.get("/transacoes/{empresa_id}")
def listar_transacoes(
    empresa_id: int,
    ano: int = 0,
    mes: int = 0,
    status: str = "",
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Lista transações bancárias de uma empresa, opcionalmente filtradas por período e status."""
    resolve_empresa_or_403(db, empresa_id, user)

    query = db.query(models.TransacaoBancaria).filter(
        models.TransacaoBancaria.empresa_id == empresa_id
    )

    if ano and mes:
        prefixo = f"{ano:04d}-{mes:02d}"
        query = query.filter(models.TransacaoBancaria.data_transacao.startswith(prefixo))
    elif ano:
        query = query.filter(models.TransacaoBancaria.data_transacao.startswith(str(ano)))

    if status in ("pendente", "conciliado", "ignorado"):
        query = query.filter(models.TransacaoBancaria.status == status)

    transacoes = query.order_by(models.TransacaoBancaria.data_transacao.desc()).all()
    return [_t_to_dict(t) for t in transacoes]


@router.post("/transacoes/{empresa_id}", status_code=201)
def criar_transacao(
    empresa_id: int,
    body: TransacaoCreate,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Registra uma única transação bancária."""
    resolve_empresa_or_403(db, empresa_id, user)

    if body.tipo not in ("credito", "debito"):
        raise HTTPException(status_code=400, detail="Tipo deve ser 'credito' ou 'debito'.")
    if body.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser positivo.")

    t = models.TransacaoBancaria(
        empresa_id=empresa_id,
        usuario_id=user.id,
        data_transacao=body.data_transacao.strip(),
        descricao=body.descricao.strip(),
        valor=body.valor,
        tipo=body.tipo,
        categoria=(body.categoria or "").strip(),
        status="pendente",
        observacao=(body.observacao or "").strip(),
        criado_em=datetime.now(timezone.utc).isoformat(),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _t_to_dict(t)


@router.post("/transacoes/{empresa_id}/bulk", status_code=201)
def importar_transacoes(
    empresa_id: int,
    body: TransacaoBulk,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Importa múltiplas transações de uma vez (colar do extrato)."""
    resolve_empresa_or_403(db, empresa_id, user)

    agora = datetime.now(timezone.utc).isoformat()
    criados = 0
    for item in body.transacoes:
        if item.tipo not in ("credito", "debito") or item.valor <= 0:
            continue
        t = models.TransacaoBancaria(
            empresa_id=empresa_id,
            usuario_id=user.id,
            data_transacao=item.data_transacao.strip(),
            descricao=item.descricao.strip(),
            valor=item.valor,
            tipo=item.tipo,
            categoria=(item.categoria or "").strip(),
            status="pendente",
            observacao=(item.observacao or "").strip(),
            criado_em=agora,
        )
        db.add(t)
        criados += 1

    db.commit()
    registrar_auditoria(db, "importar_transacoes_conciliacao", usuario_id=user.id, usuario_nome=user.nome,
                        escritorio_id=user.escritorio_id, recurso="conciliacao", recurso_id=empresa_id,
                        detalhes={"empresa_id": empresa_id, "criadas": criados})
    return {"mensagem": f"{criados} transações importadas.", "criadas": criados}


@router.patch("/transacoes/{transacao_id}")
def atualizar_transacao(
    transacao_id: int,
    body: TransacaoUpdate,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Atualiza status, categoria ou observação de uma transação."""
    t = db.query(models.TransacaoBancaria).filter(
        models.TransacaoBancaria.id == transacao_id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada.")

    resolve_empresa_or_403(db, t.empresa_id, user)

    if body.status is not None:
        if body.status not in ("pendente", "conciliado", "ignorado"):
            raise HTTPException(status_code=400, detail="Status inválido.")
        t.status = body.status
    if body.categoria is not None:
        t.categoria = body.categoria.strip()
    if body.observacao is not None:
        t.observacao = body.observacao.strip()
    if body.descricao is not None:
        t.descricao = body.descricao.strip()

    db.commit()
    return _t_to_dict(t)


@router.delete("/transacoes/{transacao_id}")
def excluir_transacao(
    transacao_id: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Remove uma transação bancária."""
    t = db.query(models.TransacaoBancaria).filter(
        models.TransacaoBancaria.id == transacao_id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada.")

    resolve_empresa_or_403(db, t.empresa_id, user)
    db.delete(t)
    db.commit()
    return {"mensagem": "Transação removida."}


@router.post("/analisar")
async def analisar_conciliacao(
    empresa_id: int = Form(...),
    pdfs: List[UploadFile] = File(default=[]),
    excels: List[UploadFile] = File(default=[]),
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """
    Reconcilia extratos PDF com planilhas Excel geradas pelo Leitor de Extrato.

    Tripla verificação:
      Pass 1 — cada PDF é lido pelos parsers que já fazem verificação item a item
      Pass 2 — cada planilha Excel é lida com rastreamento de linha
      Pass 3 — cruzamento (data + valor ±R$0,02 + tipo) via matcher específico do banco
    Sem filtro de período: todo o conteúdo dos arquivos enviados é processado.
    """
    resolve_empresa_or_403(db, empresa_id, user)

    from services.extrator_pdf import processar_extrato
    from services.conciliacao import reconciliar, ler_excel_com_linhas

    avisos: list[str] = []

    # ── Pass 1: parsear cada PDF ──────────────────────────────────────
    transacoes_pdf: list[dict] = []
    saldo_inicial_total: float | None = None
    saldo_final_total:   float | None = None

    for pdf_file in (pdfs or []):
        conteudo = await pdf_file.read()
        if not conteudo:
            continue
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        try:
            tmp.write(conteudo)
            tmp.close()
            resultado = processar_extrato(tmp.name)
            if resultado.get("erro"):
                avisos.append(f"{pdf_file.filename}: {resultado['erro']}")
                continue
            for t in resultado.get("transacoes", []):
                t["_arquivo"] = pdf_file.filename
            transacoes_pdf.extend(resultado.get("transacoes", []))
            avisos.extend(resultado.get("avisos", []))
            # Acumula saldo inicial / final (soma múltiplos PDFs de contas diferentes)
            si = resultado.get("saldo_inicial")
            sf = resultado.get("saldo_final")
            if si is not None:
                saldo_inicial_total = (saldo_inicial_total or 0.0) + si
            if sf is not None:
                saldo_final_total = (saldo_final_total or 0.0) + sf
        except Exception as e:
            avisos.append(f"{pdf_file.filename}: erro ao processar — {e}")
        finally:
            try:
                _os.unlink(tmp.name)
            except Exception:
                pass

    # ── Pass 2: ler cada Excel com rastreamento de linha ─────────────
    excels_bytes: list[bytes] = []
    for excel_file in (excels or []):
        conteudo = await excel_file.read()
        if conteudo:
            excels_bytes.append(conteudo)

    transacoes_excel: list[dict] = []
    if excels_bytes:
        try:
            transacoes_excel = ler_excel_com_linhas(excels_bytes)
        except Exception as e:
            avisos.append(f"Erro ao ler planilha(s) Excel: {e}")

    # ── Pass 3: reconciliação com matcher específico do banco ─────────
    try:
        relatorio = reconciliar(transacoes_pdf, transacoes_excel)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"Erro na reconciliação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao processar conciliação.")

    relatorio["avisos"] = avisos
    # Injeta saldo inicial/final do extrato nos totais_pdf para exibição na conciliação
    relatorio["totais_pdf"]["saldo_inicial"] = saldo_inicial_total
    relatorio["totais_pdf"]["saldo_final"]   = saldo_final_total
    return relatorio


@router.get("/resumo/{empresa_id}")
def resumo_conciliacao(
    empresa_id: int,
    ano: int,
    mes: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """
    Compara totais do extrato bancário (transações registradas) vs
    lançamentos mensais registrados no sistema para o mesmo período.
    """
    resolve_empresa_or_403(db, empresa_id, user)

    # Transações bancárias do período
    prefixo = f"{ano:04d}-{mes:02d}"
    transacoes = db.query(models.TransacaoBancaria).filter(
        models.TransacaoBancaria.empresa_id == empresa_id,
        models.TransacaoBancaria.data_transacao.startswith(prefixo),
    ).all()

    banco_entradas = sum(t.valor for t in transacoes if t.tipo == "credito" and t.status != "ignorado")
    banco_saidas   = sum(t.valor for t in transacoes if t.tipo == "debito"  and t.status != "ignorado")
    banco_saldo    = banco_entradas - banco_saidas

    pendentes   = sum(1 for t in transacoes if t.status == "pendente")
    conciliados = sum(1 for t in transacoes if t.status == "conciliado")
    ignorados   = sum(1 for t in transacoes if t.status == "ignorado")

    # Lançamento mensal registrado no sistema
    lancamento = db.query(models.LancamentoMensal).filter(
        models.LancamentoMensal.empresa_id == empresa_id,
        models.LancamentoMensal.ano == ano,
        models.LancamentoMensal.mes == mes,
    ).first()

    sistema_entradas = lancamento.entradas_caixa if lancamento else None
    sistema_saidas   = lancamento.saidas_caixa   if lancamento else None
    sistema_saldo    = (sistema_entradas - sistema_saidas) if lancamento else None

    # Diferenças
    diff_entradas = round(banco_entradas - sistema_entradas, 2) if sistema_entradas is not None else None
    diff_saidas   = round(banco_saidas   - sistema_saidas,   2) if sistema_saidas   is not None else None
    diff_saldo    = round(banco_saldo    - sistema_saldo,    2) if sistema_saldo    is not None else None

    return {
        "periodo": f"{ano:04d}-{mes:02d}",
        "banco": {
            "entradas": banco_entradas,
            "saidas":   banco_saidas,
            "saldo":    banco_saldo,
        },
        "sistema": {
            "entradas": sistema_entradas,
            "saidas":   sistema_saidas,
            "saldo":    sistema_saldo,
        },
        "diferencas": {
            "entradas": diff_entradas,
            "saidas":   diff_saidas,
            "saldo":    diff_saldo,
        },
        "status_counts": {
            "pendentes":   pendentes,
            "conciliados": conciliados,
            "ignorados":   ignorados,
            "total":       len(transacoes),
        },
        "conciliado": (
            diff_saldo is not None and abs(diff_saldo) < 0.01
        ),
    }
