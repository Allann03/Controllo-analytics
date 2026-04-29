"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { EmpresaProvider, useEmpresa } from "@/contexts/EmpresaContext";
import type { EmpresaSimples } from "@/contexts/EmpresaContext";
import { ToastProvider } from "@/contexts/ToastContext";
import { UserAvatar } from "@/components/UserAvatar";

interface Usuario {
  id: number;
  nome: string;
  is_master?: boolean;
  is_admin: boolean;
  is_gestor?: boolean;
  is_ceo?: boolean;
  is_aprovado: boolean;
  nome_exibicao?: string;
  cargo?: string;
  role?: "master" | "ceo" | "admin" | "gestor" | "analista";
}

// ── NavLink ──────────────────────────────────────────────────────────
function NavLink({
  href, label, icon, active, badge, collapsed,
}: {
  href: string; label: string; icon: React.ReactNode; active: boolean; badge?: number; collapsed?: boolean;
}) {
  const [hovered, setHovered] = useState(false);

  // Estado visual
  const textColor = active || hovered ? "var(--text-primary)" : "var(--text-secondary)";
  const bgColor = active
    ? "var(--accent-subtle)"
    : hovered ? "var(--bg-elevated)" : "transparent";

  return (
    <Link
      href={href}
      className={`group relative flex items-center w-full font-medium ${collapsed ? "justify-center" : ""}`}
      style={{
        padding: collapsed ? "10px 0" : "8px 12px",
        gap: collapsed ? 0 : 12,
        color: textColor,
        background: bgColor,
        borderRadius: "var(--radius-md)",
        // Border-left 2px do estado ativo via box-shadow inset (não afeta layout)
        boxShadow: active && !collapsed ? "inset 2px 0 0 var(--accent)" : "none",
        transition: "padding 0.25s cubic-bezier(0.4,0,0.2,1), gap 0.25s cubic-bezier(0.4,0,0.2,1), background 0.15s, color 0.15s, box-shadow 0.15s",
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Icon (Lucide ~18px) */}
      <span
        className="flex-shrink-0 flex items-center justify-center [&>svg]:w-[18px] [&>svg]:h-[18px]"
        style={{ width: 18, height: 18 }}
      >
        {icon}
      </span>

      {/* Label */}
      <span
        className="text-sm leading-normal whitespace-nowrap"
        style={{
          maxWidth: collapsed ? 0 : 200,
          opacity: collapsed ? 0 : 1,
          overflow: "hidden",
          transition: "max-width 0.25s cubic-bezier(0.4,0,0.2,1), opacity 0.15s",
          transitionDelay: collapsed ? "0s" : "0.05s",
        }}
      >
        {label}
      </span>

      {/* Badge numérico (modo expandido) */}
      {badge !== undefined && badge > 0 && (
        <span
          className="flex-shrink-0 min-w-[18px] h-[18px] flex items-center justify-center rounded-full text-white text-[10px] font-bold px-1"
          style={{
            background: "var(--danger)",
            maxWidth: collapsed ? 0 : 40,
            opacity: collapsed ? 0 : 1,
            overflow: "hidden",
            transition: "max-width 0.25s, opacity 0.15s",
          }}
        >
          {badge > 99 ? "99+" : badge}
        </span>
      )}

      {/* Dot indicador no modo colapsado */}
      {collapsed && badge !== undefined && badge > 0 && (
        <span
          className="absolute top-1 right-1 w-2 h-2 rounded-full"
          style={{
            background: "var(--danger)",
            boxShadow: "0 0 0 2px var(--bg-canvas)",
          }}
        />
      )}
    </Link>
  );
}

// ── SectionLabel ──────────────────────────────────────────────────────────────
function SectionLabel({ label, color, collapsed }: { label: string; color?: string; collapsed: boolean }) {
  if (collapsed) {
    return (
      <div className="my-2 flex items-center justify-center">
        <div className="w-5 h-px" style={{ background: "var(--border-subtle)" }} />
      </div>
    );
  }
  return (
    <div className="px-3 pt-6 pb-2">
      <span
        className="text-xs uppercase font-medium whitespace-nowrap"
        style={{
          color: color || "var(--text-tertiary)",
          letterSpacing: "var(--tracking-widest)",
        }}
      >
        {label}
      </span>
    </div>
  );
}

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace(/\/api\/?$/, "").replace(/\/$/, "");

// ── ThemeToggle ───────────────────────────────────────────────────────
function ThemeToggle() {
  const [tema, setTema] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const salvo = (localStorage.getItem("controllo_tema") as "dark" | "light") || "dark";
    setTema(salvo);
    const handler = (e: Event) => setTema((e as CustomEvent<"dark" | "light">).detail);
    window.addEventListener("controllo-tema-change", handler);
    return () => window.removeEventListener("controllo-tema-change", handler);
  }, []);

  function alternar(novoTema: "dark" | "light") {
    if (novoTema === tema) return;
    setTema(novoTema);
    localStorage.setItem("controllo_tema", novoTema);
    const html = document.documentElement;
    if (novoTema === "light") { html.classList.add("light"); html.classList.remove("dark"); }
    else { html.classList.remove("light"); html.classList.add("dark"); }
    window.dispatchEvent(new CustomEvent("controllo-tema-change", { detail: novoTema }));
  }

  const isLight = tema === "light";
  // Toggle icon-only 32x32 — clicar alterna o tema oposto.
  // Mostra Sun no dark (porque clica para virar light) e Moon no light.
  const proximoTema = isLight ? "dark" : "light";
  return (
    <button
      onClick={() => alternar(proximoTema)}
      className="w-8 h-8 flex items-center justify-center rounded-md transition-colors flex-shrink-0"
      style={{ color: "var(--text-tertiary)" }}
      onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text-primary)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-tertiary)"; }}
      title={isLight ? "Mudar para tema escuro" : "Mudar para tema claro"}
      aria-label={isLight ? "Mudar para tema escuro" : "Mudar para tema claro"}
    >
      {isLight ? (
        // Moon (Lucide)
        <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      ) : (
        // Sun (Lucide)
        <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="4" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      )}
    </button>
  );
}

