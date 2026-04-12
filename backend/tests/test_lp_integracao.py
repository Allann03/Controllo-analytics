"""
Testes de integracao end-to-end do Lucro Presumido (BLOCO 3F.2).

Verifica o fluxo completo: endpoint -> service -> dispatch -> motor -> adapter -> resposta JSON.

5 testes: T-INT-01 a T-INT-05.
"""

import json
import os
import pytest
from decimal import Decimal
from unittest.mock import patch

from tests.conftest import (
    _criar_escritorio, _criar_usuario, _criar_empresa,
    _auth_header, _agora,
)
from data.database import models


# -- Helpers ------------------------------------------------------------------

def _setup_empresa_fiscal(db, cnae, regime="presumido"):
    """Cria infraestrutura completa com empresa e dados fiscais."""
    esc = _criar_escritorio(db, "Int Esc", "int-esc")
    user = _criar_usuario(db, "int_master", esc.id, is_admin=True, is_master=True)
    empresa = _criar_empresa(db, "Empresa Integracao", esc.id, user.id)
    fiscal = models.EmpresaFiscal(
        empresa_id=empresa.id,
        cnae=cnae,
        cnae_descricao="Atividade integracao",
        regime_tributario=regime,
        anexo_simples="III",
        criado_em=_agora(),
        atualizado_em=_agora(),
    )
    db.add(fiscal)

    # Lancamento para que endpoints nao precisem de query params
    lanc = models.LancamentoMensal(
        empresa_id=empresa.id,
        ano=2026, mes=3,
        receita_bruta=500_000,
        custo_servicos=100_000,
        criado_em=_agora(),
        atualizado_em=_agora(),
    )
    db.add(lanc)
    db.commit()
    return empresa, user


# -- Testes -------------------------------------------------------------------

class TestIntegracaoLP:
    """T-INT-01 a T-INT-05: integracao end-to-end."""

    def test_int_01_comparar_regimes_motor_novo(self, client, db):
        """T-INT-01: endpoint /comparar-regimes com flag novo retorna presumido correto."""
        empresa, user = _setup_empresa_fiscal(db, cnae="4711-3/02", regime="presumido")
        headers = _auth_header(user)

        with patch("services.simulacao_tributaria_service.LP_ENGINE", "novo"):
            with patch("services.simulacao_tributaria_service._usar_motor_lp_novo", return_value=True):
                resp = client.get(
                    f"/api/financeiro/comparar-regimes/{empresa.id}"
                    f"?receita_bruta=500000&custo_servicos=100000",
                    headers=headers,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "presumido" in data
        pres = data["presumido"]
        assert pres["label"] == "Lucro Presumido"
        # Para comercio (8% IRPJ): base_irpj = 500000 * 0.08 = 40000
        assert pres["base_irpj"] == 40_000.0
        assert pres["total"] > 0

    def test_int_02_simulacao_motor_novo(self, client, db):
        """T-INT-02: endpoint /simulacao com regime presumido + flag novo usa motor novo."""
        empresa, user = _setup_empresa_fiscal(db, cnae="4711-3/02", regime="presumido")
        headers = _auth_header(user)

        with patch("services.simulacao_tributaria_service.LP_ENGINE", "novo"):
            with patch("services.simulacao_tributaria_service._usar_motor_lp_novo", return_value=True):
                resp = client.get(
                    f"/api/financeiro/simulacao/{empresa.id}"
                    f"?receita_bruta=500000&custo_servicos=100000",
                    headers=headers,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "regime_atual" in data
        # Se regime=presumido e flag=novo, o calculo usa motor novo
        assert data["regime_atual"]["total"] > 0

    def test_int_03_resposta_json_serializavel(self, client, db):
        """T-INT-03: resposta JSON serializavel (sem Decimal)."""
        empresa, user = _setup_empresa_fiscal(db, cnae="6201-5/01", regime="presumido")
        headers = _auth_header(user)

        with patch("services.simulacao_tributaria_service.LP_ENGINE", "novo"):
            with patch("services.simulacao_tributaria_service._usar_motor_lp_novo", return_value=True):
                resp = client.get(
                    f"/api/financeiro/comparar-regimes/{empresa.id}"
                    f"?receita_bruta=500000&custo_servicos=100000",
                    headers=headers,
                )

        assert resp.status_code == 200
        # Se houvesse Decimal na resposta, json.dumps falharia
        raw = resp.text
        data = json.loads(raw)
        assert isinstance(data["presumido"]["total"], (int, float))
        assert isinstance(data["presumido"]["base_irpj"], (int, float))

    def test_int_04_cnae_comercial_base_8_pct(self, db):
        """T-INT-04: empresa com CNAE comercial -> base 8% (via cnae_presuncao)."""
        from services.contabil.cnae_presuncao import inferir_bases

        bases = inferir_bases("4711-3/02")
        assert bases.base_irpj == Decimal("0.08")
        assert bases.base_csll == Decimal("0.12")
        assert bases.eh_fallback is False
        assert "art. 15 caput" in bases.norma_aplicada

    def test_int_05_cnae_desconhecido_fallback_32(self, db):
        """T-INT-05: empresa com CNAE desconhecido -> fallback 32% (conservador)."""
        from services.contabil.cnae_presuncao import inferir_bases

        bases = inferir_bases("9999-9/99")
        assert bases.base_irpj == Decimal("0.32")
        assert bases.base_csll == Decimal("0.32")
        assert bases.eh_fallback is True
        assert "Fallback conservador" in bases.norma_aplicada
