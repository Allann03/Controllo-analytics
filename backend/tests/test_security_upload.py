"""
Testes de segurança: upload de arquivos (magic bytes, tamanho, extensão).
"""

import pytest
from tests.conftest import _auth_header


class TestUploadValidation:
    """Validação de uploads no endpoint processar-extrato."""

    def test_non_pdf_magic_bytes_rejected(self, client, admin_a):
        """Arquivo .exe renomeado para .pdf deve ser rejeitado (magic bytes)."""
        fake_pdf = b"MZ\x90\x00" + b"\x00" * 100  # EXE magic bytes
        r = client.post(
            "/api/processar-extrato",
            files={"arquivo": ("extrato.pdf", fake_pdf, "application/pdf")},
            data={"banco": "nubank"},
            headers=_auth_header(admin_a),
        )
        assert r.status_code == 400, f"Esperado 400, recebeu {r.status_code}: {r.text}"

    def test_empty_file_rejected(self, client, admin_a):
        """Arquivo vazio deve retornar 400."""
        r = client.post(
            "/api/processar-extrato",
            files={"arquivo": ("empty.pdf", b"", "application/pdf")},
            data={"banco": "nubank"},
            headers=_auth_header(admin_a),
        )
        assert r.status_code == 400

    def test_valid_pdf_magic_accepted(self, client, admin_a):
        """PDF com magic bytes corretos não deve retornar 400 por magic bytes."""
        valid_pdf = b"%PDF-1.4 minimal test content"
        r = client.post(
            "/api/processar-extrato",
            files={"arquivo": ("test.pdf", valid_pdf, "application/pdf")},
            data={"banco": "nubank"},
            headers=_auth_header(admin_a),
        )
        # May return 422 (parser can't read it) but NOT 400 for magic bytes
        assert r.status_code != 400 or "PDF" not in r.text

    def test_wrong_extension_rejected(self, client, admin_a):
        """Arquivo com extensão .docx deve ser rejeitado."""
        r = client.post(
            "/api/processar-extrato",
            files={"arquivo": ("extrato.docx", b"%PDF-1.4 content", "application/pdf")},
            data={"banco": "nubank"},
            headers=_auth_header(admin_a),
        )
        assert r.status_code == 400


class TestTokenVersion:
    """Token deve ser invalidado quando role muda."""

    def test_token_version_field_exists(self, db):
        """Modelo Usuario deve ter campo token_version."""
        from data.database import models as m
        assert hasattr(m.Usuario, "token_version"), "token_version não encontrado no modelo"

    def test_token_version_starts_at_zero(self, db, admin_a):
        """Novo usuário deve ter token_version = 0."""
        tv = getattr(admin_a, "token_version", None)
        assert tv is not None, "token_version é None"
        assert tv == 0, f"token_version deveria ser 0, é {tv}"

    def test_token_version_in_jwt_payload(self, admin_a):
        """JWT deve conter campo 'tv'."""
        from tests.conftest import _gerar_token
        from jose import jwt as _jwt
        token = _gerar_token(admin_a)
        import os
        _sk = os.environ.get("CONTROLLO_SECRET_KEY", "controllo-fpa-dev-secret-key-change-in-production-2025")
        payload = _jwt.decode(token, _sk, algorithms=["HS256"])
        assert "tv" in payload, f"JWT não contém 'tv': {payload.keys()}"
        assert payload["tv"] == 0
