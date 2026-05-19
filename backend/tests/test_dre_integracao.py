"""
Testes BLOCO 3B.2 -- Integracao DRE motor novo com endpoint e financeiro_service.

T54-T58: endpoint com flag=novo
T59-T63: endpoint com flag=legado (regressao)
T64-T65: feature flag invalida e ausente
T66:     reproducao cenario Fase 2 via endpoint
T67:     empresa sem lancamentos
T68:     tenant isolation preservada
T69:     norma no campo memoria
T70:     lancamento com campo nullable NULL
T71:     consistencia simulador frontend vs motor
"""

import os
import pytest
from decimal import Decimal

from tests.conftest import (
    _auth_header, _criar_usuario, _criar_escritorio, _criar_empresa,
)
from data.database import models
from services.contabil.core import money
from services.contabil.dre import calcular_dre


# -- Helpers ------------------------------------------------------------------

def _criar_lancamento(db, empresa_id, ano, mes, **kwargs):
    from datetime import datetime, timezone
    agora = datetime.now(timezone.utc).isoformat()
    defaults = {
        "receita_bruta": 0, "deducoes_receita": 0, "custo_servicos": 0,
        "despesas_adm": 0, "despesas_comerciais": 0, "despesas_financeiras": 0,
        "outras_despesas": 0, "ir_csll": 0, "entradas_caixa": 0, "saidas_caixa": 0,
        "saldo_inicial_caixa": 0, "caixa_equivalentes": 0, "contas_receber": 0,
        "estoques": 0, "outros_ativo_circ": 0, "ativo_nao_circulante": 0,
        "fornecedores": 0, "emprestimos_cp": 0, "tributos_pagar": 0,
        "outros_passivo_circ": 0, "passivo_nao_circulante": 0, "capital_social": 0,
        "reservas": 0, "lucros_acumulados": 0, "folha_pagamento": 0,
        "depreciacao_amortizacao": 0,
    }
    defaults.update(kwargs)
    lanc = models.LancamentoMensal(
        empresa_id=empresa_id, ano=ano, mes=mes,
        criado_em=agora, atualizado_em=agora, **defaults,
    )
    db.add(lanc)
    db.flush()
    return lanc


def _fase2_lancamento(db, empresa_id):
    """Cenario Fase 2 mes 1 com DFin=2000."""
    return _criar_lancamento(
        db, empresa_id, 2025, 1,
        receita_bruta=105000, deducoes_receita=5000, custo_servicos=30000,
        despesas_adm=15000, despesas_comerciais=5000, outras_despesas=1000,
        depreciacao_amortizacao=1500, despesas_financeiras=2000, ir_csll=3000,
    )


# ============================================================
# T54-T58 -- Endpoint com flag=novo
# ============================================================

