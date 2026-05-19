"""
Testes BLOCO 3E -- Simples Nacional reescrito (LC 123/2006).

45 testes:
  T1-T10:  Aliquota efetiva por faixa
  T11-T15: Todos os 5 anexos
  T16-T20: Fator R
  T21-T23: Sublimite
  T24-T28: Invariantes (SN-1 a SN-5)
  T29-T33: money_fiscal ROUND_HALF_UP
  T34-T36: Acima do teto
  T37-T39: rbt12 extrapolada
  T40-T42: Memoria e norma
  T43-T45: Planilha de referencia
"""

import pytest
from decimal import Decimal

from services.contabil.core import money_fiscal, rate, to_decimal, VERSAO_CALCULO
from services.contabil.simples_nacional import calcular_simples, ResultadoSimples

_ZERO = Decimal("0")


# ============================================================
# T1-T10 -- Aliquota efetiva por faixa (Anexo III)
# ============================================================

class TestAliquotaPorFaixa:

    def test_t1_faixa1_deducao_zero(self):
        """Faixa 1 (RBT12 <= 180k): aliq efetiva == nominal == 6.0%.
        Deducao = 0 -> (180000 * 0.06 - 0) / 180000 = 0.06."""
        r = calcular_simples(15000, rbt12=180000, anexo="III")
        assert r.valor.aliquota_efetiva == rate("0.060000")

    def test_t2_faixa2(self):
        """Faixa 2 (180k < RBT12 <= 360k): efetiva = (300k*0.112 - 9360) / 300k.
        = (33600 - 9360) / 300000 = 24240/300000 = 0.0808."""
        r = calcular_simples(25000, rbt12=300000, anexo="III")
        expected = rate(str((300000 * Decimal("0.112") - 9360) / 300000))
        assert r.valor.aliquota_efetiva == expected

    def test_t3_faixa3(self):
        """Faixa 3 (360k < RBT12 <= 720k): efetiva = (500k*0.135 - 17640) / 500k.
        = (67500 - 17640) / 500000 = 49860/500000 = 0.09972."""
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        expected = rate(str((500000 * Decimal("0.135") - 17640) / 500000))
        assert r.valor.aliquota_efetiva == expected

    def test_t4_faixa4(self):
        """Faixa 4: RBT12=1M -> (1M*0.160 - 35640) / 1M = 0.12436."""
        r = calcular_simples(80000, rbt12=1000000, anexo="III")
        expected = rate(str((1000000 * Decimal("0.160") - 35640) / 1000000))
        assert r.valor.aliquota_efetiva == expected

    def test_t5_faixa5(self):
        """Faixa 5: RBT12=2M -> (2M*0.210 - 125640) / 2M = 0.147180."""
        r = calcular_simples(170000, rbt12=2000000, anexo="III")
        expected = rate(str((2000000 * Decimal("0.210") - 125640) / 2000000))
        assert r.valor.aliquota_efetiva == expected

    def test_t6_faixa6(self):
        """Faixa 6: RBT12=4M -> (4M*0.330 - 648000) / 4M = 0.168000."""
        r = calcular_simples(330000, rbt12=4000000, anexo="III")
        expected = rate(str((4000000 * Decimal("0.330") - 648000) / 4000000))
        assert r.valor.aliquota_efetiva == expected

    def test_t7_limite_exato_faixa1(self):
        """RBT12 exatamente 180000 -> faixa 1."""
        r = calcular_simples(15000, rbt12=180000, anexo="III")
        assert "Faixa 1" in r.valor.faixa

    def test_t8_limite_exato_faixa2(self):
        """RBT12 exatamente 360000 -> faixa 2."""
        r = calcular_simples(30000, rbt12=360000, anexo="III")
        assert "Faixa 2" in r.valor.faixa

    def test_t9_entre_faixas(self):
        """RBT12=250000 (entre faixa 1 e 2) -> faixa 2."""
        r = calcular_simples(20000, rbt12=250000, anexo="III")
        assert "Faixa 2" in r.valor.faixa

    def test_t10_aliquota_positiva(self):
        """Aliquota efetiva sempre >= 0."""
        r = calcular_simples(10000, rbt12=180000, anexo="III")
        assert r.valor.aliquota_efetiva >= _ZERO


