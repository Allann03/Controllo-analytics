"""
Serviço de dados financeiros — cálculos de DRE, KPIs, Fluxo de Caixa e Balanço.
Agregações são feitas via queries SQL sempre que possível.
"""
import logging
import os
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func

from data.database import models
from services.insights_engine import avaliar_insights, Insight
from services.motor_narrativa import MotorNarrativa
from services.contabil.dre import calcular_dre as _calcular_dre_motor, DRE as _DREModel
from services.contabil.core import VERSAO_CALCULO

_narrativa_engine = MotorNarrativa()
_logger = logging.getLogger(__name__)

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# -- Feature flag: CONTROLLO_DRE_ENGINE ----------------------------------------
# Fase 1: legado (default). Fase 2: novo. Fase 3: flag removida.
_DRE_ENGINE_RAW = os.environ.get("CONTROLLO_DRE_ENGINE", "").strip().lower()
if _DRE_ENGINE_RAW not in ("novo", "legado", ""):
    _logger.error(
        "CONTROLLO_DRE_ENGINE=%r invalido. Valores aceitos: 'novo', 'legado'. "
        "Usando fallback 'legado'.", _DRE_ENGINE_RAW,
    )
    _DRE_ENGINE_RAW = "legado"
if not _DRE_ENGINE_RAW:
    _logger.warning(
        "CONTROLLO_DRE_ENGINE nao definida. Usando 'legado' como default. "
        "Defina 'novo' para ativar o motor DRE corrigido (BLOCO 3B)."
    )
    _DRE_ENGINE_RAW = "legado"
DRE_ENGINE: str = _DRE_ENGINE_RAW


def _usar_motor_novo(override: Optional[str] = None) -> bool:
    """Decide se usa o motor novo. Override vem do query param (master only)."""
    if override and override.strip().lower() == "novo":
        return True
    return DRE_ENGINE == "novo"


# -- Wrapper ORM -> motor puro -------------------------------------------------

_DRE_CAMPOS = [
    "receita_bruta", "deducoes_receita", "custo_servicos", "despesas_adm",
    "despesas_comerciais", "outras_despesas", "depreciacao_amortizacao",
    "despesas_financeiras", "ir_csll",
]


def _safe(valor):
    """None -> 0 para campos nullable do ORM."""
    return valor if valor is not None else 0


def _calcular_dre_from_lancamento(lanc: models.LancamentoMensal):
    """Converte ORM -> dict -> motor puro. Trata None como 0."""
    dados = {col: _safe(getattr(lanc, col, 0)) for col in _DRE_CAMPOS}
    return _calcular_dre_motor(dados, periodo=f"{lanc.ano}-{lanc.mes:02d}")

_ZERO = Decimal('0')


def _to_dec(valor) -> Decimal:
    """Converte qualquer valor para Decimal de forma segura."""
    if valor is None:
        return _ZERO
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def _dec_to_float(valor) -> float | None:
    """Converte Decimal/float para float; preserva None."""
    if valor is None:
        return None
    return float(valor)


def _pct(num, den) -> float:
    return float(num / den * 100) if den and den != 0 else 0.0


def _variacao(atual, anterior) -> Optional[float]:
    if anterior and anterior != 0:
        return float(((atual - anterior) / abs(anterior)) * 100)
    return None


def _pct_safe(num, den) -> Optional[float]:
    """Retorna percentual ou None se denominador zero (indica dados insuficientes)."""
    return float(num / den * 100) if den and den != 0 else None


def _div_safe(num, den) -> Optional[float]:
    """Divisão segura retornando None em vez de erro."""
    return float(num / den) if den and den != 0 else None


