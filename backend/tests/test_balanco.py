"""
Testes BLOCO 3C.1 -- Balanco Patrimonial gerencial.

47 testes:
  T1-T8:   Totalizadores
  T9-T12:  Invariante fechada (sintetico equilibrado)
  T13-T20: Invariante aberta (dados reais)
  T21-T24: Gap aritmetica
  T25-T28: Avisos e limitacoes
  T29-T34: Edge cases
  T35-T37: Comparativo (periodo anterior)
  T38-T40: Integracao flag + endpoint
  T41-T43: Planilha referencia
  T44-T46: Validacao cruzada DRE -> Lucros Acumulados
  T47:     Metodo assertir_fechamento
"""

import pytest
from decimal import Decimal

from services.contabil.core import money, IntegridadeContabilError, ResultadoCalculo, MemoriaCalculo, NormaContabil
from services.contabil.balanco import calcular_balanco, BalancoPatrimonial
from services.contabil.dre import calcular_dre

_ZERO = Decimal("0")


# -- Fixtures -----------------------------------------------------------------

def _bp_equilibrado():
    """BP sintetico que fecha: AT=100k = PT+PL=100k."""
    return {
        "caixa_equivalentes": 30000, "contas_receber": 20000,
        "estoques": 10000, "outros_ativo_circ": 5000,
        "ativo_nao_circulante": 35000,
        "fornecedores": 15000, "emprestimos_cp": 10000,
        "tributos_pagar": 5000, "outros_passivo_circ": 5000,
        "passivo_nao_circulante": 10000,
        "capital_social": 30000, "reservas": 5000, "lucros_acumulados": 20000,
    }
    # AC=65k, ANC=35k, AT=100k, PC=35k, PNC=10k, PT=45k, PL=55k, P+PL=100k


def _bp_alpha_mes1():
    """Alpha mes 1 — dados reais da Fase 2. Gap = -13000."""
    return {
        "caixa_equivalentes": 20000, "contas_receber": 15000,
        "estoques": 5000, "outros_ativo_circ": 0,
        "ativo_nao_circulante": 30000,
        "fornecedores": 8000, "emprestimos_cp": 10000,
        "tributos_pagar": 5000, "outros_passivo_circ": 0,
        "passivo_nao_circulante": 0,
        "capital_social": 50000, "reservas": 0, "lucros_acumulados": 10000,
        "depreciacao_amortizacao": 1500,
    }
    # AT=70k, P+PL=83k, gap=-13k


def _bp_industria_mes1():
    """Industria mes 1 — gap grande negativo."""
    return {
        "caixa_equivalentes": 180000, "contas_receber": 81500,
        "estoques": 65200, "outros_ativo_circ": 15000,
        "ativo_nao_circulante": 350000,
        "fornecedores": 65200, "emprestimos_cp": 50000,
        "tributos_pagar": 48900, "outros_passivo_circ": 10000,
        "passivo_nao_circulante": 200000,
        "capital_social": 300000, "reservas": 50000, "lucros_acumulados": 15000,
        "depreciacao_amortizacao": 20000,
    }
    # AT=691700, P+PL=739100, gap=-47400


# ============================================================
# T1-T8 -- Totalizadores
# ============================================================

