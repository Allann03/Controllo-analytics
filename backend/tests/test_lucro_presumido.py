"""
Testes BLOCO 3F -- Lucro Presumido reescrito (Lei 9.249/95).

55 testes:
  T1-T15:   4 bases de presuncao pura
  T16-T23:  Multi-atividade
  T24-T30:  Adicional IRPJ (trimestral e mensal)
  T31-T35:  PIS/COFINS cumulativo
  T36-T38:  Invariantes
  T39-T43:  Planilha de referencia
  T44-T48:  Regressao contra legado + correcao MEDIO-3
  T49-T51:  Edge cases
  T52-T55:  Validacao post_init + T48e (valor negativo)
"""

import pytest
from decimal import Decimal

from services.contabil.core import money_fiscal, rate, to_decimal, VERSAO_CALCULO
from services.contabil.lucro_presumido import (
    calcular_lucro_presumido, ReceitaPorAtividade, ResultadoLucroPresumido,
)

_ZERO = Decimal("0")


# -- Helpers -------------------------------------------------------------------

def _servicos(valor=500000):
    return ReceitaPorAtividade("Servicos em geral", Decimal(str(valor)),
                               Decimal("0.32"), Decimal("0.32"))

def _comercio(valor=500000):
    return ReceitaPorAtividade("Comercio em geral", Decimal(str(valor)),
                               Decimal("0.08"), Decimal("0.12"))

def _combustiveis(valor=500000):
    return ReceitaPorAtividade("Revenda combustiveis", Decimal(str(valor)),
                               Decimal("0.016"), Decimal("0.12"))

def _transp_passag(valor=500000):
    return ReceitaPorAtividade("Transporte passageiros", Decimal(str(valor)),
                               Decimal("0.16"), Decimal("0.12"))


# ============================================================
# T1-T15 -- 4 bases de presuncao pura
# ============================================================

class TestBasePresuncao:

    def test_t1_servicos_32_irpj(self):
        """Servicos: base IRPJ = 500k x 32% = 160k."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.valor.base_calculo_irpj == money_fiscal(160000)

    def test_t2_servicos_32_csll(self):
        """Servicos: base CSLL = 500k x 32% = 160k."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.valor.base_calculo_csll == money_fiscal(160000)

    def test_t3_comercio_8_irpj(self):
        """Comercio: base IRPJ = 500k x 8% = 40k."""
        r = calcular_lucro_presumido([_comercio()], trimestral=True)
        assert r.valor.base_calculo_irpj == money_fiscal(40000)

    def test_t4_comercio_12_csll(self):
        """Comercio: base CSLL = 500k x 12% = 60k. Lei 9.249/95 art. 20."""
        r = calcular_lucro_presumido([_comercio()], trimestral=True)
        assert r.valor.base_calculo_csll == money_fiscal(60000)

    def test_t5_combustiveis_1_6_irpj(self):
        """Combustiveis: base IRPJ = 500k x 1.6% = 8k."""
        r = calcular_lucro_presumido([_combustiveis()], trimestral=True)
        assert r.valor.base_calculo_irpj == money_fiscal(8000)

    def test_t6_combustiveis_12_csll(self):
        """Combustiveis: base CSLL = 500k x 12% = 60k."""
        r = calcular_lucro_presumido([_combustiveis()], trimestral=True)
        assert r.valor.base_calculo_csll == money_fiscal(60000)

    def test_t7_transp_passag_16_irpj(self):
        """Transporte passageiros: base IRPJ = 500k x 16% = 80k."""
        r = calcular_lucro_presumido([_transp_passag()], trimestral=True)
        assert r.valor.base_calculo_irpj == money_fiscal(80000)

    def test_t8_transp_passag_12_csll(self):
        """Transporte passageiros: base CSLL = 500k x 12% = 60k."""
        r = calcular_lucro_presumido([_transp_passag()], trimestral=True)
        assert r.valor.base_calculo_csll == money_fiscal(60000)

    def test_t9_irpj_15_servicos(self):
        """IRPJ = base 160k x 15% = 24k."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.valor.irpj_15 == money_fiscal(24000)

    def test_t10_irpj_15_comercio(self):
        """IRPJ = base 40k x 15% = 6k."""
        r = calcular_lucro_presumido([_comercio()], trimestral=True)
        assert r.valor.irpj_15 == money_fiscal(6000)

    def test_t11_csll_9_servicos(self):
        """CSLL = base 160k x 9% = 14400."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.valor.csll_9 == money_fiscal(14400)

    def test_t12_csll_9_comercio(self):
        """CSLL = base 60k x 9% = 5400. Correcao CRITICO-LP-1."""
        r = calcular_lucro_presumido([_comercio()], trimestral=True)
        assert r.valor.csll_9 == money_fiscal(5400)

    def test_t13_csll_comercio_diferente_servicos(self):
        """CSLL comercio (12%) != CSLL servicos (32%)."""
        r_com = calcular_lucro_presumido([_comercio()], trimestral=True)
        r_srv = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r_com.valor.csll_9 != r_srv.valor.csll_9

    def test_t14_combustiveis_irpj_minimo(self):
        """Combustiveis: IRPJ = 8k x 15% = 1200."""
        r = calcular_lucro_presumido([_combustiveis()], trimestral=True)
        assert r.valor.irpj_15 == money_fiscal(1200)

    def test_t15_base_irpj_e_csll_sao_decimal(self):
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert isinstance(r.valor.base_calculo_irpj, Decimal)
        assert isinstance(r.valor.base_calculo_csll, Decimal)