def _lanc_to_metricas(l: models.LancamentoMensal, dre_engine_override: Optional[str] = None) -> Dict[str, Any]:
    """Converte um LancamentoMensal em dicionário de métricas calculadas."""
    # Converte valores do ORM para Decimal para precisão financeira
    rb = _to_dec(l.receita_bruta)
    dr = _to_dec(l.deducoes_receita)
    cs = _to_dec(l.custo_servicos)
    da_adm = _to_dec(l.despesas_adm)
    da_com = _to_dec(l.despesas_comerciais)
    da_fin = _to_dec(l.despesas_financeiras)
    da_out = _to_dec(l.outras_despesas)
    ir = _to_dec(l.ir_csll)

    if _usar_motor_novo(dre_engine_override):
        # Motor novo (BLOCO 3B): DRE calculada pelo motor isolado
        _res = _calcular_dre_from_lancamento(l)
        _dre = _res.valor
        receita_liquida = _dre.receita_liquida
        lucro_bruto = _dre.lucro_bruto
        ebit = _dre.ebit
        ebitda_val = _dre.ebitda
        lair = _dre.lair
        lucro_liquido = _dre.resultado_liquido
        total_despesas_op = da_adm + da_com + da_out + _to_dec(getattr(l, "depreciacao_amortizacao", 0))
        ebit_legado = lucro_bruto - (da_adm + da_com + da_fin + da_out)  # valor antigo (= LAIR)
    else:
        # Motor legado (preservado para fallback)
        receita_liquida = rb - dr
        lucro_bruto = receita_liquida - cs
        total_despesas_op = da_adm + da_com + da_fin + da_out
        ebit = lucro_bruto - total_despesas_op
        lucro_liquido = ebit - ir
        ebitda_val = None  # calculado abaixo
        lair = None
        ebit_legado = None

    cx = _to_dec(l.caixa_equivalentes)
    cr = _to_dec(l.contas_receber)
    est = _to_dec(l.estoques)
    oac = _to_dec(l.outros_ativo_circ)
    forn = _to_dec(l.fornecedores)
    emp_cp = _to_dec(l.emprestimos_cp)
    trib_pg = _to_dec(l.tributos_pagar)
    opc = _to_dec(l.outros_passivo_circ)
    pnc = _to_dec(l.passivo_nao_circulante)
    cap_soc = _to_dec(l.capital_social)
    res = _to_dec(l.reservas)
    luc_ac = _to_dec(l.lucros_acumulados)
    anc = _to_dec(l.ativo_nao_circulante)

    ativo_circulante = cx + cr + est + oac
    passivo_circulante = forn + emp_cp + trib_pg + opc
    passivo_total = passivo_circulante + pnc
    patrimonio_liquido = cap_soc + res + luc_ac
    ativo_total = ativo_circulante + anc
    total_tributos = dr + ir

    sic = _to_dec(l.saldo_inicial_caixa)
    ec = _to_dec(l.entradas_caixa)
    sc = _to_dec(l.saidas_caixa)
    saldo_caixa = sic + ec - sc

    # ── Indicadores Avançados ─────────────────────────────────────
    da = _to_dec(getattr(l, "depreciacao_amortizacao", 0))
    if ebitda_val is not None:
        ebitda = ebitda_val  # motor novo ja calculou
    else:
        ebitda = ebit + da  # motor legado

    # Liquidez
    liquidez_corrente = _div_safe(ativo_circulante, passivo_circulante)
    liquidez_seca     = _div_safe(ativo_circulante - est, passivo_circulante)
    capital_giro_liq  = ativo_circulante - passivo_circulante

    # Rentabilidade
    roe = _pct_safe(lucro_liquido, patrimonio_liquido)
    roa = _pct_safe(lucro_liquido, ativo_total)

    # Endividamento
    endividamento_geral = _pct_safe(passivo_total, ativo_total)

    # Ciclo Financeiro (em dias, base 360)
    pmr = _div_safe(cr, rb)
    pmr = pmr * 360 if pmr is not None else None

    pme = _div_safe(est, cs)
    pme = pme * 360 if pme is not None else None

    # PMP usa custo_servicos como proxy de compras (padrão quando não há campo de compras)
    pmp = _div_safe(forn, cs)
    pmp = pmp * 360 if pmp is not None else None

    ciclo_financeiro = (
        (pmr or 0) + (pme or 0) - (pmp or 0)
        if any(v is not None for v in [pmr, pme, pmp])
        else None
    )

    # Converte tudo para float na saída (JSON não serializa Decimal)
    f = _dec_to_float
    return {
        "id": l.id,
        "ano": l.ano,
        "mes": l.mes,
        "mes_label": MESES_PT[l.mes - 1],
        # DRE
        "receita_bruta": f(rb),
        "deducoes_receita": f(dr),
        "receita_liquida": f(receita_liquida),
        "custo_servicos": f(cs),
        "lucro_bruto": f(lucro_bruto),
        "despesas_adm": f(da_adm),
        "despesas_comerciais": f(da_com),
        "despesas_financeiras": f(da_fin),
        "outras_despesas": f(da_out),
        "total_despesas": f(total_despesas_op),
        "ebit": f(ebit),
        "lair": f(lair) if lair is not None else f(ebit),
        "ir_csll": f(ir),
        "lucro_liquido": f(lucro_liquido),
        "resultado_liquido": f(lucro_liquido),
        **({"ebit_legado": f(ebit_legado),
            "deprecation_warning": "Campo ebit_legado sera removido no proximo release. Use 'lair' para o valor equivalente."}
           if ebit_legado is not None else {}),
        # Indicadores básicos
        "margem_liquida": _pct(lucro_liquido, receita_liquida),
        "margem_bruta": _pct(lucro_bruto, receita_liquida),
        "carga_tributaria": _pct(total_tributos, rb),
        "total_tributos": f(total_tributos),
        # Indicadores avançados — EBITDA
        "depreciacao_amortizacao": f(da),
        "ebitda": f(ebitda),
        "margem_ebitda": _pct_safe(ebitda, receita_liquida),
        # Indicadores avançados — Liquidez e Capital de Giro
        "liquidez_corrente": liquidez_corrente,
        "liquidez_seca": liquidez_seca,
        "capital_giro_liquido": f(capital_giro_liq),
        # Indicadores avançados — Rentabilidade
        "roe": roe,
        "roa": roa,
        # Indicadores avançados — Endividamento
        "endividamento_geral": endividamento_geral,
        # Indicadores avançados — Ciclo Financeiro
        "pmr": pmr,
        "pme": pme,
        "pmp": pmp,
        "ciclo_financeiro": ciclo_financeiro,
        # Fluxo de caixa
        "entradas_caixa": f(ec),
        "saidas_caixa": f(sc),
        "saldo_inicial_caixa": f(sic),
        "saldo_caixa": f(saldo_caixa),
        # Balanço
        "caixa_equivalentes": f(cx),
        "contas_receber": f(cr),
        "estoques": f(est),
        "outros_ativo_circ": f(oac),
        "ativo_circulante": f(ativo_circulante),
        "ativo_nao_circulante": f(anc),
        "ativo_total": f(ativo_total),
        "fornecedores": f(forn),
        "emprestimos_cp": f(emp_cp),
        "tributos_pagar": f(trib_pg),
        "outros_passivo_circ": f(opc),
        "passivo_circulante": f(passivo_circulante),
        "passivo_nao_circulante": f(pnc),
        "passivo_total": f(passivo_total),
        "capital_social": f(cap_soc),
        "reservas": f(res),
        "lucros_acumulados": f(luc_ac),
        "patrimonio_liquido": f(patrimonio_liquido),
        # RH
        "folha_pagamento": f(_to_dec(l.folha_pagamento)),
        # Meta
        "criado_em": l.criado_em,
        "atualizado_em": l.atualizado_em,
    }


