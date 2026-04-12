"""
Testes BLOCO 3G -- Lucro Real reescrito (RIR/2018, Lei 9.249/95, Lei 9.065/95).

69 testes:
  T1-T10:   Adicoes LALUR
  T11-T20:  Exclusoes LALUR
  T21-T28:  Compensacao de prejuizo
  T29-T36:  IRPJ + adicional
  T37-T42:  CSLL base propria
  T43-T50:  PIS/COFINS creditos
  T51-T55:  Planilha referencia + adversariais
  T56-T58:  Regressao legado
  T59-T61:  Invariantes
  T62-T65:  Edge cases + adversariais
  T66-T69:  Validacao post_init
"""

import pytest
from decimal import Decimal

from services.contabil.core import money_fiscal, rate, to_decimal, VERSAO_CALCULO
from services.contabil.lucro_real import (
    calcular_lucro_real, AjusteLALUR, CreditoPISCofins, ResultadoLucroReal,
)

_ZERO = Decimal("0")


# -- Helpers -------------------------------------------------------------------

def _adic(desc="Multas punitivas", valor=10000, norma="RIR/2018 art. 352"):
    return AjusteLALUR(desc, Decimal(str(valor)), "adicao", norma)

def _excl(desc="Dividendos recebidos", valor=5000, norma="Lei 9.249/95 art. 10"):
    return AjusteLALUR(desc, Decimal(str(valor)), "exclusao", norma)

def _cred(desc="Insumos diretos", base=50000, tipo="insumos"):
    return CreditoPISCofins(desc, Decimal(str(base)), tipo)


# ============================================================
# T1-T10 -- Adicoes LALUR
# ============================================================

class TestAdicoesLALUR:

    def test_t1_uma_adicao(self):
        r = calcular_lucro_real(100000, 200000, adicoes=[_adic(valor=10000)])
        assert r.valor.total_adicoes == money_fiscal(10000)

    def test_t2_multiplas_adicoes(self):
        ads = [_adic(valor=10000), _adic("Brindes", 5000, "Lei 9.249/95 art. 13 VII")]
        r = calcular_lucro_real(100000, 200000, adicoes=ads)
        assert r.valor.total_adicoes == money_fiscal(15000)

    def test_t3_adicao_aumenta_lucro_real(self):
        """Adicao: lucro_antes = LC + adicoes."""
        r = calcular_lucro_real(100000, 200000, adicoes=[_adic(valor=20000)])
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(120000)

    def test_t4_sem_adicoes(self):
        r = calcular_lucro_real(100000, 200000)
        assert r.valor.total_adicoes == _ZERO

    def test_t5_adicao_zero(self):
        r = calcular_lucro_real(100000, 200000, adicoes=[_adic(valor=0)])
        assert r.valor.total_adicoes == _ZERO

    def test_t6_adicao_decimal(self):
        r = calcular_lucro_real(100000, 200000, adicoes=[_adic(valor="1234.56")])
        assert r.valor.total_adicoes == money_fiscal("1234.56")

    def test_t7_multas_punitivas(self):
        """Multas fiscais punitivas sao indedutiveis (RIR/2018 art. 352)."""
        r = calcular_lucro_real(100000, 200000,
                                adicoes=[_adic("Multa SEFAZ", 8000, "RIR/2018 art. 352")])
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(108000)

    def test_t8_doacoes_indedutiveis(self):
        r = calcular_lucro_real(100000, 200000,
                                adicoes=[_adic("Doacao fora de lei", 3000, "RIR/2018 art. 365")])
        assert r.valor.total_adicoes == money_fiscal(3000)

    def test_t9_provisoes_nao_dedutiveis(self):
        r = calcular_lucro_real(100000, 200000,
                                adicoes=[_adic("Provisao contabil", 15000, "RIR/2018 art. 335")])
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(115000)

    def test_t10_aviso_sem_lalur(self):
        """Sem adicoes nem exclusoes -> aviso."""
        r = calcular_lucro_real(100000, 200000)
        assert any("Nenhum ajuste LALUR" in a for a in r.avisos)


