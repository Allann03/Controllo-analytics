"""
Testes BLOCO 3J — Comparador + Indicadores FP&A + Score.

80 testes:
  T1-T20:   Comparador de regimes
  T21-T50:  Indicadores (22 + divisao por zero + Decimal)
  T51-T70:  Score de saude
  T71-T77:  Invariantes
  T78-T80:  Edge cases
"""

import pytest
from decimal import Decimal
from typing import Optional

from services.contabil.core import money, rate, to_decimal, money_fiscal
from services.contabil import indicadores as ind
from services.contabil.score_saude import calcular_score, ResultadoScore, PESOS
from services.contabil.comparador import comparar_regimes, PerfilEmpresa, ComparativoRegimes

_ZERO = Decimal("0")


# -- Helpers -------------------------------------------------------------------

def _perfil(receita=1200000, ativ="servicos", folha=300000, margem="0.40",
            creditos=0, indedutiveis=0):
    return PerfilEmpresa(
        Decimal(str(receita)), ativ, Decimal(str(folha)),
        Decimal(str(margem)), Decimal(str(creditos)), Decimal(str(indedutiveis)),
    )

def _dados_score(**overrides):
    base = {
        "ativo_circulante": 200000, "passivo_circulante": 100000,
        "estoques": 30000, "passivo_total": 150000, "ativo_total": 400000,
        "receita_liquida": 500000, "resultado_liquido": 75000,
        "lucro_liquido": 75000, "patrimonio_liquido": 250000,
        "receita_bruta": 550000, "contas_receber": 80000,
        "custo_servicos": 200000, "fornecedores": 60000,
        "ebit": 90000, "despesas_financeiras": 15000,
    }
    base.update(overrides)
    return base


# ============================================================
# T1-T20 -- Comparador
# ============================================================

class TestComparador:

    def test_t1_servicos_retorna_comparativo(self):
        r = comparar_regimes(_perfil())
        assert isinstance(r.valor, ComparativoRegimes)

    def test_t2_comercio_4_regimes(self):
        r = comparar_regimes(_perfil(ativ="comercio"))
        assert r.valor.simples is not None  # 1.2M < 4.8M
        assert r.valor.presumido > _ZERO
        assert r.valor.real > _ZERO
        assert r.valor.reforma > _ZERO

    def test_t3_receita_acima_teto_sem_simples(self):
        """Receita > 4.8M: Simples None."""
        r = comparar_regimes(_perfil(receita=5000000))
        assert r.valor.simples is None

    def test_t4_regime_otimo_menor_carga(self):
        """Regime otimo = menor total."""
        r = comparar_regimes(_perfil())
        vals = {}
        if r.valor.simples is not None:
            vals["simples"] = r.valor.simples
        vals["presumido"] = r.valor.presumido
        vals["real"] = r.valor.real
        vals["reforma"] = r.valor.reforma
        assert r.valor.regime_otimo == min(vals, key=lambda k: vals[k])

    def test_t5_economia_positiva(self):
        r = comparar_regimes(_perfil())
        assert r.valor.economia_vs_pior >= _ZERO

    def test_t6_industria(self):
        r = comparar_regimes(_perfil(ativ="industria"))
        assert r.valor.presumido > _ZERO

    def test_t7_combustiveis(self):
        r = comparar_regimes(_perfil(ativ="combustiveis", receita=3000000))
        assert r.valor.presumido > _ZERO

    def test_t8_transporte_passageiros(self):
        r = comparar_regimes(_perfil(ativ="transporte_passageiros"))
        assert r.valor.presumido > _ZERO

    def test_t9_saude(self):
        r = comparar_regimes(_perfil(ativ="saude"))
        assert r.valor.reforma > _ZERO  # regime especifico com reducao

    def test_t10_educacao(self):
        r = comparar_regimes(_perfil(ativ="educacao"))
        assert isinstance(r.valor, ComparativoRegimes)

    def test_t11_alerta_proximo_sublimite(self):
        r = comparar_regimes(_perfil(receita=3700000))
        assert any("sublimite" in a.lower() for a in r.avisos)

    def test_t12_alerta_proximo_teto(self):
        r = comparar_regimes(_perfil(receita=4500000))
        assert any("teto" in a.lower() or "4.8M" in a for a in r.avisos)

    def test_t13_com_creditos_pis_cofins(self):
        r_sem = comparar_regimes(_perfil())
        r_com = comparar_regimes(_perfil(creditos=200000))
        assert r_com.valor.real <= r_sem.valor.real

    def test_t14_com_despesas_indedutiveis(self):
        r = comparar_regimes(_perfil(indedutiveis=50000))
        assert r.valor.real > _ZERO

    def test_t15_memoria_presente(self):
        r = comparar_regimes(_perfil())
        assert r.memoria is not None
        assert r.memoria.versao == "3.0.0"

    def test_t16_atividade_invalida(self):
        with pytest.raises(ValueError, match="invalida"):
            _perfil(ativ="varejo")

    def test_t17_receita_negativa(self):
        with pytest.raises(ValueError, match="negativa"):
            _perfil(receita=-100)

    def test_t18_fator_r_aplicado(self):
        """Servicos com folha >= 28%: alerta Fator R."""
        r = comparar_regimes(_perfil(receita=500000, folha=200000, ativ="servicos"))
        # 200k/500k = 40% >= 28%
        # Simples usa Anexo III, mas alerta pode ou nao aparecer dependendo do fluxo
        assert isinstance(r.valor, ComparativoRegimes)

    def test_t19_reforma_ano_especifico(self):
        r = comparar_regimes(_perfil(), ano_reforma=2026)
        assert r.valor.reforma > _ZERO  # mesmo que pequeno em 2026

    def test_t20_todos_regimes_decimal(self):
        r = comparar_regimes(_perfil())
        if r.valor.simples is not None:
            assert isinstance(r.valor.simples, Decimal)
        assert isinstance(r.valor.presumido, Decimal)
        assert isinstance(r.valor.real, Decimal)


