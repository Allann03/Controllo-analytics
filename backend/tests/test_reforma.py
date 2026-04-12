"""
Testes BLOCO 3H -- Reforma Tributaria (EC 132/2023, LC 214/2025).

50 testes:
  T1-T16:   Ano x cenario basico
  T17-T22:  Regimes especificos
  T23-T30:  Invariantes
  T31-T35:  Planilha referencia
  T36-T40:  Transicao 2026 vs 2033
  T41-T45:  Edge cases
  T46-T50:  Validacoes input
"""

import pytest
from decimal import Decimal

from services.contabil.core import money_fiscal, rate, to_decimal, VERSAO_CALCULO
from services.contabil.reforma import calcular_reforma, OperacaoReforma, ResultadoReforma
from services.contabil.tabelas.reforma_tributaria import get_aliquotas, REGIMES_VALIDOS

_ZERO = Decimal("0")


# -- Helpers -------------------------------------------------------------------

def _op(valor=500000, regime="geral"):
    return OperacaoReforma("Operacao teste", Decimal(str(valor)), regime)


# ============================================================
# T1-T16 -- Ano x cenario
# ============================================================

class TestAnoCenario:

    def test_t1_2026_teste_cbs(self):
        """2026 teste: CBS 0.9%, IBS 0.1%."""
        r = calcular_reforma([_op()], 2026)
        assert r.valor.fase == "teste"
        # CBS debito = 500k * 0.9% = 4500
        assert r.valor.cbs_debito == money_fiscal(Decimal("500000") * Decimal("0.009"))

    def test_t2_2026_teste_ibs(self):
        r = calcular_reforma([_op()], 2026)
        assert r.valor.ibs_debito == money_fiscal(Decimal("500000") * Decimal("0.001"))

    def test_t3_2026_total_baixo(self):
        """2026: carga total ~1% (nao 26.5%)."""
        r = calcular_reforma([_op()], 2026)
        assert r.valor.aliquota_efetiva < rate("0.02")

    def test_t4_2027_cbs_plena(self):
        """2027: CBS plena 8.8%, IBS ainda 0.1%."""
        r = calcular_reforma([_op()], 2027)
        assert r.valor.fase == "cbs_plena"
        assert r.valor.cbs_debito == money_fiscal(Decimal("500000") * Decimal("0.088"))

    def test_t5_2028_referencia(self):
        r = calcular_reforma([_op()], 2028)
        assert r.valor.fase == "referencia"

    def test_t6_2029_transicao(self):
        r = calcular_reforma([_op()], 2029)
        assert "transicao" in r.valor.fase

    def test_t7_2033_pleno(self):
        """2033: regime pleno CBS 8.8% + IBS 17.7%."""
        r = calcular_reforma([_op()], 2033)
        assert r.valor.fase == "pleno"

    def test_t8_2033_aliquota_total(self):
        """2033: ~26.5% total (sem creditos)."""
        r = calcular_reforma([_op()], 2033)
        assert r.valor.aliquota_efetiva > rate("0.25")

    def test_t9_com_creditos_2033(self):
        """Creditos reduzem carga."""
        r_sem = calcular_reforma([_op()], 2033, base_credito=0)
        r_com = calcular_reforma([_op()], 2033, base_credito=200000)
        assert r_com.valor.total_tributos < r_sem.valor.total_tributos

    def test_t10_creditos_maiores_debitos(self):
        """Creditos > debitos: devido = 0."""
        r = calcular_reforma([_op(100000)], 2033, base_credito=500000)
        assert r.valor.cbs_devido == _ZERO
        assert r.valor.ibs_devido == _ZERO

    def test_t11_2030_ibs_crescente(self):
        """IBS cresce entre 2029 e 2033."""
        r29 = calcular_reforma([_op()], 2029)
        r33 = calcular_reforma([_op()], 2033)
        assert r33.valor.ibs_debito > r29.valor.ibs_debito

    def test_t12_2034_usa_pleno(self):
        """Ano > 2033: usa regime pleno."""
        r34 = calcular_reforma([_op()], 2034)
        r33 = calcular_reforma([_op()], 2033)
        assert r34.valor.cbs_aliquota == r33.valor.cbs_aliquota

    def test_t13_carga_crescente_cronograma(self):
        """Carga total cresce de 2026 a 2033."""
        cargas = []
        for ano in [2026, 2027, 2029, 2033]:
            r = calcular_reforma([_op()], ano)
            cargas.append(r.valor.total_tributos)
        for i in range(1, len(cargas)):
            assert cargas[i] >= cargas[i-1]

    def test_t14_split_payment_2026(self):
        r = calcular_reforma([_op()], 2026)
        assert r.valor.split_payment_obrigatorio is True

    def test_t15_aviso_fase_teste(self):
        r = calcular_reforma([_op()], 2026)
        assert any("teste" in a.lower() for a in r.avisos)

    def test_t16_aviso_transicao(self):
        r = calcular_reforma([_op()], 2029)
        assert any("transicao" in a.lower() for a in r.avisos)


# ============================================================
# T17-T22 -- Regimes especificos
# ============================================================

