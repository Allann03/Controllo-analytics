"""
Engine de Insights Automáticos — compartilhado pelos módulos DRE, Insights e Balanço.

Cada regra é uma função de negócio pura (sem IA).
Retorna lista de Insight ordenada por severidade.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Insight:
    id: str
    categoria: str       # tributario | operacional | caixa | patrimonial
    severidade: str      # critico | atencao | info
    titulo: str
    mensagem: str
    valor_atual: Optional[float] = None
    valor_referencia: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "categoria": self.categoria,
            "severidade": self.severidade,
            "titulo": self.titulo,
            "mensagem": self.mensagem,
            "valor_atual": self.valor_atual,
            "valor_referencia": self.valor_referencia,
        }


def _pct(num: float, den: float) -> float:
    return (num / den * 100) if den and den != 0 else 0.0


def avaliar_insights(
    atual: Dict[str, Any],
    anterior: Optional[Dict[str, Any]] = None,
    historico: Optional[List[Dict[str, Any]]] = None,
    benchmarks: Optional[Dict[str, Any]] = None,
) -> List[Insight]:
    """
    Avalia todas as regras e retorna insights ativos, ordenados por severidade.

    atual / anterior  — métricas calculadas do período (saídas de _lanc_to_metricas)
    historico         — lista dos últimos N meses (para detectar tendências)
    benchmarks        — dados do setor { margem_liquida_media, carga_tributaria_media, ... }
    """
    insights: List[Insight] = []

    # ── Regras que exigem período anterior ────────────────────────
    if anterior:

        # R1: Despesas cresceram > 5 %
        desp_a = atual.get("total_despesas", 0)
        desp_p = anterior.get("total_despesas", 0)
        if desp_p > 0 and desp_a > desp_p * 1.05:
            var = _pct(desp_a - desp_p, desp_p)
            insights.append(Insight(
                id="despesas_crescimento",
                categoria="operacional",
                severidade="atencao",
                titulo="Crescimento de Despesas",
                mensagem=f"Despesas cresceram {var:.1f}% em relação ao mês anterior.",
                valor_atual=desp_a,
                valor_referencia=desp_p,
            ))

        # R2: Margem líquida caiu > 5 pontos percentuais
        m_a = atual.get("margem_liquida", 0)
        m_p = anterior.get("margem_liquida", 0)
        if m_p > 0 and (m_p - m_a) > 5:
            insights.append(Insight(
                id="margem_queda",
                categoria="operacional",
                severidade="atencao",
                titulo="Queda de Margem Líquida",
                mensagem=(
                    f"Margem caiu {(m_p - m_a):.1f} pontos percentuais "
                    f"(de {m_p:.1f}% para {m_a:.1f}%)."
                ),
                valor_atual=m_a,
                valor_referencia=m_p,
            ))

        # R3: Custo proporcional à receita cresceu > 10 %
        rl_a = atual.get("receita_liquida", 0)
        rl_p = anterior.get("receita_liquida", 0)
        cs_a = atual.get("custo_servicos", 0)
        cs_p = anterior.get("custo_servicos", 0)
        if rl_a > 0 and rl_p > 0 and cs_p > 0:
            ratio_a = cs_a / rl_a
            ratio_p = cs_p / rl_p
            if ratio_a > ratio_p * 1.10:
                var = _pct(ratio_a - ratio_p, ratio_p)
                insights.append(Insight(
                    id="custo_proporcional",
                    categoria="operacional",
                    severidade="atencao",
                    titulo="Custo Proporcional em Alta",
                    mensagem=f"Custo proporcional à receita aumentou {var:.1f}%.",
                    valor_atual=ratio_a * 100,
                    valor_referencia=ratio_p * 100,
                ))

        # R9: Endividamento crescente > 10 % no trimestre
        pass_a = atual.get("passivo_total", 0)
        pl_a = atual.get("patrimonio_liquido", 0)
        pass_p = anterior.get("passivo_total", 0)
        pl_p = anterior.get("patrimonio_liquido", 0)
        if pl_a > 0 and pl_p > 0 and pass_p > 0:
            rat_a = pass_a / pl_a
            rat_p = pass_p / pl_p
            if rat_a > rat_p * 1.10:
                crescimento = _pct(rat_a - rat_p, rat_p)
                insights.append(Insight(
                    id="endividamento_crescente",
                    categoria="patrimonial",
                    severidade="atencao",
                    titulo="Endividamento em Alta",
                    mensagem=f"Relação Passivo/PL cresceu {crescimento:.1f}% no período.",
                    valor_atual=rat_a,
                    valor_referencia=rat_p,
                ))

        # R10: Estoque cresceu > 20 % e receita não acompanhou
        est_a = atual.get("estoques", 0)
        est_p = anterior.get("estoques", 0)
        rb_a = atual.get("receita_bruta", 0)
        rb_p = anterior.get("receita_bruta", 0)
        if est_p > 0 and rb_p > 0:
            cresc_est = (est_a - est_p) / est_p
            cresc_rec = (rb_a - rb_p) / rb_p
            if cresc_est > 0.20 and cresc_rec < cresc_est:
                insights.append(Insight(
                    id="estoque_parado",
                    categoria="patrimonial",
                    severidade="info",
                    titulo="Possível Estoque Parado",
                    mensagem=(
                        f"Estoque cresceu {cresc_est*100:.1f}% enquanto a receita "
                        f"cresceu {cresc_rec*100:.1f}%."
                    ),
                    valor_atual=est_a,
                    valor_referencia=est_p,
                ))

    # ── Regras baseadas em historico ──────────────────────────────
    if historico and len(historico) >= 3:
        ultimos_3 = historico[-3:]
        receitas = [m.get("receita_bruta", 0) for m in ultimos_3]
        # R4: Receita em queda por 3 meses consecutivos
        if receitas[0] > receitas[1] > receitas[2] and receitas[2] > 0:
            queda = _pct(receitas[0] - receitas[2], receitas[0])
            insights.append(Insight(
                id="receita_tendencia_queda",
                categoria="operacional",
                severidade="critico",
                titulo="Tendência de Queda na Receita",
                mensagem=f"Receita em queda por 3 meses consecutivos (acumulado: -{queda:.1f}%).",
                valor_atual=receitas[2],
                valor_referencia=receitas[0],
            ))

    # ── Regras sobre dados do período atual ───────────────────────

    # R5: Folha de pagamento > 40 % da receita líquida
    folha = atual.get("folha_pagamento", 0)
    rl = atual.get("receita_liquida", 0)
    if rl > 0 and (folha / rl) > 0.40:
        pct_folha = _pct(folha, rl)
        insights.append(Insight(
            id="folha_sobre_receita",
            categoria="operacional",
            severidade="atencao",
            titulo="Folha de Pagamento Elevada",
            mensagem=f"Folha representa {pct_folha:.1f}% da receita líquida (limite: 40%).",
            valor_atual=pct_folha,
            valor_referencia=40.0,
        ))

    # R6: Risco de caixa (saldo projetado negativo)
    saldo_proj = atual.get("saldo_projetado_3m")
    if saldo_proj is not None and saldo_proj < 0:
        insights.append(Insight(
            id="risco_caixa",
            categoria="caixa",
            severidade="critico",
            titulo="Risco de Caixa",
            mensagem=f"Projeção indica saldo negativo em até 3 meses (R$ {saldo_proj:,.2f}).",
            valor_atual=saldo_proj,
            valor_referencia=0,
        ))

    # R7: Liquidez corrente crítica (< 1)
    ativo_circ = atual.get("ativo_circulante", 0)
    pass_circ = atual.get("passivo_circulante", 0)
    if pass_circ > 0:
        liquidez = ativo_circ / pass_circ
        if liquidez < 1.0:
            insights.append(Insight(
                id="liquidez_critica",
                categoria="patrimonial",
                severidade="critico",
                titulo="Liquidez Corrente Crítica",
                mensagem=f"Índice de liquidez corrente abaixo de 1 (atual: {liquidez:.2f}).",
                valor_atual=liquidez,
                valor_referencia=1.0,
            ))
        elif liquidez >= 1.0:
            # Info positiva
            insights.append(Insight(
                id="liquidez_ok",
                categoria="patrimonial",
                severidade="info",
                titulo="Liquidez Corrente Saudável",
                mensagem=f"Índice de liquidez corrente está positivo ({liquidez:.2f}).",
                valor_atual=liquidez,
                valor_referencia=1.0,
            ))

    # R8: Alto grau de imobilização (ativo não circ > 70 % do ativo total)
    ativo_total = atual.get("ativo_total", 0)
    anc = atual.get("ativo_nao_circulante", 0)
    if ativo_total > 0 and (anc / ativo_total) > 0.70:
        pct_imobi = _pct(anc, ativo_total)
        insights.append(Insight(
            id="alto_imobilizacao",
            categoria="patrimonial",
            severidade="atencao",
            titulo="Alto Grau de Imobilização",
            mensagem=f"Ativo não circulante representa {pct_imobi:.1f}% do ativo total.",
            valor_atual=pct_imobi,
            valor_referencia=70.0,
        ))

    # ── Regras compostas (R11–R15) ──────────────────────────────
    if anterior:

        # R11: Crescimento sem lucro — receita crescendo > 10% mas margem caindo > 5 p.p.
        rl_a = atual.get("receita_liquida", 0)
        rl_p = anterior.get("receita_liquida", 0)
        m_a_r11 = atual.get("margem_liquida", 0)
        m_p_r11 = anterior.get("margem_liquida", 0)
        if rl_p > 0 and rl_a > rl_p * 1.10 and (m_p_r11 - m_a_r11) > 5:
            insights.append(Insight(
                id="crescimento_sem_lucro",
                categoria="operacional",
                severidade="atencao",
                titulo="Crescimento sem Rentabilidade",
                mensagem=(
                    f"A receita cresceu {_pct(rl_a - rl_p, rl_p):.1f}%, mas a margem "
                    f"caiu {(m_p_r11 - m_a_r11):.1f} p.p. A empresa está crescendo sem "
                    f"gerar lucro proporcional."
                ),
                valor_atual=m_a_r11,
                valor_referencia=m_p_r11,
            ))

    # R12: Dependência de poucos clientes (alta concentração de receita)
    # Proxy: se uma única categoria de entrada representa > 50% das entradas
    entradas_total_r12 = atual.get("entradas_caixa", 0)
    receita_bruta_r12 = atual.get("receita_bruta", 0)
    if entradas_total_r12 > 0 and receita_bruta_r12 > 0:
        # Verifica se receita bruta é muito concentrada comparada ao total de entradas
        concentracao = receita_bruta_r12 / entradas_total_r12 if entradas_total_r12 > 0 else 0
        if concentracao > 0.8:
            insights.append(Insight(
                id="concentracao_receita",
                categoria="operacional",
                severidade="info",
                titulo="Alta Concentração de Receita",
                mensagem=(
                    f"A receita bruta representa {concentracao*100:.0f}% do total de entradas. "
                    f"Alta concentração em uma única fonte de receita pode representar risco."
                ),
                valor_atual=concentracao * 100,
                valor_referencia=50.0,
            ))

    # R13: Ciclo financeiro deteriorando (PMR subindo E PMP descendo)
    if anterior:
        pmr_a = atual.get("pmr")
        pmr_p = anterior.get("pmr")
        pmp_a = atual.get("pmp")
        pmp_p = anterior.get("pmp")
        if (pmr_a is not None and pmr_p is not None and pmp_a is not None and pmp_p is not None):
            if pmr_a > pmr_p * 1.05 and pmp_a < pmp_p * 0.95:
                insights.append(Insight(
                    id="ciclo_deteriorando",
                    categoria="operacional",
                    severidade="atencao",
                    titulo="Ciclo Financeiro Deteriorando",
                    mensagem=(
                        f"O prazo médio de recebimento subiu de {pmr_p:.0f} para {pmr_a:.0f} dias "
                        f"e o prazo de pagamento caiu de {pmp_p:.0f} para {pmp_a:.0f} dias. "
                        f"A empresa está recebendo mais tarde e pagando mais cedo."
                    ),
                    valor_atual=atual.get("ciclo_financeiro"),
                    valor_referencia=anterior.get("ciclo_financeiro"),
                ))

    # R14: Ponto de equilíbrio em risco — receita < custos fixos por 2+ meses
    if historico and len(historico) >= 2:
        meses_abaixo = 0
        for m in historico[-3:]:
            rl_m = m.get("receita_liquida", 0)
            desp_m = m.get("total_despesas", 0) + m.get("custo_servicos", 0)
            if rl_m > 0 and rl_m < desp_m:
                meses_abaixo += 1
        if meses_abaixo >= 2:
            insights.append(Insight(
                id="ponto_equilibrio_risco",
                categoria="operacional",
                severidade="critico",
                titulo="Ponto de Equilíbrio em Risco",
                mensagem=(
                    f"A receita não cobriu os custos totais em {meses_abaixo} dos últimos "
                    f"meses. A operação está consistentemente abaixo do ponto de equilíbrio."
                ),
                valor_atual=atual.get("receita_liquida"),
                valor_referencia=atual.get("total_despesas", 0) + atual.get("custo_servicos", 0),
            ))

    # R15: Melhora consistente — 3+ meses de margem crescente (insight POSITIVO)
    if historico and len(historico) >= 3:
        margens = [m.get("margem_liquida", 0) for m in historico[-4:]]
        if len(margens) >= 3:
            crescente = all(margens[i] < margens[i + 1] for i in range(len(margens) - 1))
            if crescente and margens[-1] > 0:
                insights.append(Insight(
                    id="melhora_consistente",
                    categoria="operacional",
                    severidade="info",
                    titulo="Melhora Consistente",
                    mensagem=(
                        f"A margem líquida está em tendência de alta nos últimos "
                        f"{len(margens)} meses (de {margens[0]:.1f}% para {margens[-1]:.1f}%). "
                        f"A empresa apresenta melhora consistente."
                    ),
                    valor_atual=margens[-1],
                    valor_referencia=margens[0],
                ))

    # ── Benchmarks do setor ───────────────────────────────────────
    if benchmarks:
        m_empresa = atual.get("margem_liquida", 0)
        m_setor = benchmarks.get("margem_liquida_media", 0)
        if m_setor > 0 and m_empresa < m_setor:
            insights.append(Insight(
                id="margem_abaixo_setor",
                categoria="operacional",
                severidade="atencao",
                titulo="Margem Abaixo da Média do Setor",
                mensagem=(
                    f"Margem líquida da empresa ({m_empresa:.1f}%) está abaixo "
                    f"da média do setor ({m_setor:.1f}%)."
                ),
                valor_atual=m_empresa,
                valor_referencia=m_setor,
            ))

    # Ordena: critico → atencao → info
    ordem = {"critico": 0, "atencao": 1, "info": 2}
    insights.sort(key=lambda x: ordem.get(x.severidade, 99))
    # Remove duplicatas por id
    vistos: set = set()
    unicos = []
    for ins in insights:
        if ins.id not in vistos:
            vistos.add(ins.id)
            unicos.append(ins)
    return unicos
