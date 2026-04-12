"""
Testes BLOCO 3I -- Retencoes na Fonte + DIFAL + ICMS-ST.

60 testes:
  T1-T15:   Retencoes
  T16-T27:  DIFAL
  T28-T39:  ICMS-ST
  T40-T47:  Invariantes
  T48-T52:  Planilha referencia
  T53-T57:  Edge cases
  T58-T60:  Validacoes input
"""

import pytest
from decimal import Decimal

from services.contabil.core import money_fiscal, rate, to_decimal, VERSAO_CALCULO
from services.contabil.retencoes import calcular_retencoes, PagamentoServico, ResultadoRetencoes
from services.contabil.difal import calcular_difal, OperacaoInterestadual, ResultadoDIFAL
from services.contabil.icms_st import calcular_icms_st, OperacaoST, ResultadoICMSST
from services.contabil.tabelas.servicos_retencao import DISPENSA_CSRF_LIMITE

_ZERO = Decimal("0")


# -- Helpers -------------------------------------------------------------------

def _pag(valor=10000, tipo="consultoria", cessao=False):
    return PagamentoServico("Servico teste", Decimal(str(valor)), tipo, True, cessao)

def _op_inter(valor=1000, orig="SP", dest="BA", cf=True, contrib=False, imp=False):
    return OperacaoInterestadual("Operacao teste", Decimal(str(valor)),
                                  orig, dest, cf, contrib, imp)

def _op_st(valor=1000, ncm="22021000", mva="0.40", aliq_int="0.18", aliq_inter="0.12"):
    return OperacaoST("Produto teste", Decimal(str(valor)), ncm,
                       Decimal(mva), Decimal(aliq_int), Decimal(aliq_inter))


# ============================================================
# T1-T15 -- Retencoes
# ============================================================

class TestRetencoes:

    def test_t1_irrf_profissional(self):
        """IRRF 1,5% sobre servico profissional. 10000*1.5% = 150."""
        r = calcular_retencoes(_pag(10000, "profissional_liberal"))
        assert r.valor.irrf == money_fiscal(150)

    def test_t2_csrf_completa(self):
        """CSRF 4,65% = 1% + 3% + 0,65%. 10000 * 4.65% = 465."""
        r = calcular_retencoes(_pag(10000, "consultoria"))
        assert r.valor.csll_retido == money_fiscal(100)
        assert r.valor.cofins_retido == money_fiscal(300)
        assert r.valor.pis_retido == money_fiscal(65)
        assert r.valor.csrf_total == money_fiscal(465)

    def test_t3_dispensa_csrf_abaixo_limite(self):
        """Valor <= 215.05: CSRF dispensada."""
        r = calcular_retencoes(_pag(200, "consultoria"))
        assert r.valor.csrf_total == _ZERO
        assert any("dispensada" in a.lower() for a in r.avisos)

    def test_t4_dispensa_csrf_exatamente_limite(self):
        """Valor = 215.05: CSRF dispensada (<=)."""
        r = calcular_retencoes(_pag("215.05", "consultoria"))
        assert r.valor.csrf_total == _ZERO

    def test_t5_csrf_acima_limite(self):
        """Valor = 215.06: CSRF aplicada."""
        r = calcular_retencoes(_pag("215.06", "consultoria"))
        assert r.valor.csrf_total > _ZERO

    def test_t6_inss_cessao_mao_obra(self):
        """INSS 11% sobre cessao. 50000*11% = 5500."""
        r = calcular_retencoes(_pag(50000, "cessao_mao_obra", cessao=True))
        assert r.valor.inss_retido == money_fiscal(5500)

    def test_t7_iss_retido(self):
        """ISS retido 5%. 10000*5% = 500."""
        r = calcular_retencoes(_pag(10000, "consultoria"), aliquota_iss_retido="0.05")
        assert r.valor.iss_retido == money_fiscal(500)

    def test_t8_sem_iss(self):
        r = calcular_retencoes(_pag(10000, "consultoria"))
        assert r.valor.iss_retido == _ZERO

    def test_t9_tipo_outros_sem_retencao_federal(self):
        """tipo='outros': sem IRRF nem CSRF."""
        r = calcular_retencoes(_pag(10000, "outros"))
        assert r.valor.irrf == _ZERO
        assert r.valor.csrf_total == _ZERO

    def test_t10_valor_liquido(self):
        """Liquido = bruto - total retido."""
        r = calcular_retencoes(_pag(10000, "consultoria"))
        assert r.valor.valor_liquido == money_fiscal(
            r.valor.valor_bruto - r.valor.total_retido)

    def test_t11_irrf_e_csrf_juntos(self):
        """Servico profissional: IRRF + CSRF aplicados."""
        r = calcular_retencoes(_pag(10000, "profissional_liberal"))
        assert r.valor.irrf > _ZERO
        assert r.valor.csrf_total > _ZERO

    def test_t12_treinamento_irrf_sem_csrf(self):
        """Treinamento: IRRF sim, CSRF nao (nao esta na lista CSRF)."""
        r = calcular_retencoes(_pag(10000, "treinamento_ensino"))
        assert r.valor.irrf > _ZERO
        assert r.valor.csrf_total == _ZERO

    def test_t13_auditoria_irrf_sem_csrf(self):
        r = calcular_retencoes(_pag(10000, "auditoria"))
        assert r.valor.irrf > _ZERO

    def test_t14_publicidade_irrf(self):
        r = calcular_retencoes(_pag(10000, "publicidade_propaganda"))
        assert r.valor.irrf == money_fiscal(150)

    def test_t15_combinacao_inss_irrf_csrf(self):
        """Cessao com servico profissional: INSS + IRRF + CSRF."""
        p = PagamentoServico("Cessao profissional", Decimal("50000"),
                              "locacao_mao_obra", True, True)
        r = calcular_retencoes(p)
        assert r.valor.inss_retido > _ZERO
        assert r.valor.irrf > _ZERO
        assert r.valor.csrf_total > _ZERO