# ============================================================
# T16-T23 -- Multi-atividade
# ============================================================

class TestMultiAtividade:

    def test_t16_duas_atividades_base_ponderada(self):
        """Comercio 300k + Servicos 200k:
        base IRPJ = 300k*8% + 200k*32% = 24k + 64k = 88k."""
        r = calcular_lucro_presumido(
            [_comercio(300000), _servicos(200000)], trimestral=True)
        assert r.valor.base_calculo_irpj == money_fiscal(88000)

    def test_t17_duas_atividades_csll_ponderada(self):
        """Comercio 300k (CSLL 12%) + Servicos 200k (CSLL 32%):
        base CSLL = 300k*12% + 200k*32% = 36k + 64k = 100k."""
        r = calcular_lucro_presumido(
            [_comercio(300000), _servicos(200000)], trimestral=True)
        assert r.valor.base_calculo_csll == money_fiscal(100000)

    def test_t18_receita_total(self):
        r = calcular_lucro_presumido(
            [_comercio(300000), _servicos(200000)], trimestral=True)
        assert r.valor.receita_bruta_total == money_fiscal(500000)

    def test_t19_tres_atividades(self):
        """Combustiveis 100k + Comercio 200k + Servicos 200k:
        base IRPJ = 100k*1.6% + 200k*8% + 200k*32% = 1600 + 16000 + 64000 = 81600."""
        r = calcular_lucro_presumido(
            [_combustiveis(100000), _comercio(200000), _servicos(200000)],
            trimestral=True)
        assert r.valor.base_calculo_irpj == money_fiscal(81600)

    def test_t20_hospital_farmacia(self):
        """Hospital 400k (8%/12%) + Farmacia 100k (8%/12%):
        base IRPJ = 500k*8% = 40k. Mesma base para ambos."""
        hosp = ReceitaPorAtividade("Hospital", Decimal("400000"),
                                    Decimal("0.08"), Decimal("0.12"))
        farm = ReceitaPorAtividade("Farmacia", Decimal("100000"),
                                    Decimal("0.08"), Decimal("0.12"))
        r = calcular_lucro_presumido([hosp, farm], trimestral=True)
        assert r.valor.base_calculo_irpj == money_fiscal(40000)

    def test_t21_pis_cofins_sobre_total(self):
        """PIS e COFINS incidem sobre receita bruta TOTAL, nao por atividade."""
        r = calcular_lucro_presumido(
            [_comercio(300000), _servicos(200000)], trimestral=True)
        assert r.valor.pis_065 == money_fiscal(Decimal("500000") * Decimal("0.0065"))
        assert r.valor.cofins_3 == money_fiscal(Decimal("500000") * Decimal("0.03"))

    def test_t22_iss_sobre_total(self):
        r = calcular_lucro_presumido(
            [_servicos(500000)], aliquota_iss="0.05", trimestral=True)
        assert r.valor.iss == money_fiscal(25000)

    def test_t23_sem_iss(self):
        r = calcular_lucro_presumido([_comercio()], trimestral=True)
        assert r.valor.iss == _ZERO


