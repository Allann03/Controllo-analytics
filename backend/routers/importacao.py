"""
Router de Importação — Controllo Analytics
Endpoints para upload, preview, mapeamento, processamento e histórico.
"""

import csv
import io
import os
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models
from services import importacao_service as svc

from services.auth_utils import get_current_user, resolve_empresa_or_403
from routers.auditoria import registrar_auditoria

router = APIRouter(prefix="/api/importacao", tags=["importacao"])


# ──────────────────────────────────────────────────────────────────
#  Schemas
# ──────────────────────────────────────────────────────────────────

class ProcessarRequest(BaseModel):
    empresa_id: int
    tipo_dado: str
    mapeamento: dict[str, str]  # {coluna_original: campo_destino}


class SalvarTemplateRequest(BaseModel):
    nome: str
    tipo_dado: str
    mapeamento: dict[str, str]


# ──────────────────────────────────────────────────────────────────
#  Metadados de campos
# ──────────────────────────────────────────────────────────────────

@router.get("/tipos")
def listar_tipos():
    """Retorna os tipos de dados suportados e seus campos destino."""
    return {
        "tipos": svc.TIPOS_DADO,
        "campos_por_tipo": svc.CAMPOS_DESTINO,
    }


# ──────────────────────────────────────────────────────────────────
#  Preview — cabeçalho + sugestão automática de mapeamento
# ──────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────
#  Template download — CSV com cabeçalho + 2 linhas de exemplo
# ──────────────────────────────────────────────────────────────────

# Exemplos de dados por tipo (2 linhas)
_EXEMPLOS: dict[str, list[dict]] = {
    "dre": [
        {"ano": 2024, "mes": 1, "receita_bruta": 150000.00, "deducoes_receita": 15000.00,
         "custo_servicos": 45000.00, "despesas_adm": 20000.00, "despesas_comerciais": 10000.00,
         "despesas_financeiras": 5000.00, "outras_despesas": 2000.00, "ir_csll": 8000.00, "folha_pagamento": 35000.00},
        {"ano": 2024, "mes": 2, "receita_bruta": 162000.00, "deducoes_receita": 16200.00,
         "custo_servicos": 48600.00, "despesas_adm": 20000.00, "despesas_comerciais": 11000.00,
         "despesas_financeiras": 5000.00, "outras_despesas": 1500.00, "ir_csll": 9000.00, "folha_pagamento": 35000.00},
    ],
    "fluxo": [
        {"ano": 2024, "mes": 1, "entradas_caixa": 148000.00, "saidas_caixa": 112000.00, "saldo_inicial_caixa": 50000.00},
        {"ano": 2024, "mes": 2, "entradas_caixa": 160000.00, "saidas_caixa": 118000.00, "saldo_inicial_caixa": 86000.00},
    ],
    "balanco": [
        {"ano": 2024, "mes": 1, "caixa_equivalentes": 86000.00, "contas_receber": 45000.00,
         "estoques": 20000.00, "outros_ativo_circ": 5000.00, "ativo_nao_circulante": 200000.00,
         "fornecedores": 30000.00, "emprestimos_cp": 20000.00, "tributos_pagar": 12000.00,
         "outros_passivo_circ": 5000.00, "passivo_nao_circulante": 80000.00,
         "capital_social": 100000.00, "reservas": 50000.00, "lucros_acumulados": 59000.00},
        {"ano": 2024, "mes": 2, "caixa_equivalentes": 128000.00, "contas_receber": 48000.00,
         "estoques": 19000.00, "outros_ativo_circ": 5000.00, "ativo_nao_circulante": 198000.00,
         "fornecedores": 28000.00, "emprestimos_cp": 20000.00, "tributos_pagar": 13500.00,
         "outros_passivo_circ": 5000.00, "passivo_nao_circulante": 78000.00,
         "capital_social": 100000.00, "reservas": 50000.00, "lucros_acumulados": 103500.00},
    ],
    "faturamento": [
        {"ano": 2024, "mes": 1, "receita_bruta": 150000.00, "deducoes_receita": 15000.00},
        {"ano": 2024, "mes": 2, "receita_bruta": 162000.00, "deducoes_receita": 16200.00},
    ],
    "folha": [
        {"ano": 2024, "mes": 1, "folha_pagamento": 35000.00},
        {"ano": 2024, "mes": 2, "folha_pagamento": 35000.00},
    ],
    "impostos": [
        {"ano": 2024, "mes": 1, "ir_csll": 8000.00, "tributos_pagar": 12000.00, "deducoes_receita": 15000.00},
        {"ano": 2024, "mes": 2, "ir_csll": 9000.00, "tributos_pagar": 13500.00, "deducoes_receita": 16200.00},
    ],
}


