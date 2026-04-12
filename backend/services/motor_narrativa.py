"""
Motor de Narrativa — gera textos analíticos a partir de dados financeiros.
Usa templates parametrizados + regras de negócio.
Zero IA — 100% determinístico e rastreável.
"""
from decimal import Decimal
from typing import Dict, Any, Optional, List

_ZERO = Decimal('0')

# ── Thresholds configuráveis ─────────────────────────────────────────
THRESHOLD_VARIACAO_SIGNIFICATIVA = Decimal('5')   # 5% = variação relevante
THRESHOLD_MARGEM_CRITICA = Decimal('3')            # < 3% = margem crítica
THRESHOLD_LIQUIDEZ_CRITICA = Decimal('1')          # < 1.0 = liquidez crítica
THRESHOLD_CAIXA_MESES = 3                          # projeção de 3 meses
THRESHOLD_FOLHA_ALTA = Decimal('40')               # > 40% = folha alta
THRESHOLD_ENDIVIDAMENTO_ALTO = Decimal('70')       # > 70% = endividamento alto


def _to_dec(val) -> Decimal:
    if val is None:
        return _ZERO
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _var_pct(atual: Decimal, anterior: Decimal) -> Optional[Decimal]:
    if anterior and anterior != 0:
        return ((atual - anterior) / abs(anterior)) * 100
    return None


# ── Templates ─────────────────────────────────────────────────────────

_TEMPLATES_RECEITA = {
    "crescimento": "A receita líquida foi de R$ {valor:,.2f}, representando um crescimento de {variacao:.1f}% em relação ao mês anterior (R$ {valor_anterior:,.2f}).",
    "queda": "A receita líquida foi de R$ {valor:,.2f}, uma queda de {variacao:.1f}% em relação ao mês anterior (R$ {valor_anterior:,.2f}).",
    "estavel": "A receita líquida manteve-se estável em R$ {valor:,.2f}, com variação de apenas {variacao:.1f}% em relação ao mês anterior.",
    "sem_anterior": "A receita líquida do período foi de R$ {valor:,.2f}.",
}

_TEMPLATES_DESPESAS = {
    "aumento_com_causa": "As despesas operacionais totalizaram R$ {valor:,.2f}, um aumento de {variacao:.1f}%. A principal causa foi o crescimento de {variacao_causa:.1f}% na categoria '{categoria_causa}', que passou de R$ {causa_anterior:,.2f} para R$ {causa_atual:,.2f}.",
    "reducao": "As despesas operacionais totalizaram R$ {valor:,.2f}, uma redução de {variacao:.1f}% em relação ao mês anterior, indicando maior controle de gastos.",
    "estavel": "As despesas operacionais totalizaram R$ {valor:,.2f}, mantendo-se estáveis em relação ao mês anterior.",
    "sem_anterior": "As despesas operacionais do período totalizaram R$ {valor:,.2f}.",
}

_TEMPLATES_MARGENS = {
    "compressao": "A margem líquida caiu de {anterior:.1f}% para {atual:.1f}%, uma compressão de {variacao:.1f} pontos percentuais. {causa}",
    "expansao": "A margem líquida subiu de {anterior:.1f}% para {atual:.1f}%, uma expansão de {variacao:.1f} pontos percentuais, refletindo {causa}.",
    "saudavel": "A margem líquida de {atual:.1f}% encontra-se em patamar saudável para o segmento.",
    "critica": "A margem líquida de {atual:.1f}% está abaixo do mínimo recomendado, exigindo atenção imediata.",
    "sem_anterior": "A margem líquida do período foi de {atual:.1f}%.",
}

_TEMPLATES_CAIXA = {
    "positivo": "O fluxo de caixa operacional foi positivo em R$ {valor:,.2f}, com saldo final de R$ {saldo:,.2f}.",
    "negativo": "O fluxo de caixa operacional foi negativo em R$ {valor:,.2f}. O saldo final de R$ {saldo:,.2f} {projecao}.",
    "projecao_critica": "indica risco de caixa negativo nos próximos {meses} meses se a tendência se mantiver",
    "projecao_ok": "é suficiente para cobrir as operações dos próximos meses",
}