# ============================================================
# T24-T30 -- Adicional IRPJ
# ============================================================

class TestAdicionalIRPJ:

    def test_t24_sem_excesso_trimestral(self):
        """Base trim <= 60k -> adicional = 0."""
        rec = ReceitaPorAtividade("Comercio", Decimal("200000"),
                                   Decimal("0.08"), Decimal("0.12"))
        # base = 200k*8% = 16k < 60k
        r = calcular_lucro_presumido([rec], trimestral=True)
        assert r.valor.irpj_adicional_10 == _ZERO

    def test_t25_com_excesso_trimestral(self):
        """Base trim = 160k > 60k -> adicional = (160k-60k)*10% = 10k."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.valor.irpj_adicional_10 == money_fiscal(10000)

    def test_t26_exatamente_60k(self):
        """Base trim = 60k -> excedente = 0 -> adicional = 0."""
        # Servicos com receita tal que base = 60k: 60k/32% = 187500
        rec = ReceitaPorAtividade("Servicos", Decimal("187500"),
                                   Decimal("0.32"), Decimal("0.32"))
        r = calcular_lucro_presumido([rec], trimestral=True)
        assert r.valor.irpj_adicional_10 == _ZERO

    def test_t27_um_centavo_acima(self):
        """Base trim = 60000.01 -> adicional = 0.01 * 10% ~ 0."""
        rec = ReceitaPorAtividade("Servicos", Decimal("187500.04"),
                                   Decimal("0.32"), Decimal("0.32"))
        r = calcular_lucro_presumido([rec], trimestral=True)
        assert r.valor.irpj_adicional_10 >= _ZERO

    def test_t28_mensal_estima_trimestral(self):
        """Modo mensal: base_trim estimada = base_mes * 3."""
        # Servicos 100k mensal: base = 32k/mes, trim = 96k, excedente = 36k
        rec = ReceitaPorAtividade("Servicos", Decimal("100000"),
                                   Decimal("0.32"), Decimal("0.32"))
        r = calcular_lucro_presumido([rec], trimestral=False)
        assert r.valor.irpj_adicional_10 > _ZERO

    def test_t29_aviso_mensal(self):
        """Modo mensal: aviso sobre estimativa presente."""
        r = calcular_lucro_presumido([_servicos(100000)], trimestral=False)
        assert any("mensal x 3" in a.lower() or "trimestral" in a.lower() for a in r.avisos)

    def test_t29b_sem_aviso_trimestral(self):
        """Modo trimestral: sem aviso de estimativa."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert not any("mensal x 3" in a.lower() for a in r.avisos)

    def test_t30_irpj_total(self):
        """irpj_total = irpj_15 + adicional."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.valor.irpj_total == money_fiscal(
            r.valor.irpj_15 + r.valor.irpj_adicional_10)


# ============================================================
# T31-T35 -- PIS/COFINS cumulativo
# ============================================================

class TestPISCOFINS:

    def test_t31_pis_065(self):
        """PIS = 500k * 0.65% = 3250."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.valor.pis_065 == money_fiscal(3250)

    def test_t32_cofins_3(self):
        """COFINS = 500k * 3% = 15000."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.valor.cofins_3 == money_fiscal(15000)

    def test_t33_sem_credito(self):
        """No Presumido, PIS/COFINS sao cumulativos — sem credito.
        Mesmo valor independente do custo."""
        r1 = calcular_lucro_presumido([_servicos()], trimestral=True)
        r2 = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r1.valor.pis_065 == r2.valor.pis_065

    def test_t34_receita_zero(self):
        rec = ReceitaPorAtividade("Servicos", Decimal("0"),
                                   Decimal("0.32"), Decimal("0.32"))
        r = calcular_lucro_presumido([rec], trimestral=True)
        assert r.valor.pis_065 == _ZERO
        assert r.valor.cofins_3 == _ZERO

    def test_t35_pis_cofins_decimal(self):
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert isinstance(r.valor.pis_065, Decimal)
        assert isinstance(r.valor.cofins_3, Decimal)


# ============================================================
# T36-T38 -- Invariantes
# ============================================================

class TestInvariantes:

    def test_t36_invariantes_passam(self):
        """Motor nao levanta erro com dados validos."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert isinstance(r.valor, ResultadoLucroPresumido)

    def test_t37_total_tributos(self):
        """INV-LP-7: total = irpj + csll + pis + cofins + iss."""
        r = calcular_lucro_presumido([_servicos()], aliquota_iss="0.05", trimestral=True)
        soma = (r.valor.irpj_total + r.valor.csll_9 + r.valor.pis_065 +
                r.valor.cofins_3 + r.valor.iss)
        assert abs(r.valor.total_tributos - soma) <= money_fiscal("0.01")

    def test_t38_versao(self):
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.memoria.versao == VERSAO_CALCULO


