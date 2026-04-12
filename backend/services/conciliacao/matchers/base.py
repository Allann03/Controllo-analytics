"""
matchers/base.py — Lógica base de reconciliação bancária.

Todos os matchers específicos por banco herdam desta classe e
sobrescrevem apenas o que for diferente para aquele banco.

Algoritmo de matching (por transação):
  1. Data: deve ser igual (ou dentro da tolerância em dias)
  2. Valor: deve ser igual dentro de ±TOLERANCIA_VALOR (arredondamento)
  3. Tipo: entrada vs saída (normalizado, ignora acentos e capitalização)

Quando um match é encontrado, aquela transação do Excel é marcada
como "usada" e não pode ser usada novamente (matching 1:1).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional


class MatcherBase:
    """
    Reconcilia transações de PDF vs transações de Excel.
    Produz relatório com divergências, linha Excel e diferenças de valor.
    """

    TOLERANCIA_VALOR = Decimal('0.02')   # R$ — cobre erros de arredondamento de centavos
    TOLERANCIA_DIAS  = 0      # dias — matching exato de data por padrão

    # ── Normalização ───────────────────────────────────────────────────

    @staticmethod
    def _tipo_norm(tipo: str) -> str:
        """Normaliza tipo de transação para 'entrada' ou 'saida'."""
        t = str(tipo).strip().lower()
        t = t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        if "entrada" in t or "credito" in t or "credit" in t or "recebido" in t:
            return "entrada"
        return "saida"

    @staticmethod
    def _data_parse(data: str) -> Optional[datetime]:
        """Converte string de data para datetime."""
        data = str(data).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%Y"):
            try:
                return datetime.strptime(data, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _data_fmt(dt: Optional[datetime]) -> str:
        return dt.strftime("%d/%m/%Y") if dt else ""

    # ── Matching de par ────────────────────────────────────────────────

    def _par(self, t_pdf: dict, t_xl: dict) -> bool:
        """Verifica se duas transações são o mesmo lançamento."""
        dt_pdf = self._data_parse(str(t_pdf.get("data", "")))
        dt_xl  = self._data_parse(str(t_xl.get("data", "")))
        if dt_pdf is None or dt_xl is None:
            return False
        if abs((dt_pdf - dt_xl).days) > self.TOLERANCIA_DIAS:
            return False

        try:
            v_pdf = Decimal(str(t_pdf.get("valor", 0)))
            v_xl  = Decimal(str(t_xl.get("valor", 0)))
        except Exception:
            return False
        if abs(v_pdf - v_xl) > self.TOLERANCIA_VALOR:
            return False

        if self._tipo_norm(str(t_pdf.get("tipo", ""))) != self._tipo_norm(str(t_xl.get("tipo", ""))):
            return False

        return True

    # ── Reconciliação principal ────────────────────────────────────────

    def reconciliar(self, transacoes_pdf: list[dict], transacoes_excel: list[dict]) -> dict:
        """
        Executa reconciliação completa e retorna relatório de divergências.

        Returns:
            {
              "totais_pdf":   { entradas, saidas, saldo, total }
              "totais_excel": { entradas, saidas, saldo, total } | None
              "diferenca":    { entradas, saidas, saldo } | None
              "conciliados":  int
              "apenas_pdf":   int
              "apenas_excel": int
              "transacoes":   list[dict com status, linha_excel, diffs]
            }
        """
        pool_excel  = list(enumerate(transacoes_excel))
        matched_xl: set[int] = set()

        transacoes_resultado: list[dict] = []

        for pdf_idx, t_pdf in enumerate(transacoes_pdf):
            melhor: Optional[int] = None

            for xl_idx, t_xl in pool_excel:
                if xl_idx in matched_xl:
                    continue
                if self._par(t_pdf, t_xl):
                    melhor = xl_idx
                    break

            if melhor is not None:
                matched_xl.add(melhor)
                t_xl        = transacoes_excel[melhor]
                linha_excel = t_xl.get("linha_excel", melhor + 2)
                v_pdf = float(t_pdf.get("valor", 0))
                v_xl  = float(t_xl.get("valor", 0))
                transacoes_resultado.append({
                    "status":          "conciliado",
                    "linha_excel":     linha_excel,
                    "data":            self._data_fmt(self._data_parse(str(t_pdf.get("data", "")))),
                    "descricao_pdf":   t_pdf.get("descricao", ""),
                    "descricao_excel": t_xl.get("descricao", ""),
                    "valor_pdf":       round(v_pdf, 2),
                    "valor_excel":     round(v_xl, 2),
                    "diff_valor":      round(v_pdf - v_xl, 2),
                    "tipo":            self._tipo_norm(str(t_pdf.get("tipo", ""))),
                    "banco":           t_pdf.get("banco", ""),
                    "categoria":       t_xl.get("categoria") or t_pdf.get("categoria", ""),
                })
            else:
                transacoes_resultado.append({
                    "status":          "apenas_pdf",
                    "linha_excel":     None,
                    "data":            self._data_fmt(self._data_parse(str(t_pdf.get("data", "")))),
                    "descricao_pdf":   t_pdf.get("descricao", ""),
                    "descricao_excel": None,
                    "valor_pdf":       round(float(t_pdf.get("valor", 0)), 2),
                    "valor_excel":     None,
                    "diff_valor":      None,
                    "tipo":            self._tipo_norm(str(t_pdf.get("tipo", ""))),
                    "banco":           t_pdf.get("banco", ""),
                    "categoria":       t_pdf.get("categoria", ""),
                })

        # Transações do Excel sem correspondência no PDF
        for xl_idx, t_xl in pool_excel:
            if xl_idx not in matched_xl:
                linha_excel = t_xl.get("linha_excel", xl_idx + 2)
                transacoes_resultado.append({
                    "status":          "apenas_excel",
                    "linha_excel":     linha_excel,
                    "data":            self._data_fmt(self._data_parse(str(t_xl.get("data", "")))),
                    "descricao_pdf":   None,
                    "descricao_excel": t_xl.get("descricao", ""),
                    "valor_pdf":       None,
                    "valor_excel":     round(float(t_xl.get("valor", 0)), 2),
                    "diff_valor":      None,
                    "tipo":            self._tipo_norm(str(t_xl.get("tipo", ""))),
                    "banco":           t_xl.get("banco", ""),
                    "categoria":       t_xl.get("categoria", ""),
                })

        # Ordenação cronológica
        transacoes_resultado.sort(key=lambda t: self._sort_key(t["data"]))

        # Totais
        ent_pdf  = sum(float(t.get("valor", 0)) for t in transacoes_pdf
                       if self._tipo_norm(str(t.get("tipo", ""))) == "entrada")
        said_pdf = sum(float(t.get("valor", 0)) for t in transacoes_pdf
                       if self._tipo_norm(str(t.get("tipo", ""))) == "saida")
        ent_xl   = sum(float(t.get("valor", 0)) for t in transacoes_excel
                       if self._tipo_norm(str(t.get("tipo", ""))) == "entrada")
        said_xl  = sum(float(t.get("valor", 0)) for t in transacoes_excel
                       if self._tipo_norm(str(t.get("tipo", ""))) == "saida")

        conciliados  = sum(1 for t in transacoes_resultado if t["status"] == "conciliado")
        apenas_pdf   = sum(1 for t in transacoes_resultado if t["status"] == "apenas_pdf")
        apenas_excel = sum(1 for t in transacoes_resultado if t["status"] == "apenas_excel")

        return {
            "totais_pdf": {
                "entradas": round(ent_pdf,  2),
                "saidas":   round(said_pdf, 2),
                "saldo":    round(ent_pdf - said_pdf, 2),
                "total":    len(transacoes_pdf),
            },
            "totais_excel": {
                "entradas": round(ent_xl,  2),
                "saidas":   round(said_xl, 2),
                "saldo":    round(ent_xl - said_xl, 2),
                "total":    len(transacoes_excel),
            } if transacoes_excel else None,
            "diferenca": {
                "entradas": round(ent_pdf - ent_xl, 2),
                "saidas":   round(said_pdf - said_xl, 2),
                "saldo":    round((ent_pdf - said_pdf) - (ent_xl - said_xl), 2),
            } if transacoes_excel else None,
            "conciliados":  conciliados,
            "apenas_pdf":   apenas_pdf,
            "apenas_excel": apenas_excel,
            "transacoes":   transacoes_resultado,
        }

    @staticmethod
    def _sort_key(data_str: str) -> tuple:
        try:
            p = str(data_str).split("/")
            return (int(p[2]), int(p[1]), int(p[0]))
        except Exception:
            return (0, 0, 0)
