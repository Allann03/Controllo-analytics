"use client";

import { useEffect, useState } from "react";
import { validarSenha, senhaValida, REGRAS_LABELS, type RegrasSenha } from "@/lib/validacao-senha";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

function tk() { return typeof window !== "undefined" ? (localStorage.getItem("controllo_token") ?? "") : ""; }

interface Perfil {
  nome: string;
  nome_exibicao: string;
  cargo: string;
  is_admin: boolean;
}

// ── Hook de tema ────────────────────────────────────────────────────
function useTheme() {
  const [isLight, setIsLight] = useState(false);
  useEffect(() => {
    const check = () => setIsLight(document.documentElement.classList.contains("light"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);
  return isLight;
}

// ── Tipos de navegação lateral ──────────────────────────────────────
type Secao = "perfil" | "avatar" | "seguranca" | "sobre";

const SECOES: { key: Secao; label: string; icon: React.ReactNode }[] = [
  {
    key: "perfil",
    label: "Meu Perfil",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
  },
  {
    key: "avatar",
    label: "Avatar",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    key: "seguranca",
    label: "Segurança",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
  },
  {
    key: "sobre",
    label: "Sobre a Plataforma",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

// ── Ícones flat para avatar ───────────────────────────────────────────
interface FlatIconDef {
  id: string;
  label: string;
  svgPath: string;
  multiPath?: boolean;
  paths?: string[];
}

const FLAT_ICONS: FlatIconDef[] = [
  { id: "m1", label: "Analista", svgPath: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" },
  { id: "m2", label: "Gestor", multiPath: true, paths: ["M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"], svgPath: "" },
  { id: "m3", label: "Executivo", svgPath: "M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
  { id: "m4", label: "Diretor", svgPath: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" },
  { id: "m5", label: "Consultor", svgPath: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { id: "m6", label: "Sócio", svgPath: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" },
  { id: "f1", label: "Analista", svgPath: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" },
  { id: "f2", label: "Gestora", svgPath: "M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" },
  { id: "f3", label: "Executiva", svgPath: "M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
  { id: "f4", label: "Diretora", svgPath: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" },
  { id: "f5", label: "Consultora", svgPath: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { id: "f6", label: "Sócia", svgPath: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" },
];

function FlatAvatar({ iconId, size = 48 }: { iconId: string; size?: number }) {
  const icon = FLAT_ICONS.find(i => i.id === iconId);
  const pathData = icon?.multiPath ? icon.paths?.[0] : icon?.svgPath;
  const iconSize = Math.max(16, Math.round(size * 0.55));
  return (
    <div
      className="flex items-center justify-center rounded-xl"
      style={{
        width: size, height: size,
        background: "linear-gradient(135deg, rgba(30,73,118,0.15), rgba(59,110,165,0.08))",
        border: "1px solid rgba(30,73,118,0.2)",
      }}
    >
      <svg
        style={{ width: iconSize, height: iconSize }}
        fill="none"
        viewBox="0 0 24 24"
        stroke="#3b6ea5"
        strokeWidth={1.8}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={pathData ?? "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"} />
      </svg>
    </div>
  );
}

// Lê/grava o avatar no localStorage
function getAvatarId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("controllo_avatar") ?? "";
}
function saveAvatarId(id: string) {
  if (typeof window !== "undefined") localStorage.setItem("controllo_avatar", id);
}

function InputField({ label, value, onChange, type = "text", placeholder, hint, disabled }: {
  label: string; value: string; onChange?: (v: string) => void;
  type?: string; placeholder?: string; hint?: string; disabled?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs font-semibold mb-1.5" style={{ color: "var(--text-secondary)" }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={e => onChange?.(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete={type === "password" ? "new-password" : "off"}
        className="w-full rounded-xl px-4 py-2.5 text-sm transition focus:outline-none focus:ring-2 focus:ring-navy-500/20"
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          color: disabled ? "var(--text-muted)" : "var(--text-primary)",
        }}
      />
      {hint && <p className="text-[11px] mt-1" style={{ color: "var(--text-muted)" }}>{hint}</p>}
    </div>
  );
}

function Feedback({ msg }: { msg: { texto: string; tipo: "ok" | "erro" } }) {
  return (
    <div className={`mt-4 px-4 py-2.5 rounded-xl text-sm font-medium border ${
      msg.tipo === "ok"
        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-500"
        : "bg-red-500/10 border-red-500/30 text-red-500"
    }`}>{msg.texto}</div>
  );
}

function SaveButton({ onClick, disabled, label, loading }: {
  onClick: () => void; disabled: boolean; label: string; loading: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="mt-5 w-full text-sm font-bold py-2.5 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      style={{ background: "#102a43", color: "white" }}
    >
      {disabled ? loading : label}
    </button>
  );
}

export default function ConfiguracoesPage() {
  const isLight = useTheme();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [secao, setSecao] = useState<Secao>("perfil");

  // Avatar
  const [avatarId, setAvatarId] = useState<string>("");
  const [avatarPendente, setAvatarPendente] = useState<string>("");
  const [salvandoAvatar, setSalvandoAvatar] = useState(false);
  const [msgAvatar, setMsgAvatar] = useState<{ texto: string; tipo: "ok" | "erro" } | null>(null);

  useEffect(() => {
    const saved = getAvatarId();
    setAvatarId(saved);
    setAvatarPendente(saved);
  }, []);

  // Perfil
  const [nomeExibicao, setNomeExibicao] = useState("");
  const [cargo, setCargo] = useState("");
  const [salvandoPerfil, setSalvandoPerfil] = useState(false);
  const [msgPerfil, setMsgPerfil] = useState<{ texto: string; tipo: "ok" | "erro" } | null>(null);

  // Senha
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [salvandoSenha, setSalvandoSenha] = useState(false);
  const [msgSenha, setMsgSenha] = useState<{ texto: string; tipo: "ok" | "erro" } | null>(null);

  useEffect(() => {
    fetch(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${tk()}` } })
      .then(r => r.json())
      .then((d: Perfil) => {
        setPerfil(d);
        setNomeExibicao(d.nome_exibicao || "");
        setCargo(d.cargo || "");
      })
      .catch(() => {});
  }, []);

  async function salvarPerfil() {
    setSalvandoPerfil(true);
    setMsgPerfil(null);
    try {
      const res = await fetch(`${API}/api/auth/perfil`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tk()}` },
        body: JSON.stringify({ nome_exibicao: nomeExibicao, cargo }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "Erro ao salvar.");
      setMsgPerfil({ texto: "Perfil atualizado com sucesso.", tipo: "ok" });
      try {
        const u = JSON.parse(localStorage.getItem("controllo_user") ?? "{}");
        localStorage.setItem("controllo_user", JSON.stringify({ ...u, nome_exibicao: d.nome_exibicao, cargo: d.cargo }));
      } catch { /* ignore */ }
    } catch (e) {
      setMsgPerfil({ texto: (e as Error).message, tipo: "erro" });
    } finally {
      setSalvandoPerfil(false);
      setTimeout(() => setMsgPerfil(null), 4000);
    }
  }

  async function salvarSenha() {
    if (!senhaAtual || !novaSenha || !confirmarSenha) {
      setMsgSenha({ texto: "Preencha todos os campos de senha.", tipo: "erro" });
      setTimeout(() => setMsgSenha(null), 4000);
      return;
    }
    if (novaSenha !== confirmarSenha) {
      setMsgSenha({ texto: "Nova senha e confirmação não coincidem.", tipo: "erro" });
      setTimeout(() => setMsgSenha(null), 4000);
      return;
    }
    if (!senhaValida(validarSenha(novaSenha))) {
      setMsgSenha({ texto: "A nova senha não atende aos requisitos de segurança.", tipo: "erro" });
      setTimeout(() => setMsgSenha(null), 4000);
      return;
    }
    setSalvandoSenha(true);
    setMsgSenha(null);
    try {
      const res = await fetch(`${API}/api/auth/senha`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tk()}` },
        body: JSON.stringify({ senha_atual: senhaAtual, nova_senha: novaSenha }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "Erro ao alterar senha.");
      setMsgSenha({ texto: "Senha alterada com sucesso.", tipo: "ok" });
      setSenhaAtual(""); setNovaSenha(""); setConfirmarSenha("");
    } catch (e) {
      setMsgSenha({ texto: (e as Error).message, tipo: "erro" });
    } finally {
      setSalvandoSenha(false);
      setTimeout(() => setMsgSenha(null), 4000);
    }
  }

  async function salvarAvatar() {
    setSalvandoAvatar(true);
    setMsgAvatar(null);
    try {
      saveAvatarId(avatarPendente);
      setAvatarId(avatarPendente);
      // Tenta persistir no backend (ignora erro se endpoint não suportar)
      await fetch(`${API}/api/auth/perfil`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tk()}` },
        body: JSON.stringify({ avatar_id: avatarPendente }),
      }).catch(() => {});
      setMsgAvatar({ texto: "Avatar salvo com sucesso.", tipo: "ok" });
      setTimeout(() => setMsgAvatar(null), 3000);
    } catch {
      setMsgAvatar({ texto: "Erro ao salvar avatar.", tipo: "erro" });
      setTimeout(() => setMsgAvatar(null), 3000);
    } finally {
      setSalvandoAvatar(false);
    }
  }

  const saudacao = nomeExibicao || perfil?.nome || "usuário";
  const iniciais = saudacao.slice(0, 2).toUpperCase();

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* ── HEADER ─────────────────────────────────────────────── */}
      <header
        className="pt-8 pb-6 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="max-w-5xl mx-auto px-6">
          <div className="flex items-center gap-4">
            {/* Avatar */}
            <div
              className="w-14 h-14 rounded-2xl overflow-hidden flex-shrink-0 shadow-lg ring-2 ring-[#102a43]/20 cursor-pointer hover:ring-[#102a43]/40 transition-all"
              onClick={() => setSecao("avatar")}
              title="Clique para alterar o avatar"
            >
              {avatarId ? (
                <FlatAvatar iconId={avatarId} />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-slate-100 text-slate-500">
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest mb-0.5" style={{ color: "#102a43" }}>
                Configurações
              </p>
              <h1 className="text-2xl font-extrabold tracking-tight" style={{ color: "var(--text-primary)" }}>
                Olá, {saudacao}
              </h1>
              <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
                {perfil?.is_admin ? "Administrador" : "Analista"}
                {cargo && <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-semibold bg-navy-100 text-navy-800 border border-navy-200 dark:bg-navy-900/40 dark:text-navy-300 dark:border-navy-800/60">{cargo}</span>}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* ── BODY: sidebar + conteúdo ────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 py-8 flex gap-8 items-start">

        {/* Sidebar de navegação */}
        <nav className="w-52 flex-shrink-0 self-start">
          <div
            className="rounded-2xl p-2 sticky top-6"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            {SECOES.map(s => (
              <button
                key={s.key}
                onClick={() => setSecao(s.key)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all mb-0.5 last:mb-0`}
                style={{
                  background: secao === s.key ? (isLight ? "rgba(16,42,67,0.08)" : "rgba(30,58,95,0.20)") : "transparent",
                  color: secao === s.key ? (isLight ? "#102a43" : "#9fb3c8") : "var(--text-secondary)",
                }}
              >
                <span className="flex-shrink-0">{s.icon}</span>
                {s.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Conteúdo central */}
        <div className="flex-1 min-w-0">

          {/* ── SEÇÃO: Meu Perfil ─────────────────────────────── */}
          {secao === "perfil" && (
            <div
              className="rounded-2xl p-6"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <h2 className="text-base font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                Informações do Perfil
              </h2>
              <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
                Seu nome de exibição aparece nos cumprimentos e relatórios gerados pela plataforma.
              </p>

              {/* Card de identidade */}
              {perfil && (
                <div
                  className="flex items-center gap-4 p-4 rounded-xl mb-6"
                  style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
                >
                  <div className="w-12 h-12 rounded-xl overflow-hidden flex-shrink-0">
                    {avatarId ? (
                      <FlatAvatar iconId={avatarId} />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-slate-100 text-slate-500">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="font-bold text-sm" style={{ color: "var(--text-primary)" }}>{perfil.nome}</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      Login · {perfil.is_admin ? "Administrador" : "Analista"}
                    </p>
                  </div>
                  <div
                    className="ml-auto px-3 py-1 rounded-full text-xs font-semibold border"
                    style={{
                      background: isLight ? "rgba(16,42,67,0.06)" : "rgba(30,58,95,0.18)",
                      borderColor: "rgba(16,42,67,0.18)",
                      color: isLight ? "#102a43" : "#93b4d4",
                    }}
                  >
                    {perfil.is_admin ? "Admin" : "Analista"}
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <InputField
                  label="Nome de exibição"
                  value={nomeExibicao}
                  onChange={setNomeExibicao}
                  placeholder="Como quer ser chamado(a)"
                  hint="Aparece nos cumprimentos e cabeçalhos de relatórios"
                />
                <InputField
                  label="Cargo / Função"
                  value={cargo}
                  onChange={setCargo}
                  placeholder="Ex: Analista Contábil, Sócio, Gerente..."
                  hint="Opcional — aparece ao lado do seu nome no sistema"
                />
                <InputField
                  label="Login (não editável)"
                  value={perfil?.nome ?? ""}
                  disabled
                  hint="Para alterar o login entre em contato com o administrador"
                />
              </div>

              {msgPerfil && <Feedback msg={msgPerfil} />}
              <SaveButton
                onClick={salvarPerfil}
                disabled={salvandoPerfil}
                label="Salvar Alterações"
                loading="Salvando..."
              />
            </div>
          )}

          {/* ── SEÇÃO: Avatar ────────────────────────────────── */}
          {secao === "avatar" && (
            <div
              className="rounded-2xl p-6"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <h2 className="text-base font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                Avatar do Perfil
              </h2>
              <p className="text-sm mb-5" style={{ color: "var(--text-secondary)" }}>
                Escolha um ícone para representar você na plataforma.
              </p>

              {/* Preview do avatar atual */}
              {avatarPendente && (
                <div className="flex items-center gap-4 mb-5 p-4 rounded-xl"
                  style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <div className="w-14 h-14 rounded-2xl overflow-hidden flex-shrink-0 ring-2 ring-[#1E4976]/30 bg-slate-100 flex items-center justify-center">
                    <FlatAvatar iconId={avatarPendente} />
                  </div>
                  <div>
                    <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                      {FLAT_ICONS.find(i => i.id === avatarPendente)?.label ?? "Ícone selecionado"}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                      {avatarPendente === avatarId ? "Avatar atual" : "Alteração pendente — clique em Salvar"}
                    </p>
                  </div>
                </div>
              )}

              {/* Grid de ícones flat */}
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-3 mb-5">
                {FLAT_ICONS.map(icon => {
                  const selected = avatarPendente === icon.id;
                  const pathData = icon.multiPath ? icon.paths?.[0] : icon.svgPath;
                  return (
                    <button
                      key={icon.id}
                      onClick={() => setAvatarPendente(icon.id)}
                      title={icon.label}
                      className={`relative flex flex-col items-center gap-1.5 p-3 rounded-xl transition-all ${
                        selected ? "ring-2 ring-[#1E4976] ring-offset-2" : "hover:bg-slate-50"
                      }`}
                      style={{ border: `1px solid ${selected ? "#1E4976" : "var(--border)"}` }}
                    >
                      <div className="w-10 h-10 rounded-full flex items-center justify-center bg-slate-100 text-slate-500">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                          <path strokeLinecap="round" strokeLinejoin="round" d={pathData ?? "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"} />
                        </svg>
                      </div>
                      <span className="text-[10px] font-medium text-center leading-tight" style={{ color: "var(--text-muted)" }}>
                        {icon.label}
                      </span>
                      {selected && (
                        <div className="absolute top-1 right-1 w-4 h-4 rounded-full bg-[#1E4976] flex items-center justify-center">
                          <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>

              {msgAvatar && <Feedback msg={msgAvatar} />}
              <button
                onClick={salvarAvatar}
                disabled={salvandoAvatar || avatarPendente === avatarId}
                className="mt-4 w-full text-sm font-bold py-2.5 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                data-notheme
                style={{ background: "#102a43", color: "white" }}
              >
                {salvandoAvatar ? "Salvando..." : avatarPendente === avatarId ? "Avatar salvo" : "Salvar Avatar"}
              </button>
            </div>
          )}

          {/* ── SEÇÃO: Segurança ──────────────────────────────── */}
          {secao === "seguranca" && (
            <div
              className="rounded-2xl p-6"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <h2 className="text-base font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                Segurança da Conta
              </h2>
              <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
                Altere sua senha periodicamente para manter a conta segura.
              </p>

              {/* Indicador de força da senha */}
              <div
                className="flex items-center gap-3 px-4 py-3 rounded-xl mb-6"
                style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: "rgba(16,42,67,0.10)" }}>
                  <svg className="w-4 h-4" style={{ color: "#102a43" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Senha protegida</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>Use no mínimo 8 caracteres com maiúsculas, minúsculas, dígitos e especiais</p>
                </div>
              </div>

              <div className="space-y-4">
                <InputField
                  label="Senha atual"
                  value={senhaAtual}
                  onChange={setSenhaAtual}
                  type="password"
                  placeholder="••••••••"
                />
                <InputField
                  label="Nova senha"
                  value={novaSenha}
                  onChange={setNovaSenha}
                  type="password"
                  placeholder="Mínimo 8 caracteres"
                />
                {novaSenha.length > 0 && (() => {
                  const regras = validarSenha(novaSenha);
                  return (
                    <ul className="space-y-1 text-xs -mt-2" aria-live="polite" aria-label="Requisitos de senha">
                      {(Object.keys(REGRAS_LABELS) as (keyof RegrasSenha)[]).map((key) => (
                        <li key={key} className={`flex items-center gap-1.5 ${regras[key] ? "text-emerald-600" : "text-slate-400"}`}>
                          <span className="flex-shrink-0">{regras[key] ? "\u2713" : "\u2717"}</span>
                          {REGRAS_LABELS[key]}
                        </li>
                      ))}
                    </ul>
                  );
                })()}
                <InputField
                  label="Confirmar nova senha"
                  value={confirmarSenha}
                  onChange={setConfirmarSenha}
                  type="password"
                  placeholder="Repita a nova senha"
                />
              </div>

              {msgSenha && <Feedback msg={msgSenha} />}
              <SaveButton
                onClick={salvarSenha}
                disabled={salvandoSenha || (novaSenha.length > 0 && !senhaValida(validarSenha(novaSenha)))}
                label="Alterar Senha"
                loading="Alterando..."
              />
            </div>
          )}

          {/* ── SEÇÃO: Sobre ──────────────────────────────────── */}
          {secao === "sobre" && (
            <div
              className="rounded-2xl p-6"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <h2 className="text-base font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                Sobre a Plataforma
              </h2>
              <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
                Informações técnicas e de licença da plataforma Controllo Analytics.
              </p>

              <div
                className="rounded-xl overflow-hidden"
                style={{ border: "1px solid var(--border)" }}
              >
                {[
                  { label: "Plataforma",  value: "Controllo BPO Analytics" },
                  { label: "Versão",      value: "15.1.7" },
                  { label: "Empresa",     value: "Controllo BPO — Assessoria Empresarial e Contábil" },
                  { label: "Ambiente",    value: "Produção" },
                  { label: "Suporte",     value: "suporte@controllobpo.com.br" },
                ].map(({ label, value }, idx, arr) => (
                  <div
                    key={label}
                    className="flex justify-between items-center px-5 py-3.5 text-sm"
                    style={{
                      borderBottom: idx < arr.length - 1 ? `1px solid var(--border)` : undefined,
                      background: idx % 2 === 0 ? "var(--bg-secondary)" : "var(--bg-card)",
                    }}
                  >
                    <span style={{ color: "var(--text-secondary)" }}>{label}</span>
                    <span className="font-semibold text-right max-w-xs" style={{ color: "var(--text-primary)" }}>{value}</span>
                  </div>
                ))}
              </div>

              {/* Badge de versão */}
              <div className="mt-5 flex items-center justify-center">
                <div
                  className="px-4 py-2 rounded-xl text-xs font-semibold"
                  style={{
                    background: isLight ? "rgba(16,42,67,0.05)" : "rgba(30,58,95,0.15)",
                    border: "1px solid rgba(16,42,67,0.15)",
                    color: isLight ? "#102a43" : "#93b4d4",
                  }}
                >
                  Controllo BPO Analytics v15.1.7 — Todos os direitos reservados
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