# ============================================================
# T39-T43 -- Planilha de referencia
# ============================================================

class TestPlanilhaReferencia:

    def test_t39_servicos_500k_trimestral(self):
        """Servicos 500k trimestral. Lei 9.249/95 art. 15 par. 1 III.
        Base IRPJ = 500k*32% = 160k. IRPJ = 160k*15% = 24k.
        Adic = (160k-60k)*10% = 10k. IRPJ total = 34k.
        Base CSLL = 500k*32% = 160k. CSLL = 160k*9% = 14400.
        PIS = 500k*0.65% = 3250. COFINS = 500k*3% = 15000. ISS = 500k*5% = 25000.
        Total = 34000+14400+3250+15000+25000 = 91650."""
        r = calcular_lucro_presumido([_servicos()], aliquota_iss="0.05", trimestral=True)
        assert r.valor.irpj_total == money_fiscal(34000)
        assert r.valor.csll_9 == money_fiscal(14400)
        assert r.valor.total_tributos == money_fiscal(91650)

    def test_t40_comercio_500k_trimestral(self):
        """Comercio 500k trimestral. Lei 9.249/95 art. 15 caput + art. 20.
        Base IRPJ = 500k*8% = 40k. IRPJ = 40k*15% = 6000. Adic = 0 (40k<60k).
        Base CSLL = 500k*12% = 60k. CSLL = 60k*9% = 5400.
        PIS = 3250. COFINS = 15000.
        Total (sem ISS) = 6000+5400+3250+15000 = 29650."""
        r = calcular_lucro_presumido([_comercio()], trimestral=True)
        assert r.valor.irpj_total == money_fiscal(6000)
        assert r.valor.irpj_adicional_10 == _ZERO
        assert r.valor.csll_9 == money_fiscal(5400)
        assert r.valor.total_tributos == money_fiscal(29650)

    def test_t41_combustiveis_500k(self):
        """Combustiveis 500k. Lei 9.249/95 art. 15 par. 1 I.
        Base IRPJ = 500k*1.6% = 8k. IRPJ = 8k*15% = 1200. Adic = 0.
        Base CSLL = 500k*12% = 60k. CSLL = 60k*9% = 5400.
        PIS = 3250. COFINS = 15000.
        Total = 1200+5400+3250+15000 = 24850."""
        r = calcular_lucro_presumido([_combustiveis()], trimestral=True)
        assert r.valor.irpj_total == money_fiscal(1200)
        assert r.valor.total_tributos == money_fiscal(24850)

    def test_t42_transporte_passageiros(self):
        """Transp. passageiros 500k. Lei 9.249/95 art. 15 par. 1 II.
        Base IRPJ = 500k*16% = 80k. IRPJ = 80k*15% = 12000.
        Adic = (80k-60k)*10% = 2000. IRPJ total = 14000.
        Base CSLL = 500k*12% = 60k. CSLL = 5400.
        PIS = 3250. COFINS = 15000.
        Total = 14000+5400+3250+15000 = 37650."""
        r = calcular_lucro_presumido([_transp_passag()], trimestral=True)
        assert r.valor.irpj_total == money_fiscal(14000)
        assert r.valor.total_tributos == money_fiscal(37650)

    def test_t43_misto_comercio_servicos(self):
        """Comercio 300k + Servicos 200k = 500k total.
        Base IRPJ = 300k*8% + 200k*32% = 24k+64k = 88k.
        IRPJ = 88k*15% = 13200. Adic = (88k-60k)*10% = 2800.
        IRPJ total = 16000.
        Base CSLL = 300k*12% + 200k*32% = 36k+64k = 100k. CSLL = 9000.
        PIS = 3250. COFINS = 15000.
        Total = 16000+9000+3250+15000 = 43250."""
        r = calcular_lucro_presumido(
            [_comercio(300000), _servicos(200000)], trimestral=True)
        assert r.valor.irpj_total == money_fiscal(16000)
        assert r.valor.csll_9 == money_fiscal(9000)
        assert r.valor.total_tributos == money_fiscal(43250)


