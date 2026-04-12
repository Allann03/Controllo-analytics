"""
Fixtures para testes do Controllo SaaS.
Usa banco SQLite em memória para isolamento total.
"""

import os
import sys
import pytest
from datetime import datetime, timezone

# Garantir imports do backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Forçar SQLite em memória ANTES de importar qualquer coisa do app
os.environ["DATABASE_URL"] = ""
os.environ["CONTROLLO_ENV"] = "test"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from jose import jwt

from data.database.config import Base
from data.database import models


# ── Engine e sessão de teste ────────────────────────────────────────
# StaticPool garante que todas as operações usam a mesma conexão ao
# SQLite em memória — necessário porque endpoints que fazem db.commit()
# (ex: registrar_auditoria no login) liberam a conexão ao pool, e sem
# StaticPool uma nova conexão obteria um banco vazio.

_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Cria tabelas antes de cada teste e dropa depois."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def db():
    """Sessão de banco de dados para testes."""
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """TestClient com dependency override para usar o banco de teste."""
    from main import app
    from data.database.config import get_db

    # Criar tabelas no engine de teste
    Base.metadata.create_all(bind=_test_engine)

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers de criação ──────────────────────────────────────────────

def _agora():
    return datetime.now(timezone.utc).isoformat()


def _criar_escritorio(db, nome, slug, plano="trial"):
    esc = models.Escritorio(
        nome=nome, slug=slug, plano=plano,
        max_empresas=50, max_usuarios=10,
        ativo=True, criado_em=_agora(), atualizado_em=_agora(),
    )
    db.add(esc)
    db.flush()
    return esc


def _criar_usuario(db, nome, escritorio_id, is_admin=False, is_gestor=False, is_master=False, is_aprovado=True):
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    user = models.Usuario(
        nome=nome,
        senha_hash=pwd.hash("Senha123!"),
        escritorio_id=escritorio_id,
        is_admin=is_admin,
        is_gestor=is_gestor,
        is_master=is_master,
        is_aprovado=is_aprovado,
        is_dono=False,
        is_ceo=False,
        nome_exibicao=nome.capitalize(),
        cargo="Teste",
    )
    db.add(user)
    db.flush()
    return user


def _gerar_token(user, escritorio_slug="test"):
    """Gera JWT válido para o usuário."""
    SECRET_KEY = os.environ.get("CONTROLLO_SECRET_KEY", "controllo-fpa-dev-secret-key-change-in-production-2025")
    payload = {
        "sub": user.nome,
        "eid": user.escritorio_id,
        "is_master": getattr(user, "is_master", False),
        "is_admin": user.is_admin,
        "is_ceo": getattr(user, "is_ceo", False),
        "is_gestor": getattr(user, "is_gestor", False),
        "role": "master" if getattr(user, "is_master", False) else ("admin" if user.is_admin else "analista"),
        "tv": getattr(user, "token_version", 0) or 0,
        "exp": 9999999999,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _auth_header(user, escritorio_slug="test"):
    """Retorna header de autorização para o usuário."""
    token = _gerar_token(user, escritorio_slug)
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures de dados ────────────────────────────────────────────────

@pytest.fixture
def escritorio_a(db):
    return _criar_escritorio(db, "Escritorio A", "escritorio-a")


@pytest.fixture
def escritorio_b(db):
    return _criar_escritorio(db, "Escritorio B", "escritorio-b")


@pytest.fixture
def admin_a(db, escritorio_a):
    return _criar_usuario(db, "admin_a", escritorio_a.id, is_admin=True)


@pytest.fixture
def admin_b(db, escritorio_b):
    return _criar_usuario(db, "admin_b", escritorio_b.id, is_admin=True)


@pytest.fixture
def user_a(db, escritorio_a):
    return _criar_usuario(db, "user_a", escritorio_a.id, is_aprovado=False)


@pytest.fixture
def user_b(db, escritorio_b):
    return _criar_usuario(db, "user_b", escritorio_b.id, is_aprovado=False)


@pytest.fixture
def gestor_a(db, escritorio_a):
    return _criar_usuario(db, "gestor_a", escritorio_a.id, is_gestor=True)


@pytest.fixture
def master_user(db, escritorio_a):
    return _criar_usuario(db, "master", escritorio_a.id, is_admin=True, is_master=True)


def _criar_empresa(db, nome, escritorio_id, usuario_id):
    empresa = models.Empresa(
        nome=nome,
        escritorio_id=escritorio_id,
        usuario_id=usuario_id,
        cnpj="",
        status="iniciada",
        ativa=True,
        criado_em=_agora(),
        atualizado_em=_agora(),
    )
    db.add(empresa)
    db.flush()
    return empresa


@pytest.fixture
def empresa_a(db, escritorio_a, admin_a):
    return _criar_empresa(db, "Empresa A", escritorio_a.id, admin_a.id)


@pytest.fixture
def empresa_b(db, escritorio_b, admin_b):
    return _criar_empresa(db, "Empresa B", escritorio_b.id, admin_b.id)
