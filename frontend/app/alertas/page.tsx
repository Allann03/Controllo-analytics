"use client";

import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

// ─────────────────────────────────────────────────────────────────
//  Tipos
// ─────────────────────────────────────────────────────────────────

interface SmtpStatus { configurado: boolean; host: string; porta: string; usuario: string; }

interface ConfigAlerta {
  configurado: boolean;
  email_destino: string;
  ativo: boolean;
  alertar_margem_negativa: boolean;
  alertar_caixa_negativo: boolean;
  alertar_desvio_orcamento: boolean;
  threshold_desvio_pct: number;
  resumo_mensal_ativo: boolean;
  dia_resumo_mensal: number;
  atualizado_em?: string;
}

// ─────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────

const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const ANOS  = Array.from({ length: 3 }, (_, i) => new Date().getFullYear() - i);

// ── Premium Toggle ────────────────────────────────────────────────
function Toggle({ value, onChange, label }: { value: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <div
      className="flex items-center justify-between gap-4 py-3.5"
      style={{ borderBottom: "1px solid rgba(79,106,255,0.08)" }}
    >
      <span className="text-sm flex-1 min-w-0" style={{ color: "var(--text-secondary, #94a3b8)" }}>{label}</span>
      <button
        onClick={() => onChange(!value)}
        className="relative flex-shrink-0 rounded-full transition-all duration-300"
        style={{
          width: 44,
          height: 24,
          background: value
            ? "linear-gradient(135deg, #102a43, #1e3a5f)"
            : "rgba(71,85,105,0.60)",
          boxShadow: value ? "0 0 12px rgba(79,106,255,0.40)" : "none",
        }}
      >
        <span
          className="absolute rounded-full bg-white shadow-md transition-transform duration-300"
          style={{
            width: 16, height: 16,
            top: 4, left: 4,
            transform: value ? "translateX(20px)" : "translateX(0px)",
            boxShadow: value ? "0 2px 8px rgba(79,106,255,0.30)" : "0 1px 4px rgba(0,0,0,0.30)",
          }}
        />
      </button>
    </div>
  );
}

