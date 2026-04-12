"""
Testes adicionais de resiliência.
"""

import pytest
from tests.conftest import _auth_header


class TestProcessarExtratoEdgeCases:
    def test_banco_invalido_not_500(self, client, admin_a):
        """Banco inexistente não deve gerar 500."""
        r = client.post(
            "/api/processar-extrato",
            files={"arquivo": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
            data={"banco": "banco_inexistente_xyz"},
            headers=_auth_header(admin_a),
        )
        assert r.status_code != 500, f"Retornou 500: {r.text[:200]}"

    def test_sem_campo_banco_aceito(self, client, admin_a):
        """Sem campo banco deve tentar auto-detectar, não retornar 500."""
        r = client.post(
            "/api/processar-extrato",
            files={"arquivo": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")},
            data={"banco": ""},
            headers=_auth_header(admin_a),
        )
        assert r.status_code != 500, f"Retornou 500: {r.text[:200]}"

    def test_empresa_id_zero_ignored(self, client, admin_a):
        """empresa_id=0 deve ser ignorado (não tentará classificar)."""
        r = client.post(
            "/api/processar-extrato",
            files={"arquivo": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
            data={"banco": "nubank", "empresa_id": "0"},
            headers=_auth_header(admin_a),
        )
        # Pode ser 422 (parser error) mas não 500
        assert r.status_code != 500


class TestHealthEndpoints:
    def test_health(self, client):
        """Endpoint /api/health deve retornar 200."""
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_root(self, client):
        """Endpoint / deve retornar 200."""
        r = client.get("/")
        assert r.status_code == 200