// ── EmpresaSelectorWidget ─────────────────────────────────────────────
function EmpresaSelectorWidget({ token, topbar }: { token: string; topbar?: boolean }) {
  const { empresaSelecionada, setEmpresaSelecionada } = useEmpresa();
  const [aberto, setAberto] = useState(false);
  const [busca, setBusca] = useState("");
  const [empresas, setEmpresas] = useState<EmpresaSimples[]>([]);
  const [carregando, setCarregando] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const buscarEmpresas = useCallback(async (q: string) => {
    if (!token) return;
    setCarregando(true);
    try {
      const params = new URLSearchParams({ per_page: "500", busca: q });
      const res = await fetch(`${API_BASE}/api/carteira?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      setEmpresas(data.items ?? []);
    } catch { } finally { setCarregando(false); }
  }, [token]);

  const handleAbrir = () => { setAberto(true); setBusca(""); buscarEmpresas(""); };

  useEffect(() => {
    if (!aberto) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => buscarEmpresas(busca), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [busca, aberto, buscarEmpresas]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const nomeExibido = empresaSelecionada
    ? (empresaSelecionada.nome_fantasia || empresaSelecionada.nome)
    : "Selecionar empresa";

  const DropdownContent = () => (
    <div className="max-h-56 overflow-y-auto">
      {carregando ? (
        <p className="text-xs text-center py-4" style={{ color: "var(--text-tertiary)" }}>Carregando...</p>
      ) : empresas.length === 0 ? (
        <p className="text-xs text-center py-4" style={{ color: "var(--text-tertiary)" }}>Nenhuma empresa encontrada</p>
      ) : (
        <>
          {empresaSelecionada && (
            <button onClick={() => { setEmpresaSelecionada(null); setAberto(false); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs transition-colors"
              style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-secondary)" }}
              onMouseEnter={ev => { (ev.currentTarget as HTMLElement).style.background = "var(--bg-elevated)"; }}
              onMouseLeave={ev => { (ev.currentTarget as HTMLElement).style.background = "transparent"; }}>
              <span style={{ color: "var(--danger)" }}>✕</span> Limpar seleção
            </button>
          )}
          {empresas.map(e => (
            <button key={e.id} onClick={() => { setEmpresaSelecionada(e); setAberto(false); }}
              className="w-full flex items-center gap-2 px-3 py-2.5 text-left transition-colors"
              style={{ background: empresaSelecionada?.id === e.id ? "var(--accent-subtle)" : undefined }}
              onMouseEnter={ev => { if (empresaSelecionada?.id !== e.id) (ev.currentTarget as HTMLElement).style.background = "var(--bg-elevated)"; }}
              onMouseLeave={ev => { if (empresaSelecionada?.id !== e.id) (ev.currentTarget as HTMLElement).style.background = "transparent"; }}>
              <div
                className="w-6 h-6 flex items-center justify-center text-[10px] font-semibold flex-shrink-0"
                style={{
                  background: "var(--accent)",
                  color: "var(--text-inverse)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {(e.nome_fantasia || e.nome).slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>{e.nome_fantasia || e.nome}</p>
                {e.cnpj && <p className="text-[10px] font-mono" style={{ color: "var(--text-tertiary)" }}>{e.cnpj}</p>}
              </div>
              {empresaSelecionada?.id === e.id && (
                <svg className="w-3 h-3 flex-shrink-0" style={{ color: "var(--accent)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </button>
          ))}
        </>
      )}
    </div>
  );

  if (topbar) {
    return (
      <div ref={ref} className="relative flex-shrink-0">
        <button
          onClick={handleAbrir}
          className="flex items-center gap-2 px-3 py-2 border text-sm transition-colors"
          style={{
            background: "var(--bg-elevated)",
            borderColor: "var(--border-default)",
            color: empresaSelecionada ? "var(--text-primary)" : "var(--text-tertiary)",
            borderRadius: "var(--radius-md)",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--border-strong)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border-default)"; }}
        >
          {/* Building2 (Lucide) */}
          <svg className="w-4 h-4 flex-shrink-0" style={{ color: empresaSelecionada ? "var(--accent)" : "var(--text-tertiary)" }}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4" />
          </svg>
          <span className="font-medium max-w-[180px] truncate">{nomeExibido}</span>
          {/* Chevron down (Lucide) */}
          <svg className="w-3.5 h-3.5 flex-shrink-0" style={{ color: "var(--text-tertiary)" }}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
          </svg>
        </button>
        {aberto && (
          <div className="absolute top-full left-0 mt-1.5 z-50 w-80 overflow-hidden"
            style={{
              background: "var(--bg-overlay)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-lg)",
              boxShadow: "var(--shadow-lg)",
            }}>
            <div className="p-2.5" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
              <input autoFocus value={busca} onChange={e => setBusca(e.target.value)}
                placeholder="Buscar empresa..."
                className="w-full px-3 py-2 text-xs focus:outline-none border"
                style={{
                  background: "var(--bg-inset)",
                  borderColor: "var(--border-default)",
                  color: "var(--text-primary)",
                  borderRadius: "var(--radius-md)",
                }}
                onFocus={ev => { ev.currentTarget.style.borderColor = "var(--border-focus)"; }}
                onBlur={ev => { ev.currentTarget.style.borderColor = "var(--border-default)"; }} />
            </div>
            <DropdownContent />
          </div>
        )}
      </div>
    );
  }

  // Sidebar variant
  return (
    <div ref={ref} className="relative px-3 pb-3">
      <button
        onClick={handleAbrir}
        className="w-full flex items-center gap-2 px-3 py-2 border text-xs transition-colors"
        style={{
          background: "var(--bg-elevated)",
          borderColor: "var(--border-default)",
          color: empresaSelecionada ? "var(--text-primary)" : "var(--text-tertiary)",
          borderRadius: "var(--radius-md)",
        }}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--border-strong)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border-default)"; }}
      >
        <svg className="w-3.5 h-3.5 flex-shrink-0" style={{ color: empresaSelecionada ? "var(--accent)" : "var(--text-tertiary)" }}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4" />
        </svg>
        <div className="flex-1 text-left min-w-0 overflow-hidden">
          <p className="truncate font-medium leading-tight">{nomeExibido}</p>
          {empresaSelecionada?.cnpj && <p className="text-[10px] font-mono truncate" style={{ color: "var(--text-tertiary)" }}>{empresaSelecionada.cnpj}</p>}
        </div>
        <svg className="w-3 h-3 flex-shrink-0" style={{ color: "var(--text-tertiary)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
        </svg>
      </button>
      {aberto && (
        <div className="absolute left-3 right-3 top-full mt-1 z-50 overflow-hidden"
          style={{
            background: "var(--bg-overlay)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-md)",
          }}>
          <div className="p-2" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
            <input autoFocus value={busca} onChange={e => setBusca(e.target.value)}
              placeholder="Buscar empresa..."
              className="w-full px-3 py-1.5 text-xs focus:outline-none border"
              style={{
                background: "var(--bg-inset)",
                borderColor: "var(--border-default)",
                color: "var(--text-primary)",
                borderRadius: "var(--radius-md)",
              }}
              onFocus={ev => { ev.currentTarget.style.borderColor = "var(--border-focus)"; }}
              onBlur={ev => { ev.currentTarget.style.borderColor = "var(--border-default)"; }} />
          </div>
          <DropdownContent />
        </div>
      )}
    </div>
  );
}

// ── ClientWrapper ─────────────────────────────────────────────────────
export default function ClientWrapper({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [atrasados, setAtrasados] = useState(0);
  const [tarefasPendentes, setTarefasPendentes] = useState(0);
  const [perfilExtra, setPerfilExtra] = useState<{ nome_exibicao: string; cargo: string } | null>(null);
  const [sidebarAberta, setSidebarAberta] = useState(true);
  const [agora, setAgora] = useState(() => new Date());
  const pathname = usePathname();
  const router = useRouter();
  const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    .replace(/\/api\/?$/, "").replace(/\/$/, "");

  const rotasPublicas = ["/login"];
  const isRotaPublica = rotasPublicas.includes(pathname);

  // Carrega estado do sidebar
  useEffect(() => {
    const saved = localStorage.getItem("controllo_sidebar");
    if (saved !== null) setSidebarAberta(saved === "true");
  }, []);

  function toggleSidebar() {
    setSidebarAberta(prev => {
      const novo = !prev;
      localStorage.setItem("controllo_sidebar", String(novo));
      return novo;
    });
  }

  useEffect(() => {
    const t = localStorage.getItem("controllo_token");
    const u = localStorage.getItem("controllo_user");
    if (t && u) {
      setToken(t);
      try {
        const parsed = JSON.parse(u);
        setUsuario(parsed);
        if (parsed.nome_exibicao || parsed.cargo) {
          setPerfilExtra({ nome_exibicao: parsed.nome_exibicao ?? "", cargo: parsed.cargo ?? "" });
        }
      } catch {
        localStorage.removeItem("controllo_token");
        localStorage.removeItem("controllo_user");
      }
      fetch(`${API_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${t}` } })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setPerfilExtra({ nome_exibicao: d.nome_exibicao ?? "", cargo: d.cargo ?? "" }); })
        .catch(() => {});
    }
    setCarregando(false);
  }, [API_URL]);

  // Tarefas pendentes (localStorage)
  useEffect(() => {
    if (isRotaPublica) return;
    const sync = () => {
      try {
        const raw = localStorage.getItem("controllo_tarefas_v2");
        const lista: Array<{ concluida: boolean }> = raw ? JSON.parse(raw) : [];
        setTarefasPendentes(lista.filter(t => !t.concluida).length);
      } catch { }
    };
    sync();
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, [isRotaPublica]);

  // Lembretes atrasados
  useEffect(() => {
    if (!token || isRotaPublica) return;
    const fetchAtrasados = async () => {
      try {
        const res = await fetch(`${API_URL}/api/agenda/lembretes`, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) return;
        const data: Array<{ status: string; data_vencimento: string }> = await res.json();
        const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
        setAtrasados(data.filter(l => {
          if (l.status === "concluido") return false;
          const parts = l.data_vencimento.split("/");
          if (parts.length !== 3) return false;
          const d = new Date(Number(parts[2]), Number(parts[1]) - 1, Number(parts[0]));
          return d < hoje;
        }).length);
      } catch { }
    };
    fetchAtrasados();
  }, [token, isRotaPublica, API_URL]);

  useEffect(() => {
    if (!carregando && !token && !isRotaPublica) router.push("/login");
  }, [carregando, token, isRotaPublica, router]);

  // Saudação — atualiza a cada minuto para refletir mudança de período
  useEffect(() => {
    const timer = setInterval(() => setAgora(new Date()), 60_000);
    return () => clearInterval(timer);
  }, []);

  if (carregando) return null;
  if (isRotaPublica) return <>{children}</>;
  if (!token) return null;

  const iniciais = usuario?.nome
    ? usuario.nome.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase()
    : "US";

  const fazerLogout = () => {
    localStorage.removeItem("controllo_token");
    localStorage.removeItem("controllo_user");
    router.push("/login");
  };

  const hora = agora.getHours();
  const saudacao = hora < 12 ? "Bom dia" : hora < 18 ? "Boa tarde" : "Boa noite";
  const diasPT = ["Domingo","Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado"];
  const mesesPT = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
  const nomeExibicao = perfilExtra?.nome_exibicao || usuario?.nome || "Usuário";
  const cargo = perfilExtra?.cargo ?? "";
  // Nomes compostos: até 2 partes (ex: "Ana Paula Silva" → "Ana Paula")
  const partes = nomeExibicao.trim().split(/\s+/);
  const primeiroNome = partes.length <= 2 ? nomeExibicao.trim() : `${partes[0]} ${partes[1]}`;

  const collapsed = !sidebarAberta;
  const isGestorOrAdmin = !!(usuario?.is_admin || usuario?.is_gestor);

  return (
    <ToastProvider>
    <EmpresaProvider>
      <div className="flex flex-col h-screen overflow-hidden" style={{ background: "var(--bg-canvas)" }}>

        {/* ════════════════════ TOPBAR ════════════════════ */}
        <header className="h-14 flex-shrink-0 flex items-center px-4 gap-3 z-30"
          style={{
            background: "var(--bg-surface)",
            borderBottom: "1px solid var(--border-subtle)",
          }}>

          {/* Logo e botão collapse foram movidos para a sidebar (Fase 4 §5.2) */}

          {/* ── Avatar + Saudação ── */}
          <div className="hidden sm:flex items-center gap-3 flex-shrink-0">
            {/* Avatar 32px à ESQUERDA da saudação */}
            <div className="relative flex-shrink-0">
              <UserAvatar size={32} fallbackIniciais={iniciais} rounded="full" />
              {/* Status online dot */}
              <span
                className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full"
                style={{
                  background: "var(--success)",
                  boxShadow: "0 0 0 2px var(--bg-surface)",
                }}
              />
            </div>
            <div className="leading-tight">
              <p
                className="text-base font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                {saudacao}, {primeiroNome}
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-tertiary)" }}>
                {diasPT[agora.getDay()]}, {String(agora.getDate()).padStart(2, "0")} de {mesesPT[agora.getMonth()]}
              </p>
            </div>

            {/* ── Pill consolidado de role (Q5: §5.3 consolida CEO + Admin) ── */}
            <span
              className="hidden lg:flex text-xs font-semibold tracking-wide px-2.5 py-1 flex-shrink-0 border"
              style={{
                background: "var(--accent-subtle)",
                color: "var(--accent-text)",
                borderColor: "var(--accent-border)",
                borderRadius: "var(--radius-md)",
              }}
            >
              {usuario?.is_ceo ? "C.E.O." : usuario?.is_admin ? "Administrador" : usuario?.is_gestor ? "Gestor" : "Analista"}
            </span>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Empresa selector */}
          {token && <EmpresaSelectorWidget token={token} topbar />}

          {/* Bell icon — alertas da agenda */}
          <a
            href="/agenda"
            className="relative flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-md transition-colors"
            style={{
              color: atrasados > 0 ? "var(--warning)" : "var(--text-tertiary)",
            }}
            onMouseEnter={(e) => {
              if (atrasados === 0) e.currentTarget.style.color = "var(--text-secondary)";
            }}
            onMouseLeave={(e) => {
              if (atrasados === 0) e.currentTarget.style.color = "var(--text-tertiary)";
            }}
            title={atrasados > 0 ? `${atrasados} lembrete${atrasados !== 1 ? "s" : ""} atrasado${atrasados !== 1 ? "s" : ""}` : "Agenda"}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            {atrasados > 0 && (
              <span
                className="absolute -top-1 -right-1 min-w-[16px] h-4 flex items-center justify-center rounded-full text-white text-[9px] font-bold px-1 leading-none"
                style={{ background: "var(--danger)" }}
              >
                {atrasados > 99 ? "99+" : atrasados}
              </span>
            )}
          </a>

          {/* Theme toggle */}
          <ThemeToggle />
        </header>

        {/* ════════════════════ BODY ════════════════════ */}
        <div className="flex flex-1 overflow-hidden">

          {/* ════════════════════ SIDEBAR ════════════════════ */}
          <aside
            className="hidden md:flex flex-col flex-shrink-0 overflow-hidden z-20"
            style={{
              width: sidebarAberta ? 256 : 56,
              transition: "width 0.25s cubic-bezier(0.4,0,0.2,1)",
              background: "var(--sidebar-bg)",
              borderRight: "1px solid var(--sidebar-border)",
              boxShadow: "var(--sidebar-shadow)",
            }}
          >
            {/* ── Header da sidebar: wordmark + botão collapse ── */}
            {collapsed ? (
              <div
                className="flex items-center justify-center"
                style={{ height: 56, borderBottom: "1px solid var(--border-subtle)" }}
              >
                <button
                  onClick={toggleSidebar}
                  className="w-7 h-7 flex items-center justify-center rounded-md transition-colors"
                  style={{ color: "var(--text-tertiary)" }}
                  aria-label="Expandir menu"
                  title="Expandir menu"
                  onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text-secondary)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-tertiary)"; }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
              </div>
            ) : (
              <div
                className="flex items-center justify-between"
                style={{
                  height: 56,
                  padding: "0 16px",
                  borderBottom: "1px solid var(--border-subtle)",
                }}
              >
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span
                    className="font-bold tracking-tight"
                    style={{ color: "var(--text-primary)", fontSize: "var(--text-base)" }}
                  >
                    CONTROLLO
                  </span>
                  <span
                    className="text-xs uppercase font-medium"
                    style={{
                      color: "var(--text-tertiary)",
                      letterSpacing: "var(--tracking-widest)",
                      lineHeight: 1,
                    }}
                  >
                    BPO Analytics
                  </span>
                </div>
                <button
                  onClick={toggleSidebar}
                  className="w-7 h-7 flex items-center justify-center rounded-md transition-colors flex-shrink-0"
                  style={{ color: "var(--text-tertiary)" }}
                  aria-label="Recolher menu"
                  title="Recolher menu"
                  onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text-secondary)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-tertiary)"; }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7M18 19l-7-7 7-7" />
                  </svg>
                </button>
              </div>
            )}

            <nav className="flex-1 overflow-y-auto overflow-x-hidden py-2 space-y-0.5"
              style={{
                paddingLeft: collapsed ? 0 : 12,
                paddingRight: collapsed ? 0 : 12,
                transition: "padding 0.25s cubic-bezier(0.4,0,0.2,1)",
              }}>

              {/* ── Visão Geral ── */}
              <SectionLabel label="Visão Geral" collapsed={collapsed} />
              <NavLink href="/dashboard-executivo" label="Dashboard Executivo" collapsed={collapsed}
                active={pathname === "/dashboard-executivo" || pathname === "/dashboard-geral"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>}
              />

              {/* ── Extratos ── */}
              <SectionLabel label="Extratos Bancários" collapsed={collapsed} />
              <NavLink href="/" label="Leitor de PDF" collapsed={collapsed}
                active={pathname === "/"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
              />
              <NavLink href="/extrato-lote" label="Leitor em Lote" collapsed={collapsed}
                active={pathname === "/extrato-lote"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>}
              />
              <NavLink href="/importar" label="Importar Dados" collapsed={collapsed}
                active={pathname === "/importar"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>}
              />
              <NavLink href="/conciliacao" label="Conciliação Bancária" collapsed={collapsed}
                active={pathname === "/conciliacao"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>}
              />

              {/* ── Análise Financeira ── */}
              <SectionLabel label="Análise Financeira" collapsed={collapsed} />
              <NavLink href="/painel-financeiro" label="Painel Financeiro" collapsed={collapsed}
                active={pathname === "/painel-financeiro"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
              />
              <NavLink href="/dre" label="DRE" collapsed={collapsed}
                active={pathname === "/dre"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg>}
              />
              <NavLink href="/fluxo-caixa" label="Fluxo de Caixa" collapsed={collapsed}
                active={pathname === "/fluxo-caixa"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
              />
              <NavLink href="/balanco" label="Balanço Patrimonial" collapsed={collapsed}
                active={pathname === "/balanco"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" /></svg>}
              />
              <NavLink href="/insights" label="Insights Financeiros" collapsed={collapsed}
                active={pathname === "/insights"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
              />
              <NavLink href="/orcamento" label="Orçamento vs. Realizado" collapsed={collapsed}
                active={pathname === "/orcamento"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>}
              />
              <NavLink href="/sazonalidade" label="Sazonalidade" collapsed={collapsed}
                active={pathname === "/sazonalidade"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>}
              />
              <NavLink href="/comparativo" label="Comparativo" collapsed={collapsed}
                active={pathname === "/comparativo"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
              />

              {/* ── Tributário ── */}
              <SectionLabel label="Tributário" collapsed={collapsed} />
              <NavLink href="/painel-tributario" label="Análise Tributária" collapsed={collapsed}
                active={pathname === "/painel-tributario"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" /></svg>}
              />
              <NavLink href="/simulacao-tributaria" label="Simulação Tributária" collapsed={collapsed}
                active={pathname === "/simulacao-tributaria"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>}
              />

              {/* ── Carteiras & Operacional ── */}
              <SectionLabel label="Carteiras" collapsed={collapsed} />
              <NavLink href="/admin/carteiras" label="Carteira Geral" collapsed={collapsed}
                active={pathname === "/admin/carteiras"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>}
              />
              <NavLink href="/carteiras" label="Minha Carteira" collapsed={collapsed}
                active={pathname === "/carteiras"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>}
              />
              <NavLink href="/plano-contas" label="Plano de Contas" collapsed={collapsed}
                active={pathname === "/plano-contas"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" /></svg>}
              />
              <NavLink href="/classificacao-contabil" label="Classificação Contábil" collapsed={collapsed}
                active={pathname === "/classificacao-contabil"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>}
              />
              <NavLink href="/relatorios" label="Relatórios" collapsed={collapsed}
                active={pathname === "/relatorios"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
              />

              {/* ── Produtividade ── */}
              <SectionLabel label="Produtividade" collapsed={collapsed} />
              <NavLink href="/agenda" label="Agenda" collapsed={collapsed}
                active={pathname === "/agenda"}
                badge={atrasados}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>}
              />
              <NavLink href="/tarefas" label="Tarefas do Dia" collapsed={collapsed}
                active={pathname === "/tarefas"}
                badge={tarefasPendentes}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              />
              <NavLink href="/alertas" label="Alertas por E-mail" collapsed={collapsed}
                active={pathname === "/alertas"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>}
              />
              <NavLink href="/configuracoes" label="Configurações" collapsed={collapsed}
                active={pathname === "/configuracoes"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>}
              />
              <NavLink href="/historico-importacoes" label="Histórico de Importações" collapsed={collapsed}
                active={pathname === "/historico-importacoes"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              />
              <NavLink href="/onboarding" label="Guia de Início" collapsed={collapsed}
                active={pathname === "/onboarding"}
                icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" /></svg>}
              />

              {/* ── Equipe (gestor + admin) ── */}
              {isGestorOrAdmin && (
                <>
                  <SectionLabel label="Equipe" collapsed={collapsed} />
                  <NavLink href="/gestor/equipe" label="Gestão de Equipe" collapsed={collapsed}
                    active={pathname === "/gestor/equipe"}
                    icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>}
                  />
                </>
              )}

              {/* ── Central de Controle (master only) ── */}
              {usuario?.is_master && (
                <>
                  <SectionLabel label="Controle" collapsed={collapsed} />
                  <NavLink href="/master" label="Central de Controle" collapsed={collapsed}
                    active={pathname === "/master"}
                    icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>}
                  />
                </>
              )}

              {/* ── Administração (admin only) ─�� */}
              {usuario?.is_admin && (
                <>
                  <SectionLabel label="Administração" collapsed={collapsed} />
                  <NavLink href="/admin" label="Usuários" collapsed={collapsed}
                    active={pathname === "/admin"}
                    icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>}
                  />
                  <NavLink href="/admin/empresas" label="Empresas" collapsed={collapsed}
                    active={pathname === "/admin/empresas"}
                    icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>}
                  />
                  <NavLink href="/admin/visao-geral" label="Visão geral da equipe" collapsed={collapsed}
                    active={pathname === "/admin/visao-geral"}
                    icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>}
                  />
                  <NavLink href="/auditoria" label="Log de Auditoria" collapsed={collapsed}
                    active={pathname === "/auditoria"}
                    icon={<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>}
                  />
                </>
              )}
            </nav>

            {/* ── Profile no rodapé ── */}
            <div
              className={collapsed ? "p-2" : "p-3"}
              style={{ borderTop: "1px solid var(--border-subtle)" }}
            >
              {collapsed ? (
                <div className="flex flex-col items-center gap-2">
                  <div title={usuario?.nome}>
                    <UserAvatar size={32} fallbackIniciais={iniciais} rounded="full" />
                  </div>
                  <button
                    onClick={fazerLogout}
                    title="Sair"
                    className="w-8 h-8 flex items-center justify-center rounded-md transition-colors"
                    style={{ color: "var(--text-tertiary)" }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = "var(--danger)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-tertiary)"; }}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                  </button>
                </div>
              ) : (
                <div
                  className="flex items-center gap-3 px-3 py-2.5 transition-colors border"
                  style={{
                    background: "var(--bg-elevated)",
                    borderColor: "var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <UserAvatar size={32} fallbackIniciais={iniciais} rounded="full" />
                  <div className="overflow-hidden flex-1 min-w-0">
                    <p
                      className="font-medium text-sm truncate leading-tight"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {usuario?.nome}
                    </p>
                    <p
                      className="text-xs mt-0.5 truncate"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      {usuario?.is_ceo ? "C.E.O." : usuario?.is_admin ? "Administrador" : usuario?.is_gestor ? "Gestor" : "Analista"}
                    </p>
                  </div>
                  <button
                    onClick={fazerLogout}
                    title="Sair"
                    className="p-1.5 rounded-md transition-colors flex-shrink-0"
                    style={{ color: "var(--text-tertiary)" }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = "var(--danger)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-tertiary)"; }}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          </aside>

          {/* ════════════════════ MAIN ════════════════════ */}
          <main className="flex-1 overflow-y-auto relative min-w-0" style={{ background: "var(--bg-canvas)" }}>
            <div className="relative min-h-full">
              {children}
            </div>
          </main>
        </div>
      </div>
    </EmpresaProvider>
    </ToastProvider>
  );
}
