"""
base.py – Classe abstrata base para todos os parsers de extrato bancário.
Cada banco herda de ParserBase e implementa o método extrair().

Pós-processamento duplo (obrigatório chamar ao final de extrair()):
  Passe 1 — Validação estrutural: valor > 0, descrição com texto, tipo válido.
  Passe 2 — Validação de data: formato DD/MM/YYYY com valores razoáveis.

Nota: deduplicação foi removida pois causava descarte de transações legítimas
idênticas (ex: dois Pix do mesmo valor para o mesmo destinatário no mesmo dia).
Se necessário, deduplicação deve ocorrer na camada de banco de dados.
"""

from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Optional
import re

# Padrões de linhas que são SALDO informativo, não transação
_PADROES_SALDO = [
    re.compile(r'(?i)saldo\s*(do\s*dia|final|anterior|total|disponivel|bloqueado|parcial)'),
    re.compile(r'(?i)s\.?\s*anterior'),
    re.compile(r'(?i)sdo\.?\s*(ant|dia|final)'),
    re.compile(r'(?i)saldo\s*em\s*\d{2}[/.\-]\d{2}'),
    re.compile(r'(?i)^saldo$'),
    re.compile(r'(?i)s\s+a\s+l\s+d\s+o'),          # BB espaçado
    re.compile(r'(?i)saldo\s+total\s+dispon'),       # Itaú
    re.compile(r'(?i)saldo\s+c/?c'),                 # saldo conta corrente
]


# Regex global para extrair valores monetários BR do raw
_RE_VALOR_BR_GLOB = re.compile(r'((?:\d{1,3}\.)*\d{1,3},\d{2})')
# Data válida: DD/MM/YYYY
_RE_DATA_VALIDA = re.compile(r'^\d{2}/\d{2}/\d{4}$')


