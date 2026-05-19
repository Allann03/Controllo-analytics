"""
Serviço de envio de e-mail via SMTP.
Configuração via variáveis de ambiente:
  SMTP_HOST     (default: smtp.gmail.com)
  SMTP_PORT     (default: 587)
  SMTP_USER     e-mail remetente
  SMTP_PASS     senha / app password
  SMTP_FROM     nome + e-mail exibido (opcional)
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


def _smtp_configurado() -> bool:
    return bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASS"))


def enviar_email(
    destinatario: str,
    assunto: str,
    corpo_html: str,
    corpo_texto: Optional[str] = None,
) -> None:
    """
    Envia um e-mail via SMTP TLS.
    Lança RuntimeError se SMTP não estiver configurado ou se houver falha.
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    smtp_from = os.environ.get("SMTP_FROM", f"Controllo BPO <{smtp_user}>")

    if not (smtp_user and smtp_pass):
        raise RuntimeError(
            "SMTP não configurado. Defina SMTP_USER e SMTP_PASS nas variáveis de ambiente."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"]    = smtp_from
    msg["To"]      = destinatario

    if corpo_texto:
        msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))

    contexto = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as servidor:
        servidor.ehlo()
        servidor.starttls(context=contexto)
        servidor.login(smtp_user, smtp_pass)
        servidor.sendmail(smtp_user, destinatario, msg.as_string())


def smtp_esta_configurado() -> bool:
    return _smtp_configurado()


# ─────────────────────────────────────────────────────────────────
#  Templates de alerta
# ─────────────────────────────────────────────────────────────────

def _base_html(titulo: str, corpo: str, empresa: str, periodo: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #f1f5f9; margin: 0; padding: 20px; }}
  .card {{ background: white; border-radius: 12px; padding: 32px; max-width: 600px; margin: 0 auto; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .logo {{ color: #4F6AFF; font-weight: 900; font-size: 18px; letter-spacing: 2px; margin-bottom: 24px; }}
  h2 {{ color: #1e293b; margin: 0 0 8px 0; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: bold; margin-bottom: 16px; }}
  .badge-ok     {{ background: #d1fae5; color: #065f46; }}
  .badge-atencao{{ background: #fef3c7; color: #92400e; }}
  .badge-critico{{ background: #fee2e2; color: #7f1d1d; }}
  .meta {{ color: #64748b; font-size: 13px; margin-bottom: 24px; }}
  .alerta {{ padding: 14px 16px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid; }}
  .alerta-critico{{ background: #fef2f2; border-color: #ef4444; color: #991b1b; }}
  .alerta-atencao{{ background: #fffbeb; border-color: #f59e0b; color: #92400e; }}
  .alerta-info   {{ background: #eff6ff; border-color: #3b82f6; color: #1d4ed8; }}
  .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 12px; }}
</style></head>
<body>
<div class="card">
  <div class="logo">CONTROLLO BPO</div>
  <h2>{titulo}</h2>
  <div class="meta">Empresa: <strong>{empresa}</strong> · Período: <strong>{periodo}</strong></div>
  {corpo}
  <div class="footer">
    Este e-mail foi enviado automaticamente pelo sistema Controllo BPO Analytics.<br>
    Não responda a este e-mail.
  </div>
</div>
</body></html>"""


def corpo_alertas_financeiros(
    empresa: str,
    periodo: str,
    alertas: list[dict],
) -> str:
    """Gera o HTML do e-mail de alertas financeiros."""
    itens_html = ""
    for a in alertas:
        sev = a.get("severidade", "info")
        css = f"alerta-{sev}"
        itens_html += f"""<div class="alerta {css}">
          <strong>{a.get('titulo', '')}</strong><br>
          {a.get('descricao', '')}
        </div>"""

    total = len(alertas)
    criticos = sum(1 for a in alertas if a.get("severidade") == "critico")
    badge_cls = "badge-critico" if criticos else "badge-atencao" if total else "badge-ok"
    badge_txt = f"🔴 {criticos} crítico(s)" if criticos else f"⚠️ {total} alerta(s)"

    corpo = f"""<span class="badge {badge_cls}">{badge_txt}</span>
    <p>Os seguintes alertas foram identificados na análise financeira do período:</p>
    {itens_html}"""

    return _base_html(
        titulo="Alertas Financeiros Identificados",
        corpo=corpo,
        empresa=empresa,
        periodo=periodo,
    )


def corpo_resumo_mensal(
    empresa: str,
    periodo: str,
    metricas: dict,
) -> str:
    """Gera o HTML do e-mail de resumo mensal."""
    fmt_brl = lambda v: f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

    ll = metricas.get("lucro_liquido", 0)
    cor_ll = "#065f46" if ll >= 0 else "#7f1d1d"

    corpo = f"""<table style="width:100%; border-collapse:collapse; font-size:14px;">
      <tr style="background:#f8fafc">
        <td style="padding:10px 12px; color:#64748b; font-weight:bold;">Receita Bruta</td>
        <td style="padding:10px 12px; text-align:right; font-family:monospace;">{fmt_brl(metricas.get('receita_bruta', 0))}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px; color:#64748b; font-weight:bold;">Receita Líquida</td>
        <td style="padding:10px 12px; text-align:right; font-family:monospace;">{fmt_brl(metricas.get('receita_liquida', 0))}</td>
      </tr>
      <tr style="background:#f8fafc">
        <td style="padding:10px 12px; color:#64748b; font-weight:bold;">Lucro Bruto</td>
        <td style="padding:10px 12px; text-align:right; font-family:monospace;">{fmt_brl(metricas.get('lucro_bruto', 0))}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px; font-weight:bold; font-size:15px;">Lucro Líquido</td>
        <td style="padding:10px 12px; text-align:right; font-family:monospace; font-weight:bold; color:{cor_ll}; font-size:15px;">{fmt_brl(ll)}</td>
      </tr>
      <tr style="background:#f8fafc">
        <td style="padding:10px 12px; color:#64748b; font-weight:bold;">Margem Líquida</td>
        <td style="padding:10px 12px; text-align:right; font-family:monospace;">{metricas.get('margem_liquida', 0):.1f}%</td>
      </tr>
      <tr>
        <td style="padding:10px 12px; color:#64748b; font-weight:bold;">Carga Tributária</td>
        <td style="padding:10px 12px; text-align:right; font-family:monospace;">{metricas.get('carga_tributaria', 0):.1f}%</td>
      </tr>
    </table>"""

    return _base_html(
        titulo="Resumo Financeiro Mensal",
        corpo=corpo,
        empresa=empresa,
        periodo=periodo,
    )


def corpo_email_livre(
    remetente_nome: str,
    assunto_original: str,
    mensagem: str,
) -> str:
    """Gera o HTML de um e-mail livre (mensagem personalizada do usuário)."""
    mensagem_html = mensagem.replace("\n", "<br>")
    corpo = f"""
    <p style="color:#475569;font-size:14px;margin-bottom:20px;">
      Mensagem enviada por <strong>{remetente_nome}</strong> via Controllo BPO:
    </p>
    <div style="background:#f8fafc;border-left:4px solid #4F6AFF;border-radius:4px;padding:20px 24px;font-size:14px;color:#1e293b;line-height:1.7;">
      {mensagem_html}
    </div>"""
    return _base_html(
        titulo=assunto_original,
        corpo=corpo,
        empresa=remetente_nome,
        periodo="",
    )