# ============================================================
# T16-T27 -- DIFAL
# ============================================================

class TestDIFAL:

    def test_t16_b2c_interestadual(self):
        """SP->BA consumidor final: DIFAL aplicavel."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", True))
        assert r.valor.aplicavel is True
        assert r.valor.difal_valor > _ZERO

    def test_t17_mesma_uf(self):
        """SP->SP: DIFAL nao aplicavel."""
        r = calcular_difal(_op_inter(1000, "SP", "SP", True))
        assert r.valor.aplicavel is False
        assert "interna" in r.valor.motivo_nao_aplicavel.lower()

    def test_t18_b2b_contribuinte(self):
        """B2B contribuinte ICMS: DIFAL nao aplicavel."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", True, contrib=True))
        assert r.valor.aplicavel is False

    def test_t19_nao_consumidor_final(self):
        """Nao consumidor final: DIFAL nao aplicavel."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", False))
        assert r.valor.aplicavel is False

    def test_t20_sp_ba_7pct(self):
        """SP(Sul/Sudeste)->BA(Nordeste): interestadual 7%."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", True))
        assert r.valor.aliquota_interestadual == rate("0.07")

    def test_t21_ba_sp_12pct(self):
        """BA(Nordeste)->SP(Sudeste): interestadual 12%."""
        r = calcular_difal(_op_inter(1000, "BA", "SP", True))
        assert r.valor.aliquota_interestadual == rate("0.12")

    def test_t22_importado_4pct(self):
        """Produto importado: interestadual 4%."""
        op = OperacaoInterestadual("Imp", Decimal("1000"), "SP", "BA", True, False, True)
        r = calcular_difal(op)
        assert r.valor.aliquota_interestadual == rate("0.04")

    def test_t23_difal_formula(self):
        """DIFAL = valor × (interna - inter). SP->BA: 1000*(20.5%-7%) = 135."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", True))
        expected = money_fiscal(Decimal("1000") * (rate("0.205") - rate("0.07")))
        assert r.valor.difal_valor == expected

    def test_t24_fcp(self):
        """FCP BA = 2%: 1000*2% = 20."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", True))
        assert r.valor.fcp == money_fiscal(20)

    def test_t25_fcp_zero_pr(self):
        """FCP PR = 0%."""
        r = calcular_difal(_op_inter(1000, "SP", "PR", True))
        assert r.valor.fcp == _ZERO

    def test_t26_rs_ma(self):
        """RS(Sul)->MA(Nordeste): inter 7%, MA interna 22%."""
        r = calcular_difal(_op_inter(1000, "RS", "MA", True))
        assert r.valor.aliquota_interestadual == rate("0.07")
        assert r.valor.aliquota_interna_destino == rate("0.22")

    def test_t27_total_difal_fcp(self):
        """Total = difal + fcp."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", True))
        assert r.valor.total == money_fiscal(r.valor.difal_valor + r.valor.fcp)


# ============================================================
# T28-T39 -- ICMS-ST
# ============================================================

class TestICMSST:

    def test_t28_base_st_com_mva(self):
        """Base ST = 1000 × (1 + 0.40) = 1400."""
        r = calcular_icms_st(_op_st(1000, mva="0.40"))
        assert r.valor.base_st == money_fiscal(1400)

    def test_t29_mva_zero(self):
        """MVA 0%: base ST = valor produto."""
        r = calcular_icms_st(_op_st(1000, mva="0"))
        assert r.valor.base_st == money_fiscal(1000)

    def test_t30_mva_alta(self):
        """MVA 100%: base ST = 2 × valor."""
        r = calcular_icms_st(_op_st(1000, mva="1.0"))
        assert r.valor.base_st == money_fiscal(2000)

    def test_t31_icms_proprio(self):
        """ICMS proprio = 1000 × 12% = 120."""
        r = calcular_icms_st(_op_st(1000, aliq_inter="0.12"))
        assert r.valor.icms_proprio == money_fiscal(120)

    def test_t32_icms_st_formula(self):
        """ST = base_st * aliq_int - icms_proprio.
        1400*18% - 1000*12% = 252 - 120 = 132."""
        r = calcular_icms_st(_op_st(1000, mva="0.40", aliq_int="0.18", aliq_inter="0.12"))
        assert r.valor.icms_st == money_fiscal(132)

    def test_t33_st_negativo_ajustado_zero(self):
        """ST negativo: ajustado para zero com aviso."""
        r = calcular_icms_st(_op_st(1000, mva="0", aliq_int="0.07", aliq_inter="0.12"))
        assert r.valor.icms_st == _ZERO
        assert any("negativo" in a.lower() for a in r.avisos)

    def test_t34_total_icms(self):
        """Total = proprio + ST."""
        r = calcular_icms_st(_op_st(1000))
        assert r.valor.total_icms == money_fiscal(r.valor.icms_proprio + r.valor.icms_st)

    def test_t35_aliquotas_diferenciadas(self):
        """Aliq interna 22%, inter 7%."""
        r = calcular_icms_st(_op_st(1000, mva="0.40", aliq_int="0.22", aliq_inter="0.07"))
        base_st = money_fiscal(1400)
        proprio = money_fiscal(Decimal("1000") * Decimal("0.07"))
        st = money_fiscal(base_st * Decimal("0.22") - proprio)
        assert r.valor.icms_st == st

    def test_t36_valor_grande(self):
        r = calcular_icms_st(_op_st(1000000, mva="0.50", aliq_int="0.18", aliq_inter="0.12"))
        assert r.valor.base_st == money_fiscal(1500000)
        assert r.valor.icms_st > _ZERO

    def test_t37_mva_fracionaria(self):
        """MVA 33.5%."""
        r = calcular_icms_st(_op_st(1000, mva="0.335"))
        assert r.valor.base_st == money_fiscal(1335)

    def test_t38_memoria_presente(self):
        r = calcular_icms_st(_op_st())
        assert r.memoria is not None
        assert r.memoria.versao == VERSAO_CALCULO

    def test_t39_decimal_types(self):
        r = calcular_icms_st(_op_st())
        assert isinstance(r.valor.base_st, Decimal)
        assert isinstance(r.valor.icms_st, Decimal)


# ============================================================
# T40-T47 -- Invariantes
# ============================================================

class TestInvariantes:

    def test_t40_inv_ret1_liquido(self):
        r = calcular_retencoes(_pag(10000, "consultoria"))
        assert r.valor.valor_liquido == money_fiscal(r.valor.valor_bruto - r.valor.total_retido)

    def test_t41_inv_ret2_csrf(self):
        r = calcular_retencoes(_pag(10000, "consultoria"))
        assert r.valor.csrf_total == money_fiscal(
            r.valor.csll_retido + r.valor.cofins_retido + r.valor.pis_retido)

    def test_t42_inv_ret3_dispensa(self):
        r = calcular_retencoes(_pag(200, "consultoria"))
        assert r.valor.csrf_total == _ZERO

    def test_t43_inv_ret4_irrf_lista(self):
        """'outros' nao esta na lista IRRF."""
        r = calcular_retencoes(_pag(10000, "outros"))
        assert r.valor.irrf == _ZERO

    def test_t44_inv_difal1(self):
        """Mesma UF: nao aplicavel."""
        r = calcular_difal(_op_inter(1000, "SP", "SP", True))
        assert r.valor.aplicavel is False

    def test_t45_inv_difal2(self):
        r = calcular_difal(_op_inter(1000, "SP", "BA", True))
        aliq_diff = rate(r.valor.aliquota_interna_destino - r.valor.aliquota_interestadual)
        expected = money_fiscal(Decimal("1000") * aliq_diff)
        assert abs(r.valor.difal_valor - expected) <= money_fiscal("0.01")

    def test_t46_inv_st1(self):
        r = calcular_icms_st(_op_st(1000, mva="0.40"))
        assert r.valor.base_st == money_fiscal(Decimal("1000") * Decimal("1.40"))

    def test_t47_inv_st2(self):
        r = calcular_icms_st(_op_st(1000, mva="0.40", aliq_int="0.18", aliq_inter="0.12"))
        expected_st = money_fiscal(
            money_fiscal(Decimal("1400") * Decimal("0.18")) -
            money_fiscal(Decimal("1000") * Decimal("0.12"))
        )
        assert abs(r.valor.icms_st - expected_st) <= money_fiscal("0.01")


# ============================================================
# T48-T52 -- Planilha referencia
# ============================================================

class TestPlanilhaReferencia:

    def test_t48_servico_profissional_10k(self):
        """Consultoria 10k: IRRF=150, CSRF=465, liq=10000-615=9385."""
        r = calcular_retencoes(_pag(10000, "consultoria"))
        assert r.valor.irrf == money_fiscal(150)
        assert r.valor.csrf_total == money_fiscal(465)
        assert r.valor.valor_liquido == money_fiscal(9385)

    def test_t49_cessao_mao_obra_50k(self):
        """Cessao 50k: INSS=5500, IRRF=750, CSRF=2325, liq=50000-8575=41425."""
        p = PagamentoServico("Cessao", Decimal("50000"),
                              "locacao_mao_obra", True, True)
        r = calcular_retencoes(p)
        assert r.valor.inss_retido == money_fiscal(5500)
        assert r.valor.irrf == money_fiscal(750)
        assert r.valor.csrf_total == money_fiscal(2325)
        assert r.valor.valor_liquido == money_fiscal(41425)

    def test_t50_difal_sp_ba_1000(self):
        """SP->BA 1000: inter 7%, BA interna 20.5%, FCP 2%.
        DIFAL = 1000*(20.5%-7%) = 135. FCP = 20. Total = 155."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", True))
        assert r.valor.difal_valor == money_fiscal(135)
        assert r.valor.fcp == money_fiscal(20)
        assert r.valor.total == money_fiscal(155)

    def test_t51_st_mva_40(self):
        """Produto 1000, MVA 40%, aliq int 18%, inter 12%.
        Base ST=1400. Proprio=120. ST=1400*18%-120=252-120=132."""
        r = calcular_icms_st(_op_st(1000, mva="0.40", aliq_int="0.18", aliq_inter="0.12"))
        assert r.valor.base_st == money_fiscal(1400)
        assert r.valor.icms_proprio == money_fiscal(120)
        assert r.valor.icms_st == money_fiscal(132)

    def test_t52_retencao_com_iss(self):
        """Consultoria 10k com ISS 5%: total retido = IRRF+CSRF+ISS = 150+465+500 = 1115."""
        r = calcular_retencoes(_pag(10000, "consultoria"), aliquota_iss_retido="0.05")
        assert r.valor.total_retido == money_fiscal(1115)


