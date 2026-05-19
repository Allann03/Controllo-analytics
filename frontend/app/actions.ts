// NOTE: This is a client-side utility module (NO "use server").
// Token is read from localStorage at call time in the browser.

const _rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// Strip trailing slash and accidental /api suffix so URLs like
// "https://backend.onrender.com/api" don't produce double /api/api/...
const API_URL = _rawApiUrl.replace(/\/api\/?$/, "").replace(/\/$/, "");

// ------------------------------------------------------------------ //
//  TIPOS                                                             //
// ------------------------------------------------------------------ //
export interface Transacao {
  data: string;
  banco: string;
  descricao: string;
  tipo: "entrada" | "saida" | "posicao";
  valor: number;
  categoria?: string;
}

export interface ResultadoProcessamento {
  sucesso: boolean;
  nome_arquivo: string;
  banco_detectado: string;
  total_transacoes: number;
  resumo: {
    entradas: number;
    saidas: number;
    posicao: number;
    aplicado: number;
    saldo: number;
    saldo_inicial?: number | null;
    saldo_final?: number | null;
  };
  excel_id: string;
  excel_url: string;
  transacoes: Transacao[];
  avisos?: string[];
  erro?: string;
}

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("controllo_token") ?? "";
}

// ------------------------------------------------------------------ //
//  ACTION: processar extrato                                         //
// ------------------------------------------------------------------ //
export async function processarExtrato(
  formData: FormData
): Promise<ResultadoProcessamento> {
  try {
    const token = getToken();
    const headers: HeadersInit = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`${API_URL}/api/processar-extrato`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const erro = await response.json().catch(() => ({ detail: "Erro desconhecido" }));
      return {
        sucesso: false,
        nome_arquivo: "",
        banco_detectado: "",
        total_transacoes: 0,
        resumo: { entradas: 0, saidas: 0, posicao: 0, aplicado: 0, saldo: 0 },
        excel_id: "",
        excel_url: "",
        transacoes: [],
        avisos: [],
        erro: erro.erro || erro.detail || `Erro HTTP ${response.status}`,
        ...(erro.requer_senha ? { requer_senha: true } : {}),
      } as ResultadoProcessamento & { requer_senha?: boolean };
    }

    const data = await response.json();
    // Garante que campos opcionais do resumo existem
    if (data.resumo) {
      if (data.resumo.posicao === undefined) data.resumo.posicao = 0;
      if (data.resumo.aplicado === undefined) data.resumo.aplicado = 0;
      if (data.resumo.saldo_inicial === undefined) data.resumo.saldo_inicial = null;
      if (data.resumo.saldo_final === undefined) data.resumo.saldo_final = null;
    }
    return data;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Erro desconhecido";
    return {
      sucesso: false,
      nome_arquivo: "",
      banco_detectado: "",
      total_transacoes: 0,
      resumo: { entradas: 0, saidas: 0, posicao: 0, aplicado: 0, saldo: 0 },
      excel_id: "",
      excel_url: "",
      transacoes: [],
      avisos: [],
      erro: msg || "Não foi possível conectar ao servidor. Verifique se o backend está rodando.",
    };
  }
}

// ------------------------------------------------------------------ //
//  ACTION: download Excel com autenticação                          //
// ------------------------------------------------------------------ //
export async function downloadExcel(excelId: string, nomeArquivo?: string): Promise<void> {
  const token = getToken();
  const url = `${API_URL}/api/download/${excelId}`;

  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    throw new Error("Falha ao baixar o arquivo Excel.");
  }

  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = nomeArquivo || "extrato_controllo.xlsx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(blobUrl);
}

// ------------------------------------------------------------------ //
//  HELPER: URL base da API                                          //
// ------------------------------------------------------------------ //
export function getApiUrl(): string {
  return API_URL;
}