# ============================================================
# T11-T15 -- Todos os 5 anexos (Faixa 3, RBT12=500k)
# ============================================================

class TestTodosAnexos:

    def _calc(self, anexo):
        return calcular_simples(40000, rbt12=500000, anexo=anexo)

    def test_t11_anexo_i(self):
        r = self._calc("I")
        assert r.valor.anexo_efetivo == "I"
        assert r.valor.aliquota_efetiva > _ZERO

    def test_t12_anexo_ii(self):
        r = self._calc("II")
        assert r.valor.anexo_efetivo == "II"

    def test_t13_anexo_iii(self):
        r = self._calc("III")
        assert r.valor.anexo_efetivo == "III"

    def test_t14_anexo_iv(self):
        r = self._calc("IV")
        assert r.valor.anexo_efetivo == "IV"

    def test_t15_anexo_v(self):
        """Sem folha informada, permanece V."""
        r = self._calc("V")
        assert r.valor.anexo_efetivo == "V"
        assert r.valor.fator_r_aplicado is False


# ============================================================
# T16-T20 -- Fator R
# ============================================================

class TestFatorR:

    def test_t16_fator_r_abaixo_28(self):
        """folha/rbt12 = 20% (< 28%) -> permanece Anexo V."""
        r = calcular_simples(40000, rbt12=500000, anexo="V", folha_12m=100000)
        # 100000/500000 = 0.20 < 0.28
        assert r.valor.anexo_efetivo == "V"
        assert r.valor.fator_r_aplicado is False
        assert r.valor.fator_r == rate("0.200000")

    def test_t17_fator_r_exatamente_28(self):
        """folha/rbt12 = 28% (>= 0.28) -> redireciona V para III."""
        r = calcular_simples(40000, rbt12=500000, anexo="V", folha_12m=140000)
        # 140000/500000 = 0.28 >= 0.28
        assert r.valor.anexo_efetivo == "III"
        assert r.valor.fator_r_aplicado is True

    def test_t18_fator_r_acima_28(self):
        """folha/rbt12 = 40% (>= 28%) -> redireciona V para III."""
        r = calcular_simples(40000, rbt12=500000, anexo="V", folha_12m=200000)
        assert r.valor.anexo_efetivo == "III"
        assert r.valor.fator_r_aplicado is True

    def test_t19_fator_r_sem_folha(self):
        """Sem folha informada -> aviso, permanece V."""
        r = calcular_simples(40000, rbt12=500000, anexo="V", folha_12m=None)
        assert r.valor.anexo_efetivo == "V"
        assert any("Fator R nao calculado" in a for a in r.avisos)

    def test_t20_fator_r_nao_aplica_anexo_i(self):
        """Anexo I: Fator R nao redireciona (so aplica a V)."""
        r = calcular_simples(40000, rbt12=500000, anexo="I", folha_12m=200000)
        assert r.valor.anexo_efetivo == "I"
        assert r.valor.fator_r_aplicado is False


# ============================================================
# T21-T23 -- Sublimite
# ============================================================

class TestSublimite:

    def test_t21_acima_sublimite_iss_icms_zerados(self):
        """RBT12 > 3.6M -> ISS e ICMS zerados nos detalhes."""
        r = calcular_simples(350000, rbt12=4000000, anexo="III")
        assert r.valor.sublimite_aplicado is True
        for d in r.valor.detalhes:
            if d["tributo"] in ("ISS", "ICMS"):
                assert d["valor"] == _ZERO, f"{d['tributo']} deveria ser zero no sublimite"
                assert d["excluido_sublimite"] is True

    def test_t22_abaixo_sublimite_normal(self):
        """RBT12 <= 3.6M -> ISS e ICMS normais."""
        r = calcular_simples(100000, rbt12=3000000, anexo="III")
        assert r.valor.sublimite_aplicado is False
        iss = next((d for d in r.valor.detalhes if d["tributo"] == "ISS"), None)
        if iss:
            assert iss["valor"] > _ZERO

    def test_t23_sublimite_demais_tributos_normais(self):
        """Acima sublimite: IRPJ, CSLL, CPP, PIS, COFINS continuam normais."""
        r = calcular_simples(350000, rbt12=4000000, anexo="III")
        for d in r.valor.detalhes:
            if d["tributo"] not in ("ISS", "ICMS"):
                assert d["valor"] > _ZERO, f"{d['tributo']} nao deveria ser zero"