def get_historico(
    db: Session,
    empresa_id: int,
    limite: int = 24,
    dre_engine_override: Optional[str] = None,
) -> List[Dict]:
    """Retorna todos os lançamentos da empresa em ordem cronológica."""
    rows = (
        db.query(models.LancamentoMensal)
        .filter(models.LancamentoMensal.empresa_id == empresa_id)
        .order_by(
            models.LancamentoMensal.ano.asc(),
            models.LancamentoMensal.mes.asc(),
        )
        .limit(limite)
        .all()
    )
    return [_lanc_to_metricas(r, dre_engine_override=dre_engine_override) for r in rows]


def get_metricas_mes(
    db: Session,
    empresa_id: int,
    ano: int,
    mes: int,
    dre_engine_override: Optional[str] = None,
) -> Optional[Dict]:
    row = (
        db.query(models.LancamentoMensal)
        .filter(
            models.LancamentoMensal.empresa_id == empresa_id,
            models.LancamentoMensal.ano == ano,
            models.LancamentoMensal.mes == mes,
        )
        .first()
    )
    return _lanc_to_metricas(row, dre_engine_override=dre_engine_override) if row else None


def get_benchmarks(db: Session, cnae: str) -> Optional[Dict]:
    row = (
        db.query(models.SetorBenchmark)
        .filter(models.SetorBenchmark.cnae == cnae)
        .first()
    )
    if not row:
        return None
    return {
        "cnae": row.cnae,
        "descricao": row.descricao,
        "margem_liquida_media": row.margem_liquida_media,
        "carga_tributaria_media": row.carga_tributaria_media,
        "folha_sobre_receita_media": row.folha_sobre_receita_media,
    }


