"""
Servico de Simulacao Tributaria.

simular_reforma()       -- Compara regime atual vs. novo modelo (IBS + CBS).
comparar_todos_regimes() -- Compara Simples / Presumido / Real / Reforma lado a lado.

Fallback (sem regras no banco): usa calculadores do modulo services.tributario,
que aplicam aliquotas oficiais conforme LC 123/2006, Lei 9.430/1996 e PLP 68/2024.

Feature flags:
  CONTROLLO_LP_ENGINE = legado | novo (env var, default "legado")
  Override: query param ?lp_engine=novo (BLOCO 3F.2)
"""
import logging
import os
from decimal import Decimal
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
from services.contabil.lucro_presumido import (
    calcular_lucro_presumido,
    ReceitaPorAtividade,
    ResultadoLucroPresumido,
)
from services.contabil.cnae_presuncao import inferir_bases
from services.contabil.core import ResultadoCalculo

_logger = logging.getLogger(__name__)

# -- Feature flag: CONTROLLO_LP_ENGINE ----------------------------------------
# Fase 1: legado (default). Fase 2: novo. Fase 3: flag removida.
_LP_ENGINE_RAW = os.environ.get("CONTROLLO_LP_ENGINE", "").strip().lower()
if _LP_ENGINE_RAW not in ("novo", "legado", ""):
    _logger.error(
        "CONTROLLO_LP_ENGINE=%r invalido. Valores aceitos: 'novo', 'legado'. "
        "Usando fallback 'legado'.", _LP_ENGINE_RAW,
    )
    _LP_ENGINE_RAW = "legado"
if not _LP_ENGINE_RAW:
    _logger.warning(
        "CONTROLLO_LP_ENGINE nao definida. Usando 'legado' como default. "
        "Defina 'novo' para ativar o motor LP corrigido (BLOCO 3F.2)."
    )
    _LP_ENGINE_RAW = "legado"
LP_ENGINE: str = _LP_ENGINE_RAW


def _usar_motor_lp_novo(override: Optional[str] = None) -> bool:
    """Decide se usa o motor novo de Lucro Presumido. Override vem do query param."""
    if override and override.strip().lower() == "novo":
        return True
    return LP_ENGINE == "novo"


# -- Adapter: ResultadoCalculo -> dict legado ---------------------------------

def _adaptar_resultado_lp(resultado: ResultadoCalculo, receita_bruta: float, custo_servicos: float) -> dict:
    """
    Converte ResultadoCalculo (motor novo) no formato dict esperado pelos callers
    (simular_reforma e comparar_todos_regimes), mantendo compatibilidade total
    com o formato do motor legado.

    Adapter pattern — BLOCO 3F.2 Decisao II.
    """
    lp: ResultadoLucroPresumido = resultado.valor

    detalhes = []

    # IRPJ (15% + adicional)
    detalhes.append({
        "tributo": "IRPJ",
        "base": "base_presumida",
        "aliquota_pct": 15.0,
        "base_valor": float(lp.base_calculo_irpj),
        "valor": float(lp.irpj_total),
    })

    # CSLL (9%)
    detalhes.append({
        "tributo": "CSLL",
        "base": "base_presumida",
        "aliquota_pct": 9.0,
        "base_valor": float(lp.base_calculo_csll),
        "valor": float(lp.csll_9),
    })

    # PIS (0.65%)
    detalhes.append({
        "tributo": "PIS",
        "base": "receita_bruta",
        "aliquota_pct": 0.65,
        "base_valor": float(lp.receita_bruta_total),
        "valor": float(lp.pis_065),
    })

    # COFINS (3%)
    detalhes.append({
        "tributo": "COFINS",
        "base": "receita_bruta",
        "aliquota_pct": 3.0,
        "base_valor": float(lp.receita_bruta_total),
        "valor": float(lp.cofins_3),
    })

    # ISS (se houver)
    if lp.iss > 0:
        detalhes.append({
            "tributo": "ISS",
            "base": "receita_bruta",
            "aliquota_pct": float(lp.iss / lp.receita_bruta_total * 100) if lp.receita_bruta_total else 0.0,
            "base_valor": float(lp.receita_bruta_total),
            "valor": float(lp.iss),
        })

    total = float(lp.total_tributos)
    rb = float(lp.receita_bruta_total)

    return {
        "regime": "presumido",
        "label": "Lucro Presumido",
        "receita_bruta": rb,
        "custo_servicos": custo_servicos,
        "base_irpj": float(lp.base_calculo_irpj),
        "base_csll": float(lp.base_calculo_csll),
        "irpj": float(lp.irpj_total),
        "csll": float(lp.csll_9),
        "pis": float(lp.pis_065),
        "cofins": float(lp.cofins_3),
        "iss": float(lp.iss),
        "total": total,
        "pct_receita": float(lp.aliquota_efetiva) * 100 if rb > 0 else 0.0,
        "detalhes": detalhes,
    }


# -- Dispatch: legado vs novo ------------------------------------------------

