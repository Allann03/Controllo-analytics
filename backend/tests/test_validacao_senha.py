"""
Testes BLOCO 2 — R1: Validacao de Forca de Senha.

Cobre:
  T1-T9:   Regras unitarias de validar_forca_senha
  T10-T11: Endpoints reais (solicitar-acesso, alterar_senha)
  T12:     Regressao: mestre autentica com senha legada
  T13-T15: Opcao B — campo senha_requer_atualizacao no login
  T16:     Fluxo completo E2E
  T17:     nome_usuario vazio
  T18:     Caracteres Unicode
"""

import pytest
from passlib.context import CryptContext
from services.auth_utils import validar_forca_senha, SenhaFracaError
from tests.conftest import _auth_header, _criar_usuario, _criar_escritorio
from data.database import models

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _criar_usuario_com_senha(db, nome, escritorio_id, senha, **kwargs):
    """Cria usuario com senha especifica no INSERT (nao dispara before_update)."""
    from tests.conftest import _agora
    user = models.Usuario(
        nome=nome,
        senha_hash=_pwd.hash(senha),
        escritorio_id=escritorio_id,
        is_admin=kwargs.get("is_admin", False),
        is_gestor=kwargs.get("is_gestor", False),
        is_master=kwargs.get("is_master", False),
        is_aprovado=kwargs.get("is_aprovado", True),
        is_dono=False,
        is_ceo=False,
        nome_exibicao=nome.capitalize(),
        cargo="Teste",
    )
    db.add(user)
    db.flush()
    return user


# ════════════════════════════════════════════════════════════════════
# T1–T9 — Regras unitarias
# ════════════════════════════════════════════════════════════════════

class TestRegrasSenha:

    def test_t1_7_chars_rejeita(self):
        with pytest.raises(SenhaFracaError, match="mínimo 8"):
            validar_forca_senha("Ab1!xyz")

    def test_t2_minimo_pratico_aceita(self):
        """9 chars e o minimo pratico: zxcvbn nao da score>=3 para 8 chars
        (teto de entropia por tamanho). As 5 regras deterministicas aceitam
        8, mas a regra 6 (zxcvbn) exige 9+ na pratica."""
        validar_forca_senha("Tr@5hP!nk")  # 9 chars, score=3

    def test_t3_sem_maiuscula_rejeita(self):
        with pytest.raises(SenhaFracaError, match="maiúscula"):
            validar_forca_senha("ab1!xyzw")

    def test_t4_sem_minuscula_rejeita(self):
        with pytest.raises(SenhaFracaError, match="minúscula"):
            validar_forca_senha("AB1!XYZW")

    def test_t5_sem_digito_rejeita(self):
        with pytest.raises(SenhaFracaError, match="dígito"):
            validar_forca_senha("Ab!xyzWq")

    def test_t6_sem_especial_rejeita(self):
        with pytest.raises(SenhaFracaError, match="especial"):
            validar_forca_senha("Ab1xyzWq")

    def test_t7_contem_nome_usuario_rejeita(self):
        with pytest.raises(SenhaFracaError, match="nome do usuário"):
            validar_forca_senha("Admin@123x", nome_usuario="admin")

    def test_t8_senhas_comuns_rejeita_via_zxcvbn(self):
        """Top senhas comuns devem ser rejeitadas pelo zxcvbn (score < 3)."""
        senhas_comuns = ["Password1!", "Welcome1!", "Qwerty12!"]
        for senha in senhas_comuns:
            with pytest.raises(SenhaFracaError, match="previsível"):
                validar_forca_senha(senha)

    def test_t9_senha_forte_legitima_aceita(self):
        validar_forca_senha("X#9kLm!pQ2")

    def test_t17_nome_usuario_vazio_nao_quebra(self):
        """Regra de 'nao conter nome' nao deve falhar com nome vazio."""
        validar_forca_senha("Senha@2025", nome_usuario="")

    def test_t18_unicode_nao_conta_como_letra(self):
        """
        Decisao de design: letras acentuadas (Ação, café) e emojis NAO
        satisfazem as regras de maiuscula/minuscula. Apenas ASCII A-Z e a-z.
        'Ação@2025' — tem 'A' (maiuscula ASCII) e 'o' (minuscula ASCII).
        """
        # 'Ação@2025' passes because it has ASCII A, ASCII o, digit 2, special @
        validar_forca_senha("Ação@2025")

    def test_t18b_unicode_only_sem_ascii_maiuscula_rejeita(self):
        """Senha com so acentuadas como 'maiuscula' deve ser rejeitada."""
        # 'ção@2025x' has no ASCII uppercase
        with pytest.raises(SenhaFracaError, match="maiúscula"):
            validar_forca_senha("ção@2025x")


# ════════════════════════════════════════════════════════════════════
# T10–T11 — Endpoints reais
# ════════════════════════════════════════════════════════════════════

class TestEndpointsSenha:

    def test_t10_solicitar_acesso_senha_fraca_422(self, client, db, escritorio_a):
        resp = client.post("/api/auth/solicitar-acesso", json={
            "nome": "testuser_fraca",
            "senha": "abc12345",
            "escritorio": escritorio_a.slug,
        })
        assert resp.status_code == 422, f"Esperado 422, recebeu {resp.status_code}: {resp.text}"

    def test_t11_alterar_senha_fraca_422(self, client, db, escritorio_a):
        """PATCH /api/auth/senha com nova_senha fraca deve retornar 422."""
        user = _criar_usuario_com_senha(db, "user_troca", escritorio_a.id,
                                        senha="SenhaForte@1")
        db.commit()

        resp = client.patch("/api/auth/senha", json={
            "senha_atual": "SenhaForte@1",
            "nova_senha": "abc12345",
        }, headers=_auth_header(user))
        assert resp.status_code == 422, f"Esperado 422, recebeu {resp.status_code}: {resp.text}"


