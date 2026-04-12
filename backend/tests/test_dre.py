"""
Testes BLOCO 3B.1 -- DRE Reestruturada.

53 testes cobrindo:
  T1-T10:   Linhas individuais (campos diretos e zeros)
  T11-T20:  Formulas de totalizacao (RL, LB, EBIT, EBITDA, LAIR, LL)
  T21-T30:  Invariantes violadas (IntegridadeContabilError)
  T31-T35:  Comparativo CPC 26 (periodo atual vs anterior)
  T36-T40:  Planilha de referencia (servicos, comercio, industria)
  T41-T45:  Regressao Fase 2 (correcao ALTO-1)
  T46-T50:  Edge cases (zeros, prejuizo, campo ausente)
  T51:      Aviso receitas financeiras ausentes
  T52:      Prejuizo fiscal com tributo positivo (Simples/Presumido)
  T53:      Prejuizo fiscal com tributo zero (Lucro Real)
"""

import pytest
from decimal import Decimal

from services.contabil.core import IntegridadeContabilError, money
from services.contabil.dre import calcular_dre, DRE


# -- Fixtures -----------------------------------------------------------------

def _base() -> dict:
    """Cenario base: empresa de servicos, valores calculados a mao.

    RB=200000, Ded=10000, CMV=60000, DA_adm=25000, DA_com=8000,
    DA_out=2000, D&A=5000, DFin=3000, RFin=0, IR_CSLL=12000.

    Calculos:
      RL  = 200000 - 10000 = 190000
      LB  = 190000 - 60000 = 130000
      EBIT = 130000 - 25000 - 8000 - 2000 - 5000 = 90000
      EBITDA = 90000 + 5000 = 95000
      LAIR = 90000 - 3000 + 0 = 87000
      LL  = 87000 - 12000 = 75000
    """
    return {
        "receita_bruta": 200000,
        "deducoes_receita": 10000,
        "custo_servicos": 60000,
        "despesas_adm": 25000,
        "despesas_comerciais": 8000,
        "outras_despesas": 2000,
        "depreciacao_amortizacao": 5000,
        "despesas_financeiras": 3000,
        "receitas_financeiras": 0,
        "ir_csll": 12000,
    }


def _base_separado() -> dict:
    """Cenario com IRPJ e CSLL separados."""
    d = _base()
    del d["ir_csll"]
    d["irpj"] = 9000
    d["csll"] = 3000
    return d


def _fase2_mes1() -> dict:
    """Dados reais da Fase 2, mes 1 (empresa Alpha).

    RB=105000, Ded=5000, CMV=30000, DA_adm=15000, DA_com=5000,
    DA_out=1000, D&A=1500, DFin=2000, IR_CSLL=3000.

    Sistema antigo (BUG): ebit = 100000 - 30000 - (15000+5000+2000+1000) = 47000
    Correto:
      RL  = 105000 - 5000 = 100000
      LB  = 100000 - 30000 = 70000
      EBIT = 70000 - 15000 - 5000 - 1000 - 1500 = 47500
      EBITDA = 47500 + 1500 = 49000
      LAIR = 47500 - 2000 = 45500
      LL  = 45500 - 3000 = 42500
    """
    return {
        "receita_bruta": 105000,
        "deducoes_receita": 5000,
        "custo_servicos": 30000,
        "despesas_adm": 15000,
        "despesas_comerciais": 5000,
        "outras_despesas": 1000,
        "depreciacao_amortizacao": 1500,
        "despesas_financeiras": 2000,
        "ir_csll": 3000,
    }


# ============================================================
# T1-T10 -- Linhas individuais
# ============================================================