# ─── Dashboard Executivo ──────────────────────────────────────────

def get_dashboard(db: Session, empresa_id: int, ano: int, mes: int) -> Dict:
    atual = get_metricas_mes(db, empresa_id, ano, mes)
    if not atual:
        return {"sem_dados": True}

    anterior_ano = get_metricas_mes(db, empresa_id, ano - 1, mes)
    historico = get_historico(db, empresa_id)

    # Últimos 12 meses (para gráfico de evolução)
    ultimos_12 = historico[-12:]

    return {
        "periodo": f"{MESES_PT[mes - 1]}/{ano}",
        "kpis": {
            "faturamento_liquido": {
                "valor": atual["receita_liquida"],
                "valor_ano_ant": anterior_ano["receita_liquida"] if anterior_ano else None,
                "variacao_pct": _variacao(atual["receita_liquida"], anterior_ano["receita_liquida"]) if anterior_ano else None,
            },
            "lucro_liquido": {
                "valor": atual["lucro_liquido"],
                "valor_ano_ant": anterior_ano["lucro_liquido"] if anterior_ano else None,
                "variacao_pct": _variacao(atual["lucro_liquido"], anterior_ano["lucro_liquido"]) if anterior_ano else None,
            },
            "margem_liquida": {
                "valor": atual["margem_liquida"],
                "valor_ano_ant": anterior_ano["margem_liquida"] if anterior_ano else None,
                "variacao_pct": _variacao(atual["margem_liquida"], anterior_ano["margem_liquida"]) if anterior_ano else None,
            },
            "carga_tributaria": {
                "valor": atual["carga_tributaria"],
                "valor_ano_ant": anterior_ano["carga_tributaria"] if anterior_ano else None,
                "variacao_pct": _variacao(atual["carga_tributaria"], anterior_ano["carga_tributaria"]) if anterior_ano else None,
            },
        },
        "evolucao_12m": [
            {
                "mes": m["mes_label"],
                "receita": m["receita_bruta"],
                "lucro": m["lucro_liquido"],
                "despesas": m["total_despesas"],
            }
            for m in ultimos_12
        ],
        "metricas": atual,
    }


# ─── DRE Visual ──────────────────────────────────────────────────

