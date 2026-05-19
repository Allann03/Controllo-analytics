"""
Testes BLOCO 3A -- Infraestrutura de Calculo Contabil-Fiscal.

43 testes cobrindo:
  T1-T5:   money() quantizacao ROUND_HALF_EVEN
  T6-T8:   money_fiscal() quantizacao ROUND_HALF_UP
  T9-T13:  rate() e pct()
  T14-T23: to_decimal() aceita tipos validos, rejeita invalidos
  T24-T27: Aritmetica deterministica
  T28-T29: MemoriaCalculo.to_dict() serializacao
  T30-T35: assertir_invariante (passa, tolerancia, levanta, campos, default)
  T36-T40: to_decimal rejeita NaN/Infinity
  T41-T42: MemoriaCalculo __post_init__ conversao
  T43:     MemoriaCalculo.versao == VERSAO_CALCULO
"""

import threading
import pytest
from decimal import Decimal
from datetime import datetime

from services.contabil.core import (
    money,
    money_fiscal,
    rate,
    pct,
    to_decimal,
    MemoriaCalculo,
    ResultadoCalculo,
    NormaContabil,
    IntegridadeContabilError,
    assertir_invariante,
    VERSAO_CALCULO,
)


# ============================================================
# T1-T5 -- money() ROUND_HALF_EVEN
# ============================================================

class TestMoney:

    def test_t1_round_half_even_5_rounds_to_even(self):
        # .455 -> .46 (5 rounds to even=6)
        assert money("100.455") == Decimal("100.46")

    def test_t2_round_half_even_5_rounds_down(self):
        # .445 -> .44 (5 rounds to even=4)
        assert money("100.445") == Decimal("100.44")

    def test_t3_round_half_even_normal(self):
        # .435 -> .44 (normal rounding, 5 rounds to even=4)
        assert money("100.435") == Decimal("100.44")

    def test_t4_zero(self):
        assert money(0) == Decimal("0.00")

    def test_t5_float_input(self):
        assert money(99.99) == Decimal("99.99")


# ============================================================
# T6-T8 -- money_fiscal() ROUND_HALF_UP
# ============================================================

class TestMoneyFiscal:

    def test_t6_round_half_up_5_always_up(self):
        # .455 -> .46 (same as HALF_EVEN here)
        assert money_fiscal("100.455") == Decimal("100.46")

    def test_t7_round_half_up_diverges_from_even(self):
        # .445 -> .45 (HALF_UP rounds up; HALF_EVEN would give .44)
        assert money_fiscal("100.445") == Decimal("100.45")

    def test_t8_normal_rounding(self):
        assert money_fiscal("100.434") == Decimal("100.43")


# ============================================================
# T9-T13 -- rate() e pct()
# ============================================================

class TestRateAndPct:

    def test_t9_rate_basic(self):
        assert rate("0.15") == Decimal("0.150000")

    def test_t10_rate_from_float(self):
        assert rate(0.0065) == Decimal("0.006500")

    def test_t11_rate_six_decimals(self):
        assert rate("0.076543") == Decimal("0.076543")

    def test_t12_pct_basic(self):
        assert pct("15.5") == Decimal("15.500000")

    def test_t13_pct_integer(self):
        assert pct(100) == Decimal("100.000000")


# ============================================================
# T14-T23 -- to_decimal() tipos validos e invalidos
# ============================================================

class TestToDecimal:

    def test_t14_int(self):
        assert to_decimal(42) == Decimal(42)

    def test_t15_float_no_artifact(self):
        # float(0.1) via str -> Decimal("0.1"), sem artefato binario
        assert to_decimal(0.1) == Decimal("0.1")

    def test_t16_string(self):
        assert to_decimal("123.45") == Decimal("123.45")

    def test_t17_decimal_passthrough(self):
        d = Decimal("99")
        assert to_decimal(d) is d

    def test_t18_none_raises(self):
        with pytest.raises(TypeError, match="None"):
            to_decimal(None)

    def test_t19_true_raises(self):
        with pytest.raises(TypeError, match="bool"):
            to_decimal(True)

    def test_t20_false_raises(self):
        with pytest.raises(TypeError, match="bool"):
            to_decimal(False)

    def test_t21_list_raises(self):
        with pytest.raises(TypeError, match="list"):
            to_decimal([])

    def test_t22_dict_raises(self):
        with pytest.raises(TypeError, match="dict"):
            to_decimal({})

    def test_t23_empty_string_raises(self):
        with pytest.raises(TypeError, match="vazia"):
            to_decimal("")


# ============================================================
# T24-T27 -- Aritmetica deterministica
# ============================================================