class TestRegimesEspecificos:

    def test_t17_saude_60_reducao(self):
        """Saude: 60% reducao -> fator 0.4."""
        r_geral = calcular_reforma([_op(regime="geral")], 2033)
        r_saude = calcular_reforma([_op(regime="saude")], 2033)
        # CBS saude = CBS geral * 0.4
        assert r_saude.valor.cbs_debito < r_geral.valor.cbs_debito
        ratio = r_saude.valor.cbs_debito / r_geral.valor.cbs_debito
        assert abs(ratio - Decimal("0.4")) < Decimal("0.01")

    def test_t18_educacao_60_reducao(self):
        r_geral = calcular_reforma([_op(regime="geral")], 2033)
        r_edu = calcular_reforma([_op(regime="educacao")], 2033)
        assert r_edu.valor.total_tributos < r_geral.valor.total_tributos

    def test_t19_transporte_publico(self):
        r = calcular_reforma([_op(regime="transporte_publico")], 2033)
        assert r.valor.total_tributos > _ZERO

    def test_t20_agropecuaria(self):
        r = calcular_reforma([_op(regime="agropecuaria")], 2033)
        assert r.valor.total_tributos > _ZERO

    def test_t21_combustiveis_placeholder(self):
        """Combustiveis: fator 1.0 (placeholder, regime monofasico real fica para 3K)."""
        r_geral = calcular_reforma([_op(regime="geral")], 2033)
        r_comb = calcular_reforma([_op(regime="combustiveis")], 2033)
        assert r_comb.valor.total_tributos == r_geral.valor.total_tributos

    def test_t22_misto_geral_saude(self):
        """Operacoes mistas: 300k geral + 200k saude."""
        ops = [_op(300000, "geral"), _op(200000, "saude")]
        r = calcular_reforma(ops, 2033)
        assert r.valor.receita_total == money_fiscal(500000)
        # Carga deve estar entre geral puro e saude puro
        r_geral = calcular_reforma([_op(500000, "geral")], 2033)
        r_saude = calcular_reforma([_op(500000, "saude")], 2033)
        assert r_saude.valor.total_tributos < r.valor.total_tributos < r_geral.valor.total_tributos


# ============================================================
# T23-T30 -- Invariantes
# ============================================================

class TestInvariantes:

    def test_t23_inv_rt1_ano_invalido(self):
        """INV-RT-1: ano < 2026 -> ValueError."""
        with pytest.raises(ValueError, match="2026"):
            calcular_reforma([_op()], 2025)

    def test_t24_inv_rt1_ano_valido(self):
        """Ano 2026 aceito sem erro."""
        r = calcular_reforma([_op()], 2026)
        assert isinstance(r.valor, ResultadoReforma)

    def test_t25_inv_rt2_aliquota_do_ano(self):
        """Aliquota CBS corresponde a tabela do ano."""
        tab = get_aliquotas(2026)
        r = calcular_reforma([_op()], 2026)
        assert r.valor.cbs_aliquota == tab["cbs"]

    def test_t26_inv_rt3_total(self):
        """Total = CBS + IBS + IS."""
        r = calcular_reforma([_op()], 2033, incluir_is=True, aliquota_is="0.05")
        soma = r.valor.cbs_devido + r.valor.ibs_devido + r.valor.is_valor
        assert abs(r.valor.total_tributos - soma) <= money_fiscal("0.01")

    def test_t27_inv_rt4_regime_saude(self):
        """Regime saude aplica fator 0.4."""
        r = calcular_reforma([_op(regime="saude")], 2033)
        tab = get_aliquotas(2033)
        expected_cbs = money_fiscal(Decimal("500000") * rate(tab["cbs"] * Decimal("0.4")))
        assert abs(r.valor.cbs_debito - expected_cbs) <= money_fiscal("0.01")

    def test_t28_inv_rt5_creditos(self):
        """Credito CBS = base * aliquota."""
        r = calcular_reforma([_op()], 2033, base_credito=100000)
        assert r.valor.cbs_credito > _ZERO

    def test_t29_inv_rt6_devido_nao_negativo(self):
        """Devido nunca negativo."""
        r = calcular_reforma([_op(100000)], 2033, base_credito=1000000)
        assert r.valor.cbs_devido >= _ZERO
        assert r.valor.ibs_devido >= _ZERO

    def test_t30_versao(self):
        r = calcular_reforma([_op()], 2033)
        assert r.memoria.versao == VERSAO_CALCULO


# ============================================================
# T31-T35 -- Planilha referencia
# ============================================================

