"""
Testes BLOCO 0 — Proteção R2: Usuário Mestre imutável por automação.

Verifica que os event listeners ORM bloqueiam corretamente:
  - Exclusão do usuário mestre
  - Rebaixamento de is_master
  - Alteração de escritorio_id
  - Sobrescrita de senha_hash

E que campos não críticos (nome_exibicao, cargo) permanecem editáveis.

Todos os testes rodam contra banco SQLite em memória (conftest.py).
"""

import pytest
from sqlalchemy.exc import StatementError
from data.database.models import UsuarioMestreProtegidoError


# ════════════════════════════════════════════════════════════════════
# T1 / T2 — Exclusão do usuário mestre
# ════════════════════════════════════════════════════════════════════

class TestDeleteMestre:
    """before_delete listener deve bloquear exclusão do mestre."""

    def test_delete_master_raises(self, db, escritorio_a):
        """Excluir usuário mestre deve levantar UsuarioMestreProtegidoError."""
        from tests.conftest import _criar_usuario
        mestre = _criar_usuario(db, "mestre_del", escritorio_a.id, is_master=True)
        db.commit()

        with pytest.raises((UsuarioMestreProtegidoError, StatementError), match="não pode ser excluído"):
            db.delete(mestre)
            db.flush()

    def test_delete_non_master_allowed(self, db, escritorio_a):
        """Excluir usuário comum deve ser permitido normalmente."""
        from tests.conftest import _criar_usuario
        user = _criar_usuario(db, "user_normal", escritorio_a.id, is_master=False)
        db.commit()

        db.delete(user)
        db.flush()  # deve passar sem erro
        db.commit()


# ════════════════════════════════════════════════════════════════════
# T3 / T4 — Rebaixamento de is_master
# ════════════════════════════════════════════════════════════════════

class TestRebaixamentoIsMaster:
    """before_update listener deve bloquear demoção de is_master=True → False."""

    def test_set_is_master_false_raises(self, db, escritorio_a):
        """Setar is_master=False no mestre deve levantar UsuarioMestreProtegidoError."""
        from tests.conftest import _criar_usuario
        mestre = _criar_usuario(db, "mestre_rebaixar", escritorio_a.id, is_master=True)
        db.commit()

        with pytest.raises((UsuarioMestreProtegidoError, StatementError), match="is_master"):
            mestre.is_master = False
            db.flush()

    def test_set_is_master_true_to_true_allowed(self, db, escritorio_a):
        """Confirmar is_master=True (sem mudança) não deve disparar erro."""
        from tests.conftest import _criar_usuario
        mestre = _criar_usuario(db, "mestre_noop", escritorio_a.id, is_master=True)
        db.commit()

        # Sem mudança real — não deve disparar listener de update
        mestre.is_master = True
        db.flush()  # deve passar sem erro
        db.commit()


# ════════════════════════════════════════════════════════════════════
# T5 / T6 — Alteração de escritorio_id
# ════════════════════════════════════════════════════════════════════

class TestAlteracaoEscritorioId:
    """before_update listener deve bloquear alteração de escritorio_id do mestre."""

    def test_change_escritorio_id_raises(self, db, escritorio_a, escritorio_b):
        """Alterar escritorio_id do mestre deve levantar UsuarioMestreProtegidoError."""
        from tests.conftest import _criar_usuario
        mestre = _criar_usuario(db, "mestre_esc", escritorio_a.id, is_master=True)
        db.commit()

        esc_id_original = mestre.escritorio_id

        with pytest.raises((UsuarioMestreProtegidoError, StatementError), match="escritorio_id"):
            mestre.escritorio_id = escritorio_b.id
            db.flush()

    def test_db_unchanged_after_rollback(self, db, escritorio_a, escritorio_b):
        """Após rollback do bloqueio, escritorio_id permanece inalterado."""
        from tests.conftest import _criar_usuario
        mestre = _criar_usuario(db, "mestre_rollback", escritorio_a.id, is_master=True)
        db.commit()

        esc_id_original = mestre.escritorio_id

        try:
            mestre.escritorio_id = escritorio_b.id
            db.flush()
        except (UsuarioMestreProtegidoError, StatementError):
            db.rollback()

        # Recarregar da base — deve ter o valor original
        db.expire(mestre)
        db.refresh(mestre)
        assert mestre.escritorio_id == esc_id_original, (
            f"escritorio_id foi alterado mesmo após rollback: {mestre.escritorio_id}"
        )


# ════════════════════════════════════════════════════════════════════
# T7 / T8 — Sobrescrita de senha_hash
# ════════════════════════════════════════════════════════════════════

class TestSobrescritaSenhaHash:
    """before_update listener deve bloquear alteração de senha_hash do mestre."""

    def test_change_senha_hash_raises(self, db, escritorio_a):
        """Alterar senha_hash do mestre deve levantar UsuarioMestreProtegidoError."""
        from tests.conftest import _criar_usuario
        mestre = _criar_usuario(db, "mestre_senha", escritorio_a.id, is_master=True)
        db.commit()

        with pytest.raises((UsuarioMestreProtegidoError, StatementError), match="senha_hash"):
            mestre.senha_hash = "$pbkdf2-sha256$hacked_hash"
            db.flush()

    def test_original_password_still_authenticates(self, db, escritorio_a):
        """Após tentativa bloqueada de alterar senha, hash original persiste."""
        from passlib.context import CryptContext
        from tests.conftest import _criar_usuario
        pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        senha_original = "Senha123!"

        mestre = _criar_usuario(db, "mestre_pwd_check", escritorio_a.id, is_master=True)
        db.commit()
        hash_original = mestre.senha_hash

        try:
            mestre.senha_hash = "$pbkdf2-sha256$hacked_hash"
            db.flush()
        except (UsuarioMestreProtegidoError, StatementError):
            db.rollback()

        db.expire(mestre)
        db.refresh(mestre)
        assert mestre.senha_hash == hash_original, "senha_hash foi alterada mesmo após bloqueio"
        assert pwd.verify(senha_original, mestre.senha_hash), "Senha original não autentica após tentativa bloqueada"


