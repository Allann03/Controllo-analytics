"use client";
import { useEffect, useState, useCallback, useMemo } from "react";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

type Prioridade = "baixa" | "media" | "alta" | "urgente";
type Status = "pendente" | "concluido" | "atrasado";

interface Lembrete {
  id: number;
  titulo: string;
  descricao: string;
  data_vencimento: string;
  hora: string;
  prioridade: Prioridade;
  status: Status;
  empresa_vinculada: string;
}

const PRIO_CFG: Record<Prioridade, { label: string; dot: string; bg: string; border: string; color: string; accent: string; glow: string }> = {
  urgente: { label: "Urgente", dot: "#B83030", bg: "bg-rose-50 dark:bg-rose-500/10",     border: "border-rose-200 dark:border-rose-500/25",     color: "text-rose-700 dark:text-rose-400",     accent: "#B83030", glow: "rgba(184,48,48,0.10)"   },
  alta:    { label: "Alta",    dot: "#92400E", bg: "bg-amber-50 dark:bg-amber-500/10",   border: "border-amber-200 dark:border-amber-500/25",   color: "text-amber-700 dark:text-amber-400",   accent: "#92400E", glow: "rgba(146,64,14,0.10)"  },
  media:   { label: "Média",   dot: "#1E4976", bg: "bg-blue-50 dark:bg-blue-500/10",     border: "border-blue-200 dark:border-blue-500/25",     color: "text-blue-700 dark:text-blue-400",     accent: "#1E4976", glow: "rgba(30,73,118,0.10)"  },
  baixa:   { label: "Baixa",   dot: "#64748B", bg: "bg-slate-100 dark:bg-slate-500/10",  border: "border-slate-200 dark:border-slate-500/25",  color: "text-[#64748B] dark:text-slate-400",  accent: "#64748B", glow: "rgba(100,116,139,0.06)" },
};

const MESES       = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
const DIAS_SEMANA = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"];

function toDate(s: string) {
  const p = s.split("/"); if (p.length !== 3) return null;
  return new Date(Number(p[2]), Number(p[1]) - 1, Number(p[0]));
}
function toKey(y: number, m: number, d: number) {
  return `${String(d).padStart(2,"0")}/${String(m+1).padStart(2,"0")}/${y}`;
}
function hojeStr() {
  const d = new Date(); return toKey(d.getFullYear(), d.getMonth(), d.getDate());
}
function tk() { return localStorage.getItem("controllo_token") ?? ""; }

