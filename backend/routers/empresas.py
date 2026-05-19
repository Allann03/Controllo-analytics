"""
Router: Gestão de Empresas (admin-only)
Cadastra, edita e remove empresas do sistema.
Endpoint base: /api/empresas
"""

import math
import os
import re
from datetime import datetime, timezone
from typing import Optional

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-.]+$')

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from data.database.config import get_db
from data.database import models

router = APIRouter(prefix="/api/empresas", tags=["empresas"])

_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
from services.auth_utils import get_current_user as _auth_user, verificar_empresa_tenant
from routers.auditoria import registrar_auditoria


# ── Auth helper ──────────────────────────────────────────────────────────────

def _get_admin(
    token: str = Depends(_oauth2),
    db: Session = Depends(get_db),
) -> models.Usuario:
    user = _auth_user(token, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return user


# ── CNPJ helpers ─────────────────────────────────────────────────────────────

def _validar_cnpj(cnpj: str) -> bool:
    n = re.sub(r"\D", "", cnpj)
    if len(n) != 14 or len(set(n)) == 1:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    def calc(nums, pesos):
        s = sum(int(nums[i]) * pesos[i] for i in range(len(pesos)))
        r = s % 11
        return 0 if r < 2 else 11 - r

    return int(n[12]) == calc(n, pesos1) and int(n[13]) == calc(n, pesos2)


def _formatar_cnpj(cnpj: str) -> str:
    n = re.sub(r"\D", "", cnpj)
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:14]}"


# ── Schemas ───────────────────────────────────────────────────────────────────

class EmpresaAdminCreate(BaseModel):
    nome: str
    cnpj: Optional[str] = ""
    ccm: Optional[str] = ""
    ie: Optional[str] = ""
    segmento: Optional[str] = ""
    porte: Optional[str] = ""
    regime_tributario: Optional[str] = "simples"
    faturamento_medio_mensal: Optional[float] = 0.0
    telefone: Optional[str] = ""
    email_contato: Optional[str] = ""
    responsavel_financeiro: Optional[str] = ""
    observacoes: Optional[str] = ""


class EmpresaAdminUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    ccm: Optional[str] = None
    ie: Optional[str] = None
    segmento: Optional[str] = None
    porte: Optional[str] = None
    regime_tributario: Optional[str] = None
    faturamento_medio_mensal: Optional[float] = None
    telefone: Optional[str] = None
    email_contato: Optional[str] = None
    responsavel_financeiro: Optional[str] = None
    observacoes: Optional[str] = None


class BancoCreate(BaseModel):
    banco: str
    banco_codigo: Optional[str] = ""
    agencia: Optional[str] = ""
    conta: Optional[str] = ""
    tipo_conta: Optional[str] = "corrente"
    chave_pix: Optional[str] = ""
    saldo_inicial: Optional[float] = 0.0
    data_saldo_inicial: Optional[str] = ""
    observacoes: Optional[str] = ""


class BancoUpdate(BaseModel):
    banco: Optional[str] = None
    banco_codigo: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    chave_pix: Optional[str] = None
    saldo_inicial: Optional[float] = None
    data_saldo_inicial: Optional[str] = None
    ativo: Optional[bool] = None
    observacoes: Optional[str] = None


# ── Serializer ───────────────────────────────────────────────────────────────

def _to_dict(
    e: models.Empresa,
    carteira_usuario_nome: Optional[str] = None,
    carteira_usuario_id: Optional[int] = None,
) -> dict:
    return {
        "id": e.id,
        "nome": e.nome,
        "nome_fantasia": getattr(e, "nome_fantasia", "") or "",
        "cnpj": e.cnpj or "",
        "ccm": e.ccm or "",
        "ie": getattr(e, "ie", "") or "",
        "segmento": getattr(e, "segmento", "") or "",
        "porte": getattr(e, "porte", "") or "",
        "regime_tributario": getattr(e, "regime_tributario", "simples") or "simples",
        "faturamento_medio_mensal": getattr(e, "faturamento_medio_mensal", 0.0) or 0.0,
        "telefone": getattr(e, "telefone", "") or "",
        "email_contato": getattr(e, "email_contato", "") or "",
        "responsavel_financeiro": getattr(e, "responsavel_financeiro", "") or "",
        "observacoes": e.observacoes or "",
        "ativa": e.ativa,
        "carteira_usuario_id": carteira_usuario_id,
        "carteira_usuario_nome": carteira_usuario_nome,
        "criado_em": e.criado_em,
        "atualizado_em": e.atualizado_em,
    }


