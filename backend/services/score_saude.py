"""
Score de Saúde Financeira — nota de 0 a 100 para cada empresa.
Baseado em indicadores reais, sem IA. 100% determinístico.
"""
from decimal import Decimal
from typing import Dict, Any, Optional, List

_ZERO = Decimal('0')


def _to_dec(val) -> Decimal:
    if val is None:
        return _ZERO
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


# Pesos de cada componente (devem somar 100)
PESOS = {
    'margem_liquida': 20,
    'liquidez_corrente': 20,
    'endividamento': 15,
    'tendencia_receita': 15,
    'fluxo_caixa': 15,
    'folha_sobre_receita': 10,
    'margem_bruta': 5,
}


class ScoreSaude:
    """
    Calcula um score de 0 a 100 para a saúde financeira de uma empresa.
    Baseado em indicadores reais, sem IA.
    """

    def calcular(self, dados_atual: Dict[str, Any], historico: Optional[List[Dict]] = None) -> Dict:
        """
        Retorna dict com score, classificação, cor, componentes e resumo.
        """
        componentes = {}

        # Margem Líquida
        ml = _to_dec(dados_atual.get("margem_liquida", 0))
        nota_ml = self._normalizar_margem_liquida(ml)
        componentes["margem_liquida"] = {"valor": float(ml), "nota": nota_ml, "peso": PESOS["margem_liquida"]}

        # Liquidez Corrente
        lc = _to_dec(dados_atual.get("liquidez_corrente") or 0)
        nota_lc = self._normalizar_liquidez(lc)
        componentes["liquidez_corrente"] = {"valor": float(lc), "nota": nota_lc, "peso": PESOS["liquidez_corrente"]}

        # Endividamento
        end = _to_dec(dados_atual.get("endividamento_geral") or 0)
        nota_end = self._normalizar_endividamento(end)
        componentes["endividamento"] = {"valor": float(end), "nota": nota_end, "peso": PESOS["endividamento"]}

        # Tendência de Receita
        receitas_hist = []
        if historico:
            receitas_hist = [m.get("receita_bruta", 0) for m in historico]
        nota_tend = self._normalizar_tendencia_receita(receitas_hist)
        componentes["tendencia_receita"] = {"valor": None, "nota": nota_tend, "peso": PESOS["tendencia_receita"]}

        # Fluxo de Caixa
        entradas = _to_dec(dados_atual.get("entradas_caixa", 0))
        saidas = abs(_to_dec(dados_atual.get("saidas_caixa", 0)))
        nota_fc = self._normalizar_fluxo_caixa(entradas, saidas)
        componentes["fluxo_caixa"] = {"valor": float(entradas - saidas), "nota": nota_fc, "peso": PESOS["fluxo_caixa"]}

        # Folha sobre Receita
        folha = _to_dec(dados_atual.get("folha_pagamento", 0))
        rl = _to_dec(dados_atual.get("receita_liquida", 0))
        pct_folha = float(folha / rl * 100) if rl > 0 else 0
        nota_folha = self._normalizar_folha(Decimal(str(pct_folha)))
        componentes["folha_sobre_receita"] = {"valor": pct_folha, "nota": nota_folha, "peso": PESOS["folha_sobre_receita"]}

        # Margem Bruta
        mb = _to_dec(dados_atual.get("margem_bruta", 0))
        nota_mb = self._normalizar_margem_bruta(mb)
        componentes["margem_bruta"] = {"valor": float(mb), "nota": nota_mb, "peso": PESOS["margem_bruta"]}

        # Calcular score ponderado
        score = sum(
            comp["nota"] * comp["peso"]
            for comp in componentes.values()
        ) / 100

        score = max(0, min(100, round(score)))
        classificacao, cor = self._classificar(score)

        # Resumo
        pontos_atencao = []
        for nome, comp in componentes.items():
            if comp["nota"] < 40:
                pontos_atencao.append(nome.replace("_", " ").title())

        if pontos_atencao:
            resumo = f"Atenção aos indicadores: {', '.join(pontos_atencao)}."
        elif score >= 80:
            resumo = "Empresa com excelente saúde financeira."
        elif score >= 60:
            resumo = "Empresa com boa saúde financeira."
        else:
            resumo = "Situação financeira exige acompanhamento próximo."

        return {
            "score": score,
            "classificacao": classificacao,
            "cor": cor,
            "componentes": componentes,
            "resumo": resumo,
        }

    def _normalizar_margem_liquida(self, valor: Decimal) -> int:
        if valor < 0:
            return 0
        if valor < 5:
            return 30
        if valor < 10:
            return 60
        if valor < 20:
            return 80
        return 100

    def _normalizar_margem_bruta(self, valor: Decimal) -> int:
        if valor < 0:
            return 0
        if valor < 15:
            return 30
        if valor < 30:
            return 60
        if valor < 50:
            return 80
        return 100

    def _normalizar_liquidez(self, valor: Decimal) -> int:
        if valor < Decimal('0.5'):
            return 0
        if valor < 1:
            return 30
        if valor < Decimal('1.5'):
            return 60
        if valor < Decimal('2.5'):
            return 85
        return 100

    def _normalizar_endividamento(self, valor: Decimal) -> int:
        if valor > 80:
            return 0
        if valor > 60:
            return 30
        if valor > 40:
            return 60
        if valor > 20:
            return 80
        return 100

    def _normalizar_tendencia_receita(self, historico: list) -> int:
        if not historico or len(historico) < 2:
            return 60  # sem dados = neutro

        ultimos = historico[-3:] if len(historico) >= 3 else historico
        quedas_consecutivas = 0
        for i in range(1, len(ultimos)):
            if ultimos[i] < ultimos[i - 1]:
                quedas_consecutivas += 1

        if quedas_consecutivas >= 3:
            return 0
        if quedas_consecutivas >= 2:
            return 20
        if quedas_consecutivas >= 1:
            return 60
        return 100

    def _normalizar_fluxo_caixa(self, entradas: Decimal, saidas: Decimal) -> int:
        if entradas <= 0:
            return 0
        razao = saidas / entradas if entradas > 0 else Decimal('999')
        if razao > 1:
            return 10
        if razao > Decimal('0.9'):
            return 40
        if razao > Decimal('0.7'):
            return 70
        return 100

    def _normalizar_folha(self, pct: Decimal) -> int:
        """Folha sobre receita: > 50% = 0, 40-50% = 30, 30-40% = 60, 20-30% = 80, < 20% = 100"""
        if pct > 50:
            return 0
        if pct > 40:
            return 30
        if pct > 30:
            return 60
        if pct > 20:
            return 80
        return 100

    def _classificar(self, score: int) -> tuple:
        if score >= 80:
            return ("Excelente", "#22c55e")
        if score >= 60:
            return ("Bom", "#84cc16")
        if score >= 40:
            return ("Atenção", "#f59e0b")
        if score >= 20:
            return ("Crítico", "#f97316")
        return ("Grave", "#ef4444")