_TEMPLATES_RESUMO = {
    "positivo": "No período analisado, a empresa apresentou desempenho {classificacao} com receita de R$ {receita:,.2f} e lucro líquido de R$ {lucro:,.2f} (margem de {margem:.1f}%). {destaque}",
    "negativo": "No período analisado, a empresa registrou {classificacao} com receita de R$ {receita:,.2f} e {resultado} de R$ {valor_resultado:,.2f}. {destaque}",
}

_TEMPLATES_CONCLUSAO = {
    "saudavel": "Com base nos indicadores analisados, a empresa apresenta situação financeira saudável. Recomenda-se manter o controle sobre {pontos_atencao}.",
    "atencao": "A análise indica pontos de atenção que merecem acompanhamento: {pontos}. Recomenda-se {recomendacao}.",
    "critico": "A situação financeira exige ação imediata. Os principais riscos identificados são: {riscos}. É fundamental {acao}.",
}


class MotorNarrativa:
    """
    Gera textos analíticos a partir de dados financeiros.
    Usa templates parametrizados + regras de negócio.
    Zero IA — 100% determinístico e rastreável.
    """

    def gerar_narrativa_completa(
        self,
        dados_atual: Dict[str, Any],
        dados_anterior: Optional[Dict[str, Any]] = None,
        historico: Optional[List[Dict]] = None,
        benchmarks: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        alertas = []

        resumo_executivo = self._gerar_resumo_executivo(dados_atual, dados_anterior, alertas)
        analise_receita = self._gerar_analise_receita(dados_atual, dados_anterior)
        analise_despesas = self._gerar_analise_despesas(dados_atual, dados_anterior)
        analise_margens = self._gerar_analise_margens(dados_atual, dados_anterior, alertas)
        analise_caixa = self._gerar_analise_caixa(dados_atual, historico, alertas)
        analise_endividamento = self._gerar_analise_endividamento(dados_atual, alertas)
        conclusao = self._gerar_conclusao(dados_atual, alertas)

        return {
            "resumo_executivo": resumo_executivo,
            "analise_receita": analise_receita,
            "analise_despesas": analise_despesas,
            "analise_margens": analise_margens,
            "analise_caixa": analise_caixa,
            "analise_endividamento": analise_endividamento,
            "conclusao": conclusao,
            "alertas": alertas,
        }

    # ── Receita ──────────────────────────────────────────────────────

    def _gerar_analise_receita(self, atual: Dict, anterior: Optional[Dict]) -> str:
        rl = _to_dec(atual.get("receita_liquida", 0))

        if not anterior:
            return _TEMPLATES_RECEITA["sem_anterior"].format(valor=float(rl))

        rl_ant = _to_dec(anterior.get("receita_liquida", 0))
        var = _var_pct(rl, rl_ant)

        if var is None:
            return _TEMPLATES_RECEITA["sem_anterior"].format(valor=float(rl))

        classificacao = self._classificar_variacao(var)
        return _TEMPLATES_RECEITA[classificacao].format(
            valor=float(rl),
            variacao=float(abs(var)),
            valor_anterior=float(rl_ant),
        )

    # ── Despesas ─────────────────────────────────────────────────────

    def _gerar_analise_despesas(self, atual: Dict, anterior: Optional[Dict]) -> str:
        td = _to_dec(atual.get("total_despesas", 0))

        if not anterior:
            return _TEMPLATES_DESPESAS["sem_anterior"].format(valor=float(td))

        td_ant = _to_dec(anterior.get("total_despesas", 0))
        var = _var_pct(td, td_ant)

        if var is None:
            return _TEMPLATES_DESPESAS["sem_anterior"].format(valor=float(td))

        classificacao = self._classificar_variacao(var)

        if classificacao == "crescimento":
            causa = self._identificar_causa_despesas(atual, anterior)
            if causa:
                return _TEMPLATES_DESPESAS["aumento_com_causa"].format(
                    valor=float(td),
                    variacao=float(abs(var)),
                    variacao_causa=float(abs(causa["variacao"])),
                    categoria_causa=causa["categoria"],
                    causa_anterior=float(causa["valor_anterior"]),
                    causa_atual=float(causa["valor_atual"]),
                )
            return _TEMPLATES_DESPESAS["aumento_com_causa"].format(
                valor=float(td),
                variacao=float(abs(var)),
                variacao_causa=float(abs(var)),
                categoria_causa="despesas gerais",
                causa_anterior=float(td_ant),
                causa_atual=float(td),
            )
        elif classificacao == "queda":
            return _TEMPLATES_DESPESAS["reducao"].format(
                valor=float(td),
                variacao=float(abs(var)),
            )
        else:
            return _TEMPLATES_DESPESAS["estavel"].format(valor=float(td))

    def _identificar_causa_despesas(self, atual: Dict, anterior: Dict) -> Optional[Dict]:
        categorias = [
            ('despesas_adm', 'Despesas Administrativas'),
            ('despesas_comerciais', 'Despesas Comerciais'),
            ('despesas_financeiras', 'Despesas Financeiras'),
            ('outras_despesas', 'Outras Despesas'),
            ('folha_pagamento', 'Folha de Pagamento'),
        ]

        maior_variacao = None
        for campo, nome in categorias:
            val_atual = _to_dec(atual.get(campo, 0))
            val_anterior = _to_dec(anterior.get(campo, 0))
            if val_anterior > 0:
                variacao = ((val_atual - val_anterior) / val_anterior) * 100
                if maior_variacao is None or abs(variacao) > abs(maior_variacao['variacao']):
                    maior_variacao = {
                        'categoria': nome,
                        'campo': campo,
                        'valor_atual': val_atual,
                        'valor_anterior': val_anterior,
                        'variacao': variacao,
                    }

        return maior_variacao

    # ── Margens ──────────────────────────────────────────────────────

    def _gerar_analise_margens(self, atual: Dict, anterior: Optional[Dict], alertas: list) -> str:
        ml = _to_dec(atual.get("margem_liquida", 0))

        if ml < THRESHOLD_MARGEM_CRITICA:
            alertas.append(f"Margem líquida crítica: {float(ml):.1f}% (abaixo de {float(THRESHOLD_MARGEM_CRITICA)}%).")
            if not anterior:
                return _TEMPLATES_MARGENS["critica"].format(atual=float(ml))

        if not anterior:
            return _TEMPLATES_MARGENS["sem_anterior"].format(atual=float(ml))

        ml_ant = _to_dec(anterior.get("margem_liquida", 0))
        diff = ml - ml_ant

        if diff < -THRESHOLD_VARIACAO_SIGNIFICATIVA:
            # Identificar causa da compressão
            causa = self._identificar_causa_margem(atual, anterior)
            return _TEMPLATES_MARGENS["compressao"].format(
                anterior=float(ml_ant),
                atual=float(ml),
                variacao=float(abs(diff)),
                causa=causa,
            )
        elif diff > THRESHOLD_VARIACAO_SIGNIFICATIVA:
            causa = "maior eficiência operacional" if _to_dec(atual.get("total_despesas", 0)) < _to_dec(anterior.get("total_despesas", 0)) else "crescimento de receita"
            return _TEMPLATES_MARGENS["expansao"].format(
                anterior=float(ml_ant),
                atual=float(ml),
                variacao=float(abs(diff)),
                causa=causa,
            )
        elif ml >= 10:
            return _TEMPLATES_MARGENS["saudavel"].format(atual=float(ml))
        elif ml < THRESHOLD_MARGEM_CRITICA:
            return _TEMPLATES_MARGENS["critica"].format(atual=float(ml))
        else:
            return _TEMPLATES_MARGENS["sem_anterior"].format(atual=float(ml))

    def _identificar_causa_margem(self, atual: Dict, anterior: Dict) -> str:
        rl_var = _var_pct(_to_dec(atual.get("receita_liquida", 0)), _to_dec(anterior.get("receita_liquida", 0)))
        td_var = _var_pct(_to_dec(atual.get("total_despesas", 0)), _to_dec(anterior.get("total_despesas", 0)))

        if td_var is not None and td_var > 10:
            causa = self._identificar_causa_despesas(atual, anterior)
            if causa:
                return f"Aumento de {float(abs(causa['variacao'])):.1f}% em {causa['categoria']}."
            return "Aumento generalizado de despesas."
        elif rl_var is not None and rl_var < -5:
            return "Queda de receita no período."
        else:
            return "Combinação de fatores operacionais."

    # ── Caixa ────────────────────────────────────────────────────────

    def _gerar_analise_caixa(self, atual: Dict, historico: Optional[List[Dict]], alertas: list) -> str:
        ec = _to_dec(atual.get("entradas_caixa", 0))
        sc = abs(_to_dec(atual.get("saidas_caixa", 0)))
        saldo = _to_dec(atual.get("saldo_caixa", 0))
        fluxo = ec - sc

        if fluxo >= 0:
            return _TEMPLATES_CAIXA["positivo"].format(valor=float(fluxo), saldo=float(saldo))

        # Projeção
        if historico and len(historico) >= 3:
            ultimos = historico[-3:]
            media_fluxo = sum(
                m.get("entradas_caixa", 0) - abs(m.get("saidas_caixa", 0))
                for m in ultimos
            ) / len(ultimos)

            if media_fluxo < 0 and saldo > 0:
                meses_restantes = int(float(saldo) / abs(media_fluxo))
                if meses_restantes <= THRESHOLD_CAIXA_MESES:
                    projecao = _TEMPLATES_CAIXA["projecao_critica"].format(meses=meses_restantes)
                    alertas.append(f"Risco de caixa: saldo pode zerar em {meses_restantes} meses.")
                else:
                    projecao = _TEMPLATES_CAIXA["projecao_ok"]
            else:
                projecao = _TEMPLATES_CAIXA["projecao_ok"]
        else:
            projecao = _TEMPLATES_CAIXA["projecao_ok"]

        alertas.append(f"Fluxo de caixa negativo: R$ {float(fluxo):,.2f}.")
        return _TEMPLATES_CAIXA["negativo"].format(
            valor=float(abs(fluxo)),
            saldo=float(saldo),
            projecao=projecao,
        )

    # ── Endividamento ────────────────────────────────────────────────

    def _gerar_analise_endividamento(self, atual: Dict, alertas: list) -> str:
        end = _to_dec(atual.get("endividamento_geral") or 0)
        pt = _to_dec(atual.get("passivo_total", 0))
        at = _to_dec(atual.get("ativo_total", 0))

        if end > THRESHOLD_ENDIVIDAMENTO_ALTO:
            alertas.append(f"Endividamento elevado: {float(end):.1f}% do ativo total.")
            return (
                f"O nível de endividamento é preocupante, com passivos representando "
                f"{float(end):.1f}% do ativo total (R$ {float(pt):,.2f} sobre R$ {float(at):,.2f}). "
                f"Recomenda-se renegociação de dívidas e avaliação da estrutura de capital."
            )
        elif end > 40:
            return (
                f"O endividamento geral está em {float(end):.1f}%, dentro de um patamar moderado. "
                f"O passivo total é de R$ {float(pt):,.2f} contra um ativo de R$ {float(at):,.2f}."
            )
        elif at > 0:
            return (
                f"O endividamento geral de {float(end):.1f}% indica uma estrutura de capital saudável, "
                f"com boa proporção entre capital próprio e de terceiros."
            )
        else:
            return "Dados insuficientes para análise de endividamento."

    # ── Resumo Executivo ─────────────────────────────────────────────

    def _gerar_resumo_executivo(self, atual: Dict, anterior: Optional[Dict], alertas: list) -> str:
        rl = _to_dec(atual.get("receita_liquida", 0))
        ll = _to_dec(atual.get("lucro_liquido", 0))
        ml = _to_dec(atual.get("margem_liquida", 0))

        # Destaque
        destaque = ""
        if anterior:
            rl_ant = _to_dec(anterior.get("receita_liquida", 0))
            var = _var_pct(rl, rl_ant)
            if var is not None and var > THRESHOLD_VARIACAO_SIGNIFICATIVA:
                destaque = f"Destaque para o crescimento de {float(var):.1f}% na receita."
            elif var is not None and var < -THRESHOLD_VARIACAO_SIGNIFICATIVA:
                destaque = f"Atenção para a queda de {float(abs(var)):.1f}% na receita."

        if ll >= 0:
            classificacao = "positivo" if ml > 10 else "moderado"
            return _TEMPLATES_RESUMO["positivo"].format(
                classificacao=classificacao,
                receita=float(rl),
                lucro=float(ll),
                margem=float(ml),
                destaque=destaque,
            )
        else:
            classificacao = "prejuízo operacional"
            alertas.append(f"Empresa registrou prejuízo de R$ {float(abs(ll)):,.2f}.")
            return _TEMPLATES_RESUMO["negativo"].format(
                classificacao=classificacao,
                receita=float(rl),
                resultado="prejuízo",
                valor_resultado=float(abs(ll)),
                destaque=destaque,
            )

    # ── Conclusão ────────────────────────────────────────────────────

    def _gerar_conclusao(self, atual: Dict, alertas: list) -> str:
        ml = _to_dec(atual.get("margem_liquida", 0))
        lc = _to_dec(atual.get("liquidez_corrente") or 0)
        end = _to_dec(atual.get("endividamento_geral") or 0)

        riscos = []
        if ml < THRESHOLD_MARGEM_CRITICA:
            riscos.append("margem líquida crítica")
        if lc < THRESHOLD_LIQUIDEZ_CRITICA:
            riscos.append("liquidez insuficiente")
        if end > THRESHOLD_ENDIVIDAMENTO_ALTO:
            riscos.append("endividamento elevado")

        if not riscos and ml >= 10:
            pontos = []
            if ml < 20:
                pontos.append("margens")
            if end > 40:
                pontos.append("endividamento")
            pontos_str = " e ".join(pontos) if pontos else "as despesas operacionais"
            return _TEMPLATES_CONCLUSAO["saudavel"].format(pontos_atencao=pontos_str)
        elif riscos:
            acoes = []
            if "margem líquida crítica" in riscos:
                acoes.append("revisar a estrutura de custos e despesas")
            if "liquidez insuficiente" in riscos:
                acoes.append("reforçar o capital de giro")
            if "endividamento elevado" in riscos:
                acoes.append("renegociar passivos de longo prazo")

            if len(riscos) >= 2:
                return _TEMPLATES_CONCLUSAO["critico"].format(
                    riscos=", ".join(riscos),
                    acao=" e ".join(acoes),
                )
            else:
                return _TEMPLATES_CONCLUSAO["atencao"].format(
                    pontos=", ".join(riscos),
                    recomendacao=" e ".join(acoes) if acoes else "acompanhamento mensal dos indicadores",
                )
        else:
            return _TEMPLATES_CONCLUSAO["atencao"].format(
                pontos="margem e custos operacionais",
                recomendacao="acompanhamento mensal dos indicadores e controle de despesas",
            )

    # ── Helpers ──────────────────────────────────────────────────────

    def _classificar_variacao(self, variacao_pct: Decimal) -> str:
        if variacao_pct > THRESHOLD_VARIACAO_SIGNIFICATIVA:
            return "crescimento"
        elif variacao_pct < -THRESHOLD_VARIACAO_SIGNIFICATIVA:
            return "queda"
        else:
            return "estavel"