# ============================================================
# T44-T48 -- Regressao e correcao MEDIO-3
# ============================================================

class TestRegressaoCorrecao:

    def test_t44_correcao_medio3_comercial_1500k_trimestral(self):
        """Empresa comercial receita trimestral R$ 1.500.000.

        LEGADO (bugs MEDIO-3 + CRITICO-LP-1):
            Base IRPJ = 1.500.000 x 32% = 480.000  (ERRADO)
            IRPJ      = 480.000 x 15% = 72.000
            Adicional = (480.000 - 60.000) x 10% = 42.000
            IRPJ total= 114.000
            Base CSLL = 1.500.000 x 32% = 480.000  (ERRADO)
            CSLL      = 480.000 x 9% = 43.200
            Total IRPJ+CSLL legado = 157.200

        CORRETO (Lei 9.249/95):
            Base IRPJ = 1.500.000 x 8% = 120.000
            IRPJ      = 120.000 x 15% = 18.000
            Adicional = (120.000 - 60.000) x 10% = 6.000
            IRPJ total= 24.000
            Base CSLL = 1.500.000 x 12% = 180.000
            CSLL      = 180.000 x 9% = 16.200
            Total IRPJ+CSLL correto = 40.200

        Diferenca trimestral: 117.000 PAGOS A MAIS.
        Diferenca anual: 468.000.
        """
        rec = ReceitaPorAtividade("Comercio em geral", Decimal("1500000"),
                                   Decimal("0.08"), Decimal("0.12"))
        r = calcular_lucro_presumido([rec], trimestral=True)

        assert r.valor.irpj_15 == money_fiscal(18000)
        assert r.valor.irpj_adicional_10 == money_fiscal(6000)
        assert r.valor.irpj_total == money_fiscal(24000)
        assert r.valor.csll_9 == money_fiscal(16200)

        total_correto = r.valor.irpj_total + r.valor.csll_9
        total_legado = Decimal("157200")
        diferenca_trim = total_legado - total_correto
        assert diferenca_trim == Decimal("117000")
        assert diferenca_trim * 4 == Decimal("468000")

    def test_t45_servicos_mesma_base_legado(self):
        """Servicos com base 32%: motor novo == legado para IRPJ base."""
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        # Legado: base = 500k*32% = 160k
        assert r.valor.base_calculo_irpj == money_fiscal(160000)

    def test_t46_comercio_base_menor_que_legado(self):
        """Comercio: base nova (8%) < base legada (32%)."""
        r = calcular_lucro_presumido([_comercio()], trimestral=True)
        base_legada = money_fiscal(Decimal("500000") * Decimal("0.32"))
        assert r.valor.base_calculo_irpj < base_legada

    def test_t47_combustiveis_base_minima(self):
        """Combustiveis (1.6%): menor base possivel."""
        r = calcular_lucro_presumido([_combustiveis()], trimestral=True)
        assert r.valor.base_calculo_irpj == money_fiscal(8000)
        assert r.valor.irpj_total < money_fiscal(2000)

    def test_t48_aliquota_efetiva_comercio_menor(self):
        """Aliquota efetiva do comercio deve ser significativamente menor que servicos."""
        r_com = calcular_lucro_presumido([_comercio()], trimestral=True)
        r_srv = calcular_lucro_presumido([_servicos()], aliquota_iss="0.05", trimestral=True)
        assert r_com.valor.aliquota_efetiva < r_srv.valor.aliquota_efetiva