def get_dre(db: Session, empresa_id: int, ano: int, mes: int,
            dre_engine_override: Optional[str] = None) -> Dict:
    atual = get_metricas_mes(db, empresa_id, ano, mes, dre_engine_override=dre_engine_override)
    if not atual:
        return {"sem_dados": True}

    anterior_mes = mes - 1 if mes > 1 else 12
    anterior_ano = ano if mes > 1 else ano - 1
    anterior = get_metricas_mes(db, empresa_id, anterior_ano, anterior_mes, dre_engine_override=dre_engine_override)

    historico = get_historico(db, empresa_id, dre_engine_override=dre_engine_override)

    empresa_fiscal = (
        db.query(models.EmpresaFiscal)
        .filter(models.EmpresaFiscal.empresa_id == empresa_id)
        .first()
    )
    benchmarks = None
    if empresa_fiscal and empresa_fiscal.cnae:
        benchmarks = get_benchmarks(db, empresa_fiscal.cnae)

    insights = avaliar_insights(atual, anterior, historico, benchmarks)

    if _usar_motor_novo(dre_engine_override):
        # Motor novo: cascata a partir do motor DRE com valores POSITIVOS
        # Convenção: frontend renderiza sinal negativo conforme 'tipo'.
        lanc = (
            db.query(models.LancamentoMensal)
            .filter(models.LancamentoMensal.empresa_id == empresa_id,
                    models.LancamentoMensal.ano == ano,
                    models.LancamentoMensal.mes == mes)
            .first()
        )
        if lanc:
            _anterior_lanc = (
                db.query(models.LancamentoMensal)
                .filter(models.LancamentoMensal.empresa_id == empresa_id,
                        models.LancamentoMensal.ano == anterior_ano,
                        models.LancamentoMensal.mes == anterior_mes)
                .first()
            )
            dados_ant = {col: _safe(getattr(_anterior_lanc, col, 0)) for col in _DRE_CAMPOS} if _anterior_lanc else None
            res = _calcular_dre_motor(
                {col: _safe(getattr(lanc, col, 0)) for col in _DRE_CAMPOS},
                periodo=f"{ano}-{mes:02d}",
                dados_anteriores=dados_ant,
            )
            dre = res.valor
            dre_cascata = [
                {"linha": li.descricao, "codigo": li.codigo, "valor": float(li.valor), "tipo": li.tipo}
                for li in dre.linhas
            ]
            # Adiciona variação % para cada linha da cascata
            if anterior:
                _campo_map_novo = {
                    "1": "receita_bruta", "2": "deducoes_receita", "3": "receita_liquida",
                    "4": "custo_servicos", "5": "lucro_bruto", "6a": "despesas_adm",
                    "6b": "despesas_comerciais", "6c": "outras_despesas",
                    "6d": "depreciacao_amortizacao", "7": "ebit", "8": "ebitda",
                    "9a": "despesas_financeiras", "10": "lair",
                    "11": "ir_csll", "11a": "ir_csll", "11b": "ir_csll",
                    "12": "lucro_liquido",
                }
                for item in dre_cascata:
                    campo = _campo_map_novo.get(item.get("codigo", ""))
                    if campo and campo in anterior:
                        item["variacao_pct"] = _variacao(item["valor"], abs(anterior[campo]))
                    else:
                        item["variacao_pct"] = None

            resultado = {
                "periodo": f"{MESES_PT[mes - 1]}/{ano}",
                "cascata": dre_cascata,
                "convencao_sinais": (
                    "Todos os valores sao positivos. Linhas de tipo 'deducao', 'custo', "
                    "'despesa', 'financeiro' e 'imposto' sao subtrativas na totalizacao. "
                    "Renderizar com sinal negativo na UI."
                ),
                "insights": [i.to_dict() for i in insights],
                "metricas": atual,
                "anterior": anterior,
                "narrativa": _narrativa_engine.gerar_narrativa_completa(atual, anterior, historico, benchmarks),
                "avisos": res.avisos,
                "memoria": res.memoria.to_dict(),
                "engine_version": VERSAO_CALCULO,
            }
            return resultado

    # Motor legado (fallback) — cascata com sinais invertidos (comportamento original)
    dre_cascata = [
        {"linha": "Receita Bruta",          "valor": atual["receita_bruta"],      "tipo": "positivo"},
        {"linha": "(-) Deduções",           "valor": -atual["deducoes_receita"],  "tipo": "negativo"},
        {"linha": "= Receita Líquida",      "valor": atual["receita_liquida"],    "tipo": "resultado"},
        {"linha": "(-) Custos (CMV/CSV)",   "valor": -atual["custo_servicos"],    "tipo": "negativo"},
        {"linha": "= Lucro Bruto",          "valor": atual["lucro_bruto"],        "tipo": "resultado"},
        {"linha": "(-) Despesas Adm.",      "valor": -atual["despesas_adm"],      "tipo": "negativo"},
        {"linha": "(-) Despesas Comerciais","valor": -atual["despesas_comerciais"],"tipo": "negativo"},
        {"linha": "(-) Despesas Financeiras","valor": -atual["despesas_financeiras"],"tipo": "negativo"},
        {"linha": "(-) Outras Despesas",    "valor": -atual["outras_despesas"],   "tipo": "negativo"},
        {"linha": "= Resultado Operacional","valor": atual["ebit"],               "tipo": "resultado"},
        {"linha": "(-) IR / CSLL",          "valor": -atual["ir_csll"],           "tipo": "negativo"},
        {"linha": "= Lucro Líquido",        "valor": atual["lucro_liquido"],      "tipo": "resultado_final"},
    ]

    if anterior:
        campo_map = {
            "Receita Bruta": "receita_bruta", "(-) Deduções": "deducoes_receita",
            "= Receita Líquida": "receita_liquida", "(-) Custos (CMV/CSV)": "custo_servicos",
            "= Lucro Bruto": "lucro_bruto", "(-) Despesas Adm.": "despesas_adm",
            "(-) Despesas Comerciais": "despesas_comerciais",
            "(-) Despesas Financeiras": "despesas_financeiras",
            "(-) Outras Despesas": "outras_despesas",
            "= Resultado Operacional": "ebit", "(-) IR / CSLL": "ir_csll",
            "= Lucro Líquido": "lucro_liquido",
        }
        for item in dre_cascata:
            campo = campo_map.get(item["linha"])
            if campo and campo in anterior:
                item["variacao_pct"] = _variacao(abs(item["valor"]), abs(anterior[campo]))
            else:
                item["variacao_pct"] = None

    narrativa = _narrativa_engine.gerar_narrativa_completa(atual, anterior, historico, benchmarks)

    return {
        "periodo": f"{MESES_PT[mes - 1]}/{ano}",
        "cascata": dre_cascata,
        "insights": [i.to_dict() for i in insights],
        "metricas": atual,
        "anterior": anterior,
        "narrativa": narrativa,
    }