# ============================================================
# T11-T20 -- Exclusoes LALUR
# ============================================================

class TestExclusoesLALUR:

    def test_t11_uma_exclusao(self):
        r = calcular_lucro_real(100000, 200000, exclusoes=[_excl(valor=5000)])
        assert r.valor.total_exclusoes == money_fiscal(5000)

    def test_t12_multiplas_exclusoes(self):
        exs = [_excl(valor=5000), _excl("Equiv. patrimonial", 10000, "RIR/2018 art. 425")]
        r = calcular_lucro_real(100000, 200000, exclusoes=exs)
        assert r.valor.total_exclusoes == money_fiscal(15000)

    def test_t13_exclusao_reduz_lucro_real(self):
        r = calcular_lucro_real(100000, 200000, exclusoes=[_excl(valor=30000)])
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(70000)

    def test_t14_exclusao_maior_que_lucro(self):
        """Exclusao pode gerar prejuizo fiscal."""
        r = calcular_lucro_real(100000, 200000, exclusoes=[_excl(valor=120000)])
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(-20000)

    def test_t15_adicoes_e_exclusoes_juntas(self):
        """lucro_antes = 100k + 20k - 8k = 112k."""
        r = calcular_lucro_real(100000, 200000,
                                adicoes=[_adic(valor=20000)],
                                exclusoes=[_excl(valor=8000)])
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(112000)

    def test_t16_reversao_provisao(self):
        r = calcular_lucro_real(100000, 200000,
                                exclusoes=[_excl("Reversao provisao", 7000, "RIR/2018 art. 335")])
        assert r.valor.total_exclusoes == money_fiscal(7000)

    def test_t17_dividendos_recebidos(self):
        r = calcular_lucro_real(100000, 200000,
                                exclusoes=[_excl("Dividendos", 12000, "Lei 9.249/95 art. 10")])
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(88000)

    def test_t18_sem_exclusoes(self):
        r = calcular_lucro_real(100000, 200000)
        assert r.valor.total_exclusoes == _ZERO

    def test_t19_exclusao_zero(self):
        r = calcular_lucro_real(100000, 200000, exclusoes=[_excl(valor=0)])
        assert r.valor.total_exclusoes == _ZERO

    def test_t20_exclusao_decimal(self):
        r = calcular_lucro_real(100000, 200000, exclusoes=[_excl(valor="999.99")])
        assert r.valor.total_exclusoes == money_fiscal("999.99")


# ============================================================
# T21-T28 -- Compensacao de prejuizo
# ============================================================

class TestCompensacaoPrejuizo:

    def test_t21_sem_prejuizo(self):
        r = calcular_lucro_real(100000, 200000, prejuizo_fiscal_acumulado=0)
        assert r.valor.prejuizo_compensado == _ZERO

    def test_t22_prejuizo_menor_que_30_pct(self):
        """Prej 20k, lucro 100k: max comp = 30k. Compensa 20k (todo)."""
        r = calcular_lucro_real(100000, 200000, prejuizo_fiscal_acumulado=20000)
        assert r.valor.prejuizo_compensado == money_fiscal(20000)
        assert r.valor.prejuizo_remanescente == _ZERO

    def test_t23_prejuizo_maior_que_30_pct(self):
        """Prej 50k, lucro 100k: max comp = 30k. Compensa 30k, remanesce 20k."""
        r = calcular_lucro_real(100000, 200000, prejuizo_fiscal_acumulado=50000)
        assert r.valor.prejuizo_compensado == money_fiscal(30000)
        assert r.valor.prejuizo_remanescente == money_fiscal(20000)

    def test_t24_exatamente_30_pct(self):
        """Prej 30k, lucro 100k: compensa exatamente 30k."""
        r = calcular_lucro_real(100000, 200000, prejuizo_fiscal_acumulado=30000)
        assert r.valor.prejuizo_compensado == money_fiscal(30000)
        assert r.valor.prejuizo_remanescente == _ZERO

    def test_t25_prejuizo_maior_que_lucro(self):
        """Prej 500k, lucro 100k: max comp = 30k. Remanesce 470k."""
        r = calcular_lucro_real(100000, 200000, prejuizo_fiscal_acumulado=500000)
        assert r.valor.prejuizo_compensado == money_fiscal(30000)
        assert r.valor.prejuizo_remanescente == money_fiscal(470000)

    def test_t26_lucro_real_final_apos_compensacao(self):
        """Lucro final = antes - compensacao."""
        r = calcular_lucro_real(100000, 200000, prejuizo_fiscal_acumulado=50000)
        assert r.valor.lucro_real_final == money_fiscal(70000)

    def test_t27_prejuizo_no_periodo_acumula(self):
        """Lucro contabil negativo: nao compensa, acumula prejuizo."""
        r = calcular_lucro_real(-50000, 200000, prejuizo_fiscal_acumulado=100000)
        assert r.valor.prejuizo_compensado == _ZERO
        assert r.valor.prejuizo_remanescente == money_fiscal(150000)

    def test_t28_prejuizo_no_periodo_sem_acumulado(self):
        """Prejuizo sem acumulado anterior."""
        r = calcular_lucro_real(-30000, 200000, prejuizo_fiscal_acumulado=0)
        assert r.valor.prejuizo_remanescente == money_fiscal(30000)