class TestTotalizadores:

    def test_t1_ativo_circulante(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.ativo_circulante == money(65000)

    def test_t2_ativo_nao_circulante(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.ativo_nao_circulante == money(35000)

    def test_t3_ativo_total(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.ativo_total == money(100000)

    def test_t4_passivo_circulante(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.passivo_circulante == money(35000)

    def test_t5_passivo_nao_circulante(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.passivo_nao_circulante == money(10000)

    def test_t6_passivo_total(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.passivo_total == money(45000)

    def test_t7_patrimonio_liquido(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.patrimonio_liquido == money(55000)

    def test_t8_passivo_mais_pl(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.passivo_mais_pl == money(100000)


# ============================================================
# T9-T12 -- Invariante fechada
# ============================================================

class TestInvarianteFechada:

    def test_t9_equilibrado_invariante_true(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.invariante_atendida is True

    def test_t10_equilibrado_gap_zero(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.gap_valor == money(0)

    def test_t11_equilibrado_natureza(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.gap_natureza == "equilibrado"

    def test_t12_equilibrado_sem_aviso_desequilibrio(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert not any("desequilibrio" in a.lower() for a in r.avisos)


# ============================================================
# T13-T20 -- Invariante aberta (dados reais)
# ============================================================

class TestInvarianteAberta:

    def test_t13_alpha_mes1_aberto(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert r.valor.invariante_atendida is False

    def test_t14_alpha_mes1_gap_valor(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert r.valor.gap_valor == money(-13000)

    def test_t15_alpha_mes1_natureza(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert r.valor.gap_natureza == "passivo_pl_maior"

    def test_t16_industria_gap_grande(self):
        r = calcular_balanco(_bp_industria_mes1(), "2025-01")
        assert r.valor.invariante_atendida is False
        assert r.valor.gap_valor == money(-47400)

    def test_t17_aviso_desequilibrio_presente(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert any("desequilibrio" in a.lower() for a in r.avisos)

    def test_t18_gap_positivo_ativo_maior(self):
        d = _bp_equilibrado()
        d["caixa_equivalentes"] = 50000  # +20k no ativo
        r = calcular_balanco(d, "2025-10")
        assert r.valor.gap_natureza == "ativo_maior"
        assert r.valor.gap_valor == money(20000)

    def test_t19_gap_percentual_calculado(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert r.valor.gap_percentual > _ZERO

    def test_t20_sem_excecao_bp_aberto(self):
        """Motor NAO levanta excecao para BP aberto — reporta apenas."""
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert isinstance(r.valor, BalancoPatrimonial)


# ============================================================
# T21-T24 -- Gap aritmetica
# ============================================================

class TestGapAritmetica:

    def test_t21_gap_formula(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert r.valor.gap_valor == money(r.valor.ativo_total - r.valor.passivo_mais_pl)

    def test_t22_gap_abs_pct(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        expected_pct = money(abs(r.valor.gap_valor) / r.valor.passivo_mais_pl * Decimal("100"))
        assert abs(r.valor.gap_percentual - expected_pct) <= money("0.01")

    def test_t23_equilibrado_gap_simetria(self):
        """Gap exato = 0 para BP equilibrado."""
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.gap_valor == _ZERO

    def test_t24_gap_negativo_valor(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert r.valor.gap_valor < _ZERO


# ============================================================
# T25-T28 -- Avisos e limitacoes
# ============================================================

class TestAvisosLimitacoes:

    def test_t25_limitacao_anc_nao_desdobrado(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert any("nao desdobrado" in a.lower() or "CPC 26" in a for a in r.avisos)

    def test_t26_limitacao_da_quando_presente(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert any("Depreciacao acumulada" in a or "D&A do periodo" in a for a in r.avisos)

    def test_t27_limitacao_lucros_manuais(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert any("Lucros Acumulados" in a and "manualmente" in a for a in r.avisos)

    def test_t28_anc_nomeado_nao_desdobrado(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        anc_linha = next(l for l in r.valor.linhas if l.codigo == "ANC.01")
        assert "nao desdobrado" in anc_linha.descricao.lower()


# ============================================================
# T29-T34 -- Edge cases
# ============================================================

class TestEdgeCases:

    def test_t29_tudo_zero(self):
        d = {k: 0 for k in _bp_equilibrado()}
        r = calcular_balanco(d, "2025-01")
        assert r.valor.ativo_total == _ZERO
        assert r.valor.invariante_atendida is True

    def test_t30_pl_negativo(self):
        d = _bp_equilibrado()
        d["lucros_acumulados"] = -100000
        r = calcular_balanco(d, "2025-01")
        assert r.valor.patrimonio_liquido < _ZERO

    def test_t31_passivo_maior_que_ativo(self):
        d = _bp_equilibrado()
        d["emprestimos_cp"] = 500000
        r = calcular_balanco(d, "2025-01")
        assert r.valor.gap_natureza == "passivo_pl_maior"

    def test_t32_campo_ausente_tratado_zero(self):
        d = {"caixa_equivalentes": 50000}
        r = calcular_balanco(d, "2025-01")
        assert r.valor.ativo_total == money(50000)

    def test_t33_valores_decimais(self):
        """Decimal preciso: reduzir ativo e passivo por 0.01 cada mantém equilíbrio."""
        d = _bp_equilibrado()
        d["caixa_equivalentes"] = "29999.99"   # -0.01 no ativo
        d["outros_passivo_circ"] = "4999.99"   # -0.01 no passivo
        r = calcular_balanco(d, "2025-10")
        assert r.valor.ativo_total == money("99999.99")
        assert r.valor.passivo_mais_pl == money("99999.99")
        assert r.valor.invariante_atendida is True  # ambos reduziram igualmente

    def test_t34_none_tratado_zero(self):
        d = _bp_equilibrado()
        d["estoques"] = None
        r = calcular_balanco(d, "2025-10")
        assert r.valor.ativo_circulante == money(55000)  # 65k - 10k estoques


# ============================================================
# T35-T37 -- Comparativo (periodo anterior)
# ============================================================

class TestComparativo:

    def test_t35_com_dados_anteriores(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10",
                             dados_anterior=_bp_equilibrado())
        assert isinstance(r.valor, BalancoPatrimonial)

    def test_t36_sem_dados_anteriores(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10", dados_anterior=None)
        assert isinstance(r.valor, BalancoPatrimonial)

    def test_t37_dre_none_sem_erro(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10", dre_periodo=None)
        assert isinstance(r.valor, BalancoPatrimonial)


# ============================================================
# T38-T40 -- Integracao (isolamento e linhas)
# ============================================================

class TestIntegracao:

    def test_t38_linhas_completas(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        codigos = [l.codigo for l in r.valor.linhas]
        assert "AC" in codigos
        assert "ANC" in codigos
        assert "AT" in codigos
        assert "PC" in codigos
        assert "PT" in codigos
        assert "PL" in codigos
        assert "PPL" in codigos

    def test_t39_memoria_presente(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.memoria is not None
        assert r.memoria.versao == "3.0.0"

    def test_t40_norma_cpc26_bp(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        norma_str = r.memoria.norma.value if hasattr(r.memoria.norma, "value") else str(r.memoria.norma)
        assert "CPC 26" in norma_str


# ============================================================
# T41-T43 -- Planilha referencia
# ============================================================

class TestPlanilhaReferencia:

    def test_t41_empresa_equilibrada(self):
        """AT=100k, P+PL=100k, gap=0."""
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        assert r.valor.ativo_total == money(100000)
        assert r.valor.passivo_mais_pl == money(100000)
        assert r.valor.invariante_atendida is True

    def test_t42_empresa_com_gap(self):
        """Alpha mes 1: AT=70k, P+PL=83k, gap=-13k."""
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        assert r.valor.ativo_total == money(70000)
        assert r.valor.passivo_mais_pl == money(83000)
        assert r.valor.gap_valor == money(-13000)

    def test_t43_empresa_pl_negativo(self):
        """Cenario: PL = -20k (empresa em falencia tecnica)."""
        d = {
            "caixa_equivalentes": 5000, "contas_receber": 3000,
            "estoques": 2000, "outros_ativo_circ": 0,
            "ativo_nao_circulante": 10000,
            "fornecedores": 8000, "emprestimos_cp": 15000,
            "tributos_pagar": 7000, "outros_passivo_circ": 0,
            "passivo_nao_circulante": 30000,
            "capital_social": 10000, "reservas": 0, "lucros_acumulados": -30000,
        }
        r = calcular_balanco(d, "2025-10")
        assert r.valor.patrimonio_liquido == money(-20000)
        assert r.valor.ativo_total == money(20000)
        assert r.valor.passivo_mais_pl == money(40000)  # PT=60k, PL=-20k -> 40k
        assert r.valor.gap_natureza == "passivo_pl_maior"


# ============================================================
# T44-T46 -- Validacao cruzada DRE -> Lucros Acumulados
# ============================================================

class TestValidacaoCruzadaDRE:

    def _dre_res(self, rl: float) -> ResultadoCalculo:
        """DRE com resultado liquido especifico."""
        dados = {
            "receita_bruta": max(rl, 0) + 50000,
            "deducoes_receita": 0, "custo_servicos": 50000 - min(rl, 0),
            "despesas_adm": 0, "despesas_comerciais": 0, "outras_despesas": 0,
            "depreciacao_amortizacao": 0, "despesas_financeiras": 0, "ir_csll": 0,
        }
        return calcular_dre(dados, "2025-10")

    def test_t44_la_consistente_com_dre(self):
        """LA variou 10k, DRE RL=10k -> sem aviso de inconsistencia."""
        d_atual = _bp_equilibrado()
        d_atual["lucros_acumulados"] = 30000  # +10k vs 20k
        d_ant = _bp_equilibrado()
        d_ant["lucros_acumulados"] = 20000

        dre = self._dre_res(10000.0)
        r = calcular_balanco(d_atual, "2025-10", dados_anterior=d_ant, dre_periodo=dre)
        assert not any("nao explicada" in a for a in r.avisos)

    def test_t45_la_inconsistente_com_dre(self):
        """LA variou 10k, DRE RL=5k -> aviso de inconsistencia."""
        d_atual = _bp_equilibrado()
        d_atual["lucros_acumulados"] = 30000
        d_ant = _bp_equilibrado()
        d_ant["lucros_acumulados"] = 20000

        dre = self._dre_res(5000.0)
        r = calcular_balanco(d_atual, "2025-10", dados_anterior=d_ant, dre_periodo=dre)
        assert any("nao explicada" in a for a in r.avisos)

    def test_t46_sem_dados_anteriores_sem_validacao(self):
        """Sem dados anteriores, pula validacao sem erro."""
        dre = self._dre_res(10000.0)
        r = calcular_balanco(_bp_equilibrado(), "2025-10", dados_anterior=None, dre_periodo=dre)
        assert not any("nao explicada" in a for a in r.avisos)


# ============================================================
# T47 -- Metodo assertir_fechamento
# ============================================================

class TestAssertirFechamento:

    def test_t47_assertir_fechamento_equilibrado_passa(self):
        r = calcular_balanco(_bp_equilibrado(), "2025-10")
        r.valor.assertir_fechamento(Decimal("0"))  # nao levanta

    def test_t47b_assertir_fechamento_aberto_levanta(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01")
        with pytest.raises(IntegridadeContabilError, match="Invariante BP"):
            r.valor.assertir_fechamento(Decimal("0.01"))


# ============================================================
# D&A acumulada observada
# ============================================================

class TestDAObservada:

    def test_da_acumulada_com_historico(self):
        hist = [
            {"ano": 2025, "mes": m, "depreciacao_amortizacao": 1500}
            for m in range(1, 7)
        ]
        r = calcular_balanco(_bp_alpha_mes1(), "2025-06", historico_da=hist)
        obs = r.valor.depreciacao_acumulada_observada
        assert obs is not None
        assert obs.valor == money(9000)
        assert obs.desde_periodo == "2025-01"
        assert obs.ate_periodo == "2025-06"

    def test_da_acumulada_sem_historico(self):
        r = calcular_balanco(_bp_alpha_mes1(), "2025-01", historico_da=None)
        assert r.valor.depreciacao_acumulada_observada is None