class TestEndpointNovo:

    def test_t54_dre_endpoint_novo_retorna_cascata(self, client, db, admin_a, empresa_a):
        _criar_lancamento(db, empresa_a.id, 2025, 10,
                          receita_bruta=200000, deducoes_receita=10000,
                          custo_servicos=60000, despesas_adm=25000,
                          despesas_comerciais=8000, outras_despesas=2000,
                          depreciacao_amortizacao=5000, despesas_financeiras=3000,
                          ir_csll=12000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{empresa_a.id}?ano=2025&mes=10&dre_engine=novo",
            headers=_auth_header(admin_a),
        )
        # admin nao e master, entao override nao funciona — usa flag global
        # Para testar motor novo via endpoint, precisamos de master
        assert resp.status_code == 200

    def test_t55_dre_master_override_novo(self, client, db, master_user, escritorio_a):
        emp = _criar_empresa(db, "EmpNova", escritorio_a.id, master_user.id)
        _criar_lancamento(db, emp.id, 2025, 10,
                          receita_bruta=200000, deducoes_receita=10000,
                          custo_servicos=60000, despesas_adm=25000,
                          despesas_comerciais=8000, outras_despesas=2000,
                          depreciacao_amortizacao=5000, despesas_financeiras=3000,
                          ir_csll=12000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{emp.id}?ano=2025&mes=10&dre_engine=novo",
            headers=_auth_header(master_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "cascata" in body
        assert "engine_version" in body
        assert body["engine_version"] == "3.0.0"
        assert "convencao_sinais" in body

    def test_t56_cascata_valores_positivos(self, client, db, master_user, escritorio_a):
        """Valores na cascata sao sempre positivos (Observacao 1)."""
        emp = _criar_empresa(db, "EmpSinal", escritorio_a.id, master_user.id)
        _criar_lancamento(db, emp.id, 2025, 10,
                          receita_bruta=100000, deducoes_receita=5000,
                          custo_servicos=30000, despesas_adm=10000,
                          ir_csll=5000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{emp.id}?ano=2025&mes=10&dre_engine=novo",
            headers=_auth_header(master_user),
        )
        body = resp.json()
        for item in body.get("cascata", []):
            assert item["valor"] >= 0, (
                f"Valor negativo na cascata: {item['linha']} = {item['valor']}. "
                "Valores devem ser sempre positivos (Observacao 1 BLOCO 3B.2)."
            )

    def test_t57_metricas_ebit_correto(self, client, db, master_user, escritorio_a):
        """metricas.ebit deve ser EBIT correto (sem DFin)."""
        emp = _criar_empresa(db, "EmpEBIT", escritorio_a.id, master_user.id)
        _criar_lancamento(db, emp.id, 2025, 10,
                          receita_bruta=200000, deducoes_receita=10000,
                          custo_servicos=60000, despesas_adm=25000,
                          despesas_comerciais=8000, outras_despesas=2000,
                          depreciacao_amortizacao=5000, despesas_financeiras=3000,
                          ir_csll=12000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{emp.id}?ano=2025&mes=10&dre_engine=novo",
            headers=_auth_header(master_user),
        )
        body = resp.json()
        m = body["metricas"]
        assert m["ebit"] == 90000.0, f"EBIT deveria ser 90000, recebeu {m['ebit']}"
        assert m["lair"] == 87000.0, f"LAIR deveria ser 87000, recebeu {m['lair']}"
        assert m["ebitda"] == 95000.0

    def test_t58_memoria_presente(self, client, db, master_user, escritorio_a):
        emp = _criar_empresa(db, "EmpMem", escritorio_a.id, master_user.id)
        _criar_lancamento(db, emp.id, 2025, 10, receita_bruta=100000, ir_csll=5000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{emp.id}?ano=2025&mes=10&dre_engine=novo",
            headers=_auth_header(master_user),
        )
        body = resp.json()
        assert "memoria" in body
        assert body["memoria"]["versao"] == "3.0.0"


# ============================================================
# T59-T63 -- Endpoint com flag=legado (regressao)
# ============================================================

class TestEndpointLegado:

    def test_t59_dre_legado_sem_engine_version(self, client, db, admin_a, empresa_a):
        _criar_lancamento(db, empresa_a.id, 2025, 6, receita_bruta=100000, ir_csll=5000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{empresa_a.id}?ano=2025&mes=6",
            headers=_auth_header(admin_a),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "engine_version" not in body

    def test_t60_legado_cascata_com_sinais_negativos(self, client, db, admin_a, empresa_a):
        """Legado mantém valores negativos na cascata (comportamento original)."""
        _criar_lancamento(db, empresa_a.id, 2025, 7, receita_bruta=100000,
                          deducoes_receita=5000, ir_csll=3000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{empresa_a.id}?ano=2025&mes=7",
            headers=_auth_header(admin_a),
        )
        body = resp.json()
        deducao = next(i for i in body["cascata"] if "Dedu" in i["linha"])
        assert deducao["valor"] < 0, "Legado deve manter sinais negativos"

    def test_t61_legado_ebit_inclui_financeiras(self, client, db, admin_a, empresa_a):
        """Regressao: legado preserva ebit = lucro_bruto - (adm+com+fin+out)."""
        _criar_lancamento(db, empresa_a.id, 2025, 8,
                          receita_bruta=105000, deducoes_receita=5000,
                          custo_servicos=30000, despesas_adm=15000,
                          despesas_comerciais=5000, despesas_financeiras=2000,
                          outras_despesas=1000, ir_csll=3000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{empresa_a.id}?ano=2025&mes=8",
            headers=_auth_header(admin_a),
        )
        m = resp.json()["metricas"]
        # Legado: ebit = 100000 - 30000 - (15000+5000+2000+1000) = 47000
        assert m["ebit"] == 47000.0

    def test_t62_legado_sem_campo_lair(self, client, db, admin_a, empresa_a):
        """Legado: lair = ebit (fallback)."""
        _criar_lancamento(db, empresa_a.id, 2025, 9,
                          receita_bruta=100000, despesas_financeiras=5000, ir_csll=3000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{empresa_a.id}?ano=2025&mes=9",
            headers=_auth_header(admin_a),
        )
        m = resp.json()["metricas"]
        assert m["lair"] == m["ebit"], "No legado, lair fallback to ebit"

    def test_t63_legado_sem_ebit_legado(self, client, db, admin_a, empresa_a):
        _criar_lancamento(db, empresa_a.id, 2025, 5, receita_bruta=50000)
        db.commit()
        resp = client.get(
            f"/api/financeiro/dre/{empresa_a.id}?ano=2025&mes=5",
            headers=_auth_header(admin_a),
        )
        m = resp.json()["metricas"]
        assert "ebit_legado" not in m


# ============================================================
# T64-T65 -- Feature flag
# ============================================================

class TestFeatureFlag:

    def test_t64_flag_invalida_usa_legado(self):
        """Flag invalida deve produzir fallback legado."""
        from services.financeiro_service import _usar_motor_novo
        assert _usar_motor_novo("foobar") is False
        assert _usar_motor_novo(None) is False

    def test_t65_override_novo(self):
        from services.financeiro_service import _usar_motor_novo
        assert _usar_motor_novo("novo") is True
        assert _usar_motor_novo("NOVO") is True  # case-insensitive
        assert _usar_motor_novo("foobar") is False


# ============================================================
# T66-T69 -- Cenarios especiais
# ============================================================

class TestCenariosEspeciais:

    def test_t66_fase2_via_endpoint(self, client, db, master_user, escritorio_a):
        """Reproducao cenario Fase 2: ebit=47500 (novo) vs ebit=47000 (legado)."""
        emp = _criar_empresa(db, "Fase2", escritorio_a.id, master_user.id)
        _fase2_lancamento(db, emp.id)
        db.commit()

        resp = client.get(
            f"/api/financeiro/dre/{emp.id}?ano=2025&mes=1&dre_engine=novo",
            headers=_auth_header(master_user),
        )
        m = resp.json()["metricas"]
        assert m["ebit"] == 47500.0, f"EBIT deveria ser 47500 (novo), recebeu {m['ebit']}"
        assert m.get("ebit_legado") == 47000.0, f"ebit_legado deveria ser 47000"

    def test_t67_sem_lancamentos(self, client, db, admin_a, empresa_a):
        """Empresa sem lancamentos retorna sem_dados."""
        resp = client.get(
            f"/api/financeiro/dre/{empresa_a.id}?ano=2020&mes=1",
            headers=_auth_header(admin_a),
        )
        assert resp.status_code == 200
        assert resp.json().get("sem_dados") is True

    def test_t68_tenant_isolation(self, client, db, admin_a, empresa_b):
        """BLOCO 1 continua protegendo: admin_a nao acessa empresa_b."""
        resp = client.get(
            f"/api/financeiro/dre/{empresa_b.id}?ano=2025&mes=1",
            headers=_auth_header(admin_a),
        )
        assert resp.status_code == 404

    def test_t69_norma_cpc26(self):
        """Motor retorna norma CPC 26 na memoria."""
        dados = {"receita_bruta": 100000, "ir_csll": 5000}
        r = calcular_dre(dados, "2025-10")
        norma_str = r.memoria.norma.value if hasattr(r.memoria.norma, "value") else str(r.memoria.norma)
        assert "CPC 26" in norma_str


# ============================================================
# T70-T71 -- Refinamentos obrigatorios
# ============================================================

class TestRefinamentosIntegracao:

    def test_t70_null_handling_wrapper(self, db, escritorio_a, admin_a):
        """Lancamento com campo nullable NULL -> wrapper converte a 0 sem erro."""
        emp = _criar_empresa(db, "EmpNull", escritorio_a.id, admin_a.id)
        lanc = models.LancamentoMensal(
            empresa_id=emp.id, ano=2025, mes=1,
            receita_bruta=100000, deducoes_receita=None,
            custo_servicos=None, despesas_adm=None,
            despesas_comerciais=None, despesas_financeiras=None,
            outras_despesas=None, ir_csll=None,
            depreciacao_amortizacao=None,
            entradas_caixa=0, saidas_caixa=0, saldo_inicial_caixa=0,
            caixa_equivalentes=0, contas_receber=0, estoques=0,
            outros_ativo_circ=0, ativo_nao_circulante=0,
            fornecedores=0, emprestimos_cp=0, tributos_pagar=0,
            outros_passivo_circ=0, passivo_nao_circulante=0,
            capital_social=0, reservas=0, lucros_acumulados=0,
            folha_pagamento=0,
            criado_em="2025-01-01T00:00:00Z", atualizado_em="2025-01-01T00:00:00Z",
        )
        db.add(lanc)
        db.flush()

        from services.financeiro_service import _calcular_dre_from_lancamento
        res = _calcular_dre_from_lancamento(lanc)
        assert res.valor.receita_bruta == money(100000)
        assert res.valor.receita_liquida == money(100000)  # deducoes=None -> 0

    def test_t71_consistencia_simulador_vs_motor(self):
        """Motor e simulador frontend devem produzir mesmo EBITDA.

        Simulador: ebitda = lucrobruto - desp_operacionais (sem financeiras)
        Motor:     ebitda = ebit + D&A = (LB - adm - com - out - D&A) + D&A = LB - adm - com - out

        Com D&A=0, EBITDA = LB - despesas_operacionais_sem_financeiras.
        """
        rb, custos, desp_op = 200000, 60000, 35000  # adm+com+out
        lucro_bruto_sim = rb - custos  # 140000
        ebitda_simulador = lucro_bruto_sim - desp_op  # 105000

        dados_motor = {
            "receita_bruta": rb, "deducoes_receita": 0,
            "custo_servicos": custos, "despesas_adm": 20000,
            "despesas_comerciais": 10000, "outras_despesas": 5000,
            "depreciacao_amortizacao": 0, "despesas_financeiras": 5000,
            "ir_csll": 10000,
        }
        r = calcular_dre(dados_motor, "2025-10")
        ebitda_motor = float(r.valor.ebitda)

        assert ebitda_motor == ebitda_simulador, (
            f"EBITDA motor={ebitda_motor} != simulador={ebitda_simulador}. "
            "Divergencia entre motor e simulador frontend."
        )
