"""
Router de Log de Auditoria
Registra ações relevantes no sistema (login, empresas, importações, etc.).
O endpoint GET é restrito a administradores.
A função `registrar_auditoria()` pode ser importada por qualquer router.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models

router = APIRouter(prefix="/api/auditoria", tags=["auditoria"])

from services.auth_utils import get_current_user as _auth_user


def _get_admin(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login")), db: Session = Depends(get_db)) -> models.Usuario:
    user = _auth_user(token, db)
    if not user.is_admin and not getattr(user, "is_master", False):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return user


# ──────────────────────────────────────────────────────────────────
#  Utilitário — importável por qualquer módulo
# ──────────────────────────────────────────────────────────────────

def registrar_auditoria(
    db: Session,
    acao: str,
    *,
    usuario_id: Optional[int] = None,
    usuario_nome: str = "",
    escritorio_id: Optional[int] = None,
    recurso: str = "",
    recurso_id: Optional[int] = None,
    detalhes: Optional[dict] = None,
    ip: str = "",
) -> None:
    """
    Grava uma linha no log de auditoria.
    Engole silenciosamente qualquer erro para não interromper o fluxo principal.
    """
    try:
        db.add(models.AuditoriaLog(
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            escritorio_id=escritorio_id,
            acao=acao,
            recurso=recurso,
            recurso_id=recurso_id,
            detalhes=json.dumps(detalhes or {}, ensure_ascii=False),
            ip=ip,
            criado_em=datetime.now(timezone.utc).isoformat(),
        ))
        db.commit()
    except Exception:
        db.rollback()


# ──────────────────────────────────────────────────────────────────
#  GET /api/auditoria  — lista com filtros (admin only)
# ──────────────────────────────────────────────────────────────────

@router.get("")
def listar_auditoria(
    acao: Optional[str]    = Query(None, description="Filtrar por ação específica"),
    recurso: Optional[str] = Query(None, description="Filtrar por tipo de recurso"),
    usuario: Optional[str] = Query(None, description="Filtrar por nome de usuário"),
    data_inicio: Optional[str] = Query(None, description="ISO date mínima (YYYY-MM-DD)"),
    data_fim: Optional[str]    = Query(None, description="ISO date máxima (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    _admin: models.Usuario = Depends(_get_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.AuditoriaLog)
    # Tenant isolation: non-master admins see only their own escritório logs
    if not getattr(_admin, "is_master", False):
        eid = getattr(_admin, "_escritorio_id", None) or _admin.escritorio_id
        q = q.filter(
            (models.AuditoriaLog.escritorio_id == eid)
            | (models.AuditoriaLog.escritorio_id == None)  # noqa: E711 — include legacy logs without eid
        )

    if acao:
        q = q.filter(models.AuditoriaLog.acao == acao)
    if recurso:
        q = q.filter(models.AuditoriaLog.recurso == recurso)
    if usuario:
        q = q.filter(models.AuditoriaLog.usuario_nome.ilike(f"%{usuario}%"))
    if data_inicio:
        # Aceita apenas YYYY-MM-DD para evitar injeção via string
        if len(data_inicio) == 10 and data_inicio.count("-") == 2:
            q = q.filter(models.AuditoriaLog.criado_em >= data_inicio + "T00:00:00")
    if data_fim:
        if len(data_fim) == 10 and data_fim.count("-") == 2:
            q = q.filter(models.AuditoriaLog.criado_em <= data_fim + "T23:59:59")

    total = q.count()
    logs = (
        q.order_by(models.AuditoriaLog.criado_em.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    def _fmt(log: models.AuditoriaLog) -> dict:
        try:
            det = json.loads(log.detalhes) if log.detalhes else {}
        except Exception:
            det = {}
        return {
            "id":           log.id,
            "usuario_id":   log.usuario_id,
            "usuario_nome": log.usuario_nome,
            "escritorio_id": getattr(log, "escritorio_id", None),
            "acao":         log.acao,
            "recurso":      log.recurso,
            "recurso_id":   log.recurso_id,
            "detalhes":     det,
            "ip":           log.ip,
            "criado_em":    log.criado_em,
        }

    return {
        "items":    [_fmt(l) for l in logs],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    max(1, -(-total // per_page)),
    }


# ──────────────────────────────────────────────────────────────────
#  GET /api/auditoria/acoes  — lista de ações distintas (para filtros)
# ──────────────────────────────────────────────────────────────────

@router.get("/acoes")
def listar_acoes(
    _admin: models.Usuario = Depends(_get_admin),
    db: Session = Depends(get_db),
):
    from sqlalchemy import distinct
    acoes = db.query(distinct(models.AuditoriaLog.acao)).order_by(models.AuditoriaLog.acao).all()
    return [a[0] for a in acoes]