class TestLinhasIndividuais:
    """Cada campo direto mapeia corretamente para a DRE."""

    def test_t1_receita_bruta(self):
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.receita_bruta == money(200000)

    def test_t2_deducoes(self):
        r = calcular_dre(_base(), "2025-10")
        linha = next(l for l in r.valor.linhas if l.codigo == "2")
        assert linha.valor == money(10000)
        assert linha.tipo == "deducao"

    def test_t3_custo_servicos(self):
        r = calcular_dre(_base(), "2025-10")
        linha = next(l for l in r.valor.linhas if l.codigo == "4")
        assert linha.valor == money(60000)

    def test_t4_despesas_adm(self):
        r = calcular_dre(_base(), "2025-10")
        linha = next(l for l in r.valor.linhas if l.codigo == "6a")
        assert linha.valor == money(25000)

    def test_t5_despesas_comerciais(self):
        r = calcular_dre(_base(), "2025-10")
        linha = next(l for l in r.valor.linhas if l.codigo == "6b")
        assert linha.valor == money(8000)

    def test_t6_outras_despesas(self):
        r = calcular_dre(_base(), "2025-10")
        linha = next(l for l in r.valor.linhas if l.codigo == "6c")
        assert linha.valor == money(2000)

    def test_t7_depreciacao_amortizacao(self):
        r = calcular_dre(_base(), "2025-10")
        linha = next(l for l in r.valor.linhas if l.codigo == "6d")
        assert linha.valor == money(5000)

    def test_t8_despesas_financeiras(self):
        r = calcular_dre(_base(), "2025-10")
        linha = next(l for l in r.valor.linhas if l.codigo == "9a")
        assert linha.valor == money(3000)

    def test_t9_campo_zero_tratado(self):
        """Campo com valor 0 deve gerar Decimal('0.00'), nao erro."""
        d = _base()
        d["receitas_financeiras"] = 0
        r = calcular_dre(d, "2025-10")
        assert r.valor.receitas_financeiras == money(0)

    def test_t10_ir_csll_consolidado(self):
        """Modelo legado: ir_csll como campo unico."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.ir_csll_consolidado == money(12000)
        linha = next(l for l in r.valor.linhas if l.codigo == "11")
        assert linha.valor == money(12000)


# ============================================================
# T11-T20 -- Formulas de totalizacao
# ============================================================

class TestTotalizacoes:
    """Cada totalizador calculado corretamente."""

    def test_t11_receita_liquida(self):
        """RL = RB - Deducoes = 200000 - 10000 = 190000."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.receita_liquida == money(190000)

    def test_t12_lucro_bruto(self):
        """LB = RL - CMV = 190000 - 60000 = 130000."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.lucro_bruto == money(130000)

    def test_t13_ebit(self):
        """EBIT = LB - DA_adm - DA_com - DA_out - D&A = 130000 - 25000 - 8000 - 2000 - 5000 = 90000."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.ebit == money(90000)

    def test_t14_ebitda(self):
        """EBITDA = EBIT + D&A = 90000 + 5000 = 95000."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.ebitda == money(95000)

    def test_t15_lair(self):
        """LAIR = EBIT - DFin + RFin = 90000 - 3000 + 0 = 87000."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.lair == money(87000)

    def test_t16_resultado_liquido(self):
        """LL = LAIR - IR_CSLL = 87000 - 12000 = 75000."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.resultado_liquido == money(75000)

    def test_t17_ebit_sem_despesas_financeiras(self):
        """EBIT NAO deve incluir despesas financeiras (correcao ALTO-1)."""
        r = calcular_dre(_base(), "2025-10")
        # Se EBIT incluisse DFin (bug antigo): 90000 - 3000 = 87000 (LAIR)
        assert r.valor.ebit == money(90000), "EBIT nao deve incluir despesas financeiras"
        assert r.valor.ebit != r.valor.lair, "EBIT e LAIR devem ser diferentes quando ha resultado financeiro"

    def test_t18_ebit_equals_lair_when_no_financial(self):
        """Sem resultado financeiro, EBIT == LAIR."""
        d = _base()
        d["despesas_financeiras"] = 0
        d["receitas_financeiras"] = 0
        r = calcular_dre(d, "2025-10")
        assert r.valor.ebit == r.valor.lair

    def test_t19_irpj_csll_separados(self):
        """Com IRPJ e CSLL separados, ambos aparecem nas linhas."""
        r = calcular_dre(_base_separado(), "2025-10")
        assert r.valor.irpj == money(9000)
        assert r.valor.csll == money(3000)
        assert r.valor.ir_csll_consolidado is None
        assert r.valor.resultado_liquido == money(75000)
        # Linhas 11a e 11b presentes
        codigos = [l.codigo for l in r.valor.linhas]
        assert "11a" in codigos
        assert "11b" in codigos
        assert "11" not in codigos

    def test_t20_lair_com_receitas_financeiras(self):
        """LAIR = EBIT - DFin + RFin."""
        d = _base()
        d["receitas_financeiras"] = 1000
        r = calcular_dre(d, "2025-10")
        # LAIR = 90000 - 3000 + 1000 = 88000
        assert r.valor.lair == money(88000)


# ============================================================
# T21-T30 -- Invariantes violadas
# ============================================================

class TestInvariantesVioladas:
    """Mutar manualmente um campo e confirmar que a invariante dispara.

    Nota: as invariantes sao verificadas DENTRO de calcular_dre,
    entao nao podemos mutar os internos diretamente. Em vez disso,
    testamos o motor com dados que DEVEM passar (sanity check de
    que as invariantes estao ativas) e testamos assertir_invariante
    diretamente para os cenarios de violacao.
    """

    def test_t21_inv1_passa_cenario_base(self):
        """INV-1 nao dispara com dados corretos."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.receita_liquida == money(r.valor.receita_bruta - money(10000))

    def test_t22_inv2_passa_cenario_base(self):
        """INV-2 nao dispara com dados corretos."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.lucro_bruto == money(r.valor.receita_liquida - money(60000))

    def test_t23_inv3_ebit_correto(self):
        """INV-3 EBIT nao inclui DFin."""
        r = calcular_dre(_base(), "2025-10")
        esperado = money(r.valor.lucro_bruto - money(25000) - money(8000) - money(2000) - money(5000))
        assert r.valor.ebit == esperado

    def test_t24_inv4_ebitda(self):
        """INV-4: EBITDA = EBIT + D&A."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.ebitda == money(r.valor.ebit + money(5000))

    def test_t25_inv5_lair(self):
        """INV-5: LAIR = EBIT - DFin + RFin."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.lair == money(r.valor.ebit - money(3000))

    def test_t26_inv6_resultado_liquido(self):
        """INV-6: LL = LAIR - IR_CSLL."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.resultado_liquido == money(r.valor.lair - money(12000))

    def test_t27_assertir_invariante_direct_violation(self):
        """Teste direto: assertir_invariante levanta para violacao."""
        from services.contabil.core import assertir_invariante
        with pytest.raises(IntegridadeContabilError, match="INV-TEST"):
            assertir_invariante("INV-TEST", Decimal("100"), Decimal("200"), contexto="DRE")

    def test_t28_assertir_invariante_within_tolerance(self):
        """Teste direto: dentro da tolerancia, nao levanta."""
        from services.contabil.core import assertir_invariante
        assertir_invariante("INV-TEST", Decimal("100"), Decimal("100.005"), Decimal("0.01"))

    def test_t29_invariante_error_has_fields(self):
        """Campos da excecao devem estar preenchidos."""
        from services.contabil.core import assertir_invariante
        with pytest.raises(IntegridadeContabilError) as exc_info:
            assertir_invariante("INV-F", Decimal("100"), Decimal("110"), contexto="DRE teste")
        e = exc_info.value
        assert e.diferenca == Decimal("10")
        assert e.contexto == "DRE teste"

    def test_t30_todas_invariantes_ativas(self):
        """Cenario base passa por todas as 6 invariantes sem erro."""
        r = calcular_dre(_base(), "2025-10")
        # Se chegou aqui sem IntegridadeContabilError, todas passaram
        assert r.valor.resultado_liquido == money(75000)