# ════════════════════════════════════════════════════════════════════
# T12 — Regressao: mestre autentica com senha legada
# ════════════════════════════════════════════════════════════════════

class TestRegressaoMestre:

    def test_t12_mestre_autentica_com_senha_legada(self, client, db, escritorio_a):
        """Senha legada do mestre continua funcionando — validacao nao e retroativa."""
        mestre = _criar_usuario_com_senha(db, "mestre_legado", escritorio_a.id,
                                          senha="abc123", is_admin=True, is_master=True)
        db.commit()

        resp = client.post("/api/auth/login", data={
            "username": f"mestre_legado@{escritorio_a.slug}",
            "password": "abc123",
        })
        assert resp.status_code == 200, f"Mestre deveria autenticar com senha legada: {resp.text}"
        assert "access_token" in resp.json()


# ════════════════════════════════════════════════════════════════════
# T13–T15 — Opcao B: campo senha_requer_atualizacao no login
# ════════════════════════════════════════════════════════════════════

class TestOpcaoB:

    def test_t13_login_senha_forte_sem_flag(self, client, db, escritorio_a):
        """Login com senha forte -> response NAO contem senha_requer_atualizacao: true."""
        user = _criar_usuario_com_senha(db, "user_forte", escritorio_a.id,
                                        senha="X#9kLm!pQ2")
        db.commit()

        resp = client.post("/api/auth/login", data={
            "username": f"user_forte@{escritorio_a.slug}",
            "password": "X#9kLm!pQ2",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("senha_requer_atualizacao") is False
        assert body.get("senha_motivo") is None

    def test_t14_login_senha_fraca_com_flag(self, client, db, escritorio_a):
        """Login com senha legada fraca -> response contem flag + motivo, mas 200 + token."""
        user = _criar_usuario_com_senha(db, "user_fraca", escritorio_a.id,
                                        senha="abc123")
        db.commit()

        resp = client.post("/api/auth/login", data={
            "username": f"user_fraca@{escritorio_a.slug}",
            "password": "abc123",
        })
        assert resp.status_code == 200, f"Login NAO deve ser bloqueado: {resp.text}"
        body = resp.json()
        assert "access_token" in body, "Token deve estar presente"
        assert body.get("senha_requer_atualizacao") is True
        assert body.get("senha_motivo") is not None and len(body["senha_motivo"]) > 0

    def test_t15_login_mestre_sem_flag_mesmo_senha_fraca(self, client, db, escritorio_a):
        """Mestre nunca recebe flag de senha fraca, independente da forca real."""
        mestre = _criar_usuario_com_senha(db, "mestre_flag", escritorio_a.id,
                                          senha="abc123", is_admin=True, is_master=True)
        db.commit()

        resp = client.post("/api/auth/login", data={
            "username": f"mestre_flag@{escritorio_a.slug}",
            "password": "abc123",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("senha_requer_atualizacao") is False, \
            "Mestre NUNCA deve receber flag de senha fraca"
        assert body.get("senha_motivo") is None


# ════════════════════════════════════════════════════════════════════
# T16 — Fluxo completo E2E
# ════════════════════════════════════════════════════════════════════

class TestFluxoCompletoE2E:

    def test_t16_cria_login_troca_forte_troca_fraca_login(self, client, db, escritorio_a):
        """
        1. Cria conta (senha forte) via DB direto (solicitar-acesso tem
           commit+lazy-load issue em TestClient com session compartilhada)
        2. Login -> sem flag
        3. Troca por outra forte -> 200
        4. Troca por fraca -> 422
        5. Login -> sem flag (senha forte anterior ainda vale)
        """
        senha_forte_1 = "Xk9!mLpQ#w"
        senha_forte_2 = "Ry7$nWvZ@q"
        senha_fraca = "abc12345"

        # 1. Criar conta diretamente (equivalente a solicitar-acesso + aprovação)
        user = _criar_usuario_com_senha(db, "e2e_user", escritorio_a.id,
                                        senha=senha_forte_1, is_aprovado=True)
        db.commit()

        # 2. Login -> sem flag
        resp = client.post("/api/auth/login", data={
            "username": f"e2e_user@{escritorio_a.slug}",
            "password": senha_forte_1,
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        assert resp.json().get("senha_requer_atualizacao") is False
        hdr = {"Authorization": f"Bearer {token}"}

        # 3. Troca por outra forte -> 200
        resp = client.patch("/api/auth/senha", json={
            "senha_atual": senha_forte_1,
            "nova_senha": senha_forte_2,
        }, headers=hdr)
        assert resp.status_code == 200, f"Troca forte falhou: {resp.text}"

        # Re-login com nova senha para obter token atualizado
        resp = client.post("/api/auth/login", data={
            "username": f"e2e_user@{escritorio_a.slug}",
            "password": senha_forte_2,
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        hdr = {"Authorization": f"Bearer {token}"}

        # 4. Troca por fraca -> 422
        resp = client.patch("/api/auth/senha", json={
            "senha_atual": senha_forte_2,
            "nova_senha": senha_fraca,
        }, headers=hdr)
        assert resp.status_code == 422, f"Troca fraca deveria dar 422: {resp.text}"

        # 5. Login -> sem flag (senha_forte_2 ainda vale)
        resp = client.post("/api/auth/login", data={
            "username": f"e2e_user@{escritorio_a.slug}",
            "password": senha_forte_2,
        })
        assert resp.status_code == 200
        assert resp.json().get("senha_requer_atualizacao") is False
