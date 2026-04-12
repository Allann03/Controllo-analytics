"""
Serviço de Simulação Tributária.

simular_reforma()       — Compara regime atual vs. novo modelo (IBS + CBS).
comparar_todos_regimes() — Compara Simples / Presumido / Real / Reforma lado a lado.

Fallback (sem regras no banco): usa calculadores do módulo services.tributario,
que aplicam alíquotas oficiais conforme LC 123/2006, Lei 9.430/1996 e PLP 68/2024.
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from data.database import models
from services.tributario import (
    calcular_simples,
    calcular_presumido,
    calcular_real,
    calcular_reforma,
    SIMPLES_ANEXOS_DESC,
)


def _get_fiscal(db: Session, empresa_id: int):
    """Retorna EmpresaFiscal ou None."""
    return (
        db.query(models.EmpresaFiscal)
        .filter(models.EmpresaFiscal.empresa_id == empresa_id)
        .first()
    )


def simular_reforma(
    db: Session,
    empresa_id: int,
    receita_bruta: float,
    custo_servicos: float,
    aliquota_iss: Optional[float] = None,
    rbt12: Optional[float] = None,
) -> Dict:
    """
    Calcula a carga tributária no regime atual da empresa e no novo modelo
    pós-Reforma Tributária, retornando comparativo completo.
    """
    # Descobre regime e dados fiscais da empresa
    empresa_fiscal = _get_fiscal(db, empresa_id)
    regime = empresa_fiscal.regime_tributario if empresa_fiscal else "simples"
    anexo_simples = (empresa_fiscal.anexo_simples or "III") if empresa_fiscal else "III"
    iss = aliquota_iss if aliquota_iss is not None else 0.05

    # Busca regras vigentes do regime atual
    regras: List[models.RegrasTributarias] = (
        db.query(models.RegrasTributarias)
        .filter(
            models.RegrasTributarias.regime == regime,
            models.RegrasTributarias.vigencia_fim == None,  # noqa: E711
        )
        .all()
    )

    # Calcula carga atual
    carga_atual = 0.0
    detalhes_atual = []
    for r in regras:
        base = receita_bruta if r.base_calculo == "receita_bruta" else custo_servicos
        valor = base * r.aliquota
        carga_atual += valor
        detalhes_atual.append({
            "tributo": r.tributo,
            "aliquota_pct": r.aliquota * 100,
            "base": r.base_calculo,
            "valor": valor,
        })

    # Fallback se não houver regras cadastradas no banco: usa calculadores oficiais
    if not regras:
        if regime == "simples":
            resultado_fb = calcular_simples(
                receita_mensal=receita_bruta, rbt12=rbt12, anexo=anexo_simples,
            )
        elif regime == "presumido":
            resultado_fb = calcular_presumido(
                receita_bruta=receita_bruta, custo_servicos=custo_servicos, aliquota_iss=iss,
            )
        else:  # real
            resultado_fb = calcular_real(
                receita_bruta=receita_bruta, custo_servicos=custo_servicos, aliquota_iss=iss,
            )

        carga_atual = resultado_fb["total"]
        detalhes_atual = [
            {
                "tributo": d.get("tributo", ""),
                "aliquota_pct": d.get("aliquota_pct", 0),
                "base": d.get("base", "receita_bruta"),
                "valor": d.get("valor", d.get("valor_liquido", 0)),
            }
            for d in resultado_fb.get("detalhes", [])
        ]

    # Busca parâmetros da reforma
    params: List[models.ReformaParametros] = (
        db.query(models.ReformaParametros)
        .filter(models.ReformaParametros.vigencia_fim == None)  # noqa: E711
        .all()
    )

    carga_nova = 0.0
    detalhes_nova = []

    # Fallback se não houver parâmetros cadastrados: usa calculador oficial da reforma
    if not params:
        resultado_reforma = calcular_reforma(receita_bruta=receita_bruta, custo_servicos=custo_servicos)
        carga_nova = resultado_reforma["total"]
        detalhes_nova = resultado_reforma["detalhes"]
    else:
        for p in params:
            credito = custo_servicos * p.aliquota_estimada
            valor_bruto = receita_bruta * p.aliquota_estimada
            valor_liq = max(0.0, valor_bruto - credito)
            carga_nova += valor_liq
            detalhes_nova.append({
                "tributo": p.tributo_novo,
                "aliquota_pct": p.aliquota_estimada * 100,
                "valor_bruto": valor_bruto,
                "credito": credito,
                "valor_liquido": valor_liq,
            })

    diferenca = carga_nova - carga_atual
    variacao_pct = (diferenca / carga_atual * 100) if carga_atual > 0 else 0
    impacto_lucro = -diferenca   # carga maior = lucro menor

    return {
        "regime_atual": {
            "nome": regime.capitalize(),
            "label": {
                "simples": "Simples Nacional",
                "presumido": "Lucro Presumido",
                "real": "Lucro Real",
            }.get(regime, regime),
            "detalhes": detalhes_atual,
            "total": carga_atual,
            "pct_receita": (carga_atual / receita_bruta * 100) if receita_bruta > 0 else 0,
        },
        "regime_novo": {
            "nome": "Reforma Tributária",
            "label": "Reforma Tributária (IBS + CBS)",
            "detalhes": detalhes_nova,
            "total": carga_nova,
            "pct_receita": (carga_nova / receita_bruta * 100) if receita_bruta > 0 else 0,
        },
        "comparativo": {
            "diferenca_rs": diferenca,
            "variacao_pct": variacao_pct,
            "impacto_lucro_rs": impacto_lucro,
            "impacto": "aumento" if diferenca > 0 else "reducao",
            "alerta_forte": abs(variacao_pct) > 5,
            "recomendacao": (
                f"Sua carga tributária tende a "
                f"{'aumentar' if diferenca > 0 else 'diminuir'} "
                f"em {abs(variacao_pct):.1f}% com a Reforma Tributária."
            ),
        },
        "inputs": {
            "receita_bruta": receita_bruta,
            "custo_servicos": custo_servicos,
        },
    }


def comparar_todos_regimes(
    db: Session,
    empresa_id: int,
    receita_bruta: float,
    custo_servicos: float,
    aliquota_iss: Optional[float] = None,
    rbt12: Optional[float] = None,
) -> Dict:
    """
    Calcula e compara a carga tributária nos 4 cenários:
      Simples Nacional (todos os 5 anexos), Lucro Presumido, Lucro Real e Reforma.

    Retorna um dict com cada regime e um ranking do menor para o maior custo.
    """
    empresa_fiscal = _get_fiscal(db, empresa_id)
    anexo_atual = (empresa_fiscal.anexo_simples or "III") if empresa_fiscal else "III"
    regime_atual = (empresa_fiscal.regime_tributario or "simples") if empresa_fiscal else "simples"
    iss = aliquota_iss if aliquota_iss is not None else 0.05

    # ── Simples Nacional — todos os 5 anexos ─────────────────────────
    simples_por_anexo = {}
    for anexo in ("I", "II", "III", "IV", "V"):
        r = calcular_simples(receita_mensal=receita_bruta, rbt12=rbt12, anexo=anexo)
        simples_por_anexo[anexo] = {
            "label": f"Simples Nacional — Anexo {anexo}",
            "descricao": SIMPLES_ANEXOS_DESC.get(anexo, ""),
            "total": r["total"],
            "pct_receita": r["pct_receita"],
            "aliquota_efetiva_pct": r["aliquota_efetiva_pct"],
            "faixa": r["faixa"],
            "detalhes": r["detalhes"],
            "eh_atual": (regime_atual == "simples" and anexo == anexo_atual),
        }

    # ── Lucro Presumido ───────────────────────────────────────────────
    r_pres = calcular_presumido(receita_bruta=receita_bruta, custo_servicos=custo_servicos, aliquota_iss=iss)
    presumido = {
        "label": "Lucro Presumido",
        "total": r_pres["total"],
        "pct_receita": r_pres["pct_receita"],
        "detalhes": r_pres["detalhes"],
        "base_irpj": r_pres["base_irpj"],
        "eh_atual": regime_atual == "presumido",
    }

    # ── Lucro Real ────────────────────────────────────────────────────
    r_real = calcular_real(receita_bruta=receita_bruta, custo_servicos=custo_servicos, aliquota_iss=iss)
    real = {
        "label": "Lucro Real",
        "total": r_real["total"],
        "pct_receita": r_real["pct_receita"],
        "lucro_real": r_real["lucro_real"],
        "margem_lucro_pct": r_real["margem_lucro_pct"],
        "detalhes": r_real["detalhes"],
        "eh_atual": regime_atual == "real",
    }

    # ── Reforma Tributária ────────────────────────────────────────────
    r_ref = calcular_reforma(receita_bruta=receita_bruta, custo_servicos=custo_servicos)
    reforma = {
        "label": "Reforma Tributária (IBS + CBS)",
        "total": r_ref["total"],
        "pct_receita": round((r_ref["total"] / receita_bruta * 100) if receita_bruta > 0 else 0, 2),
        "detalhes": r_ref["detalhes"],
    }

    # ── Ranking do menor para o maior custo ──────────────────────────
    candidatos = [
        {"regime": "presumido", "label": presumido["label"], "total": presumido["total"]},
        {"regime": "real",      "label": real["label"],      "total": real["total"]},
        {"regime": "reforma",   "label": reforma["label"],   "total": reforma["total"]},
    ]
    for anexo, dados in simples_por_anexo.items():
        candidatos.append({
            "regime": f"simples_{anexo}",
            "label": dados["label"],
            "total": dados["total"],
        })
    candidatos.sort(key=lambda x: x["total"])

    return {
        "simples": simples_por_anexo,
        "presumido": presumido,
        "real": real,
        "reforma": reforma,
        "ranking": candidatos,
        "inputs": {
            "receita_bruta": receita_bruta,
            "custo_servicos": custo_servicos,
            "aliquota_iss": iss,
            "rbt12": rbt12,
            "regime_atual": regime_atual,
            "anexo_simples_atual": anexo_atual,
        },
    }