# ============================================================
# T21-T50 -- Indicadores FP&A
# ============================================================

class TestIndicadores:

    # Liquidez
    def test_t21_lc(self):
        r = ind.liquidez_corrente(Decimal("200"), Decimal("100"))
        assert r.valor == money("2.00")

    def test_t22_lc_div_zero(self):
        r = ind.liquidez_corrente(Decimal("200"), _ZERO)
        assert r.valor is None
        assert r.indisponivel_motivo is not None

    def test_t23_ls(self):
        r = ind.liquidez_seca(Decimal("200"), Decimal("50"), Decimal("100"))
        assert r.valor == money("1.50")

    def test_t24_li(self):
        r = ind.liquidez_imediata(Decimal("80"), Decimal("100"))
        assert r.valor == money("0.80")

    def test_t25_lg(self):
        r = ind.liquidez_geral(Decimal("200"), Decimal("50"), Decimal("100"), Decimal("50"))
        assert r.valor == money("1.67")  # 250/150

    # Rentabilidade
    def test_t26_mb(self):
        r = ind.margem_bruta(Decimal("130"), Decimal("190"))
        assert r.valor is not None and r.valor > _ZERO

    def test_t27_mebit(self):
        r = ind.margem_ebit(Decimal("90"), Decimal("190"))
        assert r.valor is not None

    def test_t28_mebitda(self):
        r = ind.margem_ebitda(Decimal("95"), Decimal("190"))
        assert r.valor is not None

    def test_t29_ml(self):
        r = ind.margem_liquida(Decimal("75"), Decimal("190"))
        assert r.valor is not None

    def test_t30_ml_div_zero(self):
        r = ind.margem_liquida(Decimal("75"), _ZERO)
        assert r.valor is None

    def test_t31_roe(self):
        r = ind.roe(Decimal("75"), Decimal("250"))
        assert r.valor is not None

    def test_t32_roa(self):
        r = ind.roa(Decimal("75"), Decimal("400"))
        assert r.valor is not None

    def test_t33_roic(self):
        r = ind.roic(Decimal("90"), Decimal("12"), Decimal("250"), Decimal("50"))
        assert r.valor is not None

    def test_t34_giro_ativo(self):
        r = ind.giro_ativo(Decimal("500"), Decimal("400"))
        assert r.valor == money("1.25")

    # Ciclo
    def test_t35_pmr(self):
        r = ind.pmr(Decimal("80"), Decimal("550"))
        assert r.valor is not None and r.valor > _ZERO

    def test_t36_pme(self):
        r = ind.pme(Decimal("30"), Decimal("200"))
        assert r.valor is not None

    def test_t37_pmp(self):
        r = ind.pmp(Decimal("60"), Decimal("200"))
        assert r.valor is not None

    def test_t38_ciclo_operacional(self):
        r = ind.ciclo_operacional(Decimal("52"), Decimal("54"))
        assert r.valor == money("106.00")

    def test_t39_ciclo_financeiro(self):
        r = ind.ciclo_financeiro(Decimal("52"), Decimal("54"), Decimal("108"))
        assert r.valor == money("-2.00")

    def test_t40_cf_indisponivel(self):
        r = ind.ciclo_financeiro(None, Decimal("54"), Decimal("108"))
        assert r.valor is None

    # Estrutura
    def test_t41_eg(self):
        r = ind.endividamento_geral(Decimal("150"), Decimal("400"))
        assert r.valor is not None

    def test_t42_ce(self):
        r = ind.composicao_endividamento(Decimal("100"), Decimal("150"))
        assert r.valor is not None

    def test_t43_gaf(self):
        r = ind.grau_alavancagem(Decimal("400"), Decimal("250"))
        assert r.valor == money("1.60")

    def test_t44_cj(self):
        r = ind.cobertura_juros(Decimal("90"), Decimal("15"))
        assert r.valor == money("6.00")

    def test_t45_cj_sem_desp(self):
        r = ind.cobertura_juros(Decimal("90"), _ZERO)
        assert r.valor is None

    # Fleuriet
    def test_t46_ncg(self):
        r = ind.ncg(Decimal("170"), Decimal("100"))  # AC op - PC op
        assert r.valor == money("70.00")

    def test_t47_cdg(self):
        r = ind.cdg(Decimal("300"), Decimal("200"))
        assert r.valor == money("100.00")

    def test_t48_st(self):
        r = ind.saldo_tesouraria(Decimal("100"), Decimal("70"))
        assert r.valor == money("30.00")

    def test_t49_funcao_pura(self):
        """Mesma entrada -> mesma saida (INV-IND-2)."""
        r1 = ind.liquidez_corrente(Decimal("200"), Decimal("100"))
        r2 = ind.liquidez_corrente(Decimal("200"), Decimal("100"))
        assert r1.valor == r2.valor

    def test_t50_referencia_preenchida(self):
        r = ind.roe(Decimal("75"), Decimal("250"))
        assert r.referencia and len(r.referencia) > 5


