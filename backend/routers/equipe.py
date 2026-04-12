"""
Router de Equipe — Controllo Analytics
Gestores e administradores podem designar/remover tarefas para colaboradores.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models
from services.auth_utils import SECRET_KEY, ALGORITHM, verificar_tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/api/equipe", tags=["equipe"])

_PRIORIDADES = {"baixa", "media", "alta", "urgente"}


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _get_user(token: str, db: Session) -> models.Usuario:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nome: str = payload.get("sub", "")
        if not nome:
            raise HTTPException(status_code=401, detail="Token inválido.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido.")
    user = db.query(models.Usuario).filter_by(nome=nome).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    if not user.is_aprovado:
        raise HTTPException(status_code=403, detail="Conta não aprovada.")
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    return _get_user(token, db)


async def get_gestor_or_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    user = _get_user(token, db)
    if not (user.is_admin or getattr(user, "is_gestor", False)):
        raise HTTPException(status_code=403, detail="Acesso restrito a gestores e administradores.")
    return user


# ── Schemas ───────────────────────────────────────────────────────────────────

class TarefaCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = ""
    prioridade: Optional[str] = "media"
    categoria: Optional[str] = ""
    data_entrega: Optional[str] = ""
    hora: Optional[str] = "09:00"

    def validar(self) -> None:
        if not self.titulo or len(self.titulo.strip()) < 2:
            raise HTTPException(400, "Título deve ter pelo menos 2 caracteres.")
        if len(self.titulo) > 200:
            raise HTTPException(400, "Título muito longo (máx. 200 caracteres).")
        if (self.prioridade or "media") not in _PRIORIDADES:
            raise HTTPException(400, "Prioridade inválida.")


class TarefaUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    prioridade: Optional[str] = None
    categoria: Optional[str] = None
    data_entrega: Optional[str] = None
    hora: Optional[str] = None
    concluida: Optional[bool] = None


def _tarefa_to_dict(t: models.TarefaEquipe) -> dict:
    return {
        "id": t.id,
        "destinatario_id": t.destinatario_id,
        "criador_id": t.criador_id,
        "titulo": t.titulo,
        "descricao": t.descricao or "",
        "prioridade": t.prioridade or "media",
        "categoria": t.categoria or "",
        "data_entrega": t.data_entrega or "",
        "hora": t.hora or "09:00",
        "concluida": bool(t.concluida),
        "criado_em": t.criado_em,
        "atualizado_em": t.atualizado_em,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/colaboradores")
def listar_colaboradores(
    current_user: models.Usuario = Depends(get_gestor_or_admin),
    db: Session = Depends(get_db),
):
    """Lista usuários aprovados do mesmo escritório com tarefas pendentes."""
    from sqlalchemy import func
    # Tenant isolation: gestor/admin vê apenas colaboradores do próprio escritório
    q = db.query(models.Usuario).filter(models.Usuario.is_aprovado == True)
    if not getattr(current_user, "is_master", False):
        q = q.filter(models.Usuario.escritorio_id == current_user.escritorio_id)
    usuarios = q.order_by(models.Usuario.nome).all()
    if not usuarios:
        return []

    usuario_ids = [u.id for u in usuarios]

    # Uma única query agrupada para contar pendentes de todos os usuários de uma vez
    contagens_raw = (
        db.query(models.TarefaEquipe.destinatario_id, func.count(models.TarefaEquipe.id))
        .filter(
            models.TarefaEquipe.destinatario_id.in_(usuario_ids),
            models.TarefaEquipe.concluida == False,
        )
        .group_by(models.TarefaEquipe.destinatario_id)
        .all()
    )
    contagens: dict[int, int] = {uid: cnt for uid, cnt in contagens_raw}

    return [
        {
            "id": u.id,
            "nome": u.nome,
            "nome_exibicao": u.nome_exibicao or "",
            "cargo": u.cargo or "",
            "is_admin": u.is_admin,
            "is_gestor": getattr(u, "is_gestor", False),
            "tarefas_pendentes": contagens.get(u.id, 0),
        }
        for u in usuarios
    ]


@router.get("/tarefas/{usuario_id}")
def listar_tarefas_usuario(
    usuario_id: int,
    current_user: models.Usuario = Depends(get_gestor_or_admin),
    db: Session = Depends(get_db),
):
    """Lista todas as tarefas de equipe de um colaborador."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(404, "Usuário não encontrado.")
    verificar_tenant(current_user, usuario.escritorio_id)
    tarefas = (
        db.query(models.TarefaEquipe)
        .filter(models.TarefaEquipe.destinatario_id == usuario_id)
        .order_by(models.TarefaEquipe.criado_em.desc())
        .all()
    )
    return [_tarefa_to_dict(t) for t in tarefas]