# ============================================================
# T29-T36 -- IRPJ + adicional
# ============================================================

class TestIRPJ:

    def test_t29_irpj_15_basico(self):
        """IRPJ = max(0, lucro_final) x 15%."""
        r = calcular_lucro_real(200000, 500000, trimestral=True)
        assert r.valor.irpj_15 == money_fiscal(30000)

    def test_t30_irpj_prejuizo_zero(self):
        """Prejuizo: IRPJ = 0."""
        r = calcular_lucro_real(-50000, 200000, trimestral=True)
        assert r.valor.irpj_15 == _ZERO
        assert r.valor.irpj_total == _ZERO

    def test_t31_adicional_sem_excesso(self):
        """Base trim 50k < 60k: adicional = 0."""
        r = calcular_lucro_real(50000, 200000, trimestral=True)
        assert r.valor.irpj_adicional_10 == _ZERO

    def test_t32_adicional_com_excesso(self):
        """Base trim 200k > 60k: adicional = (200k-60k)*10% = 14k."""
        r = calcular_lucro_real(200000, 500000, trimestral=True)
        assert r.valor.irpj_adicional_10 == money_fiscal(14000)

    def test_t33_adicional_exatamente_60k(self):
        r = calcular_lucro_real(60000, 200000, trimestral=True)
        assert r.valor.irpj_adicional_10 == _ZERO

    def test_t34_irpj_total(self):
        r = calcular_lucro_real(200000, 500000, trimestral=True)
        assert r.valor.irpj_total == money_fiscal(r.valor.irpj_15 + r.valor.irpj_adicional_10)

    def test_t35_mensal_estima_trimestral(self):
        """Modo mensal: aviso sobre estimativa."""
        r = calcular_lucro_real(100000, 300000, trimestral=False)
        if r.valor.irpj_15 > _ZERO:
            assert any("mensal x 3" in a.lower() or "trimestral" in a.lower() for a in r.avisos)

    def test_t36_irpj_decimal(self):
        r = calcular_lucro_real(200000, 500000, trimestral=True)
        assert isinstance(r.valor.irpj_15, Decimal)
        assert isinstance(r.valor.irpj_adicional_10, Decimal)


# ============================================================
# T37-T42 -- CSLL base propria
# ============================================================