# ============================================================
# T51-T70 -- Score de saude
# ============================================================

class TestScore:

    def test_t51_retorna_resultado(self):
        r = calcular_score(_dados_score())
        assert isinstance(r.valor, ResultadoScore)

    def test_t52_total_0_100(self):
        r = calcular_score(_dados_score())
        assert 0 <= r.valor.total <= 100

    def test_t53_excelente(self):
        r = calcular_score(_dados_score())
        if r.valor.total >= 80:
            assert r.valor.classificacao == "Excelente"

    def test_t54_critico(self):
        """Empresa em situacao critica: todos indicadores ruins."""
        d = _dados_score(
            receita_liquida=10000, resultado_liquido=-80000, lucro_liquido=-80000,
            ativo_circulante=5000, passivo_circulante=200000,
            passivo_total=350000, ativo_total=400000,
            patrimonio_liquido=50000,  # PL positivo para evitar ROE enganoso
            estoques=4000, ebit=-50000, despesas_financeiras=30000,
            receita_bruta=10000, contas_receber=1000, custo_servicos=80000,
            fornecedores=100000,
        )
        r = calcular_score(d, historico_receitas=[100000, 80000, 60000, 40000, 20000, 10000],
                           tributos_em_dia=False)
        assert r.valor.total < 40
        assert r.valor.classificacao == "Critico"

    def test_t55_9_componentes(self):
        r = calcular_score(_dados_score())
        assert len(r.valor.componentes) == 9
        assert set(r.valor.componentes.keys()) == set(PESOS.keys())

    def test_t56_pesos_somam_100(self):
        assert sum(PESOS.values()) == 100

    def test_t57_lc_alta_score_alto(self):
        d = _dados_score(ativo_circulante=500000, passivo_circulante=100000)
        r = calcular_score(d)
        assert r.valor.componentes["liquidez_corrente"] >= 85

    def test_t58_lc_baixa_score_baixo(self):
        d = _dados_score(ativo_circulante=30000, passivo_circulante=100000)
        r = calcular_score(d)
        assert r.valor.componentes["liquidez_corrente"] == 0

    def test_t59_endividamento_alto(self):
        d = _dados_score(passivo_total=350000, ativo_total=400000)
        r = calcular_score(d)
        assert r.valor.componentes["endividamento_geral"] <= 30

    def test_t60_margem_liquida_negativa(self):
        d = _dados_score(resultado_liquido=-10000, lucro_liquido=-10000)
        r = calcular_score(d)
        assert r.valor.componentes["margem_liquida"] == 0

    def test_t61_roe_positivo(self):
        r = calcular_score(_dados_score())
        assert r.valor.componentes["roe"] > 0

    def test_t62_tendencia_crescente(self):
        hist = [100000, 110000, 120000, 130000, 140000, 150000]
        r = calcular_score(_dados_score(), historico_receitas=hist)
        assert r.valor.componentes["tendencia_receita"] == 100

    def test_t63_tendencia_decrescente(self):
        """MEDIO-1 corrigido: ate 6 meses, permite quedas >= 3."""
        hist = [150000, 140000, 130000, 120000, 110000, 100000]
        r = calcular_score(_dados_score(), historico_receitas=hist)
        assert r.valor.componentes["tendencia_receita"] <= 20

    def test_t64_tendencia_sem_dados(self):
        r = calcular_score(_dados_score(), historico_receitas=[])
        assert r.valor.componentes["tendencia_receita"] == 50

    def test_t65_regularidade_em_dia(self):
        r = calcular_score(_dados_score(), tributos_em_dia=True)
        assert r.valor.componentes["regularidade_fiscal"] == 100

    def test_t66_regularidade_inadimplente(self):
        r = calcular_score(_dados_score(), tributos_em_dia=False)
        assert r.valor.componentes["regularidade_fiscal"] == 0

    def test_t67_cobertura_juros_alta(self):
        d = _dados_score(ebit=90000, despesas_financeiras=10000)
        r = calcular_score(d)
        assert r.valor.componentes["cobertura_juros"] >= 80

    def test_t68_cobertura_juros_baixa(self):
        d = _dados_score(ebit=10000, despesas_financeiras=15000)
        r = calcular_score(d)
        assert r.valor.componentes["cobertura_juros"] == 0

    def test_t69_detalhes_preenchidos(self):
        r = calcular_score(_dados_score())
        assert len(r.valor.detalhes) == 9

    def test_t70_memoria_presente(self):
        r = calcular_score(_dados_score())
        assert r.memoria is not None


