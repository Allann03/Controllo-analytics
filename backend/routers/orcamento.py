"""
Router de Orçamento vs. Realizado
Permite cadastrar metas orçamentárias mensais por empresa e
compará-las automaticamente com os lançamentos mensais registrados.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models

router = APIRouter(prefix="/api/orcamento", tags=["orcamento"])

# ──────────────────────────────────────────────────────────────────
#  Auth
# ──────────────────────────────────────────────────────────────────

from services.auth_utils import get_current_user as _get_user, resolve_empresa_or_403


# ──────────────────────────────────────────────────────────────────
#  Schemas
# ──────────────────────────────────────────────────────────────────

class OrcamentoUpsert(BaseModel):
    ano: int
    mes: int                              # 1–12
    receita_bruta: float = 0.0
    deducoes_receita: float = 0.0
    custo_servicos: float = 0.0
    despesas_adm: float = 0.0
    despesas_comerciais: float = 0.0
    despesas_financeiras: float = 0.0
    outras_despesas: float = 0.0
    ir_csll: float = 0.0
    entradas_caixa: float = 0.0
    saidas_caixa: float = 0.0
    folha_pagamento: float = 0.0


# ──────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────

def _o_to_dict(o: models.OrcamentoMensal) -> dict:
    return {
        "id": o.id,
        "empresa_id": o.empresa_id,
        "ano": o.ano,
        "mes": o.mes,
        "receita_bruta": o.receita_bruta,
        "deducoes_receita": o.deducoes_receita,
        "custo_servicos": o.custo_servicos,
        "despesas_adm": o.despesas_adm,
        "despesas_comerciais": o.despesas_comerciais,
        "despesas_financeiras": o.despesas_financeiras,
        "outras_despesas": o.outras_despesas,
        "ir_csll": o.ir_csll,
        "entradas_caixa": o.entradas_caixa,
        "saidas_caixa": o.saidas_caixa,
        "folha_pagamento": o.folha_pagamento,
        "criado_em": o.criado_em,
        "atualizado_em": o.atualizado_em,
    }


def _variacao(realizado: float, orcado: float) -> Optional[float]:
    """Percentual de desvio: positivo = acima do orçado."""
    if orcado == 0:
        return None
    return round((realizado - orcado) / abs(orcado) * 100, 2)


def _build_comparativo(orc: models.OrcamentoMensal, lanc: Optional[models.LancamentoMensal]) -> dict:
    """Monta objeto comparativo por linha com orçado, realizado e variação."""
    def par(campo: str, invertido: bool = False):
        """invertido=True → desvio positivo é ruim (despesas)."""
        orcado    = getattr(orc, campo, 0.0) or 0.0
        realizado = getattr(lanc, campo, 0.0) if lanc else 0.0
        realizado = realizado or 0.0
        var = _variacao(realizado, orcado)
        return {
            "orcado":    orcado,
            "realizado": realizado,
            "variacao":  var,
            "status": (
                "sem_orcamento" if orcado == 0
                else "ok"      if var is not None and (
                    (not invertido and var >= -5) or (invertido and var <= 5)
                )
                else "atencao" if var is not None and (
                    (not invertido and var >= -20) or (invertido and var <= 20)
                )
                else "critico"
            ),
        }

    # Derivadas
    orc_rl    = (orc.receita_bruta or 0) - (orc.deducoes_receita or 0)
    lanc_rl   = ((lanc.receita_bruta or 0) - (lanc.deducoes_receita or 0)) if lanc else 0.0
    orc_lb    = orc_rl - (orc.custo_servicos or 0)
    lanc_lb   = lanc_rl - ((lanc.custo_servicos or 0) if lanc else 0)
    orc_desp  = sum(getattr(orc, c, 0) or 0 for c in ["despesas_adm", "despesas_comerciais", "despesas_financeiras", "outras_despesas"])
    lanc_desp = sum((getattr(lanc, c, 0) or 0) for c in ["despesas_adm", "despesas_comerciais", "despesas_financeiras", "outras_despesas"]) if lanc else 0.0
    orc_ll    = orc_lb - orc_desp - (orc.ir_csll or 0)
    lanc_ll   = lanc_lb - lanc_desp - ((lanc.ir_csll or 0) if lanc else 0)

    def par_calc(orcado: float, realizado: float, invertido: bool = False) -> dict:
        var = _variacao(realizado, orcado)
        return {
            "orcado": orcado, "realizado": realizado, "variacao": var,
            "status": (
                "sem_orcamento" if orcado == 0
                else "ok"      if var is not None and ((not invertido and var >= -5) or (invertido and var <= 5))
                else "atencao" if var is not None and ((not invertido and var >= -20) or (invertido and var <= 20))
                else "critico"
            ),
        }

    return {
        "periodo": {"ano": orc.ano, "mes": orc.mes},
        "receita_bruta":        par("receita_bruta"),
        "deducoes_receita":     par("deducoes_receita", invertido=True),
        "receita_liquida":      par_calc(orc_rl, lanc_rl),
        "custo_servicos":       par("custo_servicos", invertido=True),
        "lucro_bruto":          par_calc(orc_lb, lanc_lb),
        "despesas_adm":         par("despesas_adm", invertido=True),
        "despesas_comerciais":  par("despesas_comerciais", invertido=True),
        "despesas_financeiras": par("despesas_financeiras", invertido=True),
        "outras_despesas":      par("outras_despesas", invertido=True),
        "ir_csll":              par("ir_csll", invertido=True),
        "lucro_liquido":        par_calc(orc_ll, lanc_ll),
        "entradas_caixa":       par("entradas_caixa"),
        "saidas_caixa":         par("saidas_caixa", invertido=True),
        "folha_pagamento":      par("folha_pagamento", invertido=True),
        "sem_lancamento": lanc is None,
    }


# ──────────────────────────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────────────────────────

@router.get("/empresas/{empresa_id}")
def listar_orcamentos(
    empresa_id: int,
    ano: int = 0,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Lista todos os orçamentos cadastrados para a empresa (opcional: filtra por ano)."""
    resolve_empresa_or_403(db, empresa_id, user)
    query = db.query(models.OrcamentoMensal).filter(
        models.OrcamentoMensal.empresa_id == empresa_id
    )
    if ano:
        query = query.filter(models.OrcamentoMensal.ano == ano)
    orcamentos = query.order_by(
        models.OrcamentoMensal.ano.desc(),
        models.OrcamentoMensal.mes.desc(),
    ).all()
    return [_o_to_dict(o) for o in orcamentos]