class TestCSLL:

    def test_t37_csll_base_padrao(self):
        """Sem base_csll explicita: usa lucro_real_final."""
        r = calcular_lucro_real(100000, 200000, trimestral=True)
        assert r.valor.csll_9 == money_fiscal(money_fiscal(100000) * Decimal("0.09"))

    def test_t38_csll_base_propria(self):
        """Com base_csll explicita."""
        r = calcular_lucro_real(100000, 200000, base_csll=80000, trimestral=True)
        assert r.valor.csll_9 == money_fiscal(Decimal("80000") * Decimal("0.09"))
        assert r.valor.base_csll == money_fiscal(80000)

    def test_t39_csll_prejuizo(self):
        """Prejuizo: base_csll = 0 (max(0, lucro_final))."""
        r = calcular_lucro_real(-50000, 200000, trimestral=True)
        assert r.valor.csll_9 == _ZERO

    def test_t40_csll_com_adicoes(self):
        """CSLL base acompanha LALUR quando nao especificada."""
        r = calcular_lucro_real(100000, 200000, adicoes=[_adic(valor=20000)], trimestral=True)
        assert r.valor.base_csll == money_fiscal(120000)
        assert r.valor.csll_9 == money_fiscal(Decimal("120000") * Decimal("0.09"))

    def test_t41_csll_com_compensacao(self):
        """CSLL base = lucro apos compensacao."""
        r = calcular_lucro_real(100000, 200000, prejuizo_fiscal_acumulado=50000, trimestral=True)
        assert r.valor.base_csll == money_fiscal(70000)

    def test_t42_csll_decimal(self):
        r = calcular_lucro_real(100000, 200000, trimestral=True)
        assert isinstance(r.valor.csll_9, Decimal)


# ============================================================
# T43-T50 -- PIS/COFINS creditos
# ============================================================

class TestPISCOFINS:

    def test_t43_sem_creditos(self):
        """Sem creditos: devido = debito total."""
        r = calcular_lucro_real(100000, 500000, trimestral=True)
        assert r.valor.pis_devido == money_fiscal(Decimal("500000") * Decimal("0.0165"))
        assert r.valor.cofins_devido == money_fiscal(Decimal("500000") * Decimal("0.076"))

    def test_t44_creditos_parciais(self):
        """Creditos < debitos: devido = debito - credito."""
        creds = [_cred(base=100000)]
        r = calcular_lucro_real(100000, 500000, creditos_pis_cofins=creds, trimestral=True)
        pis_deb = money_fiscal(Decimal("500000") * Decimal("0.0165"))
        pis_cred = money_fiscal(Decimal("100000") * Decimal("0.0165"))
        assert r.valor.pis_devido == money_fiscal(pis_deb - pis_cred)

    def test_t45_creditos_maiores_que_debitos(self):
        """Creditos > debitos: devido = 0 (nao negativo)."""
        creds = [_cred(base=1000000)]  # base maior que receita
        r = calcular_lucro_real(100000, 200000, creditos_pis_cofins=creds, trimestral=True)
        assert r.valor.pis_devido == _ZERO
        assert r.valor.cofins_devido == _ZERO

    def test_t46_multiplos_creditos(self):
        """Multiplos tipos de credito somam."""
        creds = [_cred("Insumos", 50000, "insumos"),
                 _cred("Energia", 20000, "energia"),
                 _cred("Aluguel", 10000, "aluguel")]
        r = calcular_lucro_real(100000, 500000, creditos_pis_cofins=creds, trimestral=True)
        total_base = Decimal("80000")
        pis_cred_esperado = money_fiscal(total_base * Decimal("0.0165"))
        assert r.valor.pis_credito == pis_cred_esperado

    def test_t47_credito_depreciacao(self):
        creds = [_cred("Depreciacao maquinas", 30000, "depreciacao")]
        r = calcular_lucro_real(100000, 500000, creditos_pis_cofins=creds, trimestral=True)
        assert r.valor.pis_credito > _ZERO

    def test_t48_credito_frete(self):
        creds = [_cred("Frete vendas", 15000, "frete")]
        r = calcular_lucro_real(100000, 500000, creditos_pis_cofins=creds, trimestral=True)
        assert r.valor.cofins_credito > _ZERO

    def test_t49_aviso_sem_creditos(self):
        r = calcular_lucro_real(100000, 500000, trimestral=True)
        assert any("Nenhum credito PIS/COFINS" in a for a in r.avisos)

    def test_t50_pis_cofins_decimal(self):
        r = calcular_lucro_real(100000, 500000, trimestral=True)
        assert isinstance(r.valor.pis_devido, Decimal)
        assert isinstance(r.valor.cofins_devido, Decimal)