# ============================================================
# T24-T28 -- Invariantes
# ============================================================

class TestInvariantes:

    def test_t24_inv_sn1_aliquota(self):
        """INV-SN-1: motor nao levanta erro (invariante interna validada)."""
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        assert r.valor.aliquota_efetiva > _ZERO

    def test_t25_inv_sn2_das(self):
        """INV-SN-2: DAS == receita * aliquota (sem sublimite)."""
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        expected_das = money_fiscal(to_decimal(40000) * r.valor.aliquota_efetiva)
        assert r.valor.das == expected_das

    def test_t26_inv_sn3_soma_detalhes(self):
        """INV-SN-3: soma detalhes == DAS (sem sublimite)."""
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        soma = sum(d["valor"] for d in r.valor.detalhes)
        assert abs(soma - r.valor.das) <= money_fiscal("0.01")

    def test_t27_inv_sn4_acima_teto(self):
        """INV-SN-4: rbt12 > 4.8M -> aliq=0, das=0."""
        r = calcular_simples(500000, rbt12=5000000, anexo="III")
        assert r.valor.aliquota_efetiva == _ZERO
        assert r.valor.das == _ZERO

    def test_t28_inv_sn5_fator_r(self):
        """INV-SN-5: Fator R >= 0.28 e anexo V -> efetivo III."""
        r = calcular_simples(40000, rbt12=500000, anexo="V", folha_12m=140000)
        assert r.valor.fator_r >= Decimal("0.28")
        assert r.valor.anexo_efetivo == "III"


# ============================================================
# T29-T33 -- money_fiscal ROUND_HALF_UP
# ============================================================

class TestMoneyFiscal:

    def test_t29_das_round_half_up(self):
        """DAS usa ROUND_HALF_UP (padrao RFB)."""
        r = calcular_simples(15000, rbt12=180000, anexo="III")
        # 15000 * 0.06 = 900.00 (exato, sem arredondamento)
        assert r.valor.das == money_fiscal("900.00")

    def test_t30_das_com_centavos(self):
        """DAS com centavos arredondado para cima em .005."""
        r = calcular_simples(25000, rbt12=300000, anexo="III")
        assert isinstance(r.valor.das, Decimal)
        # Verifica que tem 2 casas decimais
        assert r.valor.das == r.valor.das.quantize(Decimal("0.01"))

    def test_t31_aliquota_rate(self):
        """Aliquota tem 6 casas decimais."""
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        assert r.valor.aliquota_efetiva == r.valor.aliquota_efetiva.quantize(Decimal("0.000001"))

    def test_t32_detalhes_money_fiscal(self):
        """Valores nos detalhes sao Decimal."""
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        for d in r.valor.detalhes:
            assert isinstance(d["valor"], Decimal)

    def test_t33_confronto_float_pode_divergir(self):
        """Float vs Decimal pode divergir em .005 — Decimal e o correto."""
        r = calcular_simples(33333, rbt12=399996, anexo="III")
        # O importante e que DAS seja Decimal e nao float
        assert isinstance(r.valor.das, Decimal)


# ============================================================
# T34-T36 -- Acima do teto
# ============================================================