@router.get("/modelo/{tipo_dado}")
def baixar_modelo_xlsx(
    tipo_dado: str,
    current_user: models.Usuario = Depends(get_current_user),
):
    """Retorna um .xlsx formatado com dados de exemplo e aba de instruções."""
    tipos_validos = list(svc._MODELOS.keys())
    if tipo_dado not in tipos_validos:
        raise HTTPException(400, f"tipo_dado inválido. Opções: {tipos_validos}")
    try:
        conteudo = svc.gerar_modelo_xlsx(tipo_dado)
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar modelo: {str(e)[:200]}")
    return StreamingResponse(
        iter([conteudo]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="modelo_{tipo_dado}.xlsx"'},
    )


@router.get("/template/{tipo_dado}")
def baixar_template(
    tipo_dado: str,
    current_user: models.Usuario = Depends(get_current_user),
):
    """Retorna um CSV de modelo para o tipo de dado especificado."""
    if tipo_dado not in svc.TIPOS_DADO:
        raise HTTPException(400, f"tipo_dado inválido. Opções: {svc.TIPOS_DADO}")

    campos = svc.CAMPOS_DESTINO[tipo_dado]
    cabecalho = [c["campo"] for c in campos]
    exemplos = _EXEMPLOS.get(tipo_dado, [])

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cabecalho, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for ex in exemplos:
        writer.writerow({k: ex.get(k, "") for k in cabecalho})

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="modelo_{tipo_dado}.csv"'},
    )


@router.post("/preview")
async def preview(
    arquivo: UploadFile = File(...),
    current_user: models.Usuario = Depends(get_current_user),
):
    """
    Recebe o arquivo e retorna:
    - colunas detectadas no cabeçalho
    - sugestão automática de mapeamento {coluna: campo_destino}
    Não persiste nada.
    """
    if not current_user.is_aprovado:
        raise HTTPException(403, "Acesso não autorizado.")

    ext = (arquivo.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls", "csv"):
        raise HTTPException(400, f"Formato .{ext} não suportado. Use .xlsx, .xls ou .csv.")

    conteudo = await arquivo.read()
    if len(conteudo) > 20 * 1024 * 1024:  # 20 MB
        raise HTTPException(413, "Arquivo muito grande. Limite: 20 MB.")

    try:
        resultado = svc.preview_arquivo(conteudo, arquivo.filename or "arquivo")
    except ValueError as e:
        raise HTTPException(400, str(e))

    return resultado


# ──────────────────────────────────────────────────────────────────
#  Processar — upload + mapeamento como form-data
# ──────────────────────────────────────────────────────────────────

@router.post("/processar")
async def processar(
    arquivo: UploadFile = File(...),
    empresa_id: int = Form(...),
    tipo_dado: str = Form(...),
    mapeamento_json: str = Form(...),  # JSON serializado
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """
    Processa o arquivo com o mapeamento fornecido e persiste em LancamentoMensal.
    """
    if not current_user.is_aprovado:
        raise HTTPException(403, "Acesso não autorizado.")

    resolve_empresa_or_403(db, empresa_id, current_user)

    if tipo_dado not in svc.TIPOS_DADO:
        raise HTTPException(400, f"tipo_dado inválido. Opções: {svc.TIPOS_DADO}")

    try:
        mapeamento: dict[str, str] = json.loads(mapeamento_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "mapeamento_json inválido.")

    # Valida que ano e mes estão mapeados
    if "ano" not in mapeamento.values() or "mes" not in mapeamento.values():
        raise HTTPException(400, "O mapeamento deve incluir os campos 'ano' e 'mes'.")

    ext = (arquivo.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls", "csv"):
        raise HTTPException(400, f"Formato .{ext} não suportado.")

    conteudo = await arquivo.read()
    if len(conteudo) > 20 * 1024 * 1024:
        raise HTTPException(413, "Arquivo muito grande. Limite: 20 MB.")

    try:
        resumo = svc.processar_importacao(
            db=db,
            empresa_id=empresa_id,
            usuario_id=current_user.id,
            nome_arquivo=arquivo.filename or "arquivo",
            tipo_dado=tipo_dado,
            mapeamento=mapeamento,
            conteudo=conteudo,
        )
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"Erro ao processar importação: {e}", exc_info=True)
        raise HTTPException(422, "Erro ao processar arquivo de importação.")

    registrar_auditoria(db, "importar_dados", usuario_id=current_user.id, usuario_nome=current_user.nome,
                        escritorio_id=current_user.escritorio_id, recurso="importacao", recurso_id=empresa_id,
                        detalhes={"empresa_id": empresa_id, "tipo": tipo_dado, "arquivo": arquivo.filename or ""})
    return {"mensagem": "Importação concluída.", "resumo": resumo}


# ──────────────────────────────────────────────────────────────────
#  Histórico
# ──────────────────────────────────────────────────────────────────

@router.get("/historico/{empresa_id}")
def historico(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if not current_user.is_aprovado:
        raise HTTPException(403, "Acesso não autorizado.")
    resolve_empresa_or_403(db, empresa_id, current_user)
    return svc.listar_historico(db, empresa_id)


# ──────────────────────────────────────────────────────────────────
#  Templates de mapeamento
# ──────────────────────────────────────────────────────────────────

@router.get("/templates")
def listar_templates(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if not current_user.is_aprovado:
        raise HTTPException(403, "Acesso não autorizado.")
    return svc.listar_templates(db, current_user.id)


@router.post("/templates")
def criar_template(
    body: SalvarTemplateRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if not current_user.is_aprovado:
        raise HTTPException(403, "Acesso não autorizado.")
    t = svc.salvar_template(db, current_user.id, body.nome, body.tipo_dado, body.mapeamento)
    return {"id": t.id, "mensagem": f"Template '{t.nome}' salvo."}


@router.delete("/templates/{template_id}")
def deletar_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if not current_user.is_aprovado:
        raise HTTPException(403, "Acesso não autorizado.")
    ok = svc.deletar_template(db, template_id, current_user.id)
    if not ok:
        raise HTTPException(404, "Template não encontrado.")
    return {"mensagem": "Template removido."}
