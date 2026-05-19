"""
Utilitários de autenticação compartilhados entre todos os routers.

Centraliza a leitura do SECRET_KEY e a lógica de decodificação de JWT
para garantir consistência e facilitar a rotação da chave.
"""

import logging
import os
import re

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models

logger = logging.getLogger(__name__)

# ── zxcvbn — carregado uma única vez no startup do módulo ────────────
_ZXCVBN_DISPONIVEL = False
try:
    from zxcvbn import zxcvbn as _zxcvbn_check
    _ZXCVBN_DISPONIVEL = True
except ImportError:
    _zxcvbn_check = None  # type: ignore[assignment]
    _env = os.environ.get("CONTROLLO_ENV", "development")
    if _env == "production":
        raise RuntimeError(
            "zxcvbn-python não está instalado. "
            "Instale com: pip install zxcvbn-python==4.4.24 — "
            "obrigatório em produção para validação de entropia de senhas (R1)."
        )
    logger.error(
        "zxcvbn-python não disponível — validação de entropia de senhas DEGRADADA. "
        "Instale com: pip install zxcvbn-python==4.4.24"
    )

# ── Chave e algoritmo lidos uma única vez na inicialização do módulo ──
SECRET_KEY: str = os.environ.get(
    "CONTROLLO_SECRET_KEY",
    "controllo-fpa-dev-secret-key-change-in-production-2025",
)
ALGORITHM: str = "HS256"