# ════════════════════════════════════════════════════════════════════
# T9 / T10 — Idempotência de _garantir_usuario_mestre
# ════════════════════════════════════════════════════════════════════

class TestIdempotenciaGarantirUsuarioMestre:
    """Simula dois inícios de servidor — senha_hash e escritorio_id não mudam."""

    def _simular_inicio_servidor(self, db, nome, escritorio_id):
        """Replica a lógica corrigida de _garantir_usuario_mestre."""
        from data.database import models as m
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

        user = db.query(m.Usuario).filter(
            m.Usuario.nome == nome,
            m.Usuario.escritorio_id == escritorio_id,
        ).first()

        if user:
            dirty = False
            for attr, val in [
                ("is_master", True), ("is_dono", True), ("is_admin", True),
                ("is_ceo", True), ("is_gestor", True), ("is_aprovado", True),
            ]:
                if getattr(user, attr) != val:
                    setattr(user, attr, val)
                    dirty = True
            user.nome_exibicao = user.nome_exibicao or "Allan"
            user.cargo = user.cargo or "Administrador Master"
            if dirty:
                db.commit()
        else:
            db.add(m.Usuario(
                nome=nome,
                senha_hash=pwd.hash("SenhaTeste@123"),
                is_master=True, is_dono=True, is_admin=True,
                is_ceo=True, is_gestor=True, is_aprovado=True,
                nome_exibicao="Allan", cargo="Administrador Master",
                escritorio_id=escritorio_id,
            ))
            db.commit()

    def test_senha_hash_unchanged_after_two_starts(self, db, escritorio_a):
        """senha_hash não muda após segundo início de servidor."""
        # Primeiro início — cria usuário
        self._simular_inicio_servidor(db, "mestre_idm1", escritorio_a.id)
        from data.database import models as m
        user = db.query(m.Usuario).filter(m.Usuario.nome == "mestre_idm1").first()
        hash_inicial = user.senha_hash

        # Segundo início — não deve modificar senha_hash
        self._simular_inicio_servidor(db, "mestre_idm1", escritorio_a.id)
        db.expire(user)
        db.refresh(user)
        assert user.senha_hash == hash_inicial, (
            f"senha_hash foi alterada no segundo início: {user.senha_hash[:20]}... != {hash_inicial[:20]}..."
        )

    def test_escritorio_id_unchanged_after_two_starts(self, db, escritorio_a):
        """escritorio_id não muda após segundo início de servidor."""
        self._simular_inicio_servidor(db, "mestre_idm2", escritorio_a.id)
        from data.database import models as m
        user = db.query(m.Usuario).filter(m.Usuario.nome == "mestre_idm2").first()
        esc_id_inicial = user.escritorio_id

        self._simular_inicio_servidor(db, "mestre_idm2", escritorio_a.id)
        db.expire(user)
        db.refresh(user)
        assert user.escritorio_id == esc_id_inicial, (
            f"escritorio_id foi alterado no segundo início: {user.escritorio_id} != {esc_id_inicial}"
        )


# ════════════════════════════════════════════════════════════════════
# T11 — Campos não protegidos são editáveis
# ════════════════════════════════════════════════════════════════════

class TestCamposNaoProtegidos:
    """nome_exibicao e cargo do mestre podem ser alterados normalmente."""

    def test_nome_exibicao_and_cargo_editable(self, db, escritorio_a):
        """Editar nome_exibicao e cargo do mestre não deve disparar erro."""
        from tests.conftest import _criar_usuario
        mestre = _criar_usuario(db, "mestre_campos", escritorio_a.id, is_master=True)
        db.commit()

        mestre.nome_exibicao = "Allan Atualizado"
        mestre.cargo = "CEO"
        db.flush()  # deve passar sem erro
        db.commit()

        db.expire(mestre)
        db.refresh(mestre)
        assert mestre.nome_exibicao == "Allan Atualizado"
        assert mestre.cargo == "CEO"


# ════════════════════════════════════════════════════════════════════
# T12 — Criação do mestre não é bloqueada (before_insert não existe)
# ════════════════════════════════════════════════════════════════════

class TestCriacaoMestre:
    """Criar usuário mestre novo deve funcionar normalmente."""

    def test_criar_usuario_mestre_ok(self, db, escritorio_a):
        """INSERT de usuário mestre não deve ser bloqueado pelos listeners."""
        from data.database import models as m
        from passlib.context import CryptContext
        from datetime import datetime, timezone
        pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

        novo_mestre = m.Usuario(
            nome="mestre_novo_criacao",
            senha_hash=pwd.hash("Senha@Master1"),
            is_master=True,
            is_admin=True,
            is_dono=True,
            is_ceo=True,
            is_gestor=True,
            is_aprovado=True,
            nome_exibicao="Mestre Novo",
            cargo="Administrador Master",
            escritorio_id=escritorio_a.id,
        )
        db.add(novo_mestre)
        db.flush()  # INSERT — deve funcionar sem erro
        db.commit()

        db.refresh(novo_mestre)
        assert novo_mestre.id is not None
        assert novo_mestre.is_master is True