# ============================================================
# T51-T55 -- Planilha referencia + adversariais
# ============================================================

class TestPlanilhaReferencia:

    def test_t51_servicos_basico(self):
        """Servicos: LC=200k, RL=500k, sem LALUR, sem creditos, trimestral.
        IRPJ = 200k*15% = 30k. Adic = (200k-60k)*10% = 14k. Total IRPJ = 44k.
        CSLL = 200k*9% = 18k. PIS = 500k*1.65% = 8250. COFINS = 500k*7.6% = 38000.
        Total = 44000+18000+8250+38000 = 108250."""
        r = calcular_lucro_real(200000, 500000, trimestral=True)
        assert r.valor.irpj_total == money_fiscal(44000)
        assert r.valor.csll_9 == money_fiscal(18000)
        assert r.valor.pis_devido == money_fiscal(8250)
        assert r.valor.cofins_devido == money_fiscal(38000)
        assert r.valor.total_tributos == money_fiscal(108250)

    def test_t52_com_lalur(self):
        """LC=200k + adicao 30k - exclusao 10k = 220k.
        IRPJ = 220k*15% = 33k. Adic = (220k-60k)*10% = 16k. Total = 49k."""
        r = calcular_lucro_real(200000, 500000,
                                adicoes=[_adic(valor=30000)],
                                exclusoes=[_excl(valor=10000)],
                                trimestral=True)
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(220000)
        assert r.valor.irpj_total == money_fiscal(49000)

    def test_t53_adv1_prejuizo_1m_lucro_200k(self):
        """T-ADV-1: prej 1M, lucro 200k -> compensa 60k (30%), remanesce 940k.
        IRPJ base = 200k-60k = 140k. IRPJ = 140k*15% = 21k.
        Adic = (140k-60k)*10% = 8k."""
        r = calcular_lucro_real(200000, 500000,
                                prejuizo_fiscal_acumulado=1000000, trimestral=True)
        assert r.valor.prejuizo_compensado == money_fiscal(60000)
        assert r.valor.prejuizo_remanescente == money_fiscal(940000)
        assert r.valor.lucro_real_final == money_fiscal(140000)
        assert r.valor.irpj_15 == money_fiscal(21000)
        assert r.valor.irpj_adicional_10 == money_fiscal(8000)

    def test_t54_adv2_prejuizo_periodo(self):
        """T-ADV-2: lucro_contabil=-50k -> IRPJ=0, CSLL=0, PIS/COFINS normais."""
        r = calcular_lucro_real(-50000, 200000, trimestral=True)
        assert r.valor.irpj_total == _ZERO
        assert r.valor.csll_9 == _ZERO
        assert r.valor.pis_devido > _ZERO
        assert r.valor.cofins_devido > _ZERO

    def test_t55_com_creditos(self):
        """LC=300k, RL=800k, creditos 200k. PIS devido = (800k-200k)*1.65%/800k... nao.
        PIS deb = 800k*1.65% = 13200. PIS cred = 200k*1.65% = 3300.
        PIS devido = 13200 - 3300 = 9900."""
        creds = [_cred("Insumos", 200000)]
        r = calcular_lucro_real(300000, 800000, creditos_pis_cofins=creds, trimestral=True)
        assert r.valor.pis_debito == money_fiscal(13200)
        assert r.valor.pis_credito == money_fiscal(3300)
        assert r.valor.pis_devido == money_fiscal(9900)


# ============================================================
# T56-T58 -- Regressao legado
# ============================================================