@router.put("/empresas/{empresa_id}", status_code=200)
def upsert_orcamento(
    empresa_id: int,
    body: OrcamentoUpsert,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Cria ou atualiza o orçamento de um mês/ano específico."""
    resolve_empresa_or_403(db, empresa_id, user)

    if not (1 <= body.mes <= 12):
        raise HTTPException(status_code=400, detail="Mês inválido (1–12).")
    if body.ano < 2000 or body.ano > 2100:
        raise HTTPException(status_code=400, detail="Ano inválido.")

    agora = datetime.now(timezone.utc).isoformat()
    orc = db.query(models.OrcamentoMensal).filter(
        models.OrcamentoMensal.empresa_id == empresa_id,
        models.OrcamentoMensal.ano == body.ano,
        models.OrcamentoMensal.mes == body.mes,
    ).first()

    campos = body.model_dump(exclude={"ano", "mes"})
    if orc:
        for k, v in campos.items():
            setattr(orc, k, v)
        orc.atualizado_em = agora
    else:
        orc = models.OrcamentoMensal(
            empresa_id=empresa_id,
            ano=body.ano,
            mes=body.mes,
            criado_em=agora,
            atualizado_em=agora,
            **campos,
        )
        db.add(orc)

    db.commit()
    db.refresh(orc)
    return _o_to_dict(orc)


@router.delete("/empresas/{empresa_id}/{ano}/{mes}")
def excluir_orcamento(
    empresa_id: int,
    ano: int,
    mes: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Remove o orçamento de um mês específico."""
    resolve_empresa_or_403(db, empresa_id, user)
    orc = db.query(models.OrcamentoMensal).filter(
        models.OrcamentoMensal.empresa_id == empresa_id,
        models.OrcamentoMensal.ano == ano,
        models.OrcamentoMensal.mes == mes,
    ).first()
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    db.delete(orc)
    db.commit()
    return {"mensagem": "Orçamento removido."}


@router.get("/comparativo/{empresa_id}")
def comparativo_orcamento(
    empresa_id: int,
    ano: int,
    mes: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """
    Retorna a comparação linha-a-linha entre orçado e realizado
    para o período informado.
    """
    resolve_empresa_or_403(db, empresa_id, user)

    orc = db.query(models.OrcamentoMensal).filter(
        models.OrcamentoMensal.empresa_id == empresa_id,
        models.OrcamentoMensal.ano == ano,
        models.OrcamentoMensal.mes == mes,
    ).first()

    if not orc:
        return {"sem_orcamento": True, "periodo": {"ano": ano, "mes": mes}}

    lanc = db.query(models.LancamentoMensal).filter(
        models.LancamentoMensal.empresa_id == empresa_id,
        models.LancamentoMensal.ano == ano,
        models.LancamentoMensal.mes == mes,
    ).first()

    return _build_comparativo(orc, lanc)


@router.get("/comparativo/{empresa_id}/anual")
def comparativo_anual(
    empresa_id: int,
    ano: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """
    Retorna comparativo acumulado do ano inteiro:
    lista de 12 meses (apenas os que têm orçamento cadastrado).
    """
    resolve_empresa_or_403(db, empresa_id, user)

    orcamentos = db.query(models.OrcamentoMensal).filter(
        models.OrcamentoMensal.empresa_id == empresa_id,
        models.OrcamentoMensal.ano == ano,
    ).order_by(models.OrcamentoMensal.mes).all()

    lancamentos = {
        l.mes: l
        for l in db.query(models.LancamentoMensal).filter(
            models.LancamentoMensal.empresa_id == empresa_id,
            models.LancamentoMensal.ano == ano,
        ).all()
    }

    meses = []
    for orc in orcamentos:
        lanc = lancamentos.get(orc.mes)
        comp = _build_comparativo(orc, lanc)
        meses.append({
            "mes": orc.mes,
            "receita_bruta_orc": comp["receita_bruta"]["orcado"],
            "receita_bruta_real": comp["receita_bruta"]["realizado"],
            "lucro_liquido_orc": comp["lucro_liquido"]["orcado"],
            "lucro_liquido_real": comp["lucro_liquido"]["realizado"],
            "desvio_receita": comp["receita_bruta"]["variacao"],
            "desvio_lucro":   comp["lucro_liquido"]["variacao"],
        })

    return {"ano": ano, "meses": meses}
