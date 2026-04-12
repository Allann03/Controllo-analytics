"""
Router: Painel Master — Gestão de escritórios (super-admin only)
Apenas o usuário do escritório master com is_admin=True pode acessar.
Endpoint base: /api/master
"""

import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.auth_utils import validar_forca_senha
from sqlalchemy import func

from data.database.config import get_db
from data.database import models
from services.auth_utils import get_current_user as _auth_user

router = APIRouter(prefix="/api/master", tags=["master"])

_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
_MASTER_SLUG = os.environ.get("CONTROLLO_MASTER_SLUG", "controllobpo")
_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{2,49}$')

PLANOS = {
    "trial":         {"max_empresas": 10,   "max_usuarios": 2},
    "basico":        {"max_empresas": 50,   "max_usuarios": 5},
    "profissional":  {"max_empresas": 500,  "max_usuarios": 30},
    "enterprise":    {"max_empresas": 1500, "max_usuarios": 150},
}


def _get_master_admin(
    token: str = Depends(_oauth2),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """Valida que o usuário é master (is_master=True)."""
    user = _auth_user(token, db)
    if not getattr(user, "is_master", False):
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador da plataforma.")
    return user


# ── Schemas ──────────────────────────────────────────────────────────

class EscritorioCreate(BaseModel):
    nome: str
    slug: str
    plano: Optional[str] = "trial"
    usuario_admin: Optional[str] = None   # Se fornecido, cria admin junto
    senha_admin: Optional[str] = None
    nome_admin: Optional[str] = ""
    max_empresas: Optional[int] = None
    max_usuarios: Optional[int] = None

class RoleUpdate(BaseModel):
    is_admin: Optional[bool] = None
    is_ceo: Optional[bool] = None
    is_gestor: Optional[bool] = None

class EscritorioUpdate(BaseModel):
    nome: Optional[str] = None
    plano: Optional[str] = None
    max_empresas: Optional[int] = None
    max_usuarios: Optional[int] = None


def _esc_to_dict(esc: models.Escritorio, db: Session) -> dict:
    num_users = db.query(func.count(models.Usuario.id)).filter(
        models.Usuario.escritorio_id == esc.id
    ).scalar() or 0
    num_pendentes = db.query(func.count(models.Usuario.id)).filter(
        models.Usuario.escritorio_id == esc.id,
        models.Usuario.is_aprovado == False  # noqa: E712
    ).scalar() or 0
    num_empresas = db.query(func.count(models.Empresa.id)).filter(
        models.Empresa.escritorio_id == esc.id
    ).scalar() or 0
    return {
        "id": esc.id,
        "nome": esc.nome,
        "slug": esc.slug,
        "plano": esc.plano,
        "max_empresas": esc.max_empresas,
        "max_usuarios": esc.max_usuarios,
        "data_expiracao": esc.data_expiracao,
        "ativo": esc.ativo,
        "usuarios_count": num_users,
        "usuarios_pendentes": num_pendentes,
        "empresas_count": num_empresas,
        "criado_em": esc.criado_em,
        "atualizado_em": esc.atualizado_em,
    }


def _user_to_dict(u: models.Usuario, slug: str = "") -> dict:
    return {
        "id": u.id,
        "nome": u.nome,
        "login_completo": f"{u.nome}@{slug}" if slug else u.nome,
        "nome_exibicao": u.nome_exibicao or "",
        "cargo": u.cargo or "",
        "is_master": getattr(u, "is_master", False),
        "is_dono": getattr(u, "is_dono", False),
        "is_admin": u.is_admin,
        "is_ceo": getattr(u, "is_ceo", False),
        "is_gestor": getattr(u, "is_gestor", False),
        "is_aprovado": u.is_aprovado,
        "escritorio_id": u.escritorio_id,
    }


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/escritorios")
def listar_escritorios(
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    escritorios = db.query(models.Escritorio).order_by(models.Escritorio.nome).all()
    return [_esc_to_dict(e, db) for e in escritorios]


@router.post("/escritorios")
def criar_escritorio(
    body: EscritorioCreate,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    slug = body.slug.strip().lower()
    if not _SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="Código inválido. Use 3-50 caracteres: letras minúsculas, números, '-' ou '_'.")

    existente = db.query(models.Escritorio).filter(models.Escritorio.slug == slug).first()
    if existente:
        raise HTTPException(status_code=409, detail=f"Código '{slug}' já está em uso.")

    plano = body.plano or "trial"
    if plano not in PLANOS:
        raise HTTPException(status_code=400, detail=f"Plano inválido. Opções: {', '.join(PLANOS.keys())}")

    limites = PLANOS[plano]
    agora = datetime.now(timezone.utc).isoformat()

    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    esc = models.Escritorio(
        nome=body.nome.strip(),
        slug=slug,
        plano=plano,
        max_empresas=body.max_empresas or limites["max_empresas"],
        max_usuarios=body.max_usuarios or limites["max_usuarios"],
        data_expiracao=None,
        ativo=True,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(esc)
    db.flush()

    admin_info = None
    # Criação de admin é OPCIONAL — se não fornecido, o responsável solicita acesso pela tela de login
    if body.usuario_admin and body.senha_admin:
        nome_admin = body.usuario_admin.strip().lower()
        if not re.match(r'^[a-zA-Z0-9._-]{3,30}$', nome_admin):
            raise HTTPException(status_code=400, detail="Nome do admin deve ter 3-30 caracteres alfanuméricos.")
        validar_forca_senha(body.senha_admin, nome_usuario=nome_admin)

        admin = models.Usuario(
            nome=nome_admin,
            senha_hash=pwd.hash(body.senha_admin[:72]),
            escritorio_id=esc.id,
            is_dono=True,
            is_admin=True,
            is_aprovado=True,
            nome_exibicao=(body.nome_admin or "").strip() or nome_admin,
            cargo="Administrador",
        )
        db.add(admin)
        admin_info = {"login": f"{nome_admin}@{slug}", "nome": admin.nome_exibicao}

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        db.query(models.Escritorio).filter(models.Escritorio.id == esc.id).delete()
        db.commit()
        import logging; logging.getLogger(__name__).error(f"Erro ao criar escritório: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao criar escritório.")
    db.refresh(esc)

    result = {
        "mensagem": f"Escritório '{esc.nome}' criado com sucesso.",
        "escritorio": _esc_to_dict(esc, db),
        "instrucoes": f"Informe o código '{slug}' ao responsável para que ele solicite acesso pela tela de login.",
    }
    if admin_info:
        result["usuario_admin"] = admin_info
    return result


@router.patch("/escritorios/{escritorio_id}")
def atualizar_escritorio(
    escritorio_id: int,
    body: EscritorioUpdate,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == escritorio_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escritório não encontrado.")

    if body.nome is not None:
        esc.nome = body.nome.strip()
    if body.plano is not None:
        if body.plano not in PLANOS:
            raise HTTPException(status_code=400, detail=f"Plano inválido.")
        esc.plano = body.plano
    if body.max_empresas is not None:
        esc.max_empresas = body.max_empresas
    if body.max_usuarios is not None:
        esc.max_usuarios = body.max_usuarios

    esc.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    return _esc_to_dict(esc, db)


@router.patch("/escritorios/{escritorio_id}/desativar")
def desativar_escritorio(
    escritorio_id: int,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == escritorio_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escritório não encontrado.")
    if esc.slug == _MASTER_SLUG:
        raise HTTPException(status_code=400, detail="Não é possível desativar o escritório master.")
    esc.ativo = False
    esc.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"mensagem": f"Escritório '{esc.nome}' desativado.", "escritorio": _esc_to_dict(esc, db)}


@router.patch("/escritorios/{escritorio_id}/ativar")
def ativar_escritorio(
    escritorio_id: int,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == escritorio_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escritório não encontrado.")
    esc.ativo = True
    esc.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"mensagem": f"Escritório '{esc.nome}' reativado.", "escritorio": _esc_to_dict(esc, db)}


@router.get("/metricas")
def metricas_globais(
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    total_escritorios = db.query(func.count(models.Escritorio.id)).scalar() or 0
    total_ativos = db.query(func.count(models.Escritorio.id)).filter(
        models.Escritorio.ativo == True  # noqa: E712
    ).scalar() or 0
    total_usuarios = db.query(func.count(models.Usuario.id)).scalar() or 0
    total_pendentes = db.query(func.count(models.Usuario.id)).filter(
        models.Usuario.is_aprovado == False  # noqa: E712
    ).scalar() or 0
    total_empresas = db.query(func.count(models.Empresa.id)).scalar() or 0
    total_lancamentos = db.query(func.count(models.LancamentoMensal.id)).scalar() or 0

    # Contagem por plano
    planos_rows = db.query(models.Escritorio.plano, func.count(models.Escritorio.id)).group_by(
        models.Escritorio.plano
    ).all()
    escritorios_por_plano = {r[0]: r[1] for r in planos_rows}

    return {
        "escritorios_total": total_escritorios,
        "escritorios_ativos": total_ativos,
        "escritorios_inativos": total_escritorios - total_ativos,
        "usuarios_total": total_usuarios,
        "usuarios_pendentes_global": total_pendentes,
        "empresas_total": total_empresas,
        "lancamentos_total": total_lancamentos,
        "escritorios_por_plano": escritorios_por_plano,
    }


# ── Detalhe de escritório ────────────────────────────────────────────

@router.get("/escritorios/{escritorio_id}")
def detalhar_escritorio(
    escritorio_id: int,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == escritorio_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escritório não encontrado.")
    return _esc_to_dict(esc, db)


@router.get("/escritorios/{escritorio_id}/resumo")
def resumo_escritorio(
    escritorio_id: int,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == escritorio_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escritório não encontrado.")
    total_usuarios = db.query(func.count(models.Usuario.id)).filter(
        models.Usuario.escritorio_id == esc.id
    ).scalar() or 0
    usuarios_pendentes = db.query(func.count(models.Usuario.id)).filter(
        models.Usuario.escritorio_id == esc.id,
        models.Usuario.is_aprovado == False  # noqa: E712
    ).scalar() or 0
    usuarios_ativos = db.query(func.count(models.Usuario.id)).filter(
        models.Usuario.escritorio_id == esc.id,
        models.Usuario.is_aprovado == True  # noqa: E712
    ).scalar() or 0
    total_empresas = db.query(func.count(models.Empresa.id)).filter(
        models.Empresa.escritorio_id == esc.id
    ).scalar() or 0
    return {
        "escritorio_id": esc.id,
        "nome": esc.nome,
        "slug": esc.slug,
        "plano": esc.plano,
        "ativo": esc.ativo,
        "max_empresas": esc.max_empresas,
        "max_usuarios": esc.max_usuarios,
        "total_usuarios": total_usuarios,
        "usuarios_pendentes": usuarios_pendentes,
        "usuarios_ativos": usuarios_ativos,
        "total_empresas": total_empresas,
    }


@router.delete("/escritorios/{escritorio_id}")
def excluir_escritorio(
    escritorio_id: int,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == escritorio_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escritório não encontrado.")
    if esc.slug == _MASTER_SLUG:
        raise HTTPException(status_code=400, detail="Não é possível excluir o escritório master.")
    num_empresas = db.query(func.count(models.Empresa.id)).filter(
        models.Empresa.escritorio_id == esc.id
    ).scalar() or 0
    if num_empresas > 0:
        raise HTTPException(status_code=400, detail=f"Escritório possui {num_empresas} empresa(s). Exclua-as primeiro.")
    # Delete users then escritorio
    db.query(models.Usuario).filter(models.Usuario.escritorio_id == esc.id).delete()
    db.delete(esc)
    db.commit()
    return {"mensagem": f"Escritório '{esc.nome}' excluído."}


# ── Usuários de um escritório ────────────────────────────────────────

@router.get("/escritorios/{escritorio_id}/usuarios")
def listar_usuarios_escritorio(
    escritorio_id: int,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == escritorio_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escritório não encontrado.")
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.escritorio_id == esc.id
    ).order_by(models.Usuario.nome).all()
    return {
        "escritorio": esc.nome,
        "slug": esc.slug,
        "usuarios": [_user_to_dict(u, esc.slug) for u in usuarios],
    }


# ── Listar TODOS os usuários (cross-tenant) ─────────────────────────

@router.get("/usuarios")
def listar_todos_usuarios(
    escritorio_id: Optional[int] = None,
    status: Optional[str] = None,
    busca: Optional[str] = None,
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    if not escritorio_id:
        raise HTTPException(
            status_code=400,
            detail="Selecione um escritório para listar seus usuários (escritorio_id obrigatório).",
        )

    # Validar que o escritório existe
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == escritorio_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escritório não encontrado.")

    q = db.query(models.Usuario).filter(models.Usuario.escritorio_id == escritorio_id)
    if status == "pendentes":
        q = q.filter(models.Usuario.is_aprovado == False)  # noqa: E712
    elif status == "ativos":
        q = q.filter(models.Usuario.is_aprovado == True)  # noqa: E712
    if busca and busca.strip():
        b = busca.strip().lower()
        q = q.filter(models.Usuario.nome.ilike(f"%{b}%"))

    usuarios = q.order_by(models.Usuario.is_aprovado.asc(), models.Usuario.nome).all()

    result = []
    for u in usuarios:
        d = _user_to_dict(u, esc.slug)
        d["escritorio_nome"] = esc.nome
        d["escritorio_slug"] = esc.slug
        result.append(d)

    return result


# ── Aprovar / Reprovar / Alterar role de usuários ────────────────────

@router.patch("/usuarios/{user_id}/aprovar")
def aprovar_usuario(
    user_id: int,
    escritorio_id: Optional[int] = Query(None),
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if escritorio_id and user.escritorio_id != escritorio_id:
        raise HTTPException(status_code=403, detail="Usuário não pertence a este escritório.")
    user.is_aprovado = True
    db.commit()
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == user.escritorio_id).first()
    return {"mensagem": f"Usuário '{user.nome}' aprovado.", "usuario": _user_to_dict(user, esc.slug if esc else "")}


@router.patch("/usuarios/{user_id}/reprovar")
def reprovar_usuario(
    user_id: int,
    escritorio_id: Optional[int] = Query(None),
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if escritorio_id and user.escritorio_id != escritorio_id:
        raise HTTPException(status_code=403, detail="Usuário não pertence a este escritório.")
    if getattr(user, "is_master", False):
        raise HTTPException(status_code=400, detail="Não é possível reprovar o usuário master.")
    user.is_aprovado = False
    db.commit()
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == user.escritorio_id).first()
    return {"mensagem": f"Usuário '{user.nome}' reprovado/bloqueado.", "usuario": _user_to_dict(user, esc.slug if esc else "")}


@router.patch("/usuarios/{user_id}/role")
def alterar_role(
    user_id: int,
    body: RoleUpdate,
    escritorio_id: Optional[int] = Query(None),
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if escritorio_id and user.escritorio_id != escritorio_id:
        raise HTTPException(status_code=403, detail="Usuário não pertence a este escritório.")
    if getattr(user, "is_master", False):
        raise HTTPException(status_code=400, detail="Permissões do master não podem ser alteradas.")

    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.is_ceo is not None:
        user.is_ceo = body.is_ceo
    if body.is_gestor is not None:
        user.is_gestor = body.is_gestor
    db.commit()

    esc = db.query(models.Escritorio).filter(models.Escritorio.id == user.escritorio_id).first()
    return {
        "mensagem": "Permissões atualizadas.",
        "usuario": _user_to_dict(user, esc.slug if esc else ""),
    }


@router.delete("/usuarios/{user_id}")
def excluir_usuario(
    user_id: int,
    escritorio_id: Optional[int] = Query(None),
    _master: models.Usuario = Depends(_get_master_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if escritorio_id and user.escritorio_id != escritorio_id:
        raise HTTPException(status_code=403, detail="Usuário não pertence a este escritório.")
    if getattr(user, "is_master", False):
        raise HTTPException(status_code=400, detail="Não é possível excluir o usuário master.")
    db.delete(user)
    db.commit()
    return {"mensagem": f"Usuário '{user.nome}' excluído."}