def _calcular_presumido_dispatch(
    db: Session,
    empresa_id: int,
    receita_bruta: float,
    custo_servicos: float,
    aliquota_iss: float,
    lp_engine_override: Optional[str] = None,
) -> dict:
    """
    Dispatch para motor legado ou novo de Lucro Presumido.

    Se motor novo: infere bases via CNAE do EmpresaFiscal, calcula com motor
    corrigido, e adapta resultado para formato dict legado.
    """
    if not _usar_motor_lp_novo(lp_engine_override):
        return calcular_presumido(
            receita_bruta=receita_bruta,
            custo_servicos=custo_servicos,
            aliquota_iss=aliquota_iss,
        )

    # Motor novo — inferir bases via CNAE
    cnae = ""
    fiscal = (
        db.query(models.EmpresaFiscal)
        .filter(models.EmpresaFiscal.empresa_id == empresa_id)
        .first()
    )
    if fiscal:
        cnae = fiscal.cnae or ""

    bases = inferir_bases(cnae)

    if bases.eh_fallback:
        _logger.warning(
            "CNAE '%s' (empresa_id=%d) nao encontrado na tabela de presuncao. "
            "Aplicado fallback conservador 32%%/32%%.", cnae, empresa_id,
        )

    receitas = [
        ReceitaPorAtividade(
            descricao=f"Atividade principal (CNAE {cnae or 'N/A'})",
            valor=Decimal(str(receita_bruta)),
            base_presuncao_irpj=bases.base_irpj,
            base_presuncao_csll=bases.base_csll,
        )
    ]

    resultado = calcular_lucro_presumido(
        receitas=receitas,
        aliquota_iss=Decimal(str(aliquota_iss)),
        trimestral=False,
    )

    # Injetar aviso de fallback na memoria
    if bases.eh_fallback:
        resultado.avisos.append(
            f"CNAE {cnae or '(vazio)'} nao encontrado na tabela de presuncao. "
            f"Aplicado fallback conservador 32%/32%. "
            f"Recomenda-se cadastro manual das bases corretas."
        )

    return _adaptar_resultado_lp(resultado, receita_bruta, custo_servicos)


# -- Helpers ------------------------------------------------------------------

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
    lp_engine_override: Optional[str] = None,
) -> Dict:
    """
    Calcula a carga tributaria no regime atual da empresa e no novo modelo
    pos-Reforma Tributaria, retornando comparativo completo.
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

    # Fallback se nao houver regras cadastradas no banco: usa calculadores oficiais
    if not regras:
        if regime == "simples":
            resultado_fb = calcular_simples(
                receita_mensal=receita_bruta, rbt12=rbt12, anexo=anexo_simples,
            )
        elif regime == "presumido":
            resultado_fb = _calcular_presumido_dispatch(
                db, empresa_id, receita_bruta, custo_servicos, iss,
                lp_engine_override=lp_engine_override,
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

    # Busca parametros da reforma
    params: List[models.ReformaParametros] = (
        db.query(models.ReformaParametros)
        .filter(models.ReformaParametros.vigencia_fim == None)  # noqa: E711
        .all()
    )

    carga_nova = 0.0
    detalhes_nova = []

    # Fallback se nao houver parametros cadastrados: usa calculador oficial da reforma
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
            "nome": "Reforma Tributaria",
            "label": "Reforma Tributaria (IBS + CBS)",
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
                f"Sua carga tributaria tende a "
                f"{'aumentar' if diferenca > 0 else 'diminuir'} "
                f"em {abs(variacao_pct):.1f}% com a Reforma Tributaria."
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
    lp_engine_override: Optional[str] = None,
) -> Dict:
    """
    Calcula e compara a carga tributaria nos 4 cenarios:
      Simples Nacional (todos os 5 anexos), Lucro Presumido, Lucro Real e Reforma.

    Retorna um dict com cada regime e um ranking do menor para o maior custo.
    """
    empresa_fiscal = _get_fiscal(db, empresa_id)
    anexo_atual = (empresa_fiscal.anexo_simples or "III") if empresa_fiscal else "III"
    regime_atual = (empresa_fiscal.regime_tributario or "simples") if empresa_fiscal else "simples"
    iss = aliquota_iss if aliquota_iss is not None else 0.05

    # -- Simples Nacional — todos os 5 anexos ----------------------------------
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

    # -- Lucro Presumido — dispatch legado/novo --------------------------------
    r_pres = _calcular_presumido_dispatch(
        db, empresa_id, receita_bruta, custo_servicos, iss,
        lp_engine_override=lp_engine_override,
    )
    presumido = {
        "label": "Lucro Presumido",
        "total": r_pres["total"],
        "pct_receita": r_pres["pct_receita"],
        "detalhes": r_pres["detalhes"],
        "base_irpj": r_pres["base_irpj"],
        "eh_atual": regime_atual == "presumido",
    }

    # -- Lucro Real ------------------------------------------------------------
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

    # -- Reforma Tributaria ----------------------------------------------------
    r_ref = calcular_reforma(receita_bruta=receita_bruta, custo_servicos=custo_servicos)
    reforma = {
        "label": "Reforma Tributaria (IBS + CBS)",
        "total": r_ref["total"],
        "pct_receita": round((r_ref["total"] / receita_bruta * 100) if receita_bruta > 0 else 0, 2),
        "detalhes": r_ref["detalhes"],
    }

    # -- Ranking do menor para o maior custo -----------------------------------
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
