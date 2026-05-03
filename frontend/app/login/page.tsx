"use client";
import { useState, useEffect } from "react";
import GlobeBackground from "@/components/GlobeBackground";
import { validarSenha, senhaValida, REGRAS_LABELS, type RegrasSenha } from "@/lib/validacao-senha";

/* ── Globe SVG (Controllo BPO brand mark) ─────────────────────────── */
function GlobeLogo({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9.5" strokeWidth="1.3"/>
      <path d="M12 2.5C9 5.8 7.8 9 7.8 12s1.2 6.2 4.2 9.5" strokeWidth="1"/>
      <path d="M12 2.5c3 3.3 4.2 6.5 4.2 9.5s-1.2 6.2-4.2 9.5" strokeWidth="1"/>
      <line x1="2.5" y1="12" x2="21.5" y2="12" strokeWidth="1"/>
      <path d="M5.2 7.5Q12 6.3 18.8 7.5" strokeWidth="0.75"/>
      <path d="M5.2 16.5Q12 17.7 18.8 16.5" strokeWidth="0.75"/>
    </svg>
  );
}

export default function LoginPage() {
  const [modoLogin, setModoLogin] = useState(true);
  const [escritorio, setEscritorio] = useState("");
  const [nome, setNome] = useState("");
  const [senha, setSenha] = useState("");
  const [senhaVisivel, setSenhaVisivel] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [escritorioValido, setEscritorioValido] = useState<{existe: boolean; nome?: string} | null>(null);
  const [validandoSlug, setValidandoSlug] = useState(false);

  const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

  useEffect(() => {
    if (modoLogin || !escritorio.trim()) {
      setEscritorioValido(null);
      return;
    }
    setValidandoSlug(true);
    const timer = setTimeout(async () => {
      try {
        const r = await fetch(`${API}/api/auth/verificar-escritorio?slug=${encodeURIComponent(escritorio.trim().toLowerCase())}`);
        if (r.ok) {
          setEscritorioValido(await r.json());
        }
      } catch { setEscritorioValido(null); }
      setValidandoSlug(false);
    }, 500);
    return () => clearTimeout(timer);
  }, [escritorio, modoLogin, API]);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setErro("");
    setCarregando(true);

    try {
      const params = new URLSearchParams();
      params.append("username", nome.trim().toLowerCase());
      params.append("password", senha);

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 20000);

      let res: Response;
      try {
        res = await fetch(`${API}/api/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: params.toString(),
          signal: controller.signal,
        });
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          throw new Error("O servidor demorou muito para responder. Aguarde alguns segundos e tente novamente.");
        }
        throw err;
      } finally {
        clearTimeout(timeout);
      }

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Credenciais inválidas");
      }

      const data = await res.json();
      localStorage.setItem("controllo_token", data.access_token);
      localStorage.setItem("controllo_user", JSON.stringify(data.usuario));
      if (data.escritorio) {
        localStorage.setItem("controllo_escritorio", JSON.stringify(data.escritorio));
      }
      window.location.href = "/";
    } catch (err: unknown) {
      setErro(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setCarregando(false);
    }
  }

  async function handleSolicitarAcesso(e: React.FormEvent) {
    e.preventDefault();
    setErro("");
    setSucesso("");
    setCarregando(true);

    try {
      const res = await fetch(`${API}/api/auth/solicitar-acesso`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: nome.trim().toLowerCase(), senha, escritorio: escritorio.trim().toLowerCase() || undefined }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Erro ao solicitar acesso");
      }

      setSucesso("Solicitação enviada! Aguarde aprovação do administrador.");
      setNome("");
      setSenha("");
    } catch (err: unknown) {
      setErro(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="min-h-screen flex">

      {/* ── Painel de Branding (esquerda 60%) ─────────────────────────── */}
      <div className="hidden lg:flex lg:w-[60%] relative overflow-hidden flex-col justify-between p-12"
        data-notheme="1"
        style={{ background: "#12103a" }}>

        <GlobeBackground light={false} />

        {/* ── Conteúdo do branding ── */}
        <div className="relative z-10">
          {/* Logo Controllo BPO com globo */}
          <div className="flex items-center gap-4">
            <GlobeLogo className="w-11 h-11 text-white opacity-90" />
            <div>
              <div className="text-white font-black text-lg tracking-[0.12em] uppercase leading-none">
                CONTROLLO BPO
              </div>
              <div className="text-[11px] font-light tracking-[0.25em] uppercase mt-0.5"
                style={{ color: "#8B9FFF" }}>
                Analytics
              </div>
            </div>
          </div>
        </div>

        {/* ── Headline e features ── */}
        <div className="relative z-10 flex-1 flex flex-col justify-center py-6">
          <p className="text-[11px] font-semibold tracking-[0.2em] uppercase mb-3"
            style={{ color: "#8B9FFF" }}>
            Inteligência Financeira em Tempo Real
          </p>
          <h2 className="text-[2.05rem] font-black text-white leading-[1.18] mb-1 tracking-tight">
            Clareza total sobre
          </h2>
          <h2 className="text-[2.05rem] font-black leading-[1.18] mb-5 tracking-tight">
            <span style={{
              background: "linear-gradient(135deg, #3b6ea5, #102a43, #60A5FA)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}>
              cada centavo do negócio.
            </span>
          </h2>
          <p className="text-slate-400 text-[0.9rem] max-w-sm leading-relaxed">
            Da DRE ao fluxo de caixa — tudo consolidado, analisado e pronto para a decisão
            que não pode esperar até o fechamento do mês.
          </p>

          {/* Features */}
          <div className="mt-10 space-y-4">
            {[
              {
                label: "Visão 360° da saúde financeira com alertas automáticos",
                svg: (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                ),
              },
              {
                label: "Importação de extratos e planilhas com mapeamento inteligente",
                svg: (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                ),
              },
              {
                label: "Simulação da Reforma Tributária com cenários comparativos",
                svg: (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                      d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" />
                  </svg>
                ),
              },
              {
                label: "Insights e recomendações gerados pelo motor de análise",
                svg: (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ),
              },
            ].map(f => (
              <div key={f.label} className="flex items-center gap-3.5">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-slate-400"
                  style={{ background: "rgba(79,106,255,0.08)", border: "1px solid rgba(79,106,255,0.15)" }}>
                  {f.svg}
                </div>
                <span className="text-slate-400 text-sm leading-snug">{f.label}</span>
              </div>
            ))}
          </div>

          {/* Quote card */}
          <div className="mt-10 rounded-2xl p-6 backdrop-blur-sm relative overflow-hidden"
            style={{ border: "1px solid rgba(79,106,255,0.1)", background: "rgba(79,106,255,0.04)" }}>
            {/* Aspas decorativas */}
            <svg className="absolute top-3 right-4 w-16 h-16" fill="currentColor"
              style={{ color: "rgba(79,106,255,0.08)" }} viewBox="0 0 32 32" aria-hidden="true">
              <path d="M10 8C5.6 8 2 11.6 2 16c0 3.7 2.4 6.8 5.8 7.8L6 28h4l2-4.5C15.1 22.8 18 19.7 18 16V8h-8zm16 0c-4.4 0-8 3.6-8 8 0 3.7 2.4 6.8 5.8 7.8L22 28h4l2-4.5C31.1 22.8 34 19.7 34 16V8h-8z" />
            </svg>
            <p className="text-slate-300 text-base font-medium leading-relaxed relative z-10 text-center">
              Quem entende seus números antes do mercado
              já chegou um passo à frente da concorrência.
            </p>
            <div className="mt-5 flex items-center gap-3">
              <div className="h-px flex-1" style={{ background: "rgba(255,255,255,0.05)" }} />
              <div className="flex items-center gap-2">
                <GlobeLogo className="w-5 h-5" style={{ color: "#8B9FFF" } as React.CSSProperties} />
                <span className="text-xs font-medium" style={{ color: "#6B7FFF" }}>
                  Controllo BPO Analytics
                </span>
              </div>
              <div className="h-px flex-1" style={{ background: "rgba(255,255,255,0.05)" }} />
            </div>
          </div>
        </div>

        {/* Rodapé branding */}
        <div className="relative z-10">
          <p className="text-slate-600 text-xs">
            Controllo BPO Analytics © {new Date().getFullYear()} — Todos os direitos reservados
          </p>
        </div>
      </div>

      {/* ── Painel do Formulário (direita 40%) ───────────────────────────── */}
      <div className="flex-1 lg:w-[40%] flex items-center justify-center p-8 relative overflow-hidden" style={{ background: "#FFFFFF" }}>
        <GlobeBackground light={true} />
        <div className="w-full max-w-sm relative z-10">

          {/* Logo mobile */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <GlobeLogo className="w-8 h-8" style={{ color: "#1e3a5f" } as React.CSSProperties} />
            <div>
              <span className="font-black text-slate-900 text-sm tracking-wider uppercase">
                CONTROLLO BPO
              </span>
              <span className="block text-[10px] text-slate-500 tracking-widest uppercase">Analytics</span>
            </div>
          </div>

          {/* Título */}
          <div className="mb-8">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">
              {modoLogin ? "Bem-vindo de volta" : "Solicitar acesso"}
            </h1>
            <p className="text-slate-600 text-sm mt-1.5">
              {modoLogin
                ? "Seus dados financeiros estão esperando por você"
                : "Informe seus dados e nossa equipe ativará seu acesso"}
            </p>
          </div>

          {/* Tabs */}
          <div className="flex border border-slate-300 rounded-xl p-1 mb-7 bg-slate-100">
            <button
              onClick={() => { setModoLogin(true); setErro(""); setSucesso(""); }}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                modoLogin
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-800"
              }`}
            >
              Entrar
            </button>
            <button
              onClick={() => { setModoLogin(false); setErro(""); setSucesso(""); }}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                !modoLogin
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-800"
              }`}
            >
              Solicitar Acesso
            </button>
          </div>

          {/* Formulário */}
          <form onSubmit={modoLogin ? handleLogin : handleSolicitarAcesso} className="space-y-4">

            {/* Campo Escritório — SOMENTE na solicitação de acesso */}
            {!modoLogin && (
              <div>
                <label className="block text-sm font-semibold text-slate-800 mb-1.5">
                  Escritório
                </label>
                <div className="relative">
                  <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500">
                    <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <input
                    type="text"
                    value={escritorio}
                    onChange={e => setEscritorio(e.target.value)}
                    placeholder="controllobpo"
                    required
                    className="w-full h-12 pl-10 pr-4 rounded-xl border border-slate-300 bg-white text-slate-900 placeholder-slate-400 text-sm transition-all outline-none"
                    onFocus={e => { e.target.style.boxShadow = "0 0 0 2px #102a43"; e.target.style.borderColor = "#102a43"; }}
                    onBlur={e => { e.target.style.boxShadow = ""; e.target.style.borderColor = ""; }}
                  />
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Peça o nome do escritório ao administrador</p>
                {!modoLogin && escritorio.trim() && (
                  <div className="mt-1.5">
                    {validandoSlug ? (
                      <p className="text-[11px] text-slate-400 flex items-center gap-1">
                        <span className="w-3 h-3 border-2 border-slate-300 border-t-slate-500 rounded-full animate-spin" />
                        Verificando...
                      </p>
                    ) : escritorioValido?.existe ? (
                      <p className="text-[11px] text-emerald-600 flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                        Escritório encontrado: {escritorioValido.nome}
                      </p>
                    ) : escritorioValido !== null ? (
                      <p className="text-[11px] text-rose-600 flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Escritório não encontrado
                      </p>
                    ) : null}
                  </div>
                )}
              </div>
            )}

            {/* Campo Usuário */}
            <div>
              <label className="block text-sm font-semibold text-slate-800 mb-1.5">
                {modoLogin ? "Nome de usuário" : "Nome de usuário"}
              </label>
              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500">
                  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <input
                  type="text"
                  value={nome}
                  onChange={e => setNome(e.target.value)}
                  placeholder={modoLogin ? "usuario@escritorio" : "seu.usuario"}
                  required
                  className="w-full h-12 pl-10 pr-4 rounded-xl border border-slate-300 bg-white text-slate-900 placeholder-slate-400 text-sm transition-all outline-none"
                  onFocus={e => { e.target.style.boxShadow = "0 0 0 2px #102a43"; e.target.style.borderColor = "#102a43"; }}
                  onBlur={e => { e.target.style.boxShadow = ""; e.target.style.borderColor = ""; }}
                />
              </div>
              {/* Preview dinâmico do login completo — apenas na solicitação */}
              {!modoLogin && nome.trim() && escritorio.trim() && (
                <p className="text-[11px] text-slate-500 mt-1">
                  Seu login será: <span className="font-semibold text-slate-700">{nome.trim().toLowerCase()}@{escritorio.trim().toLowerCase()}</span>
                </p>
              )}
            </div>

            {/* Campo Senha */}
            <div>
              <label className="block text-sm font-semibold text-slate-800 mb-1.5">
                Senha
              </label>
              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500">
                  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <input
                  type={senhaVisivel ? "text" : "password"}
                  value={senha}
                  onChange={e => setSenha(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full h-12 pl-10 pr-11 rounded-xl border border-slate-300 bg-white text-slate-900 placeholder-slate-400 text-sm transition-all outline-none"
                  onFocus={e => { e.target.style.boxShadow = "0 0 0 2px #102a43"; e.target.style.borderColor = "#102a43"; }}
                  onBlur={e => { e.target.style.boxShadow = ""; e.target.style.borderColor = ""; }}
                />
                <button
                  type="button"
                  onClick={() => setSenhaVisivel(v => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700 transition-colors"
                >
                  {senhaVisivel ? (
                    <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>

              {/* Checklist de força de senha — apenas na solicitação de acesso */}
              {!modoLogin && senha.length > 0 && (() => {
                const regras = validarSenha(senha, nome);
                return (
                  <ul className="mt-2 space-y-1 text-xs" aria-live="polite" aria-label="Requisitos de senha">
                    {(Object.keys(REGRAS_LABELS) as (keyof RegrasSenha)[]).map((key) => (
                      <li key={key} className={`flex items-center gap-1.5 ${regras[key] ? "text-emerald-600" : "text-rose-600"}`}>
                        <span className="flex-shrink-0">{regras[key] ? "\u2713" : "\u2717"}</span>
                        {REGRAS_LABELS[key]}
                      </li>
                    ))}
                  </ul>
                );
              })()}
            </div>

            {/* Mensagens */}
            {erro && (
              <div className="flex items-start gap-2.5 p-3.5 bg-red-50 border border-red-200 rounded-xl">
                <svg className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                </svg>
                <span className="text-red-700 text-sm leading-snug">{erro}</span>
              </div>
            )}

            {sucesso && (
              <div className="flex items-start gap-2.5 p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl">
                <svg className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                </svg>
                <span className="text-emerald-700 text-sm leading-snug">{sucesso}</span>
              </div>
            )}

            {/* Botão de submit */}
            <button
              type="submit"
              disabled={carregando || (!modoLogin && !senhaValida(validarSenha(senha, nome)))}
              className="w-full h-12 rounded-xl text-white font-semibold text-sm transition-all shadow-lg disabled:opacity-60 disabled:cursor-not-allowed mt-2"
              style={{
                background: "#1e3a5f",
                boxShadow: "0 4px 20px rgba(45,43,75,0.4)",
              }}
              onMouseEnter={e => !carregando && ((e.target as HTMLElement).style.background = "#3D3A63")}
              onMouseLeave={e => !carregando && ((e.target as HTMLElement).style.background = "#1e3a5f")}
            >
              {carregando ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  Processando...
                </span>
              ) : modoLogin ? "Entrar na plataforma" : "Solicitar acesso"}
            </button>
          </form>

          <p className="text-center text-slate-500 text-xs mt-8">
            Controllo BPO Analytics © {new Date().getFullYear()}
          </p>
        </div>
      </div>
    </div>
  );
}