# ─── Fluxo de Caixa ──────────────────────────────────────────────

def get_fluxo_caixa(db: Session, empresa_id: int) -> Dict:
    historico = get_historico(db, empresa_id)
    if not historico:
        return {"sem_dados": True}

    # Médias para projeção
    n = min(len(historico), 6)
    ultimos = historico[-n:]
    media_entradas = sum(m["entradas_caixa"] for m in ultimos) / n
    media_saidas = sum(m["saidas_caixa"] for m in ultimos) / n

    ultimo = historico[-1]
    saldo_atual = ultimo["saldo_caixa"]

    # Projeção simples: saldo_atual + (media_entradas - media_saidas) * k
    projecoes = []
    for k in range(1, 4):
        projecoes.append({
            "mes_offset": k,
            "saldo_projetado": saldo_atual + (media_entradas - media_saidas) * k,
        })

    saldo_proj_3m = projecoes[-1]["saldo_projetado"]

    # Despesas fixas médias como referência de capital de giro
    media_despesas = sum(m["total_despesas"] for m in ultimos) / n

    alertas = []
    if saldo_proj_3m < 0:
        alertas.append({
            "tipo": "critico",
            "mensagem": f"Projeção indica saldo negativo em 3 meses (R$ {saldo_proj_3m:,.2f}).",
        })
    elif saldo_proj_3m < media_despesas:
        alertas.append({
            "tipo": "atencao",
            "mensagem": f"Saldo projetado (R$ {saldo_proj_3m:,.2f}) é inferior a 1 mês de despesas.",
        })

    return {
        "historico": [
            {
                "mes": f"{m['mes_label']}/{m['ano']}",
                "entradas": m["entradas_caixa"],
                "saidas": m["saidas_caixa"],
                "saldo": m["saldo_caixa"],
            }
            for m in historico
        ],
        "projecoes": projecoes,
        "saldo_atual": saldo_atual,
        "saldo_proj_3m": saldo_proj_3m,
        "media_entradas": media_entradas,
        "media_saidas": media_saidas,
        "alertas": alertas,
    }


# ─── Balanço Patrimonial ─────────────────────────────────────────

