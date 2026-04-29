"use client";

import { TIPO_INFO } from "./types";
import type { CampoDestino, HistoricoItem } from "./types";

// ─────────────────────────────────────────────────────────────────
//  Status badge
// ─────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    concluido:   "border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400",
    erro:        "border-red-200    dark:border-red-500/30     bg-red-50    dark:bg-red-950/40     text-red-700    dark:text-red-400",
    processando: "border-amber-200  dark:border-amber-500/30   bg-amber-50  dark:bg-amber-950/40   text-amber-700  dark:text-amber-400",
  };
  return (
    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${map[status] ?? map.processando}`}>
      {status.toUpperCase()}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────────────────────────

interface Props {
  empresaId: number | null;
  camposDestino: Record<string, CampoDestino[]>;
  historico: HistoricoItem[];
  carregandoHist: boolean;
  mostrarHistorico: boolean;
  setMostrarHistorico: (v: boolean) => void;
  carregarHistorico: () => void;
  baixarTemplate: (tipo: string) => void;
  setModo: (m: "inicio" | "template" | "avancado") => void;
  setEtapa: (e: "upload" | "classificar" | "mapear" | "resultado") => void;
}

// ─────────────────────────────────────────────────────────────────
//  Tipos de planilha — ordem canônica
// ─────────────────────────────────────────────────────────────────

const TIPOS_ORDER = ["faturamento", "despesas", "impostos", "folha", "fluxo", "balanco", "dre"];

// ─────────────────────────────────────────────────────────────────
//  Component
// ─────────────────────────────────────────────────────────────────

export default function ModoInicio({
  empresaId, camposDestino, historico, carregandoHist, mostrarHistorico,
  setMostrarHistorico, carregarHistorico, baixarTemplate, setModo, setEtapa,
}: Props) {

  const howItWorks = [
    {
      num: "01",
      title: "Baixe o modelo",
      desc: "Cada tipo de dado tem uma planilha modelo com as colunas certas e exemplos preenchidos.",
    },
    {
      num: "02",
      title: "Preencha com seus dados",
      desc: "Substitua os exemplos pelos dados reais da empresa. Mantenha o formato das colunas.",
    },
    {
      num: "03",
      title: "Faça o upload",
      desc: "Suba o arquivo preenchido. O sistema processa e atualiza automaticamente os painéis.",
    },
  ];

  return (
    <>
      {/* ── Como funciona ── */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        {/* Section title */}
        <div className="flex items-center gap-3 mb-6">
          <span
            className="text-[11px] font-semibold uppercase"
            style={{
              color: "var(--text-tertiary)",
              letterSpacing: "var(--tracking-widest)",
            }}
          >
            Como funciona
          </span>
          <div className="flex-1 h-px" style={{ background: "var(--border-subtle)" }} />
        </div>

        {/* 3-step horizontal flow — sober numeric headers, no connector lines */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {howItWorks.map((s) => (
            <div key={s.num} className="flex flex-col gap-2">
              <span
                className="text-xs uppercase font-medium"
                style={{
                  color: "var(--text-tertiary)",
                  letterSpacing: "var(--tracking-widest)",
                }}
              >
                Passo {s.num}
              </span>
              <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {s.title}
              </p>
              <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {s.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Planilhas Modelo ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Planilhas Modelo</p>
          <span
            className="text-[11px] font-medium px-2.5 py-1 font-mono"
            style={{
              background: "var(--bg-inset)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              color: "var(--text-tertiary)",
              letterSpacing: "0.03em",
            }}
          >
            .xlsx
          </span>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {TIPOS_ORDER.map((tipo) => {
            const info = TIPO_INFO[tipo];
            const campos = camposDestino[tipo] ?? [];
            const obrig = campos.filter((c) => c.obrigatorio).map((c) => c.label);

            return (
              <div
                key={tipo}
                className="rounded-2xl overflow-hidden flex flex-col"
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {/* Card body */}
                <div className="p-3.5 flex flex-col gap-2 flex-1">
                  {/* Icon + label row */}
                  <div className="flex items-center gap-2">
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{
                        background: "var(--bg-inset)",
                        border: "1px solid var(--border-subtle)",
                        color: "var(--text-secondary)",
                      }}
                    >
                      <svg
                        className="w-3.5 h-3.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <p className="font-semibold text-xs" style={{ color: "var(--text-primary)" }}>
                      {info?.label ?? tipo}
                    </p>
                  </div>

                  {/* Description */}
                  <p className="text-[11px] leading-snug" style={{ color: "var(--text-secondary)" }}>
                    {info?.descricao ?? ""}
                  </p>

                  {/* Required fields pills */}
                  {obrig.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {obrig.map((l) => (
                        <span
                          key={l}
                          className="text-[9px] font-medium px-1.5 py-0.5 rounded-full"
                          style={{
                            background: "var(--bg-inset)",
                            border: "1px solid var(--border-subtle)",
                            color: "var(--text-secondary)",
                          }}
                        >
                          {l}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Download button — separated section */}
                <button
                  onClick={() => baixarTemplate(tipo)}
                  className="w-full text-left px-3.5 py-2.5 text-[11px] font-semibold transition-colors"
                  style={{
                    borderTop: "1px solid var(--border-subtle)",
                    color: "var(--accent)",
                    background: "transparent",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "var(--accent-subtle)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                >
                  Download →
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Como deseja importar? ── */}
      <div>
        <span
          className="text-[11px] font-bold uppercase tracking-widest block mb-4"
          style={{ color: "var(--text-muted)" }}
        >
          Como deseja importar?
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Card 1: Planilha Modelo (Recomendado) */}
          <button
            disabled={!empresaId}
            onClick={() => setModo("template")}
            className="flex flex-col items-start rounded-2xl text-left overflow-hidden transition-all duration-200 hover:-translate-y-1 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderTop: "3px solid #102a43",
            }}
            onMouseEnter={e => {
              if (empresaId) (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 8px 30px rgba(79,106,255,0.15)";
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "none";
            }}
          >
            <div className="p-5 w-full">
              {/* Icon + Recomendado badge */}
              <div className="flex items-center justify-between mb-4">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center bg-navy-50 border border-navy-200 dark:bg-navy-900/30 dark:border-navy-700/50">
                  <svg className="w-5 h-5 text-navy-600 dark:text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <span
                  className="text-[10px] font-bold px-2.5 py-1 rounded-full text-white"
                  style={{
                    background: "linear-gradient(135deg, #102a43, #3b6ea5)",
                    boxShadow: "0 2px 8px rgba(79,106,255,0.30)",
                  }}
                >
                  Recomendado
                </span>
              </div>

              <p className="text-base font-bold mb-1.5" style={{ color: "var(--text-primary)" }}>
                Usar Planilha Modelo
              </p>
              <p className="text-sm leading-snug" style={{ color: "var(--text-secondary)" }}>
                Baixe o modelo, preencha com seus dados e suba. O sistema mapeia tudo automaticamente.
              </p>

              <p className="mt-4 text-sm font-bold" style={{ color: "#102a43" }}>
                Selecionar →
              </p>
            </div>
          </button>

          {/* Card 2: Planilha Própria */}
          <button
            disabled={!empresaId}
            onClick={() => { setModo("avancado"); setEtapa("upload"); }}
            className="flex flex-col items-start rounded-2xl text-left overflow-hidden transition-all duration-200 hover:-translate-y-1 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderTop: "3px solid #64748b",
            }}
          >
            <div className="p-5 w-full">
              {/* Icon */}
              <div className="mb-4">
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center"
                  style={{
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border)",
                    color: "var(--text-muted)",
                  }}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
              </div>

              <p className="text-base font-bold mb-1.5" style={{ color: "var(--text-primary)" }}>
                Usar Planilha Própria
              </p>
              <p className="text-sm leading-snug" style={{ color: "var(--text-secondary)" }}>
                Tem sua própria planilha? Faça o upload e mapeie manualmente as colunas.
              </p>

              <p className="mt-4 text-sm font-bold" style={{ color: "var(--text-muted)" }}>
                Selecionar →
              </p>
            </div>
          </button>
        </div>
      </div>

      {/* ── Histórico de importações ── */}
      <div>
        <button
          onClick={() => { setMostrarHistorico(!mostrarHistorico); if (!mostrarHistorico && empresaId) carregarHistorico(); }}
          className="inline-flex items-center gap-2 text-sm font-semibold transition-all duration-150 group"
          style={{
            color: "var(--text-muted)",
            borderBottom: mostrarHistorico ? "1px solid rgba(79,106,255,0.40)" : "1px solid transparent",
            paddingBottom: 2,
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLButtonElement).style.color = "var(--text-secondary)";
            if (!mostrarHistorico) (e.currentTarget as HTMLButtonElement).style.borderBottomColor = "var(--border)";
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)";
            if (!mostrarHistorico) (e.currentTarget as HTMLButtonElement).style.borderBottomColor = "transparent";
          }}
        >
          <svg
            className={`w-4 h-4 transition-transform duration-200 ${mostrarHistorico ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          Ver histórico de importações
        </button>

        {mostrarHistorico && (
          <div className="mt-3 space-y-2">
            {carregandoHist ? (
              <div className="flex justify-center py-6">
                <div
                  className="w-5 h-5 rounded-full border-2 animate-spin"
                  style={{ borderColor: "rgba(79,106,255,0.25)", borderTopColor: "#102a43" }}
                />
              </div>
            ) : historico.length === 0 ? (
              <p
                className="text-sm py-5 text-center rounded-xl"
                style={{
                  color: "var(--text-muted)",
                  border: "1px dashed var(--border)",
                }}
              >
                Nenhuma importação registrada.
              </p>
            ) : (
              historico.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-xl px-4 py-3"
                  style={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                      {item.nome_arquivo}
                    </p>
                    <p className="text-[11px] mt-0.5" style={{ color: "var(--text-muted)" }}>
                      {TIPO_INFO[item.tipo_dado]?.label ?? item.tipo_dado} · {item.linhas_processadas} linhas · {item.criado_em.slice(0, 10)}
                    </p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </>
  );
}