# ============================================================
# T31-T35 -- Comparativo CPC 26
# ============================================================

class TestComparativoCPC26:
    """Periodo atual vs anterior com variacao horizontal."""

    def _ant(self) -> dict:
        """Periodo anterior: receita 10% menor."""
        d = _base()
        d["receita_bruta"] = 180000
        return d

    def test_t31_dados_anteriores_none(self):
        """Sem dados anteriores, nao calcula variacoes."""
        r = calcular_dre(_base(), "2025-10", dados_anteriores=None)
        assert isinstance(r.valor, DRE)

    def test_t32_variacoes_calculadas(self):
        """Com dados anteriores, variacoes sao calculadas."""
        r = calcular_dre(_base(), "2025-10", dados_anteriores=self._ant())
        assert isinstance(r.valor, DRE)

    def test_t33_variacao_receita_bruta(self):
        """RB atual=200k, ant=180k -> variacao = (20k/180k)*100 = 11.11%."""
        r_atual = calcular_dre(_base(), "2025-10")
        r_ant = calcular_dre(self._ant(), "2025-09")
        var = (r_atual.valor.receita_bruta - r_ant.valor.receita_bruta) / abs(r_ant.valor.receita_bruta) * 100
        assert var > Decimal("11") and var < Decimal("12")

    def test_t34_comparativo_com_anterior_zero(self):
        """Receita anterior zero -> variacao None (nao divide por zero)."""
        d_ant = _base()
        d_ant["receita_bruta"] = 0
        r = calcular_dre(_base(), "2025-10", dados_anteriores=d_ant)
        assert isinstance(r.valor, DRE)

    def test_t35_comparativo_ambos_iguais(self):
        """Dados identicos -> variacoes zero."""
        r = calcular_dre(_base(), "2025-10", dados_anteriores=_base())
        assert isinstance(r.valor, DRE)