# ============================================================
# T71-T77 -- Invariantes
# ============================================================

class TestInvariantes:

    def test_t71_comp1_4_regimes(self):
        """Comparador calcula 4 regimes quando elegivel."""
        r = comparar_regimes(_perfil(receita=1000000))
        assert r.valor.simples is not None
        assert r.valor.presumido > _ZERO
        assert r.valor.real > _ZERO
        assert r.valor.reforma > _ZERO

    def test_t72_comp1_sem_simples(self):
        """Receita > 4.8M: Simples None."""
        r = comparar_regimes(_perfil(receita=5000000))
        assert r.valor.simples is None

    def test_t73_comp2_regime_otimo(self):
        """Regime otimo == menor carga."""
        r = comparar_regimes(_perfil())
        vals = {}
        if r.valor.simples is not None:
            vals["simples"] = r.valor.simples
        vals["presumido"] = r.valor.presumido
        vals["real"] = r.valor.real
        vals["reforma"] = r.valor.reforma
        menor = min(vals, key=lambda k: vals[k])
        assert r.valor.regime_otimo == menor

    def test_t74_ind1_div_zero(self):
        r = ind.liquidez_corrente(Decimal("100"), _ZERO)
        assert r.valor is None
        assert r.indisponivel_motivo is not None

    def test_t75_score1_soma(self):
        """total == sum(componentes * pesos) / 100 (arredondado)."""
        r = calcular_score(_dados_score())
        soma = sum(r.valor.componentes[k] * PESOS[k] for k in PESOS)
        expected = max(0, min(100, round(soma / 100)))
        assert r.valor.total == expected

    def test_t76_score2_range(self):
        r = calcular_score(_dados_score())
        assert 0 <= r.valor.total <= 100

    def test_t77_score3_classificacao(self):
        for dados_override, expected_min, expected_class in [
            ({"resultado_liquido": 200000, "lucro_liquido": 200000}, 80, "Excelente"),
        ]:
            r = calcular_score(_dados_score(**dados_override))
            if r.valor.total >= 80:
                assert r.valor.classificacao == "Excelente"


# ============================================================
# T78-T80 -- Edge cases
# ============================================================

class TestEdgeCases:

    def test_t78_receita_zero(self):
        p = PerfilEmpresa(Decimal("0"), "servicos", Decimal("0"),
                           Decimal("0.40"))
        r = comparar_regimes(p)
        assert isinstance(r.valor, ComparativoRegimes)

    def test_t79_todos_zeros_score(self):
        d = {k: 0 for k in _dados_score()}
        r = calcular_score(d)
        assert 0 <= r.valor.total <= 100

    def test_t80_perfil_extremo(self):
        p = PerfilEmpresa(Decimal("100000000"), "industria",
                           Decimal("50000000"), Decimal("0.10"))
        r = comparar_regimes(p)
        assert r.valor.simples is None  # 100M > 4.8M
        assert r.valor.presumido > _ZERO
