"""
Testes do adapter de Lucro Presumido (BLOCO 3F.2 -- Decisao II).

Verifica que _adaptar_resultado_lp() converte ResultadoCalculo do motor novo
no formato dict identico ao esperado pelos callers legados.

10 testes: T-ADP-01 a T-ADP-10.
"""

import pytest
from decimal import Decimal

from services.contabil.lucro_presumido import (
    calcular_lucro_presumido,
    ReceitaPorAtividade,
)
from services.simulacao_tributaria_service import _adaptar_resultado_lp


# -- Helpers ------------------------------------------------------------------

def _resultado_servicos(receita=500_000, iss=0.05):
    """Motor novo para servicos puros (32%/32%)."""
    receitas = [
        ReceitaPorAtividade(
            descricao="Servicos em geral",
            valor=Decimal(str(receita)),
            base_presuncao_irpj=Decimal("0.32"),
            base_presuncao_csll=Decimal("0.32"),
        )
    ]
    return calcular_lucro_presumido(
        receitas=receitas,
        aliquota_iss=Decimal(str(iss)),
    )


def _resultado_comercio(receita=500_000, iss=0.05):
    """Motor novo para comercio (8%/12%)."""
    receitas = [
        ReceitaPorAtividade(
            descricao="Comercio varejista",
            valor=Decimal(str(receita)),
            base_presuncao_irpj=Decimal("0.08"),
            base_presuncao_csll=Decimal("0.12"),
        )
    ]
    return calcular_lucro_presumido(
        receitas=receitas,
        aliquota_iss=Decimal(str(iss)),
    )


def _resultado_sem_iss(receita=500_000):
    """Motor novo sem ISS."""
    receitas = [
        ReceitaPorAtividade(
            descricao="Comercio varejista",
            valor=Decimal(str(receita)),
            base_presuncao_irpj=Decimal("0.08"),
            base_presuncao_csll=Decimal("0.12"),
        )
    ]
    return calcular_lucro_presumido(receitas=receitas, aliquota_iss=None)


def _resultado_multi_atividade():
    """Motor novo com multiplas atividades."""
    receitas = [
        ReceitaPorAtividade(
            descricao="Comercio varejista",
            valor=Decimal("300000"),
            base_presuncao_irpj=Decimal("0.08"),
            base_presuncao_csll=Decimal("0.12"),
        ),
        ReceitaPorAtividade(
            descricao="Servicos de TI",
            valor=Decimal("200000"),
            base_presuncao_irpj=Decimal("0.32"),
            base_presuncao_csll=Decimal("0.32"),
        ),
    ]
    return calcular_lucro_presumido(
        receitas=receitas,
        aliquota_iss=Decimal("0.05"),
    )


# -- Testes -------------------------------------------------------------------

class TestAdapterLP:
    """T-ADP-01 a T-ADP-10: adapter ResultadoCalculo -> dict legado."""

    def test_adp_01_chaves_formato_legado(self):
        """T-ADP-01: adapter retorna dict com todas as chaves do formato legado."""
        resultado = _resultado_servicos()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        chaves_obrigatorias = {
            "regime", "label", "receita_bruta", "custo_servicos",
            "base_irpj", "base_csll", "irpj", "csll", "pis", "cofins",
            "iss", "total", "pct_receita", "detalhes",
        }
        assert chaves_obrigatorias.issubset(d.keys()), f"Faltam chaves: {chaves_obrigatorias - d.keys()}"

    def test_adp_02_total_igual_total_tributos(self):
        """T-ADP-02: total == float(total_tributos)."""
        resultado = _resultado_servicos()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        assert d["total"] == float(resultado.valor.total_tributos)

    def test_adp_03_pct_receita_igual_aliquota_efetiva(self):
        """T-ADP-03: pct_receita == float(aliquota_efetiva) * 100."""
        resultado = _resultado_servicos()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        assert d["pct_receita"] == float(resultado.valor.aliquota_efetiva) * 100

    def test_adp_04_base_irpj_correta(self):
        """T-ADP-04: base_irpj == float(base_calculo_irpj)."""
        resultado = _resultado_comercio()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        assert d["base_irpj"] == float(resultado.valor.base_calculo_irpj)
        # Para comercio: base_irpj = 500000 * 0.08 = 40000
        assert d["base_irpj"] == 40_000.0

    def test_adp_05_detalhes_5_itens_com_iss(self):
        """T-ADP-05: detalhes tem 5 itens (IRPJ, CSLL, PIS, COFINS, ISS) quando ISS > 0."""
        resultado = _resultado_servicos(iss=0.05)
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        assert len(d["detalhes"]) == 5
        tributos = [det["tributo"] for det in d["detalhes"]]
        assert tributos == ["IRPJ", "CSLL", "PIS", "COFINS", "ISS"]

    def test_adp_06_detalhes_campos_presentes(self):
        """T-ADP-06: cada detalhe tem tributo, aliquota_pct, base, valor."""
        resultado = _resultado_servicos()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        for det in d["detalhes"]:
            assert "tributo" in det
            assert "aliquota_pct" in det
            assert "base" in det
            assert "valor" in det

    def test_adp_07_sem_iss_omite_detalhe(self):
        """T-ADP-07: adapter com ISS=0 omite ISS dos detalhes (4 itens)."""
        resultado = _resultado_sem_iss()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        tributos = [det["tributo"] for det in d["detalhes"]]
        assert "ISS" not in tributos
        assert len(d["detalhes"]) == 4

    def test_adp_08_multi_atividade_consolida(self):
        """T-ADP-08: adapter com multiplas atividades consolida corretamente."""
        resultado = _resultado_multi_atividade()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        # Receita total = 300k + 200k = 500k
        assert d["receita_bruta"] == 500_000
        # base_irpj = 300k * 0.08 + 200k * 0.32 = 24000 + 64000 = 88000
        assert d["base_irpj"] == float(resultado.valor.base_calculo_irpj)
        assert d["total"] > 0

    def test_adp_09_regime_e_label(self):
        """T-ADP-09: adapter preserva regime='presumido' e label."""
        resultado = _resultado_servicos()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)
        assert d["regime"] == "presumido"
        assert d["label"] == "Lucro Presumido"

    def test_adp_10_valores_float_nao_decimal(self):
        """T-ADP-10: todos os valores numericos sao float (compatibilidade JSON)."""
        resultado = _resultado_servicos()
        d = _adaptar_resultado_lp(resultado, 500_000, 0)

        assert isinstance(d["total"], float)
        assert isinstance(d["pct_receita"], float)
        assert isinstance(d["base_irpj"], float)
        assert isinstance(d["base_csll"], float)
        assert isinstance(d["irpj"], float)
        assert isinstance(d["csll"], float)
        assert isinstance(d["pis"], float)
        assert isinstance(d["cofins"], float)
        assert isinstance(d["iss"], float)
        for det in d["detalhes"]:
            assert isinstance(det["valor"], float)
            assert isinstance(det["aliquota_pct"], float)
