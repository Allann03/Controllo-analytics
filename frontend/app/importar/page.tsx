"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useEmpresa } from "@/contexts/EmpresaContext";
import ModoInicio from "./_components/ModoInicio";
import ModoTemplate from "./_components/ModoTemplate";
import ModoAvancado from "./_components/ModoAvancado";
import Resultado from "./_components/Resultado";
import type { CampoDestino, HistoricoItem, Modo, Etapa } from "./_components/types";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

export default function ImportarPage() {
  const router = useRouter();
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [modo, setModo] = useState<Modo>("inicio");
  const [etapa, setEtapa] = useState<Etapa>("upload");

  // Arquivo
  const dropRef = useRef<HTMLDivElement>(null);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);

  // Classificar / mapear (modo avançado)
  const [tipoDado, setTipoDado] = useState("dre");
  const [camposDestino, setCamposDestino] = useState<Record<string, CampoDestino[]>>({});
  const [tiposDisponiveis, setTiposDisponiveis] = useState<string[]>([]);
  const [colunasArquivo, setColunasArquivo] = useState<string[]>([]);
  const [mapeamento, setMapeamento] = useState<Record<string, string>>({});
  const [carregandoPreview, setCarregandoPreview] = useState(false);

  // Processamento
  const [processando, setProcessando] = useState(false);
  const [resultado, setResultado] = useState<Record<string, unknown> | null>(null);
  const [erro, setErro] = useState("");

  // Histórico
  const [historico, setHistorico] = useState<HistoricoItem[]>([]);
  const [carregandoHist, setCarregandoHist] = useState(false);
  const [mostrarHistorico, setMostrarHistorico] = useState(false);

  const token = () => localStorage.getItem("controllo_token") ?? "";

  useEffect(() => {
    const t = localStorage.getItem("controllo_token");
    const u = localStorage.getItem("controllo_user");
    if (!t || !u) { router.push("/"); return; }
    try { if (!JSON.parse(u).is_aprovado) { router.push("/"); return; } } catch { router.push("/"); return; }
  }, [router]);

  useEffect(() => {
    fetch(`${API}/api/importacao/tipos`, { headers: { Authorization: `Bearer ${token()}` } })
      .then((r) => r.json())
      .then((d) => { setTiposDisponiveis(d.tipos ?? []); setCamposDestino(d.campos_por_tipo ?? {}); })
      .catch(() => {});
  }, []);

  const baixarTemplate = async (tipo: string) => {
    const res = await fetch(`${API}/api/importacao/modelo/${tipo}`, {
      headers: { Authorization: `Bearer ${token()}` },
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `modelo_${tipo}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const buscarPreview = async () => {
    if (!arquivo) return;
    setCarregandoPreview(true);
    const form = new FormData();
    form.append("arquivo", arquivo);
    try {
      const res = await fetch(`${API}/api/importacao/preview`, {
        method: "POST", headers: { Authorization: `Bearer ${token()}` }, body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Erro no preview");
      setColunasArquivo(data.colunas ?? []);
      setMapeamento(data.sugestoes ?? {});
      setEtapa("mapear");
    } catch (e) { setErro((e as Error).message); }
    finally { setCarregandoPreview(false); }
  };

  const processarTemplate = async (tipo: string) => {
    if (!arquivo || !empresaId) return;
    setProcessando(true); setErro("");
    const formPrev = new FormData();
    formPrev.append("arquivo", arquivo);
    let map: Record<string, string> = {};
    try {
      const prevRes = await fetch(`${API}/api/importacao/preview`, {
        method: "POST", headers: { Authorization: `Bearer ${token()}` }, body: formPrev,
      });
      const prevData = await prevRes.json();
      map = prevData.sugestoes ?? {};
    } catch { /* tenta com mapeamento vazio */ }
    await processarComMapeamento(tipo, map);
  };

  const processarAvancado = () => processarComMapeamento(tipoDado, mapeamento);

  const processarComMapeamento = async (tipo: string, map: Record<string, string>) => {
    if (!arquivo || !empresaId) return;
    setProcessando(true); setErro("");
    const form = new FormData();
    form.append("arquivo", arquivo);
    form.append("empresa_id", String(empresaId));
    form.append("tipo_dado", tipo);
    form.append("mapeamento_json", JSON.stringify(map));
    try {
      const res = await fetch(`${API}/api/importacao/processar`, {
        method: "POST", headers: { Authorization: `Bearer ${token()}` }, body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Erro no processamento");
      setResultado(data.resumo);
      setEtapa("resultado");
    } catch (e) { setErro((e as Error).message); }
    finally { setProcessando(false); }
  };

  const carregarHistorico = async () => {
    if (!empresaId) return;
    setCarregandoHist(true);
    try {
      const r = await fetch(`${API}/api/importacao/historico/${empresaId}`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      setHistorico(await r.json());
    } catch { /* silencioso */ }
    finally { setCarregandoHist(false); }
  };

  const reiniciar = () => {
    setArquivo(null); setColunasArquivo([]); setMapeamento({});
    setResultado(null); setErro(""); setModo("inicio"); setEtapa("upload");
  };

  const baixarModeloExtrato = () => {
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Extrato">
  <Table>
   <Row>
    <Cell><Data ss:Type="String">Data</Data></Cell>
    <Cell><Data ss:Type="String">Categoria</Data></Cell>
    <Cell><Data ss:Type="String">Descrição</Data></Cell>
    <Cell><Data ss:Type="String">Valor</Data></Cell>
    <Cell><Data ss:Type="String">Tipo</Data></Cell>
   </Row>
   <Row>
    <Cell><Data ss:Type="String">01/01/2025</Data></Cell>
    <Cell><Data ss:Type="String">Receita de Serviços</Data></Cell>
    <Cell><Data ss:Type="String">Pagamento cliente XYZ</Data></Cell>
    <Cell><Data ss:Type="Number">5000.00</Data></Cell>
    <Cell><Data ss:Type="String">entrada</Data></Cell>
   </Row>
   <Row>
    <Cell><Data ss:Type="String">05/01/2025</Data></Cell>
    <Cell><Data ss:Type="String">Despesas Administrativas</Data></Cell>
    <Cell><Data ss:Type="String">Aluguel do escritório</Data></Cell>
    <Cell><Data ss:Type="Number">1200.00</Data></Cell>
    <Cell><Data ss:Type="String">saida</Data></Cell>
   </Row>
  </Table>
 </Worksheet>
</Workbook>`;
    const blob = new Blob([xml], { type: "application/vnd.ms-excel;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "modelo_extrato.xls"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>

      {/* HEADER */}
      <header className="px-8 pt-8 pb-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-navy-50 border border-navy-200 dark:bg-navy-500/10 dark:border-navy-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-navy-600 dark:text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Importar Dados</h1>
              <p className="text-slate-500 text-sm">Carregue planilhas para alimentar os painéis financeiros</p>
            </div>
          </div>
          <button
            onClick={baixarModeloExtrato}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-emerald-600/40 text-emerald-400 bg-emerald-500/5 hover:bg-emerald-500/15 transition-all"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Modelo Extrato (.xls)
          </button>
        </div>
      </header>

      <div className="px-8 py-8 space-y-8">

        {/* Modo início */}
        {modo === "inicio" && etapa !== "resultado" && (
          <ModoInicio
            empresaId={empresaId}
            camposDestino={camposDestino}
            historico={historico}
            carregandoHist={carregandoHist}
            mostrarHistorico={mostrarHistorico}
            setMostrarHistorico={setMostrarHistorico}
            carregarHistorico={carregarHistorico}
            baixarTemplate={baixarTemplate}
            setModo={setModo}
            setEtapa={setEtapa}
          />
        )}

        {/* Modo template */}
        {modo === "template" && etapa !== "resultado" && (
          <ModoTemplate
            empresaId={empresaId}
            tipoDado={tipoDado}
            setTipoDado={setTipoDado}
            arquivo={arquivo}
            setArquivo={setArquivo}
            dragging={dragging}
            setDragging={setDragging}
            tiposDisponiveis={tiposDisponiveis}
            camposDestino={camposDestino}
            erro={erro}
            processando={processando}
            baixarTemplate={baixarTemplate}
            processarTemplate={processarTemplate}
            reiniciar={reiniciar}
          />
        )}

        {/* Modo avançado */}
        {modo === "avancado" && (etapa === "upload" || etapa === "classificar") && (
          <ModoAvancado
            empresaId={empresaId}
            etapa={etapa}
            tipoDado={tipoDado}
            setTipoDado={setTipoDado}
            arquivo={arquivo}
            setArquivo={setArquivo}
            dragging={dragging}
            setDragging={setDragging}
            tiposDisponiveis={tiposDisponiveis}
            camposDestino={camposDestino}
            colunasArquivo={colunasArquivo}
            mapeamento={mapeamento}
            setMapeamento={setMapeamento}
            carregandoPreview={carregandoPreview}
            erro={erro}
            processando={processando}
            buscarPreview={buscarPreview}
            processarAvancado={processarAvancado}
            setEtapa={setEtapa}
            reiniciar={reiniciar}
          />
        )}

        {/* Resultado */}
        {etapa === "resultado" && resultado && (
          <Resultado resultado={resultado} reiniciar={reiniciar} />
        )}
      </div>
    </div>
  );
}