class TestPlanilhaReferencia:

    def test_t31_servicos_geral_2026(self):
        """Servicos geral 500k, 2026 teste.
        CBS = 500k*0.9% = 4500. IBS = 500k*0.1% = 500. Total = 5000."""
        r = calcular_reforma([_op()], 2026)
        assert r.valor.cbs_devido == money_fiscal(4500)
        assert r.valor.ibs_devido == money_fiscal(500)
        assert r.valor.total_tributos == money_fiscal(5000)

    def test_t32_comercio_2033_sem_credito(self):
        """Comercio geral 500k, 2033 pleno, sem creditos.
        CBS = 500k*8.8% = 44000. IBS = 500k*17.7% = 88500. Total = 132500."""
        r = calcular_reforma([_op()], 2033)
        assert r.valor.cbs_devido == money_fiscal(44000)
        assert r.valor.ibs_devido == money_fiscal(88500)
        assert r.valor.total_tributos == money_fiscal(132500)

    def test_t33_saude_2029(self):
        """Saude 500k, 2029.
        CBS = 500k * 8.8% * 0.4 = 17600. IBS = 500k * 11.0% * 0.4 = 22000."""
        r = calcular_reforma([_op(regime="saude")], 2029)
        assert r.valor.cbs_debito == money_fiscal(17600)
        assert r.valor.ibs_debito == money_fiscal(22000)

    def test_t34_com_creditos_2033(self):
        """Geral 500k, 2033, creditos sobre 200k.
        CBS deb=44000, cred=200k*8.8%=17600, dev=26400.
        IBS deb=88500, cred=200k*17.7%=35400, dev=53100.
        Total = 26400+53100 = 79500."""
        r = calcular_reforma([_op()], 2033, base_credito=200000)
        assert r.valor.cbs_devido == money_fiscal(26400)
        assert r.valor.ibs_devido == money_fiscal(53100)
        assert r.valor.total_tributos == money_fiscal(79500)

    def test_t35_com_is(self):
        """Geral 500k, 2033, IS 5%.
        CBS+IBS = 132500. IS = 500k*5% = 25000. Total = 157500."""
        r = calcular_reforma([_op()], 2033, incluir_is=True, aliquota_is="0.05")
        assert r.valor.is_valor == money_fiscal(25000)
        assert r.valor.total_tributos == money_fiscal(157500)


# ============================================================
# T36-T40 -- Transicao
# ============================================================

class TestTransicao:

    def test_t36_2026_vs_2033(self):
        """2026 carga drasticamente menor que 2033."""
        r26 = calcular_reforma([_op()], 2026)
        r33 = calcular_reforma([_op()], 2033)
        assert r26.valor.total_tributos < r33.valor.total_tributos * Decimal("0.1")

    def test_t37_cbs_constante_pos_2027(self):
        """CBS plena a partir de 2027."""
        r27 = calcular_reforma([_op()], 2027)
        r33 = calcular_reforma([_op()], 2033)
        assert r27.valor.cbs_debito == r33.valor.cbs_debito

    def test_t38_ibs_cresce(self):
        """IBS cresce de 2026 a 2033."""
        r26 = calcular_reforma([_op()], 2026)
        r33 = calcular_reforma([_op()], 2033)
        assert r33.valor.ibs_debito > r26.valor.ibs_debito

    def test_t39_2026_compensavel(self):
        """2026: aviso sobre compensabilidade."""
        r = calcular_reforma([_op()], 2026)
        assert any("compensavel" in a.lower() or "compensaveis" in a.lower() for a in r.avisos)

    def test_t40_2033_sem_aviso_transicao(self):
        """2033 pleno: sem aviso de transicao."""
        r = calcular_reforma([_op()], 2033)
        assert not any("transicao" in a.lower() for a in r.avisos)


# ============================================================
# T41-T45 -- Edge cases
# ============================================================

class TestEdgeCases:

    def test_t41_ano_antes_2026(self):
        with pytest.raises(ValueError, match="2026"):
            calcular_reforma([_op()], 2024)

    def test_t42_receita_zero(self):
        r = calcular_reforma([_op(0)], 2033)
        assert r.valor.total_tributos == _ZERO

    def test_t43_creditos_maiores_debitos(self):
        r = calcular_reforma([_op(10000)], 2033, base_credito=1000000)
        assert r.valor.cbs_devido == _ZERO
        assert r.valor.ibs_devido == _ZERO

    def test_t44_is_incluido(self):
        r = calcular_reforma([_op()], 2033, incluir_is=True, aliquota_is="0.10")
        assert r.valor.is_valor == money_fiscal(50000)

    def test_t45_is_excluido(self):
        r = calcular_reforma([_op()], 2033, incluir_is=False)
        assert r.valor.is_valor == _ZERO


# ============================================================
# T46-T50 -- Validacoes input
# ============================================================

class TestValidacoesInput:

    def test_t46_regime_invalido(self):
        with pytest.raises(ValueError, match="invalido"):
            OperacaoReforma("X", Decimal("100"), "varejo")

    def test_t47_valor_negativo(self):
        with pytest.raises(ValueError, match="negativo"):
            OperacaoReforma("X", Decimal("-100"), "geral")

    def test_t48_descricao_vazia(self):
        with pytest.raises(ValueError, match="descricao"):
            OperacaoReforma("", Decimal("100"), "geral")

    def test_t49_memoria_norma(self):
        r = calcular_reforma([_op()], 2033)
        norma_str = r.memoria.norma.value if hasattr(r.memoria.norma, "value") else str(r.memoria.norma)
        assert "LC 214" in norma_str

    def test_t50_operacoes_vazia(self):
        """Lista vazia de operacoes: total = 0."""
        r = calcular_reforma([], 2033)
        assert r.valor.total_tributos == _ZERO