def _enrich(empresas: list, db: Session) -> list:
    """Adiciona info de carteira (quem tem cada empresa). Usa apenas 2 queries."""
    ids = [e.id for e in empresas]
    membros: dict = {}
    usuarios: dict = {}
    try:
        if ids:
            membros = {
                m.empresa_id: m
                for m in db.query(models.CarteiraMembro)
                .filter(models.CarteiraMembro.empresa_id.in_(ids))
                .all()
            }
        # Filtra apenas usuários que aparecem na carteira das empresas carregadas
        usuario_ids = {m.usuario_id for m in membros.values()}
        if usuario_ids:
            usuarios = {
                u.id: u.nome
                for u in db.query(models.Usuario)
                .filter(models.Usuario.id.in_(usuario_ids))
                .all()
            }
    except Exception as exc:
        print(f"[CONTROLLO] Aviso em _enrich: {exc}")
    result = []
    for e in empresas:
        m = membros.get(e.id)
        nome = usuarios.get(m.usuario_id) if m else None
        uid = m.usuario_id if m else None
        result.append(_to_dict(e, nome, uid))
    return result


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def listar_empresas(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=500),
    busca: str = "",
    _admin: models.Usuario = Depends(_get_admin),
    db: Session = Depends(get_db),
):
    query = db.query(models.Empresa)
    # Tenant isolation: filtra por escritório (master vê tudo)
    _is_master = getattr(_admin, "_is_master", False) or getattr(_admin, "is_master", False)
    if not _is_master:
        _eid = getattr(_admin, "_escritorio_id", None) or getattr(_admin, "escritorio_id", None)
        if _eid:
            query = query.filter(models.Empresa.escritorio_id == _eid)

    if busca.strip():
        b = busca.strip()
        b_nums = "".join(c for c in b if c.isdigit())
        conds = [
            models.Empresa.nome.ilike(f"%{b}%"),
            models.Empresa.nome_fantasia.ilike(f"%{b}%"),
        ]
        if b_nums:
            conds.append(models.Empresa.cnpj.contains(b_nums))
        query = query.filter(or_(*conds))

    total = query.count()
    empresas = (
        query.order_by(models.Empresa.nome.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "items": _enrich(empresas, db),
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, math.ceil(total / per_page)),
    }