class TestAritmetica:

    def test_t24_sum_01_02(self):
        assert money("0.1") + money("0.2") == Decimal("0.30")

    def test_t25_subtraction_exact_zero(self):
        result = money("100.00") - money("33.33") - money("33.33") - money("33.34")
        assert result == Decimal("0.00")

    def test_t26_rate_times_money(self):
        assert money(rate("0.15") * money("1000")) == Decimal("150.00")

    def test_t27_compound_expression(self):
        result = money(rate("0.15") * money("1000") + money("500"))
        assert result == Decimal("650.00")


# ============================================================
# T28-T29 -- MemoriaCalculo.to_dict()
# ============================================================

class TestMemoriaCalculo:

    def _make_memoria(self, **kwargs):
        defaults = {
            "insumos": {"receita": Decimal("1000")},
            "formula": "receita * aliquota",
            "norma": NormaContabil.RIR_2018,
            "resultado": Decimal("150.00"),
        }
        defaults.update(kwargs)
        return MemoriaCalculo(**defaults)

    def test_t28_to_dict_types(self):
        d = self._make_memoria().to_dict()
        assert isinstance(d["insumos"]["receita"], str)
        assert isinstance(d["resultado"], str)
        assert isinstance(d["calculado_em"], str)

    def test_t29_norma_serialization(self):
        # NormaContabil enum
        d1 = self._make_memoria(norma=NormaContabil.RIR_2018).to_dict()
        assert d1["norma"] == "RIR/2018"

        # String livre
        d2 = self._make_memoria(norma="IN RFB 2.121/2022").to_dict()
        assert d2["norma"] == "IN RFB 2.121/2022"


# ============================================================
# T30-T35 -- assertir_invariante
# ============================================================

class TestAssertirInvariante:

    def test_t30_igualdade_exata_passa(self):
        assertir_invariante("BP", Decimal("100"), Decimal("100"))

    def test_t31_dentro_tolerancia_passa(self):
        assertir_invariante("BP", Decimal("100"), Decimal("100.004"), Decimal("0.01"))

    def test_t32_acima_tolerancia_levanta(self):
        with pytest.raises(IntegridadeContabilError):
            assertir_invariante("BP", Decimal("100"), Decimal("100.02"), Decimal("0.01"))

    def test_t33_campos_da_excecao(self):
        with pytest.raises(IntegridadeContabilError) as exc_info:
            assertir_invariante("BP", Decimal("100"), Decimal("200"),
                                contexto="teste_campos")
        e = exc_info.value
        assert e.esperado == Decimal("100")
        assert e.obtido == Decimal("200")
        assert e.diferenca == Decimal("100")
        assert e.contexto == "teste_campos"

    def test_t34_tolerancia_zero_exige_igualdade(self):
        with pytest.raises(IntegridadeContabilError):
            assertir_invariante("BP", Decimal("100"), Decimal("100.01"))

    def test_t35_thread_safety_money(self):
        """money() em thread separada deve usar ROUND_HALF_EVEN corretamente."""
        resultados = []

        def worker():
            r = money("100.455")
            resultados.append(r)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert len(resultados) == 1
        assert resultados[0] == Decimal("100.46"), (
            f"money() em thread retornou {resultados[0]}, esperado 100.46 (ROUND_HALF_EVEN)"
        )


# ============================================================
# T36-T40 -- to_decimal rejeita NaN/Infinity
# ============================================================

class TestToDecimalNanInf:

    def test_t36_float_nan(self):
        with pytest.raises(TypeError, match="invalido"):
            to_decimal(float("nan"))

    def test_t37_float_inf(self):
        with pytest.raises(TypeError, match="invalido"):
            to_decimal(float("inf"))

    def test_t38_float_neg_inf(self):
        with pytest.raises(TypeError, match="invalido"):
            to_decimal(float("-inf"))

    def test_t39_string_nan(self):
        with pytest.raises(TypeError, match="nao-finito"):
            to_decimal("nan")

    def test_t40_string_infinity(self):
        with pytest.raises(TypeError, match="nao-finito"):
            to_decimal("Infinity")


# ============================================================
# T41-T43 -- MemoriaCalculo __post_init__ e versao
# ============================================================

class TestMemoriaPostInit:

    def test_t41_float_insumo_converted(self):
        m = MemoriaCalculo(
            insumos={"x": 1.5},
            formula="x",
            norma="teste",
            resultado=Decimal("1.5"),
        )
        assert isinstance(m.insumos["x"], Decimal)
        assert m.insumos["x"] == Decimal("1.5")

    def test_t42_nan_insumo_raises(self):
        with pytest.raises(TypeError):
            MemoriaCalculo(
                insumos={"x": float("nan")},
                formula="x",
                norma="teste",
                resultado=Decimal("0"),
            )

    def test_t43_versao_matches_constant(self):
        m = MemoriaCalculo(
            insumos={"x": Decimal("1")},
            formula="x",
            norma="teste",
            resultado=Decimal("1"),
        )
        assert m.versao == VERSAO_CALCULO