@router.get("/minhas-tarefas")
def minhas_tarefas_equipe(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna as tarefas designadas pelo gestor para o usuário atual."""
    tarefas = (
        db.query(models.TarefaEquipe)
        .filter(models.TarefaEquipe.destinatario_id == current_user.id)
        .order_by(models.TarefaEquipe.criado_em.desc())
        .all()
    )
    return [_tarefa_to_dict(t) for t in tarefas]


@router.post("/tarefas/{usuario_id}", status_code=201)
def criar_tarefa_equipe(
    usuario_id: int,
    body: TarefaCreate,
    current_user: models.Usuario = Depends(get_gestor_or_admin),
    db: Session = Depends(get_db),
):
    """Cria e designa uma tarefa para um colaborador."""
    body.validar()
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(404, "Usuário não encontrado.")
    verificar_tenant(current_user, usuario.escritorio_id)
    agora = datetime.now(timezone.utc).isoformat()
    tarefa = models.TarefaEquipe(
        destinatario_id=usuario_id,
        criador_id=current_user.id,
        titulo=body.titulo.strip(),
        descricao=(body.descricao or "").strip(),
        prioridade=body.prioridade or "media",
        categoria=(body.categoria or "").strip(),
        data_entrega=(body.data_entrega or "").strip(),
        hora=body.hora or "09:00",
        concluida=False,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(tarefa)
    db.commit()
    db.refresh(tarefa)
    return _tarefa_to_dict(tarefa)


@router.put("/tarefas/{usuario_id}/{tarefa_id}")
def atualizar_tarefa_equipe(
    usuario_id: int,
    tarefa_id: int,
    body: TarefaUpdate,
    current_user: models.Usuario = Depends(get_gestor_or_admin),
    db: Session = Depends(get_db),
):
    """Atualiza uma tarefa designada (gestor/admin ou o próprio destinatário pode marcar como concluída)."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(404, "Usuário não encontrado.")
    verificar_tenant(current_user, usuario.escritorio_id)
    tarefa = db.query(models.TarefaEquipe).filter(
        models.TarefaEquipe.id == tarefa_id,
        models.TarefaEquipe.destinatario_id == usuario_id,
    ).first()
    if not tarefa:
        raise HTTPException(404, "Tarefa não encontrada.")

    if body.titulo is not None:
        if len(body.titulo.strip()) < 2:
            raise HTTPException(400, "Título deve ter pelo menos 2 caracteres.")
        tarefa.titulo = body.titulo.strip()
    if body.descricao is not None:
        tarefa.descricao = body.descricao.strip()
    if body.prioridade is not None:
        if body.prioridade not in _PRIORIDADES:
            raise HTTPException(400, "Prioridade inválida.")
        tarefa.prioridade = body.prioridade
    if body.categoria is not None:
        tarefa.categoria = body.categoria.strip()
    if body.data_entrega is not None:
        tarefa.data_entrega = body.data_entrega.strip()
    if body.hora is not None:
        tarefa.hora = body.hora.strip()
    if body.concluida is not None:
        tarefa.concluida = body.concluida

    tarefa.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(tarefa)
    return _tarefa_to_dict(tarefa)


@router.patch("/minhas-tarefas/{tarefa_id}/concluir")
def concluir_minha_tarefa(
    tarefa_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permite que o próprio colaborador marque uma tarefa como concluída/pendente."""
    tarefa = db.query(models.TarefaEquipe).filter(
        models.TarefaEquipe.id == tarefa_id,
        models.TarefaEquipe.destinatario_id == current_user.id,
    ).first()
    if not tarefa:
        raise HTTPException(404, "Tarefa não encontrada.")
    tarefa.concluida = not tarefa.concluida
    tarefa.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(tarefa)
    return _tarefa_to_dict(tarefa)


@router.delete("/tarefas/{usuario_id}/{tarefa_id}", status_code=204)
def remover_tarefa_equipe(
    usuario_id: int,
    tarefa_id: int,
    current_user: models.Usuario = Depends(get_gestor_or_admin),
    db: Session = Depends(get_db),
):
    """Remove uma tarefa designada."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(404, "Usuário não encontrado.")
    verificar_tenant(current_user, usuario.escritorio_id)
    tarefa = db.query(models.TarefaEquipe).filter(
        models.TarefaEquipe.id == tarefa_id,
        models.TarefaEquipe.destinatario_id == usuario_id,
    ).first()
    if not tarefa:
        raise HTTPException(404, "Tarefa não encontrada.")
    db.delete(tarefa)
    db.commit()
    return None