export default function AgendaPage() {
  const [lembretes,      setLembretes]      = useState<Lembrete[]>([]);
  const [carregando,     setCarregando]     = useState(true);
  const [anoAtual,       setAnoAtual]       = useState(() => new Date().getFullYear());
  const [mesAtual,       setMesAtual]       = useState(() => new Date().getMonth());
  const [diaSelecionado, setDiaSelecionado] = useState(() => hojeStr());
  const [modalAberto,    setModalAberto]    = useState(false);
  const [editando,       setEditando]       = useState<Lembrete | null>(null);
  const [toast,          setToast]          = useState<{ msg: string; tipo: "ok" | "erro" } | null>(null);
  const [confirmar,      setConfirmar]      = useState<{ id: number; titulo: string } | null>(null);

  const [titulo,     setTitulo]     = useState("");
  const [descricao,  setDescricao]  = useState("");
  const [dataVenc,   setDataVenc]   = useState(hojeStr());
  const [hora,       setHora]       = useState("09:00");
  const [prioridade, setPrioridade] = useState<Prioridade>("media");
  const [empresa,    setEmpresa]    = useState("");

  const showToast = (msg: string, tipo: "ok" | "erro") => {
    setToast({ msg, tipo }); setTimeout(() => setToast(null), 3500);
  };

  const carregar = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/agenda/lembretes`, { headers: { Authorization: `Bearer ${tk()}` } });
      if (!res.ok) throw new Error();
      const data: Lembrete[] = await res.json();
      const hj = new Date(); hj.setHours(0,0,0,0);
      setLembretes(data.map(l => {
        if (l.status === "pendente") {
          const d = toDate(l.data_vencimento);
          if (d && d < hj) return { ...l, status: "atrasado" as Status };
        }
        return l;
      }));
    } catch { showToast("Erro ao carregar lembretes", "erro"); }
    finally { setCarregando(false); }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const porData = useMemo(() => {
    const map: Record<string, Lembrete[]> = {};
    lembretes.forEach(l => { (map[l.data_vencimento] ??= []).push(l); });
    return map;
  }, [lembretes]);

  const diasCalendario = useMemo(() => {
    const primeiro = new Date(anoAtual, mesAtual, 1).getDay();
    const ultimo   = new Date(anoAtual, mesAtual + 1, 0).getDate();
    const antUlt   = new Date(anoAtual, mesAtual, 0).getDate();
    const cells: { dia: number; mes: number; ano: number; fora: boolean }[] = [];
    for (let i = primeiro - 1; i >= 0; i--) {
      const m = mesAtual === 0 ? 11 : mesAtual - 1;
      const a = mesAtual === 0 ? anoAtual - 1 : anoAtual;
      cells.push({ dia: antUlt - i, mes: m, ano: a, fora: true });
    }
    for (let d = 1; d <= ultimo; d++) cells.push({ dia: d, mes: mesAtual, ano: anoAtual, fora: false });
    const total = Math.ceil(cells.length / 7) * 7;
    const m2 = mesAtual === 11 ? 0 : mesAtual + 1;
    const a2 = mesAtual === 11 ? anoAtual + 1 : anoAtual;
    for (let d = 1; cells.length < total; d++) cells.push({ dia: d, mes: m2, ano: a2, fora: true });
    return cells;
  }, [anoAtual, mesAtual]);

  const lembretesDia = useMemo(
    () => (porData[diaSelecionado] || []).sort((a, b) => a.hora.localeCompare(b.hora)),
    [porData, diaSelecionado]
  );

  function navMes(d: number) {
    let m = mesAtual + d, a = anoAtual;
    if (m < 0) { m = 11; a--; } if (m > 11) { m = 0; a++; }
    setMesAtual(m); setAnoAtual(a);
  }

  function abrirNovo() {
    setEditando(null); setTitulo(""); setDescricao(""); setDataVenc(diaSelecionado);
    setHora("09:00"); setPrioridade("media"); setEmpresa(""); setModalAberto(true);
  }

  function abrirEditar(l: Lembrete) {
    setEditando(l); setTitulo(l.titulo); setDescricao(l.descricao);
    setDataVenc(l.data_vencimento); setHora(l.hora); setPrioridade(l.prioridade);
    setEmpresa(l.empresa_vinculada); setModalAberto(true);
  }

  async function salvar(e: React.SyntheticEvent) {
    e.preventDefault();
    const body = { titulo, descricao, data_vencimento: dataVenc, hora, prioridade, empresa_vinculada: empresa };
    try {
      if (editando) {
        const r = await fetch(`${API}/api/agenda/lembretes/${editando.id}`, {
          method: "PUT", headers: { Authorization: `Bearer ${tk()}`, "Content-Type": "application/json" }, body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error();
        showToast("Lembrete atualizado!", "ok");
      } else {
        const r = await fetch(`${API}/api/agenda/lembretes`, {
          method: "POST", headers: { Authorization: `Bearer ${tk()}`, "Content-Type": "application/json" }, body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error();
        showToast("Lembrete criado!", "ok");
      }
      setModalAberto(false); carregar();
    } catch { showToast("Erro ao salvar", "erro"); }
  }

  async function concluir(id: number) {
    try {
      await fetch(`${API}/api/agenda/lembretes/${id}/concluir`, { method: "PUT", headers: { Authorization: `Bearer ${tk()}` } });
      showToast("Concluído!", "ok"); carregar();
    } catch { showToast("Erro", "erro"); }
  }

  function excluir(id: number) {
    setConfirmar({ id, titulo: lembretes.find(l => l.id === id)?.titulo ?? "" });
  }

  async function excluirConfirmado() {
    if (!confirmar) return;
    try {
      await fetch(`${API}/api/agenda/lembretes/${confirmar.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${tk()}` } });
      showToast("Removido!", "ok"); setConfirmar(null); carregar();
    } catch { showToast("Erro", "erro"); }
  }

  const totalPendentes = lembretes.filter(l => l.status === "pendente").length;
  const atrasados      = lembretes.filter(l => l.status === "atrasado").length;
  const concluidos     = lembretes.filter(l => l.status === "concluido").length;

  const dataSelecionadaFormatada = useMemo(() => {
    const p = diaSelecionado.split("/");
    if (p.length !== 3) return diaSelecionado;
    return new Date(Number(p[2]), Number(p[1]) - 1, Number(p[0]))
      .toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
  }, [diaSelecionado]);

  if (carregando) return (
    <div className="h-full flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-[#102a43]/20 border-t-[#102a43] rounded-full animate-spin" />
        <p className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>Carregando agenda...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* ── TOAST ── */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3.5 rounded-2xl border text-sm font-semibold shadow-2xl backdrop-blur-sm ${
          toast.tipo === "ok"
            ? "bg-emerald-50 dark:bg-emerald-600/15 border-emerald-200 dark:border-emerald-500/25 text-emerald-700 dark:text-emerald-300"
            : "bg-red-50 dark:bg-red-600/15 border-red-200 dark:border-red-500/25 text-red-700 dark:text-red-300"
        }`}>
          {toast.tipo === "ok"
            ? <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
            : <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" /></svg>
          }
          {toast.msg}
        </div>
      )}

      {/* ── HEADER ── */}
      <div className="relative px-6 pt-7 pb-6 overflow-hidden"
        style={{ borderBottom: "1px solid var(--border)" }}>
        {/* Full-width gradient bg */}
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "linear-gradient(to right, rgba(79,106,255,0.06), transparent 70%)" }} />
        <div className="absolute top-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: "linear-gradient(90deg, rgba(79,106,255,0.4), transparent 60%)" }} />

        <div className="relative flex items-start justify-between gap-4 mb-5">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight leading-none">
              Agenda{" "}
              <span className="text-navy-600 dark:text-navy-400">&amp;</span>
              {" "}Lembretes
            </h1>
            <p className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>
              Calendário pessoal de prazos e compromissos
            </p>
          </div>

          <button
            onClick={abrirNovo}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-white text-sm font-bold transition-all hover:brightness-110 active:scale-95 flex-shrink-0 mt-1"
            style={{
              background: "linear-gradient(135deg, #102a43, #1e3a5f)",
              boxShadow: "0 4px 20px rgba(79,106,255,0.35)",
            }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            Novo Lembrete
          </button>
        </div>

        {/* ── INLINE STATS ── */}
        <div className="relative flex items-center gap-3 flex-wrap">
          <span className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full"
            style={{ background: "rgba(79,106,255,0.1)", border: "1px solid rgba(79,106,255,0.18)", color: "#3b6ea5" }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#102a43" }} />
            {lembretes.length} total
          </span>
          {totalPendentes > 0 && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
              style={{ background: "rgba(59,130,246,0.1)", color: "#3b82f6", border: "1px solid rgba(59,130,246,0.18)" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              {totalPendentes} pendente{totalPendentes !== 1 ? "s" : ""}
            </span>
          )}
          {atrasados > 0 && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full text-rose-700 dark:text-rose-400"
              style={{ background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.2)" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500 dark:bg-rose-400" />
              {atrasados} atrasado{atrasados !== 1 ? "s" : ""}
            </span>
          )}
          {concluidos > 0 && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full text-emerald-700 dark:text-emerald-400"
              style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.18)" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400" />
              {concluidos} concluído{concluidos !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* ── GRID PRINCIPAL ── */}
      <div className="px-6 py-6 grid grid-cols-1 lg:grid-cols-5 gap-5">

        {/* ── CALENDÁRIO ── */}
        <div className="lg:col-span-3 rounded-2xl overflow-hidden relative"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "0 4px 28px rgba(0,0,0,0.15)",
          }}>

          {/* Inner top gradient overlay */}
          <div className="absolute top-0 inset-x-0 h-32 pointer-events-none rounded-t-2xl"
            style={{ background: "linear-gradient(180deg, rgba(79,106,255,0.04), transparent)" }} />

          {/* Navegação de mês */}
          <div className="relative flex items-center justify-between px-6 pt-5 pb-4"
            style={{ borderBottom: "1px solid var(--border)" }}>
            <button onClick={() => navMes(-1)}
              className="w-9 h-9 flex items-center justify-center rounded-xl transition-all hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95"
              style={{ color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="text-center">
              <h2 className="font-extrabold text-xl tracking-tight" style={{ color: "var(--text-primary)" }}>
                {MESES[mesAtual]}
              </h2>
              <p className="text-xs font-bold mt-0.5 text-navy-600 dark:text-navy-400">
                {anoAtual}
              </p>
            </div>
            <button onClick={() => navMes(1)}
              className="w-9 h-9 flex items-center justify-center rounded-xl transition-all hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95"
              style={{ color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          <div className="p-5">
            {/* Dias da semana */}
            <div className="grid grid-cols-7 mb-3">
              {DIAS_SEMANA.map((d, i) => (
                <div key={d} className="text-center text-[10px] font-bold uppercase tracking-widest py-2"
                  style={{ color: i === 0 || i === 6 ? "#3b6ea5" : "var(--text-muted)" }}>{d}</div>
              ))}
            </div>

            {/* Grid de dias */}
            <div className="grid grid-cols-7 gap-1.5">
              {diasCalendario.map((cell, i) => {
                const key         = toKey(cell.ano, cell.mes, cell.dia);
                const isHoje      = key === hojeStr();
                const isSel       = key === diaSelecionado;
                const lemsDia     = porData[key] || [];
                const prioridades = lemsDia.map(l => l.prioridade);
                const temUrgente  = prioridades.includes("urgente");
                const isWeekend   = (i % 7 === 0 || i % 7 === 6);

                return (
                  <button key={i} onClick={() => setDiaSelecionado(key)}
                    className={`relative flex flex-col items-center justify-center rounded-xl transition-all duration-150 min-h-[44px] font-semibold
                      ${cell.fora ? "opacity-20" : "hover:bg-slate-100 dark:hover:bg-white/5"}
                    `}
                    style={
                      isSel
                        ? {
                            background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                            color: "white",
                            boxShadow: "0 4px 16px rgba(79,106,255,0.35)",
                          }
                        : isHoje
                        ? {
                            background: "rgba(16,185,129,0.08)",
                            border: "2px solid rgba(16,185,129,0.4)",
                            color: "#10b981",
                          }
                        : { color: isWeekend && !cell.fora ? "#3b6ea5" : "var(--text-primary)" }
                    }
                  >
                    <span className="text-sm leading-none">{cell.dia}</span>
                    {lemsDia.length > 0 && (
                      <div className="flex gap-0.5 mt-1.5">
                        {(["urgente","alta","media","baixa"] as Prioridade[])
                          .filter(p => prioridades.includes(p)).slice(0, 3)
                          .map(p => (
                            <span key={p} className="w-2 h-2 rounded-full"
                              style={{ background: isSel ? "rgba(255,255,255,0.8)" : PRIO_CFG[p].dot }} />
                          ))}
                      </div>
                    )}
                    {temUrgente && !isSel && (
                      <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Legenda */}
            <div className="flex gap-4 mt-5 justify-center pt-4" style={{ borderTop: "1px solid var(--border)" }}>
              {(["urgente","alta","media","baixa"] as Prioridade[]).map(p => (
                <div key={p} className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ background: PRIO_CFG[p].dot }} />
                  <span className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>{PRIO_CFG[p].label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── DETALHE DO DIA ── */}
        <div className="lg:col-span-2 flex flex-col gap-3">

          {/* Header do dia — more dramatic */}
          <div className="rounded-2xl px-5 py-5 relative overflow-hidden bg-navy-50 border border-navy-100 dark:bg-navy-900/30 dark:border-navy-800/60">
            <div className="absolute inset-0 pointer-events-none"
              style={{ background: "radial-gradient(ellipse at top left, rgba(79,106,255,0.12), transparent 65%)" }} />
            <div className="relative">
              <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5" style={{ color: "#3b6ea5" }}>
                Dia selecionado
              </p>
              <h3 className="font-bold text-base capitalize leading-snug" style={{ color: "var(--text-primary)" }}>
                {dataSelecionadaFormatada}
              </h3>
              <div className="flex items-center gap-2 mt-3 flex-wrap">
                {lembretesDia.length === 0 ? (
                  <span className="text-xs px-2.5 py-1 rounded-full font-medium"
                    style={{ background: "var(--bg-secondary)", color: "var(--text-muted)" }}>
                    Dia livre
                  </span>
                ) : (
                  <>
                    <span className="text-xs px-2.5 py-1 rounded-full font-semibold"
                      style={{ background: "rgba(79,106,255,0.15)", color: "#3b6ea5", border: "1px solid rgba(79,106,255,0.25)" }}>
                      {lembretesDia.length} lembrete{lembretesDia.length > 1 ? "s" : ""}
                    </span>
                    {lembretesDia.some(l => l.status === "atrasado") && (
                      <span className="text-xs px-2.5 py-1 rounded-full font-semibold bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-400">
                        {lembretesDia.filter(l => l.status === "atrasado").length} atrasado{lembretesDia.filter(l => l.status === "atrasado").length > 1 ? "s" : ""}
                      </span>
                    )}
                    {lembretesDia.some(l => l.status === "concluido") && (
                      <span className="text-xs px-2.5 py-1 rounded-full font-semibold bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400">
                        {lembretesDia.filter(l => l.status === "concluido").length} concluído{lembretesDia.filter(l => l.status === "concluido").length > 1 ? "s" : ""}
                      </span>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Lista do dia */}
          <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: "calc(100vh - 420px)" }}>
            {lembretesDia.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-14 rounded-2xl border-2 border-dashed"
                style={{ borderColor: "var(--border)" }}>
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
                  style={{ background: "rgba(79,106,255,0.07)", border: "1px solid rgba(79,106,255,0.14)" }}>
                  <svg className="w-7 h-7" style={{ color: "#3b6ea5", opacity: 0.5 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <p className="text-sm font-semibold mb-1" style={{ color: "var(--text-secondary)" }}>Dia livre</p>
                <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>Nenhum compromisso agendado</p>
                <button onClick={abrirNovo}
                  className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl transition-all hover:brightness-110 active:scale-95"
                  style={{ background: "rgba(79,106,255,0.12)", color: "#3b6ea5", border: "1px solid rgba(79,106,255,0.22)" }}>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                  </svg>
                  Adicionar lembrete
                </button>
              </div>
            ) : (
              lembretesDia.map(l => {
                const p = PRIO_CFG[l.prioridade];
                const isConcluido = l.status === "concluido";
                const isAtrasado  = l.status === "atrasado";
                return (
                  <div key={l.id}
                    className={`rounded-2xl overflow-hidden transition-all duration-200 ${isConcluido ? "opacity-50" : "hover:-translate-y-px"}`}
                    style={{
                      background: "var(--bg-card)",
                      border: `1px solid ${isAtrasado ? "rgba(239,68,68,0.3)" : "var(--border)"}`,
                      boxShadow: isConcluido ? "none" : `0 2px 14px ${p.glow}`,
                    }}
                  >
                    {/* Atrasado warning strip */}
                    {isAtrasado && (
                      <div className="h-0.5 w-full"
                        style={{ background: "linear-gradient(90deg, #ef4444, #f97316, transparent 80%)" }} />
                    )}
                    {/* Priority top accent */}
                    {!isAtrasado && (
                      <div className="h-0.5 w-full"
                        style={{ background: isConcluido ? "transparent" : `linear-gradient(90deg, ${p.accent}, transparent 80%)` }} />
                    )}

                    <div className="p-5">
                      <div className="flex items-start gap-3">
                        {/* Hora */}
                        <div className="flex-shrink-0 pt-0.5">
                          <span className="text-xs font-mono font-bold tabular-nums"
                            style={{ color: isConcluido ? "var(--text-muted)" : p.accent }}>{l.hora}</span>
                        </div>

                        <div className="flex-1 min-w-0">
                          <p className={`text-base font-semibold mb-2 ${isConcluido ? "line-through" : ""}`}
                            style={{ color: isConcluido ? "var(--text-muted)" : "var(--text-primary)" }}>
                            {l.titulo}
                          </p>

                          {/* Priority + status — cleaner: dot + label only */}
                          <div className="flex items-center gap-3 flex-wrap mb-2">
                            <span className="flex items-center gap-1.5 text-xs font-semibold">
                              <span className="w-2 h-2 rounded-full" style={{ background: p.dot }} />
                              <span style={{ color: p.accent }}>{p.label}</span>
                            </span>
                            {isAtrasado && (
                              <span className="flex items-center gap-1.5 text-xs font-semibold text-rose-700 dark:text-rose-400">
                                <span className="w-2 h-2 rounded-full bg-rose-600 dark:bg-rose-400" />
                                Atrasado
                              </span>
                            )}
                            {isConcluido && (
                              <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                                <span className="w-2 h-2 rounded-full bg-emerald-600 dark:bg-emerald-400" />
                                Concluído
                              </span>
                            )}
                          </div>

                          {l.descricao && (
                            <p className="text-xs leading-relaxed mb-2" style={{ color: "var(--text-secondary)" }}>
                              {l.descricao}
                            </p>
                          )}
                          {l.empresa_vinculada && (
                            <p className="text-[11px] flex items-center gap-1.5" style={{ color: "var(--text-muted)" }}>
                              <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                              </svg>
                              {l.empresa_vinculada}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Ações — refined pill style */}
                      <div className="flex gap-1.5 mt-4 pt-3 justify-end" style={{ borderTop: "1px solid var(--border)" }}>
                        {!isConcluido && (
                          <button onClick={() => concluir(l.id)} title="Concluir"
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border text-[#64748B] dark:text-slate-500 hover:text-emerald-700 dark:hover:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-400/10 hover:border-emerald-200 dark:hover:border-emerald-400/20"
                            style={{ border: "1px solid var(--border)" }}>
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                            </svg>
                            Concluir
                          </button>
                        )}
                        <button onClick={() => abrirEditar(l)} title="Editar"
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border text-[#64748B] dark:text-slate-500 hover:text-blue-700 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-400/10 hover:border-blue-200 dark:hover:border-blue-400/20"
                          style={{ border: "1px solid var(--border)" }}>
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                          Editar
                        </button>
                        <button onClick={() => setConfirmar({ id: l.id, titulo: l.titulo })} title="Excluir"
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border text-[#64748B] dark:text-slate-500 hover:text-rose-700 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-400/10 hover:border-rose-200 dark:hover:border-rose-400/20"
                          style={{ border: "1px solid var(--border)" }}>
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Excluir
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {lembretesDia.length > 0 && (
            <button onClick={abrirNovo}
              className="flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm font-semibold transition-all border-2 border-dashed hover:border-[#102a43]/50 hover:bg-[#102a43]/5 hover:text-[#3b6ea5] active:scale-[.99]"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
              Adicionar neste dia
            </button>
          )}
        </div>
      </div>

      {/* ── CONFIRM DELETE DIALOG ── */}
      {confirmar && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-3xl overflow-hidden shadow-2xl"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              boxShadow: "0 30px 70px rgba(0,0,0,0.5), 0 0 0 1px rgba(244,63,94,0.08)",
            }}>
            {/* Header */}
            <div className="relative px-6 pt-6 pb-4 overflow-hidden bg-rose-50 dark:bg-rose-900/10 border-b border-rose-100 dark:border-rose-800/40">
              <div className="absolute inset-0 pointer-events-none"
                style={{ background: "radial-gradient(ellipse at top left, rgba(244,63,94,0.1), transparent 60%)" }} />
              <div className="relative flex items-center gap-3 mb-1">
                <div className="w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "rgba(244,63,94,0.12)", border: "1px solid rgba(244,63,94,0.2)" }}>
                  <svg className="w-5 h-5 text-rose-600 dark:text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </div>
                <h3 className="font-extrabold text-lg tracking-tight" style={{ color: "var(--text-primary)" }}>
                  Remover lembrete?
                </h3>
              </div>
            </div>
            <div className="px-6 py-5">
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                <span className="font-semibold" style={{ color: "var(--text-primary)" }}>"{confirmar.titulo}"</span>{" "}
                será removido permanentemente e não poderá ser recuperado.
              </p>
            </div>
            <div className="flex gap-2 px-6 pb-6">
              <button onClick={() => setConfirmar(null)}
                className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95"
                style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                Cancelar
              </button>
              <button onClick={excluirConfirmado}
                className="flex-1 py-2.5 rounded-xl text-white text-sm font-bold transition-all hover:brightness-110 active:scale-95"
                style={{ background: "linear-gradient(135deg, #f43f5e, #be123c)", boxShadow: "0 4px 16px rgba(244,63,94,0.3)" }}>
                Remover
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL ── */}
      {modalAberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
          <div className="w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              boxShadow: "0 30px 70px rgba(0,0,0,0.5), 0 0 0 1px rgba(79,106,255,0.1)",
            }}>

            {/* Modal header with gradient bg */}
            <div className="relative px-6 py-5 overflow-hidden bg-navy-50 dark:bg-navy-900/40 border-b border-navy-100 dark:border-navy-700/50">
              <div className="absolute inset-0 pointer-events-none"
                style={{ background: "radial-gradient(ellipse at top left, rgba(79,106,255,0.12), transparent 60%)" }} />
              <div className="relative flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                    style={{ background: "rgba(79,106,255,0.2)", border: "1px solid rgba(79,106,255,0.3)" }}>
                    <svg className="w-5 h-5" style={{ color: "#3b6ea5" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="font-extrabold text-base tracking-tight" style={{ color: "var(--text-primary)" }}>
                      {editando ? "Editar Lembrete" : "Novo Lembrete"}
                    </h2>
                    <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                      {editando ? "Atualize os dados do lembrete" : "Preencha os dados abaixo"}
                    </p>
                  </div>
                </div>
                <button onClick={() => setModalAberto(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-xl transition-all hover:bg-slate-100 dark:hover:bg-white/5"
                  style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <form onSubmit={salvar} className="p-6 space-y-4">
              {/* Título */}
              <div>
                <label className="block text-[11px] font-bold mb-2 uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                  Título *
                </label>
                <input value={titulo} onChange={e => setTitulo(e.target.value)} required
                  placeholder="Ex: Enviar declaração do cliente"
                  className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#102a43]/50 transition-all"
                  style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
              </div>

              {/* Data e hora */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold mb-2 uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Data *</label>
                  <input value={dataVenc} onChange={e => setDataVenc(e.target.value)} required placeholder="DD/MM/AAAA"
                    className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#102a43]/50 transition-all"
                    style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
                </div>
                <div>
                  <label className="block text-[11px] font-bold mb-2 uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Hora</label>
                  <input type="time" value={hora} onChange={e => setHora(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#102a43]/50 transition-all"
                    style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
                </div>
              </div>

              {/* Prioridade */}
              <div>
                <label className="block text-[11px] font-bold mb-2 uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Prioridade</label>
                <div className="grid grid-cols-4 gap-2">
                  {(["baixa","media","alta","urgente"] as Prioridade[]).map(p => {
                    const c = PRIO_CFG[p];
                    const sel = prioridade === p;
                    return (
                      <button key={p} type="button" onClick={() => setPrioridade(p)}
                        className={`py-2.5 rounded-xl text-xs font-bold border transition-all active:scale-95 ${
                          sel ? `${c.bg} ${c.border} ${c.color}` : "hover:bg-slate-100 dark:hover:bg-white/5"
                        }`}
                        style={!sel ? { background: "var(--bg-secondary)", borderColor: "var(--border)", color: "var(--text-muted)" } : undefined}>
                        <span className="flex items-center justify-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.dot }} />
                          {c.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Empresa */}
              <div>
                <label className="block text-[11px] font-bold mb-2 uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Empresa</label>
                <input value={empresa} onChange={e => setEmpresa(e.target.value)} placeholder="Opcional"
                  className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#102a43]/50 transition-all"
                  style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
              </div>

              {/* Descrição */}
              <div>
                <label className="block text-[11px] font-bold mb-2 uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Descrição</label>
                <textarea value={descricao} onChange={e => setDescricao(e.target.value)} rows={2}
                  placeholder="Detalhes opcionais..."
                  className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#102a43]/50 transition-all resize-none"
                  style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
              </div>

              {/* Botões */}
              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => setModalAberto(false)}
                  className="flex-1 py-3 rounded-xl text-sm font-semibold transition-all hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95"
                  style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                  Cancelar
                </button>
                <button type="submit"
                  className="flex-1 py-3 rounded-xl text-white text-sm font-bold transition-all hover:brightness-110 hover:shadow-[#102a43]/40 active:scale-95"
                  style={{
                    background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                    boxShadow: "0 4px 20px rgba(79,106,255,0.3)",
                  }}>
                  {editando ? "Salvar alterações" : "Criar lembrete"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