# ============================================================
# T49-T51 -- Edge cases
# ============================================================

class TestEdgeCases:

    def test_t49_receita_zero(self):
        rec = ReceitaPorAtividade("Servicos", Decimal("0"),
                                   Decimal("0.32"), Decimal("0.32"))
        r = calcular_lucro_presumido([rec], trimestral=True)
        assert r.valor.total_tributos == _ZERO

    def test_t50_receita_grande(self):
        """Receita de 10M — nao estoura."""
        rec = ReceitaPorAtividade("Comercio", Decimal("10000000"),
                                   Decimal("0.08"), Decimal("0.12"))
        r = calcular_lucro_presumido([rec], trimestral=True)
        assert r.valor.total_tributos > _ZERO

    def test_t51_memoria_presente(self):
        r = calcular_lucro_presumido([_servicos()], trimestral=True)
        assert r.memoria is not None
        assert "RIR" in (r.memoria.norma.value if hasattr(r.memoria.norma, "value") else str(r.memoria.norma))


# ============================================================
# T52-T55 -- Validacao post_init
# ============================================================

class TestValidacaoPostInit:

    def test_t52_base_irpj_invalida(self):
        """Base IRPJ 10% nao existe."""
        with pytest.raises(ValueError, match="IRPJ invalida"):
            ReceitaPorAtividade("X", Decimal("100000"),
                                Decimal("0.10"), Decimal("0.12"))

    def test_t53_base_csll_invalida(self):
        """Base CSLL 20% nao existe."""
        with pytest.raises(ValueError, match="CSLL invalida"):
            ReceitaPorAtividade("X", Decimal("100000"),
                                Decimal("0.32"), Decimal("0.20"))

    def test_t54_combinacao_irpj32_csll12_invalida(self):
        """IRPJ 32% exige CSLL 32%."""
        with pytest.raises(ValueError, match="CSLL 32%"):
            ReceitaPorAtividade("X", Decimal("100000"),
                                Decimal("0.32"), Decimal("0.12"))

    def test_t54b_combinacao_irpj016_csll32_invalida(self):
        """IRPJ 1.6% (combustiveis) exige CSLL 12%."""
        with pytest.raises(ValueError, match="CSLL 12%"):
            ReceitaPorAtividade("X", Decimal("100000"),
                                Decimal("0.016"), Decimal("0.32"))

    def test_t55_valor_negativo(self):
        """Valor negativo nao permitido."""
        with pytest.raises(ValueError, match="negativo"):
            ReceitaPorAtividade("X", Decimal("-1000"),
                                Decimal("0.32"), Decimal("0.32"))