@router.post("", status_code=201)
def criar_empresa(
    body: EmpresaAdminCreate,
    _admin: models.Usuario = Depends(_get_admin),
    db: Session = Depends(get_db),
):
    nome = body.nome.strip() if body.nome else ""
    if len(nome) < 2:
        raise HTTPException(status_code=400, detail="Nome deve ter pelo menos 2 caracteres.")

    cnpj_fmt = ""
    if body.cnpj and body.cnpj.strip():
        nums = re.sub(r"\D", "", body.cnpj.strip())
        if nums:
            if not _validar_cnpj(nums):
                raise HTTPException(status_code=400, detail="CNPJ inválido — verifique os dígitos verificadores.")
            cnpj_fmt = _formatar_cnpj(nums)
            dup = db.query(models.Empresa).filter(models.Empresa.cnpj == cnpj_fmt).first()
            if dup:
                raise HTTPException(status_code=409, detail=f"CNPJ já cadastrado para '{dup.nome}'.")

    email_contato = (body.email_contato or "").strip()[:150]
    if email_contato and not _EMAIL_RE.match(email_contato):
        raise HTTPException(status_code=400, detail="E-mail de contato inválido.")

    regime = (body.regime_tributario or "simples").strip()
    if regime not in ("simples", "presumido", "real"):
        raise HTTPException(status_code=400, detail="Regime tributário inválido.")

    agora = datetime.now(timezone.utc).isoformat()
    empresa = models.Empresa(
        nome=nome,
        nome_fantasia="",
        cnpj=cnpj_fmt,
        ccm=(body.ccm or "").strip(),
        ie=(body.ie or "").strip(),
        segmento=(body.segmento or "").strip()[:100],
        porte=(body.porte or "").strip(),
        regime_tributario=regime,
        faturamento_medio_mensal=float(body.faturamento_medio_mensal or 0.0),
        telefone=(body.telefone or "").strip()[:30],
        email_contato=email_contato,
        responsavel_financeiro=(body.responsavel_financeiro or "").strip()[:100],
        status="iniciada",
        ativa=True,
        observacoes=(body.observacoes or "").strip()[:500],
        escritorio_id=getattr(_admin, "_escritorio_id", None) or getattr(_admin, "escritorio_id", None),
        usuario_id=_admin.id,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    registrar_auditoria(db, "criar_empresa_admin", usuario_id=_admin.id, usuario_nome=_admin.nome,
                        escritorio_id=_admin.escritorio_id, recurso="empresa", recurso_id=empresa.id,
                        detalhes={"nome": empresa.nome})
    return {"mensagem": "Empresa cadastrada com sucesso.", "empresa": _to_dict(empresa)}


@router.put("/{empresa_id}")
def atualizar_empresa(
    empresa_id: int,
    body: EmpresaAdminUpdate,
    _admin: models.Usuario = Depends(_get_admin),
    db: Session = Depends(get_db),
):
    empresa = verificar_empresa_tenant(db, _admin, empresa_id)

    if body.nome is not None:
        nome = body.nome.strip()
        if len(nome) < 2:
            raise HTTPException(status_code=400, detail="Nome deve ter pelo menos 2 caracteres.")
        empresa.nome = nome

    if body.cnpj is not None:
        nums = re.sub(r"\D", "", body.cnpj.strip())
        if nums:
            if not _validar_cnpj(nums):
                raise HTTPException(status_code=400, detail="CNPJ inválido — verifique os dígitos verificadores.")
            cnpj_fmt = _formatar_cnpj(nums)
            dup = db.query(models.Empresa).filter(
                models.Empresa.cnpj == cnpj_fmt,
                models.Empresa.id != empresa_id,
            ).first()
            if dup:
                raise HTTPException(status_code=409, detail=f"CNPJ já cadastrado para '{dup.nome}'.")
            empresa.cnpj = cnpj_fmt
        else:
            empresa.cnpj = ""

    if body.ccm is not None:
        empresa.ccm = body.ccm.strip()[:50]

    if body.ie is not None:
        empresa.ie = body.ie.strip()[:30]

    if body.segmento is not None:
        empresa.segmento = body.segmento.strip()[:100]

    if body.porte is not None:
        empresa.porte = body.porte.strip()

    if body.regime_tributario is not None:
        if body.regime_tributario not in ("simples", "presumido", "real"):
            raise HTTPException(status_code=400, detail="Regime tributário inválido.")
        empresa.regime_tributario = body.regime_tributario

    if body.faturamento_medio_mensal is not None:
        empresa.faturamento_medio_mensal = float(body.faturamento_medio_mensal)

    if body.telefone is not None:
        empresa.telefone = body.telefone.strip()[:30]

    if body.email_contato is not None:
        ec = body.email_contato.strip()[:150]
        if ec and not _EMAIL_RE.match(ec):
            raise HTTPException(status_code=400, detail="E-mail de contato inválido.")
        empresa.email_contato = ec

    if body.responsavel_financeiro is not None:
        empresa.responsavel_financeiro = body.responsavel_financeiro.strip()[:100]

    if body.observacoes is not None:
        empresa.observacoes = body.observacoes.strip()[:500]

    empresa.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(empresa)

    m = db.query(models.CarteiraMembro).filter(models.CarteiraMembro.empresa_id == empresa_id).first()
    nome_dono: Optional[str] = None
    uid_dono: Optional[int] = None
    if m:
        u = db.query(models.Usuario).filter(models.Usuario.id == m.usuario_id).first()
        nome_dono = u.nome if u else None
        uid_dono = m.usuario_id

    registrar_auditoria(db, "atualizar_empresa_admin", usuario_id=_admin.id, usuario_nome=_admin.nome,
                        escritorio_id=_admin.escritorio_id, recurso="empresa", recurso_id=empresa_id,
                        detalhes={"nome": empresa.nome})
    return {"mensagem": "Empresa atualizada.", "empresa": _to_dict(empresa, nome_dono, uid_dono)}


@router.get("/{empresa_id}/dados")
def verificar_dados_empresa(
    empresa_id: int,
    _admin: models.Usuario = Depends(_get_admin),
    db: Session = Depends(get_db),
):
    """Verifica se a empresa possui dados financeiros vinculados."""
    empresa = verificar_empresa_tenant(db, _admin, empresa_id)

    tem_lancamentos = db.query(models.LancamentoMensal).filter(
        models.LancamentoMensal.empresa_id == empresa_id
    ).first() is not None

    tem_importacoes = db.query(models.Importacao).filter(
        models.Importacao.empresa_id == empresa_id
    ).first() is not None

    tem_transacoes = db.query(models.TransacaoBancaria).filter(
        models.TransacaoBancaria.empresa_id == empresa_id
    ).first() is not None

    has_data = tem_lancamentos or tem_importacoes or tem_transacoes

    return {
        "has_data": has_data,
        "nome": empresa.nome,
        "lancamentos": tem_lancamentos,
        "importacoes": tem_importacoes,
        "transacoes": tem_transacoes,
    }


@router.delete("/{empresa_id}")
def excluir_empresa(
    empresa_id: int,
    nome_confirmacao: Optional[str] = Query(None),
    _admin: models.Usuario = Depends(_get_admin),
    db: Session = Depends(get_db),
):
    empresa = verificar_empresa_tenant(db, _admin, empresa_id)

    # Verifica dados vinculados
    tem_dados = (
        db.query(models.LancamentoMensal).filter(models.LancamentoMensal.empresa_id == empresa_id).first() is not None
        or db.query(models.Importacao).filter(models.Importacao.empresa_id == empresa_id).first() is not None
        or db.query(models.TransacaoBancaria).filter(models.TransacaoBancaria.empresa_id == empresa_id).first() is not None
    )

    if tem_dados:
        if not nome_confirmacao or nome_confirmacao.strip().lower() != empresa.nome.strip().lower():
            raise HTTPException(
                status_code=409,
                detail=f"Empresa possui dados importados. Para confirmar, informe o nome exato: '{empresa.nome}'.",
            )

    # Todas as exclusões em cascata dentro de uma única transação atômica
    nome_empresa = empresa.nome
    try:
        if tem_dados:
            db.query(models.LancamentoMensal).filter(models.LancamentoMensal.empresa_id == empresa_id).delete()
            db.query(models.Importacao).filter(models.Importacao.empresa_id == empresa_id).delete()
            db.query(models.TransacaoBancaria).filter(models.TransacaoBancaria.empresa_id == empresa_id).delete()
            db.query(models.OrcamentoMensal).filter(models.OrcamentoMensal.empresa_id == empresa_id).delete()
            db.query(models.ConfigAlerta).filter(models.ConfigAlerta.empresa_id == empresa_id).delete()
            db.query(models.MapeamentoContas).filter(models.MapeamentoContas.empresa_id == empresa_id).delete()
            db.query(models.EmpresaFiscal).filter(models.EmpresaFiscal.empresa_id == empresa_id).delete()

        db.query(models.CarteiraMembro).filter(models.CarteiraMembro.empresa_id == empresa_id).delete()
        db.query(models.EmpresaBanco).filter(models.EmpresaBanco.empresa_id == empresa_id).delete()
        db.delete(empresa)
        db.commit()
    except Exception as exc:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(f"Erro ao excluir empresa: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao excluir empresa.")

    registrar_auditoria(db, "excluir_empresa_admin", usuario_id=_admin.id, usuario_nome=_admin.nome,
                        escritorio_id=_admin.escritorio_id, recurso="empresa", recurso_id=empresa_id,
                        detalhes={"nome": nome_empresa})
    return {"mensagem": f"Empresa '{nome_empresa}' excluída com sucesso."}


@router.patch("/{empresa_id}/reatribuir")
def reatribuir_empresa(
    empresa_id: int,
    novo_usuario_id: Optional[int] = None,
    _admin: models.Usuario = Depends(_get_admin),
    db: Session = Depends(get_db),
):
    """Admin pode mover empresa da carteira de um usuário para outro (ou liberar)."""
    empresa = verificar_empresa_tenant(db, _admin, empresa_id)

    membro = db.query(models.CarteiraMembro).filter(
        models.CarteiraMembro.empresa_id == empresa_id
    ).first()

    if novo_usuario_id is None:
        # Liberar a empresa
        if membro:
            db.delete(membro)
    else:
        usuario = db.query(models.Usuario).filter(models.Usuario.id == novo_usuario_id).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        if membro:
            membro.usuario_id = novo_usuario_id
        else:
            db.add(models.CarteiraMembro(
                empresa_id=empresa_id,
                usuario_id=novo_usuario_id,
                adicionado_em=datetime.now(timezone.utc).isoformat(),
            ))

    db.commit()
    return {"mensagem": "Empresa reatribuída com sucesso."}


# ── Bancos da empresa ──────────────────────────────────────────────────────────

def _get_user(
    token: str = Depends(_oauth2),
    db: Session = Depends(get_db),
) -> models.Usuario:
    return _auth_user(token, db)


def _banco_to_dict(b: models.EmpresaBanco) -> dict:
    return {
        "id": b.id,
        "empresa_id": b.empresa_id,
        "banco": b.banco,
        "banco_codigo": b.banco_codigo or "",
        "agencia": b.agencia or "",
        "conta": b.conta or "",
        "tipo_conta": b.tipo_conta or "corrente",
        "chave_pix": b.chave_pix or "",
        "saldo_inicial": b.saldo_inicial or 0.0,
        "data_saldo_inicial": b.data_saldo_inicial or "",
        "ativo": b.ativo,
        "observacoes": b.observacoes or "",
        "criado_em": b.criado_em,
        "atualizado_em": b.atualizado_em,
    }


@router.get("/{empresa_id}/bancos")
def listar_bancos(
    empresa_id: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    verificar_empresa_tenant(db, user, empresa_id)
    bancos = (
        db.query(models.EmpresaBanco)
        .filter(models.EmpresaBanco.empresa_id == empresa_id)
        .order_by(models.EmpresaBanco.id.asc())
        .all()
    )
    return [_banco_to_dict(b) for b in bancos]


@router.post("/{empresa_id}/bancos", status_code=201)
def adicionar_banco(
    empresa_id: int,
    body: BancoCreate,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    verificar_empresa_tenant(db, user, empresa_id)

    total = db.query(models.EmpresaBanco).filter(
        models.EmpresaBanco.empresa_id == empresa_id,
        models.EmpresaBanco.ativo == True,
    ).count()
    if total >= 10:
        raise HTTPException(status_code=400, detail="Limite de 10 contas bancárias ativas por empresa.")

    banco_nome = (body.banco or "").strip()
    if not banco_nome:
        raise HTTPException(status_code=400, detail="Nome do banco é obrigatório.")

    agora = datetime.now(timezone.utc).isoformat()
    banco = models.EmpresaBanco(
        empresa_id=empresa_id,
        banco=banco_nome[:100],
        banco_codigo=(body.banco_codigo or "").strip()[:10],
        agencia=(body.agencia or "").strip()[:20],
        conta=(body.conta or "").strip()[:30],
        tipo_conta=(body.tipo_conta or "corrente").strip(),
        chave_pix=(body.chave_pix or "").strip()[:150],
        saldo_inicial=float(body.saldo_inicial or 0.0),
        data_saldo_inicial=(body.data_saldo_inicial or "").strip()[:10],
        ativo=True,
        observacoes=(body.observacoes or "").strip()[:500],
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(banco)
    db.commit()
    db.refresh(banco)
    return {"mensagem": "Banco adicionado.", "banco": _banco_to_dict(banco)}


@router.put("/{empresa_id}/bancos/{banco_id}")
def atualizar_banco(
    empresa_id: int,
    banco_id: int,
    body: BancoUpdate,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    verificar_empresa_tenant(db, user, empresa_id)
    banco = db.query(models.EmpresaBanco).filter(
        models.EmpresaBanco.id == banco_id,
        models.EmpresaBanco.empresa_id == empresa_id,
    ).first()
    if not banco:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada.")

    if body.banco is not None:
        banco.banco = body.banco.strip()[:100]
    if body.banco_codigo is not None:
        banco.banco_codigo = body.banco_codigo.strip()[:10]
    if body.agencia is not None:
        banco.agencia = body.agencia.strip()[:20]
    if body.conta is not None:
        banco.conta = body.conta.strip()[:30]
    if body.tipo_conta is not None:
        banco.tipo_conta = body.tipo_conta.strip()
    if body.chave_pix is not None:
        banco.chave_pix = body.chave_pix.strip()[:150]
    if body.saldo_inicial is not None:
        banco.saldo_inicial = float(body.saldo_inicial)
    if body.data_saldo_inicial is not None:
        banco.data_saldo_inicial = body.data_saldo_inicial.strip()[:10]
    if body.ativo is not None:
        banco.ativo = body.ativo
    if body.observacoes is not None:
        banco.observacoes = body.observacoes.strip()[:500]

    banco.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(banco)
    return {"mensagem": "Banco atualizado.", "banco": _banco_to_dict(banco)}


@router.delete("/{empresa_id}/bancos/{banco_id}", status_code=200)
def remover_banco(
    empresa_id: int,
    banco_id: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    verificar_empresa_tenant(db, user, empresa_id)
    banco = db.query(models.EmpresaBanco).filter(
        models.EmpresaBanco.id == banco_id,
        models.EmpresaBanco.empresa_id == empresa_id,
    ).first()
    if not banco:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada.")
    db.delete(banco)
    db.commit()
    return {"mensagem": "Conta bancária removida."}