_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _decode_token(token: str) -> dict:
    """Decodifica o JWT e retorna o payload completo. Levanta 401 se inválido."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nome: str = payload.get("sub", "")
        if not nome:
            raise ValueError("sub vazio")
        return payload
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Credenciais inválidas ou expiradas.")


def get_current_user(
    token: str = Depends(_oauth2),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """Dependência: retorna o usuário autenticado e aprovado."""
    payload = _decode_token(token)
    nome = payload["sub"]
    eid = payload.get("eid")
    q = db.query(models.Usuario).filter(models.Usuario.nome == nome)
    if eid:
        q = q.filter(models.Usuario.escritorio_id == eid)
    user = q.first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    if not user.is_aprovado:
        raise HTTPException(status_code=403, detail="Conta não aprovada.")
    # Validate token version — invalidates old tokens when role changes
    user_tv = getattr(user, "token_version", 0) or 0
    token_tv = payload.get("tv", 0)
    if user_tv != token_tv:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
    # Attach helpers
    user._escritorio_id = user.escritorio_id  # type: ignore[attr-defined]
    user._is_master = getattr(user, "is_master", False)  # type: ignore[attr-defined]
    return user


def get_admin_user(
    token: str = Depends(_oauth2),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """Dependência: admin OU master podem acessar."""
    user = get_current_user(token, db)
    if not user.is_admin and not getattr(user, "is_master", False):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return user


def get_gestor_or_admin(
    token: str = Depends(_oauth2),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """Dependência: gestor, admin OU master podem acessar."""
    user = get_current_user(token, db)
    _is_master = getattr(user, "is_master", False)
    if not (user.is_admin or getattr(user, "is_gestor", False) or _is_master):
        raise HTTPException(status_code=403, detail="Acesso restrito a gestores e administradores.")
    return user


# ── Tenant isolation helpers ─────────────────────────────────────────

def query_tenant(db: Session, model, usuario: models.Usuario):
    """Query filtrada por escritório. Master vê TUDO."""
    if getattr(usuario, "is_master", False):
        return db.query(model)
    if hasattr(model, "escritorio_id"):
        eid = getattr(usuario, "_escritorio_id", None) or usuario.escritorio_id
        return db.query(model).filter(model.escritorio_id == eid)
    return db.query(model)


def validate_empresa_access(db: Session, empresa_id: int, usuario: models.Usuario):
    """Valida acesso à empresa. Master acessa QUALQUER empresa."""
    if getattr(usuario, "is_master", False):
        empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    else:
        eid = getattr(usuario, "_escritorio_id", None) or usuario.escritorio_id
        empresa = db.query(models.Empresa).filter(
            models.Empresa.id == empresa_id,
            models.Empresa.escritorio_id == eid,
        ).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return empresa


def verificar_tenant(current_user, recurso_escritorio_id: int):
    """Verifica que o usuário tem acesso ao tenant do recurso.
    Master bypassa. Todos os outros devem pertencer ao mesmo escritório."""
    if getattr(current_user, "is_master", False):
        return
    eid = getattr(current_user, "_escritorio_id", None) or current_user.escritorio_id
    if recurso_escritorio_id != eid:
        raise HTTPException(
            status_code=403,
            detail="Sem permissão: recurso pertence a outro escritório.",
        )


def verificar_empresa_tenant(db: Session, current_user, empresa_id: int):
    """Verifica que a empresa pertence ao tenant do usuário. Retorna a empresa."""
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    verificar_tenant(current_user, empresa.escritorio_id)
    return empresa


def resolve_empresa_or_403(
    db: Session,
    empresa_id: int,
    current_user: models.Usuario,
) -> models.Empresa:
    """
    Resolve o acesso a uma empresa respeitando isolamento multi-tenant.

    Substitui os helpers _check_empresa / _empresa_do_usuario dos routers,
    eliminando o bypass `if user.is_admin: return empresa` (CRÍTICO-1).

    Semântica:
      - is_master=True  → bypass legítimo, acessa qualquer empresa_id (cross-tenant)
      - is_admin=True   → acesso apenas se empresa.escritorio_id == current_user.escritorio_id
      - Usuário comum   → mesma regra de tenant + deve ser dono ou CarteiraMembro
      - Empresa inexistente   → 404
      - Empresa de outro tenant → 404 (não 403 — não vaza existência cross-tenant)
    """
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    # Master: bypass de tenant legítimo (acesso cross-tenant intencional)
    if getattr(current_user, "is_master", False):
        return empresa

    # Isolamento de tenant — retorna 404 (não 403) para não vazar existência cross-tenant
    if empresa.escritorio_id != current_user.escritorio_id:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    # Admin dentro do mesmo escritório: acesso a todas as empresas do tenant
    if current_user.is_admin:
        return empresa

    # Usuário comum: deve ser dono direto ou CarteiraMembro
    if empresa.usuario_id == current_user.id:
        return empresa

    membro = db.query(models.CarteiraMembro).filter(
        models.CarteiraMembro.empresa_id == empresa_id,
        models.CarteiraMembro.usuario_id == current_user.id,
    ).first()
    if not membro:
        raise HTTPException(status_code=403, detail="Acesso negado a esta empresa.")

    return empresa


# ── Privacidade do nome social ───────────────────────────────────────

def filtrar_nome_social(target_user, viewer_user_id) -> str:
    """Retorna nome_exibicao do target apenas quando permitido.

    Regra unica (sem excecao por role): o proprio usuario sempre ve seu
    nome_exibicao. Outros so veem se target.exibir_nome_social == True.
    Quando bloqueado, retorna string vazia para preservar o tipo (frontend
    cai no fallback `nome_exibicao || nome` automaticamente).
    """
    if target_user.id == viewer_user_id:
        return target_user.nome_exibicao or ""
    if getattr(target_user, "exibir_nome_social", False):
        return target_user.nome_exibicao or ""
    return ""


# ── Validação de força de senha (R1) ────────────────────────────────

_ESPECIAIS = set("!@#$%^&*()_+-=[]{}|;:,.<>?")


class SenhaFracaError(Exception):
    """Senha não atende aos critérios de segurança R1."""
    pass


def validar_forca_senha(senha: str, nome_usuario: str = "") -> None:
    """
    Valida força da senha conforme regra R1.

    Levanta SenhaFracaError com mensagem específica por regra violada.
    Regras (todas obrigatórias):
      1. Mínimo 8 caracteres
      2. Pelo menos 1 letra maiúscula ASCII (A-Z)
      3. Pelo menos 1 letra minúscula ASCII (a-z)
      4. Pelo menos 1 dígito
      5. Pelo menos 1 caractere especial do conjunto _ESPECIAIS
      6. score zxcvbn >= 3 (escala 0–4) — se lib disponível
      7. Não pode conter o nome do usuário (case-insensitive)

    Decisão de design (T18): letras acentuadas e caracteres Unicode NÃO
    satisfazem as regras de maiúscula/minúscula — apenas ASCII A-Z e a-z.
    Caracteres Unicode são permitidos na senha mas não contam como "letra"
    para as regras 2 e 3. Isto garante comportamento previsível e idêntico
    entre backend Python e frontend JavaScript (regex [A-Z]/[a-z]).
    """
    if len(senha) < 8:
        raise SenhaFracaError("Senha deve ter no mínimo 8 caracteres.")
    if len(senha) > 128:
        raise SenhaFracaError("Senha muito longa (máximo 128 caracteres).")
    if not re.search(r"[A-Z]", senha):
        raise SenhaFracaError("Senha deve conter pelo menos 1 letra maiúscula.")
    if not re.search(r"[a-z]", senha):
        raise SenhaFracaError("Senha deve conter pelo menos 1 letra minúscula.")
    if not re.search(r"\d", senha):
        raise SenhaFracaError("Senha deve conter pelo menos 1 dígito.")
    if not any(c in _ESPECIAIS for c in senha):
        raise SenhaFracaError(
            "Senha deve conter pelo menos 1 caractere especial: !@#$%^&*()_+-=[]{}|;:,.<>?"
        )
    if nome_usuario and nome_usuario.lower() in senha.lower():
        raise SenhaFracaError("Senha não pode conter o nome do usuário.")
    if _ZXCVBN_DISPONIVEL and _zxcvbn_check is not None:
        resultado = _zxcvbn_check(senha, user_inputs=[nome_usuario] if nome_usuario else [])
        if resultado["score"] < 3:
            raise SenhaFracaError(
                "Senha muito previsível. Evite sequências, palavras comuns ou padrões de teclado. "
                "Tente aumentar o comprimento ou variar mais os caracteres."
            )


def verificar_forca_senha_silencioso(senha: str, nome_usuario: str = "") -> tuple:
    """
    Verifica força da senha sem levantar exceção.
    Retorna (True, None) se forte, ou (False, mensagem) se fraca.
    Uso: Opção B no login — informar sem bloquear.
    """
    try:
        validar_forca_senha(senha, nome_usuario)
        return True, None
    except SenhaFracaError as e:
        return False, str(e)
