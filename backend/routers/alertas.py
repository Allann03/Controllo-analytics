"""
Router de Alertas e Configurações de E-mail
Permite ao usuário configurar seus alertas financeiros automáticos
e disparar e-mails de resumo/alerta manualmente.
"""

import os
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models
from services.email_service import (
    enviar_email, smtp_esta_configurado,
    corpo_alertas_financeiros, corpo_resumo_mensal, corpo_email_livre,
)

router = APIRouter(prefix="/api/alertas", tags=["alertas"])

# ──────────────────────────────────────────────────────────────────
#  Auth
# ──────────────────────────────────────────────────────────────────

from services.auth_utils import get_current_user as _get_user, resolve_empresa_or_403


# ──────────────────────────────────────────────────────────────────
#  Schemas
# ──────────────────────────────────────────────────────────────────

class ConfigAlertaUpsert(BaseModel):
    email_destino: str
    ativo: bool = True
    alertar_margem_negativa: bool = True
    alertar_caixa_negativo: bool = True
    alertar_desvio_orcamento: bool = True
    threshold_desvio_pct: float = 20.0        # % de desvio para disparar alerta
    resumo_mensal_ativo: bool = False
    dia_resumo_mensal: int = 1                 # dia do mês para enviar o resumo


class EnviarEmailManualBody(BaseModel):
    empresa_id: int
    tipo: str   # "alertas" | "resumo"
    ano: int
    mes: int
    email_destino: str


class TesteEmailBody(BaseModel):
    email_destino: str


class EmailLivreBody(BaseModel):
    email_destino: str
    assunto: str
    mensagem: str


# ──────────────────────────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────────────────────────

@router.get("/status-smtp")
def status_smtp(_user: models.Usuario = Depends(_get_user)):
    """Informa se o SMTP está configurado nas variáveis de ambiente."""
    smtp_user = os.environ.get("SMTP_USER", "")
    # Exibe apenas domínio do e-mail para não expor o endereço completo
    usuario_mascarado = ""
    if smtp_user and "@" in smtp_user:
        partes = smtp_user.split("@")
        usuario_mascarado = f"***@{partes[-1]}"
    return {
        "configurado": smtp_esta_configurado(),
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "porta": os.environ.get("SMTP_PORT", "587"),
        "usuario": usuario_mascarado,
    }


@router.get("/configuracao/{empresa_id}")
def obter_config(
    empresa_id: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Retorna a configuração de alertas de uma empresa."""
    resolve_empresa_or_403(db, empresa_id, user)
    cfg = db.query(models.ConfigAlerta).filter(
        models.ConfigAlerta.empresa_id == empresa_id,
        models.ConfigAlerta.usuario_id == user.id,
    ).first()
    if not cfg:
        return {"empresa_id": empresa_id, "configurado": False}
    return _cfg_to_dict(cfg)


@router.put("/configuracao/{empresa_id}")
def salvar_config(
    empresa_id: int,
    body: ConfigAlertaUpsert,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Cria ou atualiza a configuração de alertas de uma empresa."""
    resolve_empresa_or_403(db, empresa_id, user)

    if not body.email_destino or "@" not in body.email_destino:
        raise HTTPException(status_code=400, detail="E-mail de destino inválido.")

    agora = datetime.now(timezone.utc).isoformat()
    cfg = db.query(models.ConfigAlerta).filter(
        models.ConfigAlerta.empresa_id == empresa_id,
        models.ConfigAlerta.usuario_id == user.id,
    ).first()

    dados = body.model_dump()
    if cfg:
        for k, v in dados.items():
            setattr(cfg, k, v)
        cfg.atualizado_em = agora
    else:
        cfg = models.ConfigAlerta(
            empresa_id=empresa_id,
            usuario_id=user.id,
            criado_em=agora,
            atualizado_em=agora,
            **dados,
        )
        db.add(cfg)

    db.commit()
    db.refresh(cfg)
    return _cfg_to_dict(cfg)


@router.post("/teste-email")
def testar_email(
    body: TesteEmailBody,
    user: models.Usuario = Depends(_get_user),
):
    """Envia um e-mail de teste para verificar a configuração SMTP."""
    if not smtp_esta_configurado():
        raise HTTPException(
            status_code=503,
            detail="SMTP não configurado. Defina SMTP_USER e SMTP_PASS nas variáveis de ambiente do servidor.",
        )
    try:
        html = """<!DOCTYPE html><html><body style="font-family:Arial;padding:24px">
        <h2 style="color:#4F6AFF">✅ Controllo BPO — Teste de E-mail</h2>
        <p>Se você recebeu esta mensagem, a configuração de e-mail está funcionando corretamente.</p>
        <p style="color:#64748b;font-size:12px">Enviado automaticamente pelo sistema Controllo BPO Analytics.</p>
        </body></html>"""
        enviar_email(body.email_destino, "Controllo BPO — Teste de Configuração", html)
        return {"mensagem": f"E-mail de teste enviado para {body.email_destino}."}
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"Falha ao enviar e-mail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao enviar alerta por e-mail.")