class ParserBase(ABC):
    """Classe base para parsers de extratos bancários."""

    def __init__(self, pdf_path: str, password: str | None = None) -> None:
        self.pdf_path = pdf_path
        self.password = password
        self.avisos: list[str] = []

    @abstractmethod
    def extrair(self) -> list[dict]:
        """
        Extrai todas as transações do PDF.

        Returns:
            Lista de dicts com as chaves:
            data, descricao, valor, tipo, categoria, banco, raw
        """
        ...

    # ------------------------------------------------------------------ #
    # Helpers compartilhados por todos os parsers                         #
    # ------------------------------------------------------------------ #

    def _normalizar_valor(self, texto: str) -> Decimal:
        """
        Converte string monetária brasileira em Decimal positivo.

        Exemplos:
            'R$ 1.234,56'  -> Decimal('1234.56')
            '1.234,56-'    -> Decimal('1234.56')  (sinal tratado externamente)
            '-1.234,56'    -> Decimal('1234.56')
            '1234.56'      -> Decimal('1234.56')
        """
        if not texto:
            return Decimal('0')
        texto = str(texto).strip()
        # Remove prefixo monetário e espaços
        texto = re.sub(r'R\$\s*', '', texto)
        # Remove sinal negativo (tratado por quem chama)
        texto = texto.replace('-', '').strip()
        # Formato brasileiro: pontos como milhar, vírgula como decimal
        if ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        try:
            return abs(Decimal(texto))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0')

    def _normalizar_data(self, texto: str, ano_referencia: Optional[int] = None) -> str:
        """
        Normaliza datas para o formato DD/MM/AAAA.

        Aceita: 'DD/MM/AAAA', 'DD/MM/AA', 'DD/MM'
        """
        if not texto:
            return ''
        texto = str(texto).strip()
        partes = texto.split('/')
        if len(partes) == 3:
            dia, mes, ano = partes
            if len(ano) == 2:
                ano = f'20{ano}'
            return f'{dia.zfill(2)}/{mes.zfill(2)}/{ano}'
        if len(partes) == 2:
            dia, mes = partes
            ano = str(ano_referencia) if ano_referencia else str(datetime.now().year)
            return f'{dia.zfill(2)}/{mes.zfill(2)}/{ano}'
        return texto

    def _transacao(
        self,
        data: str,
        descricao: str,
        valor,
        tipo: str,
        banco: str,
        raw: str = '',
        **extras,
    ) -> dict:
        """Monta o dict padronizado de uma transação."""
        if not isinstance(valor, Decimal):
            valor = Decimal(str(valor))
        t = {
            'data': data,
            'descricao': descricao.strip(),
            'valor': round(valor, 2),
            'tipo': tipo,          # 'entrada' | 'saida' | 'ignorar' | 'posicao'
            'categoria': '',
            'banco': banco,
            'raw': raw,
        }
        t.update(extras)
        return t

    # ------------------------------------------------------------------ #
    # Detecção de linhas de saldo informativo                             #
    # ------------------------------------------------------------------ #

    def _is_linha_saldo(self, descricao: str) -> bool:
        """
        Verifica se a descrição é uma linha de saldo informativo (não transação).

        Protege contra transações legítimas que mencionam "saldo" em contexto
        diferente (ex: "TRANSFERENCIA SALDO CONTA") exigindo padrão específico.
        """
        if not descricao:
            return False
        for padrao in _PADROES_SALDO:
            if padrao.search(descricao):
                return True
        return False

    # ------------------------------------------------------------------ #
    # Pós-processamento triplo (chamar ao final de extrair())             #
    # ------------------------------------------------------------------ #

    def _validar_data(self, data: str) -> bool:
        """Valida se a data está no formato DD/MM/YYYY com valores razoáveis."""
        if not data:
            return False
        if not _RE_DATA_VALIDA.match(data):
            return False
        try:
            d, m, a = map(int, data.split('/'))
            return 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= a <= 2100
        except (ValueError, TypeError):
            return False

    def _reparse_valor_do_raw(self, raw: str) -> list[Decimal]:
        """
        Extrai TODOS os valores monetários BR presentes no raw string.
        Útil para verificação cruzada.
        """
        matches = _RE_VALOR_BR_GLOB.findall(raw)
        valores = []
        for m in matches:
            v = self._normalizar_valor(m)
            if v > 0:
                valores.append(round(v, 2))
        return valores

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """
        Extrai saldos intermediários ("Saldo do dia") do extrato para verificação progressiva.
        Retorna lista de dicts: [{data: "DD/MM/YYYY", saldo: Decimal}]
        Implementação padrão retorna lista vazia. Parsers que têm saldos do dia
        no extrato devem sobrescrever este método.
        """
        return []

    def _post_processar(self, transacoes: list[dict]) -> list[dict]:
        """
        Pós-processamento duplo de todas as transações extraídas.

        Passe 1 — Validação estrutural:
            • valor > 0 e < R$ 500 milhões por transação (sanity check)
            • descrição contém pelo menos uma letra
            • tipo é 'entrada', 'saida', 'posicao' ou 'ignorar'

        Passe 2 — Validação de data:
            • formato DD/MM/YYYY
            • dia 1-31, mês 1-12, ano 2000-2100

        Nota: deduplicação é responsabilidade da camada de banco de dados —
        dois Pix do mesmo valor para o mesmo destinatário no mesmo dia são
        transações legítimas e não devem ser descartadas aqui.
        """
        # ── Passe 0: filtrar linhas de saldo informativo ────────────
        p0: list[dict] = []
        for t in transacoes:
            if not t:
                continue
            desc = str(t.get('descricao') or '').strip()
            if self._is_linha_saldo(desc):
                self.avisos.append(
                    f'Linha de saldo informativo filtrada: "{desc[:60]}"'
                )
                continue
            p0.append(t)

        # ── Passe 1: validação estrutural ─────────────────────────────
        p1: list[dict] = []
        for t in p0:
            # Valor deve ser numérico e positivo
            valor = t.get('valor')
            if not isinstance(valor, (int, float, Decimal)) or valor <= 0:
                continue

            # Sanity check: nenhuma transação individual ultrapassa R$ 500 mi
            if valor > 500_000_000:
                self.avisos.append(
                    f'Valor fora do intervalo razoável ignorado: '
                    f'R$ {valor:,.2f} — {str(t.get("descricao",""))[:50]}'
                )
                continue

            # Descrição deve conter ao menos uma letra
            desc = str(t.get('descricao') or '').strip()
            if not desc or not re.search(r'[a-zA-ZÀ-ÿ]', desc):
                continue

            # Tipo deve ser válido
            if t.get('tipo') not in ('entrada', 'saida', 'posicao', 'ignorar'):
                continue

            p1.append(t)

        # ── Passe 2: validação de data ─────────────────────────────────
        p2: list[dict] = []
        for t in p1:
            data = str(t.get('data') or '')
            if data and not self._validar_data(data):
                self.avisos.append(
                    f'Data inválida ignorada: "{data}" — {str(t.get("descricao",""))[:40]}'
                )
                continue
            p2.append(t)

        return p2

    def _segunda_verificacao_valor(self, raw: str, valor) -> Decimal:
        """
        Segunda verificação de valor: re-extrai todos os valores BR da linha bruta
        e confirma que o valor extraído está entre eles.

        Se o valor não for confirmado, registra aviso mas mantém o valor original
        para não descartar transações por diferença de arredondamento.

        Returns:
            Valor confirmado (Decimal).
        """
        if not isinstance(valor, Decimal):
            valor = Decimal(str(valor))
        if not raw:
            return valor

        valores_no_raw = self._reparse_valor_do_raw(raw)
        if not valores_no_raw:
            return valor

        valor_rd = round(valor, 2)
        # Confirmado se diferença <= R$ 0,01 (arredondamento)
        for v in valores_no_raw:
            if abs(round(v, 2) - valor_rd) <= Decimal('0.01'):
                return valor  # confirmado

        # Não encontrado — pode ser raw composto (buffer multilinhas)
        # Não descarta, apenas registra
        self.avisos.append(
            f'Verificação dupla: valor R$ {valor:.2f} não confirmado no raw '
            f'(encontrados: {[round(v,2) for v in valores_no_raw[:3]]})'
        )
        return valor

    def _verificar_tipo_cruzado(
        self,
        tipo_por_sinal: str,
        descricao: str,
        palavras_entrada: list[str],
        palavras_saida: list[str] | None = None,
    ) -> str:
        """
        Verificação cruzada de tipo (entrada/saída) usando sinal E palavras-chave.

        Regra:
          • Se sinal e palavras concordam → retorna o tipo com confiança alta.
          • Se discordam → sinal tem prioridade (o sinal do banco é autoritário).
          • Se não há sinal → usa palavras-chave.
          • Default conservador: 'saida'.

        Args:
            tipo_por_sinal: 'entrada' | 'saida' | '' (desconhecido)
            descricao: texto da transação
            palavras_entrada: lista de substrings que indicam entrada
            palavras_saida: lista de substrings que indicam saída (opcional)

        Returns:
            'entrada' | 'saida'
        """
        desc_lower = descricao.lower()

        tem_entrada = any(p in desc_lower for p in palavras_entrada)
        tem_saida = (
            palavras_saida is not None
            and any(p in desc_lower for p in palavras_saida)
        )

        tipo_por_desc = ''
        if tem_entrada and not tem_saida:
            tipo_por_desc = 'entrada'
        elif tem_saida and not tem_entrada:
            tipo_por_desc = 'saida'

        # Sinal explícito tem prioridade absoluta
        if tipo_por_sinal in ('entrada', 'saida'):
            return tipo_por_sinal

        # Sem sinal: usa palavras-chave
        if tipo_por_desc:
            return tipo_por_desc

        # Default conservador
        return 'saida'