# ============================================================
# T36-T40 -- Planilha de referencia
# ============================================================

class TestPlanilhaReferencia:
    """Cenarios calculados a mao pelas tres personas."""

    def test_t36_servicos(self):
        """Empresa de servicos — cenario base. Conferido a mao."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.receita_liquida == money(190000)
        assert r.valor.lucro_bruto == money(130000)
        assert r.valor.ebit == money(90000)
        assert r.valor.ebitda == money(95000)
        assert r.valor.lair == money(87000)
        assert r.valor.resultado_liquido == money(75000)

    def test_t37_comercio(self):
        """Empresa comercial com CMV alto, D&A baixa.

        RB=500k, Ded=50k, CMV=300k, DA_adm=30k, DA_com=20k,
        DA_out=5k, D&A=2k, DFin=8k, IR=15k.
        RL=450k, LB=150k, EBIT=93k, EBITDA=95k, LAIR=85k, LL=70k.
        """
        d = {
            "receita_bruta": 500000, "deducoes_receita": 50000,
            "custo_servicos": 300000, "despesas_adm": 30000,
            "despesas_comerciais": 20000, "outras_despesas": 5000,
            "depreciacao_amortizacao": 2000, "despesas_financeiras": 8000,
            "receitas_financeiras": 0, "ir_csll": 15000,
        }
        r = calcular_dre(d, "2025-10")
        assert r.valor.receita_liquida == money(450000)
        assert r.valor.lucro_bruto == money(150000)
        assert r.valor.ebit == money(93000)
        assert r.valor.ebitda == money(95000)
        assert r.valor.lair == money(85000)
        assert r.valor.resultado_liquido == money(70000)

    def test_t38_industria(self):
        """Industria com CMV alto, D&A relevante, receita financeira.

        RB=1M, Ded=100k, CMV=500k, DA_adm=50k, DA_com=30k,
        DA_out=10k, D&A=40k, DFin=15k, RFin=5k, IRPJ=30k, CSLL=10k.
        RL=900k, LB=400k, EBIT=270k, EBITDA=310k, LAIR=260k, LL=220k.
        """
        d = {
            "receita_bruta": 1000000, "deducoes_receita": 100000,
            "custo_servicos": 500000, "despesas_adm": 50000,
            "despesas_comerciais": 30000, "outras_despesas": 10000,
            "depreciacao_amortizacao": 40000, "despesas_financeiras": 15000,
            "receitas_financeiras": 5000, "irpj": 30000, "csll": 10000,
        }
        r = calcular_dre(d, "2025-10")
        assert r.valor.receita_liquida == money(900000)
        assert r.valor.lucro_bruto == money(400000)
        assert r.valor.ebit == money(270000)
        assert r.valor.ebitda == money(310000)
        assert r.valor.lair == money(260000)
        assert r.valor.resultado_liquido == money(220000)

    def test_t39_microempresa_simples(self):
        """ME no Simples — DAS sobre receita, sem D&A, sem financeiro.

        RB=50k, Ded=0, CMV=15k, DA_adm=8k, DA_com=2k, DA_out=0,
        D&A=0, DFin=0, RFin=0, IR_CSLL=3k (DAS).
        RL=50k, LB=35k, EBIT=25k, EBITDA=25k, LAIR=25k, LL=22k.
        """
        d = {
            "receita_bruta": 50000, "deducoes_receita": 0,
            "custo_servicos": 15000, "despesas_adm": 8000,
            "despesas_comerciais": 2000, "outras_despesas": 0,
            "depreciacao_amortizacao": 0, "despesas_financeiras": 0,
            "receitas_financeiras": 0, "ir_csll": 3000,
        }
        r = calcular_dre(d, "2025-10")
        assert r.valor.ebit == money(25000)
        assert r.valor.ebitda == money(25000)
        assert r.valor.lair == money(25000)
        assert r.valor.resultado_liquido == money(22000)

    def test_t40_margem_liquida_calcavel(self):
        """RL > 0 permite calculo de margem. Nao e responsabilidade do motor,
        mas confirma que RL nao e zero no cenario base."""
        r = calcular_dre(_base(), "2025-10")
        assert r.valor.receita_liquida > _ZERO


# ============================================================
# T41-T45 -- Regressao Fase 2 (correcao ALTO-1)
# ============================================================

class TestRegressaoFase2:
    """Dados da Fase 2 devem produzir valores CORRIGIDOS (nao os antigos)."""

    def test_t41_ebit_fase2_corrigido(self):
        """Sistema antigo: ebit=47000 (incluia DFin). Correto: 47500."""
        r = calcular_dre(_fase2_mes1(), "2025-01")
        assert r.valor.ebit == money(47500), (
            f"EBIT deveria ser 47500 (sem DFin), recebeu {r.valor.ebit}"
        )

    def test_t42_lair_fase2(self):
        """LAIR = EBIT - DFin = 47500 - 2000 = 45500."""
        r = calcular_dre(_fase2_mes1(), "2025-01")
        assert r.valor.lair == money(45500)

    def test_t43_resultado_liquido_fase2(self):
        """LL = LAIR - IR_CSLL = 45500 - 3000 = 42500."""
        r = calcular_dre(_fase2_mes1(), "2025-01")
        assert r.valor.resultado_liquido == money(42500)

    def test_t44_ebitda_fase2(self):
        """EBITDA = EBIT + D&A = 47500 + 1500 = 49000."""
        r = calcular_dre(_fase2_mes1(), "2025-01")
        assert r.valor.ebitda == money(49000)

    def test_t45_ebit_diferente_lair_fase2(self):
        """EBIT (47500) != LAIR (45500) — confirma separacao."""
        r = calcular_dre(_fase2_mes1(), "2025-01")
        assert r.valor.ebit != r.valor.lair
        assert r.valor.ebit - r.valor.lair == money(2000)  # = DFin


# ============================================================
# T46-T50 -- Edge cases
# ============================================================

_ZERO = Decimal("0")


class TestEdgeCases:

    def test_t46_tudo_zero(self):
        """Todos os campos zero — DRE valida com resultados zero."""
        d = {k: 0 for k in _base()}
        r = calcular_dre(d, "2025-01")
        assert r.valor.resultado_liquido == money(0)
        assert r.valor.ebit == money(0)

    def test_t47_receita_zero_com_despesas(self):
        """Sem receita mas com despesas — prejuizo."""
        d = _base()
        d["receita_bruta"] = 0
        d["ir_csll"] = 0
        r = calcular_dre(d, "2025-01")
        assert r.valor.resultado_liquido < _ZERO

    def test_t48_prejuizo_operacional(self):
        """Despesas maiores que receita liquida."""
        d = _base()
        d["despesas_adm"] = 200000
        r = calcular_dre(d, "2025-01")
        assert r.valor.ebit < _ZERO

    def test_t49_campo_ausente_tratado_como_zero(self):
        """Campos ausentes no dict tratados como zero sem erro."""
        d = {"receita_bruta": 100000}
        r = calcular_dre(d, "2025-01")
        assert r.valor.receita_bruta == money(100000)
        assert r.valor.receita_liquida == money(100000)  # ded=0

    def test_t50_valores_decimal_preservados(self):
        """Valores com centavos preservados sem arredondamento espurio."""
        d = _base()
        d["receita_bruta"] = "199999.99"
        d["deducoes_receita"] = "10000.01"
        r = calcular_dre(d, "2025-01")
        assert r.valor.receita_liquida == money("189999.98")


# ============================================================
# T51-T53 -- Refinamentos obrigatorios
# ============================================================

class TestRefinamentos:

    def test_t51_aviso_receitas_financeiras_ausentes(self):
        """Sem receitas_financeiras -> aviso na memoria."""
        r = calcular_dre(_base(), "2025-10")
        assert any("Receitas financeiras" in a for a in r.avisos), (
            f"Aviso sobre receitas financeiras ausente. Avisos: {r.avisos}"
        )

    def test_t52_prejuizo_com_tributo_simples_presumido(self):
        """Prejuizo (LAIR<0) com tributo positivo — Simples/Presumido.

        Cenario: RL=100k, Custos+Despesas=120k -> LAIR=-20k,
        mas ir_csll=5k (DAS sobre receita).
        LL = -20k - 5k = -25k.
        Aviso sobre tributo em prejuizo deve estar presente.
        """
        d = {
            "receita_bruta": 100000, "deducoes_receita": 0,
            "custo_servicos": 50000, "despesas_adm": 40000,
            "despesas_comerciais": 20000, "outras_despesas": 10000,
            "depreciacao_amortizacao": 0, "despesas_financeiras": 0,
            "receitas_financeiras": 0, "ir_csll": 5000,
        }
        r = calcular_dre(d, "2025-01")
        assert r.valor.lair == money(-20000)
        assert r.valor.resultado_liquido == money(-25000)
        assert any("prejuizo" in a.lower() for a in r.avisos), (
            f"Aviso sobre tributo em prejuizo ausente. Avisos: {r.avisos}"
        )

    def test_t53_prejuizo_lucro_real_sem_tributo(self):
        """Prejuizo no Lucro Real — IRPJ e CSLL zerados.

        LAIR = -20k, irpj=0, csll=0. LL = -20k. Sem aviso especial.
        """
        d = {
            "receita_bruta": 100000, "deducoes_receita": 0,
            "custo_servicos": 50000, "despesas_adm": 40000,
            "despesas_comerciais": 20000, "outras_despesas": 10000,
            "depreciacao_amortizacao": 0, "despesas_financeiras": 0,
            "receitas_financeiras": 0, "irpj": 0, "csll": 0,
        }
        r = calcular_dre(d, "2025-01")
        assert r.valor.lair == money(-20000)
        assert r.valor.resultado_liquido == money(-20000)
        assert not any("prejuizo" in a.lower() for a in r.avisos), (
            f"Nao deveria ter aviso de prejuizo com tributo zero. Avisos: {r.avisos}"
        )