# ============================================================
# T53-T57 -- Edge cases
# ============================================================

class TestEdgeCases:

    def test_t53_retencao_valor_zero(self):
        r = calcular_retencoes(_pag(0, "consultoria"))
        assert r.valor.total_retido == _ZERO

    def test_t54_difal_valor_zero(self):
        r = calcular_difal(_op_inter(0, "SP", "BA", True))
        assert r.valor.difal_valor == _ZERO

    def test_t55_st_valor_zero(self):
        r = calcular_icms_st(_op_st(0))
        assert r.valor.icms_st == _ZERO

    def test_t56_iss_zero_pct(self):
        r = calcular_retencoes(_pag(10000, "consultoria"), aliquota_iss_retido="0")
        assert r.valor.iss_retido == _ZERO

    def test_t57_difal_override_aliquota(self):
        """Override aliquota interna."""
        r = calcular_difal(_op_inter(1000, "SP", "BA", True), aliquota_interna_override="0.25")
        assert r.valor.aliquota_interna_destino == rate("0.25")


# ============================================================
# T58-T60 -- Validacoes input
# ============================================================

class TestValidacoesInput:

    def test_t58_tipo_servico_invalido(self):
        with pytest.raises(ValueError, match="invalido"):
            PagamentoServico("X", Decimal("100"), "inexistente")

    def test_t59_uf_invalida(self):
        with pytest.raises(ValueError, match="UF"):
            OperacaoInterestadual("X", Decimal("100"), "XX", "SP", True)

    def test_t60_ncm_vazio(self):
        with pytest.raises(ValueError, match="ncm"):
            OperacaoST("X", Decimal("100"), "", Decimal("0.40"),
                        Decimal("0.18"), Decimal("0.12"))