class TestRegressaoLegado:

    def test_t56_sem_lalur_reproduz_legado(self):
        """Sem LALUR: lucro_real = lucro_contabil (similar ao legado)."""
        r = calcular_lucro_real(100000, 300000, trimestral=True)
        assert r.valor.lucro_real_final == money_fiscal(100000)

    def test_t57_com_lalur_difere_legado(self):
        """Com LALUR: resultado difere do legado."""
        r = calcular_lucro_real(100000, 300000,
                                adicoes=[_adic(valor=20000)], trimestral=True)
        assert r.valor.lucro_real_final == money_fiscal(120000)
        assert r.valor.lucro_real_final != money_fiscal(100000)

    def test_t58_creditos_reduzem_pis_cofins(self):
        """Legado: credito = custo*aliq. Novo: creditos detalhados."""
        r_sem = calcular_lucro_real(100000, 300000, trimestral=True)
        r_com = calcular_lucro_real(100000, 300000,
                                    creditos_pis_cofins=[_cred(base=100000)], trimestral=True)
        assert r_com.valor.pis_devido < r_sem.valor.pis_devido


# ============================================================
# T59-T61 -- Invariantes
# ============================================================

class TestInvariantes:

    def test_t59_inv_lr3(self):
        """INV-LR-3: lucro_antes = LC + adic - excl."""
        r = calcular_lucro_real(100000, 200000,
                                adicoes=[_adic(valor=20000)],
                                exclusoes=[_excl(valor=5000)], trimestral=True)
        assert r.valor.lucro_real_antes_compensacao == money_fiscal(115000)

    def test_t60_inv_lr11(self):
        """INV-LR-11: total = irpj + csll + pis + cofins."""
        r = calcular_lucro_real(200000, 500000, trimestral=True)
        soma = r.valor.irpj_total + r.valor.csll_9 + r.valor.pis_devido + r.valor.cofins_devido
        assert abs(r.valor.total_tributos - soma) <= money_fiscal("0.01")

    def test_t61_versao(self):
        r = calcular_lucro_real(100000, 200000, trimestral=True)
        assert r.memoria.versao == VERSAO_CALCULO


# ============================================================
# T62-T65 -- Edge cases + adversariais
# ============================================================

class TestEdgeCasesAdversariais:

    def test_t62_adv3_creditos_maiores_debitos(self):
        """T-ADV-3: creditos > debitos -> devido = 0 (nao negativo)."""
        creds = [_cred(base=2000000)]
        r = calcular_lucro_real(100000, 200000, creditos_pis_cofins=creds, trimestral=True)
        assert r.valor.pis_devido == _ZERO
        assert r.valor.cofins_devido == _ZERO

    def test_t63_adv4_norma_obrigatoria(self):
        """T-ADV-4: AjusteLALUR sem norma -> ValueError."""
        with pytest.raises(ValueError, match="norma"):
            AjusteLALUR("Algo", Decimal("1000"), "adicao", "")

    def test_t64_receita_zero(self):
        r = calcular_lucro_real(0, 0, trimestral=True)
        assert r.valor.total_tributos == _ZERO

    def test_t65_tudo_zero(self):
        r = calcular_lucro_real(0, 0, prejuizo_fiscal_acumulado=0, trimestral=True)
        assert r.valor.lucro_real_final == _ZERO


# ============================================================
# T66-T69 -- Validacao post_init
# ============================================================

class TestValidacaoPostInit:

    def test_t66_ajuste_tipo_invalido(self):
        with pytest.raises(ValueError, match="adicao.*exclusao"):
            AjusteLALUR("X", Decimal("100"), "deducao", "RIR art. 1")

    def test_t67_ajuste_valor_negativo(self):
        with pytest.raises(ValueError, match="negativo"):
            AjusteLALUR("X", Decimal("-100"), "adicao", "RIR art. 1")

    def test_t68_credito_tipo_invalido(self):
        with pytest.raises(ValueError, match="invalido"):
            CreditoPISCofins("X", Decimal("100"), "servicos")

    def test_t69_credito_descricao_vazia(self):
        with pytest.raises(ValueError, match="descricao"):
            CreditoPISCofins("", Decimal("100"), "insumos")