def get_balanco(db: Session, empresa_id: int, ano: int, mes: int) -> Dict:
    atual = get_metricas_mes(db, empresa_id, ano, mes)
    if not atual:
        return {"sem_dados": True}

    anterior_mes = mes - 1 if mes > 1 else 12
    anterior_ano = ano if mes > 1 else ano - 1
    anterior = get_metricas_mes(db, empresa_id, anterior_ano, anterior_mes)
    historico = get_historico(db, empresa_id)

    insights = avaliar_insights(atual, anterior, historico)

    liquidez_corrente = (
        atual["ativo_circulante"] / atual["passivo_circulante"]
        if atual["passivo_circulante"] > 0
        else None
    )
    grau_imobilizacao = (
        _pct(atual["ativo_nao_circulante"], atual["ativo_total"])
        if atual["ativo_total"] > 0
        else None
    )

    estrutura = {
        "ativo": {
            "circulante": {
                "total": atual["ativo_circulante"],
                "itens": {
                    "Caixa e Equivalentes": atual["caixa_equivalentes"],
                    "Contas a Receber": atual["contas_receber"],
                    "Estoques": atual["estoques"],
                    "Outros": atual["outros_ativo_circ"],
                },
            },
            "nao_circulante": {
                "total": atual["ativo_nao_circulante"],
                "itens": {"Imobilizado e Investimentos": atual["ativo_nao_circulante"]},
            },
            "total": atual["ativo_total"],
        },
        "passivo": {
            "circulante": {
                "total": atual["passivo_circulante"],
                "itens": {
                    "Fornecedores": atual["fornecedores"],
                    "Empréstimos (CP)": atual["emprestimos_cp"],
                    "Tributos a Pagar": atual["tributos_pagar"],
                    "Outros": atual["outros_passivo_circ"],
                },
            },
            "nao_circulante": {
                "total": atual["passivo_nao_circulante"],
                "itens": {"Empréstimos (LP)": atual["passivo_nao_circulante"]},
            },
            "total": atual["passivo_total"],
        },
        "patrimonio_liquido": {
            "total": atual["patrimonio_liquido"],
            "itens": {
                "Capital Social": atual["capital_social"],
                "Reservas": atual["reservas"],
                "Lucros/Prejuízos Acumulados": atual["lucros_acumulados"],
            },
        },
    }

    return {
        "periodo": f"{MESES_PT[mes - 1]}/{ano}",
        "estrutura": estrutura,
        "indicadores": {
            "liquidez_corrente": liquidez_corrente,
            "grau_imobilizacao": grau_imobilizacao,
            "passivo_pl": (
                atual["passivo_total"] / atual["patrimonio_liquido"]
                if atual["patrimonio_liquido"] > 0
                else None
            ),
        },
        "insights": [i.to_dict() for i in insights],
        "metricas": atual,
    }


# ─── Insights Consolidados ───────────────────────────────────────

def get_todos_insights(db: Session, empresa_id: int) -> Dict:
    historico = get_historico(db, empresa_id)
    if not historico:
        return {"sem_dados": True}

    atual = historico[-1]
    anterior = historico[-2] if len(historico) >= 2 else None

    empresa_fiscal = (
        db.query(models.EmpresaFiscal)
        .filter(models.EmpresaFiscal.empresa_id == empresa_id)
        .first()
    )
    benchmarks = None
    if empresa_fiscal and empresa_fiscal.cnae:
        benchmarks = get_benchmarks(db, empresa_fiscal.cnae)

    # Projeta saldo para o engine de risco de caixa
    n = min(len(historico), 6)
    ultimos = historico[-n:]
    media_entradas = sum(m["entradas_caixa"] for m in ultimos) / n
    media_saidas = sum(m["saidas_caixa"] for m in ultimos) / n
    atual_com_proj = dict(atual)
    atual_com_proj["saldo_projetado_3m"] = (
        atual["saldo_caixa"] + (media_entradas - media_saidas) * 3
    )

    insights = avaliar_insights(atual_com_proj, anterior, historico, benchmarks)

    return {
        "empresa_id": empresa_id,
        "periodo_referencia": f"{atual['mes_label']}/{atual['ano']}",
        "total": len(insights),
        "criticos": sum(1 for i in insights if i.severidade == "critico"),
        "atencao": sum(1 for i in insights if i.severidade == "atencao"),
        "info": sum(1 for i in insights if i.severidade == "info"),
        "insights": [i.to_dict() for i in insights],
    }