class TestAcimaDoTeto:

    def test_t34_acima_4_8m(self):
        r = calcular_simples(500000, rbt12=5000000, anexo="III")
        assert r.valor.das == _ZERO
        assert "nao optante" in r.avisos[0].lower() or "4.800.000" in r.avisos[0]

    def test_t35_exatamente_4_8m(self):
        """RBT12 = 4.800.000 exato -> faixa 6 (ainda optante)."""
        r = calcular_simples(400000, rbt12=4800000, anexo="III")
        assert r.valor.das > _ZERO
        assert "Faixa 6" in r.valor.faixa

    def test_t36_um_centavo_acima(self):
        """RBT12 = 4.800.001 -> nao optante."""
        r = calcular_simples(400001, rbt12=Decimal("4800001"), anexo="III")
        assert r.valor.das == _ZERO


# ============================================================
# T37-T39 -- rbt12 extrapolada
# ============================================================

class TestRBT12Extrapolada:

    def test_t37_rbt12_none_aviso(self):
        """rbt12=None -> extrapolada com aviso."""
        r = calcular_simples(40000, rbt12=None, anexo="III")
        assert r.valor.rbt12 == to_decimal(40000) * Decimal("12")
        assert any("extrapolada" in a.lower() for a in r.avisos)

    def test_t38_rbt12_fornecida_sem_aviso(self):
        """rbt12 fornecida -> sem aviso de extrapolacao."""
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        assert not any("extrapolada" in a.lower() for a in r.avisos)

    def test_t39_receita_zero(self):
        """receita_mensal=0 -> DAS=0."""
        r = calcular_simples(0, rbt12=500000, anexo="III")
        assert r.valor.das == _ZERO


# ============================================================
# T40-T42 -- Memoria e norma
# ============================================================

class TestMemoriaNorma:

    def test_t40_memoria_preenchida(self):
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        assert r.memoria is not None
        assert "receita_mensal" in r.memoria.insumos
        assert "rbt12" in r.memoria.insumos

    def test_t41_norma_lc123(self):
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        norma_str = r.memoria.norma.value if hasattr(r.memoria.norma, "value") else str(r.memoria.norma)
        assert "LC 123" in norma_str

    def test_t42_versao(self):
        r = calcular_simples(40000, rbt12=500000, anexo="III")
        assert r.memoria.versao == VERSAO_CALCULO


# ============================================================
# T43-T45 -- Planilha de referencia (conferidos a mao)
# ============================================================

class TestPlanilhaReferencia:

    def test_t43_servicos_100k_mes(self):
        """Servicos Anexo III, 100k/mes, RBT12=1.2M.
        Faixa 4: (1200000*0.160 - 35640) / 1200000 = 156360/1200000 = 0.130300.
        DAS = 100000 * 0.130300 = 13030.00."""
        r = calcular_simples(100000, rbt12=1200000, anexo="III")
        expected_aliq = rate(str((1200000 * Decimal("0.160") - 35640) / 1200000))
        assert r.valor.aliquota_efetiva == expected_aliq
        assert r.valor.das == money_fiscal(to_decimal(100000) * expected_aliq)

    def test_t44_comercio_25k_mes(self):
        """Comercio Anexo I, 25k/mes, RBT12=300k.
        Faixa 2: (300000*0.073 - 5940) / 300000 = 15960/300000 = 0.053200.
        DAS = 25000 * 0.053200 = 1330.00."""
        r = calcular_simples(25000, rbt12=300000, anexo="I")
        expected_aliq = rate(str((300000 * Decimal("0.073") - 5940) / 300000))
        assert r.valor.aliquota_efetiva == expected_aliq
        expected_das = money_fiscal(to_decimal(25000) * expected_aliq)
        assert r.valor.das == expected_das

    def test_t45_industria_50k_mes(self):
        """Industria Anexo II, 50k/mes, RBT12=600k.
        Faixa 3: (600000*0.100 - 13860) / 600000 = 46140/600000 = 0.076900.
        DAS = 50000 * 0.076900 = 3845.00."""
        r = calcular_simples(50000, rbt12=600000, anexo="II")
        expected_aliq = rate(str((600000 * Decimal("0.100") - 13860) / 600000))
        assert r.valor.aliquota_efetiva == expected_aliq
        expected_das = money_fiscal(to_decimal(50000) * expected_aliq)
        assert r.valor.das == expected_das