// ── Section Card ─────────────────────────────────────────────────
function SectionCard({
  children,
  title,
  subtitle,
  icon,
  accentColor = "#102a43",
}: {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  accentColor?: string;
}) {
  return (
    <div
      className="section-card-alertas rounded-2xl overflow-hidden"
      style={{
        background: "var(--bg-card, #1e293b)",
        border: "1px solid var(--border, #334155)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
      }}
    >
      {/* Gradient top accent */}
      <div className="h-px" style={{ background: `linear-gradient(90deg, ${accentColor}, transparent 70%)` }} />

      <div className="p-6">
        {/* Section header */}
        <div className="flex items-center gap-3 mb-5">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{
              background: `${accentColor}18`,
              border: `1px solid ${accentColor}30`,
            }}
          >
            {icon}
          </div>
          <div>
            <h2
              className="text-xs font-bold tracking-widest uppercase"
              style={{ color: accentColor, letterSpacing: "0.12em" }}
            >
              {title}
            </h2>
            {subtitle && (
              <p className="text-xs mt-0.5 text-slate-500 dark:text-slate-400">{subtitle}</p>
            )}
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

// ── Input style helper ────────────────────────────────────────────
// Theme-aware: branco/borda-slate no claro, escuro no escuro
const inputCls = [
  "w-full rounded-xl px-3 py-2.5 text-sm focus:outline-none transition-all",
  "bg-white dark:bg-slate-900/80",
  "border border-slate-300 dark:border-slate-700/60",
  "text-slate-900 dark:text-slate-200",
  "placeholder:text-slate-400 dark:placeholder:text-slate-500",
  "focus:border-blue-700 focus:ring-2 focus:ring-blue-900/20",
].join(" ");
const labelCls = "text-[10px] font-bold text-slate-500 uppercase tracking-widest";

// ─────────────────────────────────────────────────────────────────
//  Pagina
// ─────────────────────────────────────────────────────────────────

export default function AlertasPage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [smtp, setSmtp]                 = useState<SmtpStatus | null>(null);
  const [config, setConfig]             = useState<ConfigAlerta | null>(null);
  const [carregando, setCarregando]     = useState(false);
  const [salvando, setSalvando]         = useState(false);
  const [enviando, setEnviando]         = useState(false);

  // Form state
  const [emailDestino, setEmailDestino] = useState("");
  const [ativo, setAtivo]               = useState(true);
  const [margem, setMargem]             = useState(true);
  const [caixa, setCaixa]               = useState(true);
  const [desvio, setDesvio]             = useState(true);
  const [threshold, setThreshold]       = useState("20");
  const [resumoAtivo, setResumoAtivo]   = useState(false);
  const [diaResumo, setDiaResumo]       = useState("1");

  // Envio manual
  const [anoMan, setAnoMan]         = useState(new Date().getFullYear());
  const [mesMan, setMesMan]         = useState(new Date().getMonth() + 1);
  const [tipoMan, setTipoMan]       = useState<"alertas" | "resumo">("alertas");
  const [emailMan, setEmailMan]     = useState("");

  // Teste
  const [emailTeste, setEmailTeste] = useState("");
  const [testando, setTestando]     = useState(false);

  // Email livre
  const [emailLivre, setEmailLivre]     = useState("");
  const [assuntoLivre, setAssuntoLivre] = useState("");
  const [msgLivre, setMsgLivre]         = useState("");
  const [enviandoLivre, setEnviandoLivre] = useState(false);

  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("controllo_token") ?? "";
    fetch(`${API}/api/alertas/status-smtp`, { headers: { Authorization: `Bearer ${t}` } })
      .then(r => r.json())
      .then(setSmtp)
      .catch(() => {});
  }, []);

  const carregarConfig = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true);
    try {
      const r = await fetch(`${API}/api/alertas/configuracao/${empresaId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("controllo_token") ?? ""}` },
        signal,
      });
      const d: ConfigAlerta = await r.json();
      setConfig(d);
      if (d.configurado) {
        setEmailDestino(d.email_destino ?? "");
        setAtivo(d.ativo);
        setMargem(d.alertar_margem_negativa);
        setCaixa(d.alertar_caixa_negativo);
        setDesvio(d.alertar_desvio_orcamento);
        setThreshold(String(d.threshold_desvio_pct));
        setResumoAtivo(d.resumo_mensal_ativo);
        setDiaResumo(String(d.dia_resumo_mensal));
        setEmailMan(d.email_destino ?? "");
      }
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
    } finally { setCarregando(false); }
  }, [empresaId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregarConfig(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregarConfig]);

  function exibirMsg(tipo: "ok" | "erro", texto: string) {
    setMsg({ tipo, texto });
    setTimeout(() => setMsg(null), 4000);
  }

  async function salvar() {
    if (!empresaId) return;
    if (!emailDestino || !emailDestino.includes("@")) {
      exibirMsg("erro", "Informe um e-mail valido.");
      return;
    }
    setSalvando(true);
    try {
      const r = await fetch(`${API}/api/alertas/configuracao/${empresaId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("controllo_token") ?? ""}` },
        body: JSON.stringify({
          email_destino: emailDestino.trim(),
          ativo, alertar_margem_negativa: margem,
          alertar_caixa_negativo: caixa, alertar_desvio_orcamento: desvio,
          threshold_desvio_pct: parseFloat(threshold) || 20,
          resumo_mensal_ativo: resumoAtivo,
          dia_resumo_mensal: parseInt(diaResumo) || 1,
        }),
      });
      if (!r.ok) { const d = await r.json(); exibirMsg("erro", d.detail || "Erro ao salvar."); return; }
      exibirMsg("ok", "Configuracao salva com sucesso.");
      carregarConfig();
    } finally { setSalvando(false); }
  }

  async function testar() {
    if (!emailTeste || !emailTeste.includes("@")) { exibirMsg("erro", "Informe um e-mail para teste."); return; }
    setTestando(true);
    try {
      const r = await fetch(`${API}/api/alertas/teste-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("controllo_token") ?? ""}` },
        body: JSON.stringify({ email_destino: emailTeste.trim() }),
      });
      const d = await r.json();
      if (!r.ok) exibirMsg("erro", d.detail || "Falha no envio.");
      else exibirMsg("ok", d.mensagem);
    } finally { setTestando(false); }
  }

  async function enviarLivre() {
    if (!emailLivre || !emailLivre.includes("@")) { exibirMsg("erro", "Informe um e-mail valido."); return; }
    if (!assuntoLivre.trim()) { exibirMsg("erro", "Assunto nao pode ser vazio."); return; }
    if (!msgLivre.trim()) { exibirMsg("erro", "Mensagem nao pode ser vazia."); return; }
    setEnviandoLivre(true);
    try {
      const r = await fetch(`${API}/api/alertas/enviar-livre`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("controllo_token") ?? ""}` },
        body: JSON.stringify({ email_destino: emailLivre.trim(), assunto: assuntoLivre.trim(), mensagem: msgLivre.trim() }),
      });
      const d = await r.json();
      if (!r.ok) exibirMsg("erro", d.detail || "Erro ao enviar.");
      else { exibirMsg("ok", d.mensagem); setEmailLivre(""); setAssuntoLivre(""); setMsgLivre(""); }
    } catch { exibirMsg("erro", "Erro de conexao com o servidor."); }
    finally { setEnviandoLivre(false); }
  }

  async function enviarManual() {
    if (!empresaId) return;
    if (!emailMan || !emailMan.includes("@")) { exibirMsg("erro", "Informe o e-mail de destino."); return; }
    setEnviando(true);
    try {
      const r = await fetch(`${API}/api/alertas/enviar-manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("controllo_token") ?? ""}` },
        body: JSON.stringify({
          empresa_id: empresaId,
          tipo: tipoMan,
          ano: anoMan,
          mes: mesMan,
          email_destino: emailMan.trim(),
        }),
      });
      const d = await r.json();
      if (!r.ok) exibirMsg("erro", d.detail || "Erro ao enviar.");
      else exibirMsg("ok", d.mensagem);
    } finally { setEnviando(false); }
  }

  // ── SVG Icons ────────────────────────────────────────────────────
  const BellIcon = ({ color = "#3b6ea5", size = 16 }: { color?: string; size?: number }) => (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  );
  const MailIcon = ({ color = "#3b6ea5", size = 16 }: { color?: string; size?: number }) => (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
  const CalendarIcon = ({ color = "#3b6ea5", size = 16 }: { color?: string; size?: number }) => (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  );
  const SendIcon = ({ color = "#3b6ea5", size = 16 }: { color?: string; size?: number }) => (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
    </svg>
  );
  const SettingsIcon = ({ color = "#3b6ea5", size = 16 }: { color?: string; size?: number }) => (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );

  return (
    <div className="min-h-full bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">

      {/* ── HEADER ── */}
      <div className="relative overflow-hidden border-b border-slate-100 dark:border-slate-800">
        <div className="absolute inset-0 pointer-events-none" style={{
          background: "radial-gradient(ellipse 60% 80% at 0% 0%, rgba(79,106,255,0.06), transparent 70%)",
        }} />
        <div className="relative px-6 pt-6 pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800/40">
                <BellIcon color="#be123c" size={18} />
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-navy-600 dark:text-navy-400 mb-0.5">Configurações</p>
                <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 leading-tight">
                  Alertas por <span className="text-blue-900 dark:text-navy-400">E-mail</span>
                </h1>
                <p className="text-sm mt-0.5 text-slate-500 dark:text-slate-400">
                  Configure notificações financeiras automáticas
                  {empresaSelecionada && (
                    <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-semibold bg-navy-50 dark:bg-navy-900/30 text-navy-700 dark:text-navy-300 border border-navy-200 dark:border-navy-800/50">
                      {empresaSelecionada.nome}
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="px-6 py-5 space-y-4 max-w-4xl mx-auto">

        {/* Feedback message — contraste WCAG AA em ambos os temas */}
        {msg && (
          <div className={`feedback-msg-${msg.tipo} px-4 py-3 rounded-xl border text-sm font-medium transition-all ${
            msg.tipo === "ok"
              ? "bg-emerald-950/30 border-emerald-500/25 text-emerald-300 dark:text-emerald-300"
              : "bg-rose-950/30 border-rose-500/25 text-rose-300 dark:text-rose-300"
          }`}>
            {msg.texto}
          </div>
        )}

        {/* ── SMTP Status ── */}
        {smtp && (
          <div className={`rounded-2xl overflow-hidden ${smtp.configurado ? "alerta-ok-banner" : "alerta-warning-banner"}`}
            style={{
              background: smtp.configurado
                ? "linear-gradient(135deg, rgba(16,185,129,0.08), rgba(6,78,59,0.05))"
                : "linear-gradient(135deg, rgba(245,158,11,0.08), rgba(78,62,6,0.05))",
              border: smtp.configurado
                ? "1px solid rgba(16,185,129,0.25)"
                : "1px solid rgba(245,158,11,0.30)",
            }}
          >
            <div className="h-px" style={{
              background: smtp.configurado
                ? "linear-gradient(90deg, #10b981, transparent 60%)"
                : "linear-gradient(90deg, #f59e0b, transparent 60%)",
            }} />
            <div className="p-5">
              <div className="flex items-center gap-3">
                <div
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{
                    background: smtp.configurado ? "#10b981" : "#f59e0b",
                    boxShadow: smtp.configurado ? "0 0 8px rgba(16,185,129,0.60)" : "0 0 8px rgba(245,158,11,0.60)",
                    animation: smtp.configurado ? "pulse 2s infinite" : "none",
                  }}
                />
                <div className="flex-1">
                  {/* Texto usa classes para WCAG AA em ambos os temas */}
                  <p className={`banner-text text-sm font-bold ${smtp.configurado ? "text-emerald-700 dark:text-emerald-300 alerta-ok-text" : "text-amber-800 dark:text-amber-300 alerta-warning-text"}`}>
                    {smtp.configurado ? "SMTP Configurado" : "SMTP não configurado"}
                  </p>
                  {smtp.configurado ? (
                    <p className="text-xs mt-0.5 text-slate-600 dark:text-slate-400">
                      {smtp.host}:{smtp.porta} · {smtp.usuario}
                    </p>
                  ) : (
                    <p className={`banner-text-muted text-xs mt-0.5 text-amber-700 dark:text-amber-400 alerta-warning-text-muted`}>
                      Defina SMTP_USER, SMTP_PASS e SMTP_HOST nas variáveis de ambiente para habilitar o envio.
                    </p>
                  )}
                </div>
              </div>

              {/* Test email */}
              {smtp.configurado && (
                <div className="mt-4 flex gap-2">
                  <input
                    value={emailTeste}
                    onChange={e => setEmailTeste(e.target.value)}
                    placeholder="seu@email.com"
                    className={inputCls}
                    style={{ flex: 1 }}
                    onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(79,106,255,0.45)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(79,106,255,0.10)"; }}
                    onBlur={e => { (e.target as HTMLInputElement).style.borderColor = ""; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                  />
                  <button
                    onClick={testar}
                    disabled={testando}
                    className="text-white text-sm font-bold px-4 py-2 rounded-xl transition-all disabled:opacity-50 active:scale-95"
                    style={{
                      background: "linear-gradient(135deg, #10b981, #065f46)",
                      boxShadow: "0 4px 14px rgba(16,185,129,0.30)",
                    }}
                  >
                    {testando ? "Enviando..." : "Testar"}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Alert configuration ── */}
        {empresaId ? (
          carregando ? (
            <div className="flex justify-center py-12">
              <div
                className="w-7 h-7 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: "rgba(79,106,255,0.20)", borderTopColor: "#102a43" }}
              />
            </div>
          ) : (
            <SectionCard
              title="Configuracao de Alertas"
              subtitle={config?.atualizado_em ? `Atualizado: ${new Date(config.atualizado_em).toLocaleDateString("pt-BR")}` : "Defina quando e como receber notificacoes"}
              icon={<SettingsIcon color="#3b6ea5" />}
            >
              <div className="space-y-1">
                <div className="mb-4">
                  <label className={labelCls}>E-mail de destino</label>
                  <input
                    value={emailDestino}
                    onChange={e => setEmailDestino(e.target.value)}
                    type="email"
                    placeholder="financeiro@empresa.com"
                    className={inputCls}
                    style={{ marginTop: 6 }}
                    onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(79,106,255,0.45)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(79,106,255,0.10)"; }}
                    onBlur={e => { (e.target as HTMLInputElement).style.borderColor = ""; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                  />
                </div>

                <Toggle value={ativo} onChange={setAtivo} label="Alertas ativos" />
                <Toggle value={margem} onChange={setMargem} label="Alertar quando margem liquida for negativa" />
                <Toggle value={caixa} onChange={setCaixa} label="Alertar quando saldo de caixa for negativo" />
                <Toggle value={desvio} onChange={setDesvio} label="Alertar quando desvio do orcamento ultrapassar threshold" />

                {desvio && (
                  <div className="pt-2 pb-1">
                    <label className={labelCls}>Threshold de desvio (%)</label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={threshold}
                      onChange={e => setThreshold(e.target.value)}
                      className={inputCls}
                      style={{ marginTop: 6, width: 128 }}
                      onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(79,106,255,0.45)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(79,106,255,0.10)"; }}
                      onBlur={e => { (e.target as HTMLInputElement).style.borderColor = ""; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                    />
                  </div>
                )}

                <Toggle value={resumoAtivo} onChange={setResumoAtivo} label="Enviar resumo financeiro mensal por e-mail" />

                {resumoAtivo && (
                  <div className="pt-2 pb-1">
                    <label className={labelCls}>Dia do mes para envio do resumo</label>
                    <input
                      type="number"
                      min="1"
                      max="28"
                      value={diaResumo}
                      onChange={e => setDiaResumo(e.target.value)}
                      className={inputCls}
                      style={{ marginTop: 6, width: 96 }}
                      onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(79,106,255,0.45)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(79,106,255,0.10)"; }}
                      onBlur={e => { (e.target as HTMLInputElement).style.borderColor = ""; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                    />
                    <p className="text-[11px] mt-1.5" style={{ color: "var(--text-muted, #64748b)" }}>
                      O resumo do mes anterior sera enviado automaticamente neste dia.
                    </p>
                  </div>
                )}
              </div>

              <button
                onClick={salvar}
                disabled={salvando}
                className="w-full mt-5 text-sm font-bold py-3 rounded-xl text-white transition-all disabled:opacity-50 active:scale-[0.98]"
                style={{
                  background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                  boxShadow: "0 4px 18px rgba(79,106,255,0.35)",
                }}
                onMouseEnter={e => { if (!salvando) (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 24px rgba(79,106,255,0.50)"; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 18px rgba(79,106,255,0.35)"; }}
              >
                {salvando ? "Salvando..." : "Salvar Configuracao"}
              </button>

              {!smtp?.configurado && (
                <p className="text-xs mt-3 text-center" style={{ color: "rgba(251,191,36,0.65)" }}>
                  Configure o SMTP no servidor para habilitar o envio de e-mails.
                </p>
              )}
            </SectionCard>
          )
        ) : (
          /* No empresa selected empty state */
          <div className="rounded-2xl overflow-hidden border border-dashed border-slate-300 dark:border-slate-700">
            <div className="h-px" style={{ background: "linear-gradient(90deg, #102a43, transparent 60%)" }} />
            <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-5"
                style={{
                  background: "linear-gradient(135deg, rgba(79,106,255,0.14), rgba(123,143,255,0.06))",
                  border: "1px solid rgba(79,106,255,0.22)",
                  boxShadow: "0 0 30px rgba(79,106,255,0.10)",
                }}
              >
                <BellIcon color="#3b6ea5" size={22} />
              </div>
              <p className="text-sm font-bold mb-1.5" style={{ color: "var(--text-secondary, #94a3b8)" }}>
                Nenhuma empresa selecionada
              </p>
              <p className="text-xs" style={{ color: "var(--text-muted, #64748b)" }}>
                Selecione uma empresa no seletor acima para configurar os alertas de e-mail.
              </p>
            </div>
          </div>
        )}

        {/* ── Manual dispatch ── */}
        {empresaId && smtp?.configurado && (
          <SectionCard
            title="Envio Manual"
            subtitle="Dispare um relatorio ou alerta para um periodo especifico"
            icon={<SendIcon color="#10b981" />}
            accentColor="#10b981"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className={labelCls}>Tipo</label>
                <select
                  value={tipoMan}
                  onChange={e => setTipoMan(e.target.value as "alertas" | "resumo")}
                  className={inputCls}
                  style={{ marginTop: 6 }}
                >
                  <option value="alertas">Alertas</option>
                  <option value="resumo">Resumo Mensal</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Mes</label>
                <select
                  value={mesMan}
                  onChange={e => setMesMan(Number(e.target.value))}
                  className={inputCls}
                  style={{ marginTop: 6 }}
                >
                  {MESES.map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Ano</label>
                <select
                  value={anoMan}
                  onChange={e => setAnoMan(Number(e.target.value))}
                  className={inputCls}
                  style={{ marginTop: 6 }}
                >
                  {ANOS.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>E-mail destino</label>
                <input
                  value={emailMan}
                  onChange={e => setEmailMan(e.target.value)}
                  placeholder="destino@email.com"
                  className={inputCls}
                  style={{ marginTop: 6 }}
                  onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(79,106,255,0.45)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(79,106,255,0.10)"; }}
                  onBlur={e => { (e.target as HTMLInputElement).style.borderColor = ""; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                />
              </div>
            </div>

            <button
              onClick={enviarManual}
              disabled={enviando}
              className="mt-4 text-sm font-semibold px-5 py-2.5 rounded-xl transition-all disabled:opacity-50 active:scale-95"
              style={{
                background: "rgba(16,185,129,0.10)",
                border: "1px solid rgba(16,185,129,0.25)",
                color: "#6ee7b7",
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(16,185,129,0.18)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(16,185,129,0.10)"; }}
            >
              {enviando ? "Enviando..." : "Enviar agora"}
            </button>
          </SectionCard>
        )}

        {/* ── Free email ── */}
        {smtp?.configurado && (
          <SectionCard
            title="E-mail Personalizado"
            subtitle="Envie uma mensagem livre para qualquer destinatario"
            icon={<MailIcon color="#3b6ea5" />}
          >
            <div className="space-y-3">
              <div>
                <label className={labelCls}>Para</label>
                <input
                  value={emailLivre}
                  onChange={e => setEmailLivre(e.target.value)}
                  type="email"
                  placeholder="destinatario@email.com"
                  className={inputCls}
                  style={{ marginTop: 6 }}
                  onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(79,106,255,0.45)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(79,106,255,0.10)"; }}
                  onBlur={e => { (e.target as HTMLInputElement).style.borderColor = ""; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                />
              </div>
              <div>
                <label className={labelCls}>Assunto</label>
                <input
                  value={assuntoLivre}
                  onChange={e => setAssuntoLivre(e.target.value)}
                  placeholder="Ex: Extrato de Janeiro/2025"
                  className={inputCls}
                  style={{ marginTop: 6 }}
                  onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(79,106,255,0.45)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(79,106,255,0.10)"; }}
                  onBlur={e => { (e.target as HTMLInputElement).style.borderColor = ""; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                />
              </div>
              <div>
                <label className={labelCls}>Mensagem</label>
                <textarea
                  value={msgLivre}
                  onChange={e => setMsgLivre(e.target.value)}
                  rows={4}
                  placeholder="Digite a mensagem..."
                  className={inputCls}
                  style={{ marginTop: 6, resize: "none" }}
                  onFocus={e => { (e.target as HTMLTextAreaElement).style.borderColor = "rgba(79,106,255,0.45)"; (e.target as HTMLTextAreaElement).style.boxShadow = "0 0 0 3px rgba(79,106,255,0.10)"; }}
                  onBlur={e => { (e.target as HTMLTextAreaElement).style.borderColor = ""; (e.target as HTMLTextAreaElement).style.boxShadow = "none"; }}
                />
              </div>
            </div>

            <button
              onClick={enviarLivre}
              disabled={enviandoLivre}
              className="mt-4 text-white text-sm font-bold px-5 py-2.5 rounded-xl transition-all disabled:opacity-40 active:scale-95"
              style={{
                background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                boxShadow: "0 4px 16px rgba(79,106,255,0.30)",
              }}
              onMouseEnter={e => { if (!enviandoLivre) (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 22px rgba(79,106,255,0.45)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 16px rgba(79,106,255,0.30)"; }}
            >
              {enviandoLivre ? "Enviando..." : "Enviar E-mail"}
            </button>
          </SectionCard>
        )}
      </div>
    </div>
  );
}