@router.post("/enviar-livre")
def enviar_email_livre(
    body: EmailLivreBody,
    user: models.Usuario = Depends(_get_user),
):
    """Envia um e-mail livre com assunto e mensagem personalizados pelo usuário."""
    if not smtp_esta_configurado():
        raise HTTPException(
            status_code=503,
            detail="SMTP não configurado. Defina SMTP_USER e SMTP_PASS nas variáveis de ambiente do servidor.",
        )
    if not body.email_destino or "@" not in body.email_destino:
        raise HTTPException(status_code=400, detail="E-mail de destino inválido.")
    if not body.assunto.strip():
        raise HTTPException(status_code=400, detail="Assunto não pode ser vazio.")
    if not body.mensagem.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia.")

    try:
        html = corpo_email_livre(
            remetente_nome=user.nome,
            assunto_original=body.assunto.strip(),
            mensagem=body.mensagem.strip(),
        )
        enviar_email(body.email_destino, body.assunto.strip(), html)
        return {"mensagem": f"E-mail enviado para {body.email_destino}."}
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"Falha ao enviar e-mail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao enviar alerta por e-mail.")


@router.post("/enviar-manual")
def enviar_email_manual(
    body: EnviarEmailManualBody,
    bg: BackgroundTasks,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Dispara manualmente um e-mail de alertas ou resumo para uma empresa/período."""
    empresa = resolve_empresa_or_403(db, body.empresa_id, user)

    if not smtp_esta_configurado():
        raise HTTPException(
            status_code=503,
            detail="SMTP não configurado no servidor. Contate o administrador.",
        )

    if body.tipo not in ("alertas", "resumo"):
        raise HTTPException(status_code=400, detail="Tipo deve ser 'alertas' ou 'resumo'.")

    MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    periodo = f"{MESES[body.mes-1]}/{body.ano}"

    lanc = db.query(models.LancamentoMensal).filter(
        models.LancamentoMensal.empresa_id == body.empresa_id,
        models.LancamentoMensal.ano == body.ano,
        models.LancamentoMensal.mes == body.mes,
    ).first()

    if not lanc:
        raise HTTPException(status_code=404, detail="Nenhum dado para este período.")

    def _enviar():
        try:
            rl  = lanc.receita_bruta - lanc.deducoes_receita
            lb  = rl - lanc.custo_servicos
            desp= lanc.despesas_adm + lanc.despesas_comerciais + lanc.despesas_financeiras + lanc.outras_despesas
            ebit= lb - desp
            ll  = ebit - lanc.ir_csll

            if body.tipo == "resumo":
                html = corpo_resumo_mensal(
                    empresa=empresa.nome,
                    periodo=periodo,
                    metricas={
                        "receita_bruta": lanc.receita_bruta,
                        "receita_liquida": rl,
                        "lucro_bruto": lb,
                        "lucro_liquido": ll,
                        "margem_liquida": (ll / lanc.receita_bruta * 100) if lanc.receita_bruta else 0,
                        "carga_tributaria": ((lanc.deducoes_receita + lanc.ir_csll) / lanc.receita_bruta * 100) if lanc.receita_bruta else 0,
                    },
                )
                assunto = f"Controllo BPO — Resumo Financeiro {periodo} | {empresa.nome}"

            else:  # alertas
                alertas_list = []
                saldo_fc = lanc.saldo_inicial_caixa + lanc.entradas_caixa - lanc.saidas_caixa
                if ll < 0:
                    alertas_list.append({"titulo": "Prejuízo no período", "descricao": f"Lucro líquido negativo: R$ {ll:,.0f}. Revise as despesas e a precificação.", "severidade": "critico"})
                if saldo_fc < 0:
                    alertas_list.append({"titulo": "Saldo de caixa negativo", "descricao": f"Saldo final de caixa: R$ {saldo_fc:,.0f}. Risco de inadimplência.", "severidade": "critico"})
                if lanc.receita_bruta > 0:
                    ml = ll / lanc.receita_bruta * 100
                    if ml < 5:
                        alertas_list.append({"titulo": "Margem líquida baixa", "descricao": f"Margem líquida de {ml:.1f}%. Abaixo do mínimo recomendado de 5%.", "severidade": "atencao"})

                if not alertas_list:
                    alertas_list.append({"titulo": "Situação Financeira Normal", "descricao": "Nenhum alerta crítico identificado neste período.", "severidade": "info"})

                html = corpo_alertas_financeiros(empresa=empresa.nome, periodo=periodo, alertas=alertas_list)
                assunto = f"Controllo BPO — Alertas Financeiros {periodo} | {empresa.nome}"

            enviar_email(body.email_destino, assunto, html)
        except Exception as exc:
            # Registra falha no log do servidor em vez de silenciar
            print(f"[CONTROLLO][alertas] Falha ao enviar e-mail para {body.email_destino}: {exc}")

    bg.add_task(_enviar)
    return {"mensagem": f"E-mail em processamento. Será enviado para {body.email_destino}."}


# ──────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────

def _cfg_to_dict(cfg: models.ConfigAlerta) -> dict:
    return {
        "id": cfg.id,
        "empresa_id": cfg.empresa_id,
        "configurado": True,
        "email_destino": cfg.email_destino,
        "ativo": cfg.ativo,
        "alertar_margem_negativa": cfg.alertar_margem_negativa,
        "alertar_caixa_negativo": cfg.alertar_caixa_negativo,
        "alertar_desvio_orcamento": cfg.alertar_desvio_orcamento,
        "threshold_desvio_pct": cfg.threshold_desvio_pct,
        "resumo_mensal_ativo": cfg.resumo_mensal_ativo,
        "dia_resumo_mensal": cfg.dia_resumo_mensal,
        "atualizado_em": cfg.atualizado_em,
    }
