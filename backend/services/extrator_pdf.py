"""
extrator_pdf.py – Orquestrador de parsers de extratos bancários.

Detecta o banco pelo conteúdo do PDF (primeiras 3 páginas) e
delega a extração ao parser específico.

Ponto de entrada para main.py: extrair_extrato(pdf_path)
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation
import pdfplumber

# Limite de páginas por PDF processado (protege contra PDFs muito grandes)
MAX_PAGINAS_PDF = 500


def _parse_valor_br(texto: str) -> Decimal | None:
    """Converte '1.234,56' ou '1234,56' em Decimal. Retorna None se inválido."""
    if not texto:
        return None
    texto = texto.strip().replace(' ', '')
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    try:
        v = abs(Decimal(texto))
        return v if v < 100_000_000 else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _extrair_saldos_pdf(pdf_path: str, banco_key: str = '', password: str | None = None) -> tuple[Decimal | None, Decimal | None]:
    """
    Extrai saldo_inicial e saldo_final do PDF com lógica específica por banco.
    Retorna (saldo_inicial, saldo_final).
    """

    def _ultimo_num(linha: str) -> Decimal | None:
        """Último número BR na linha."""
        m = re.search(r'([\d.,]+)\s*[CD]?\s*$', linha.strip())
        return _parse_valor_br(m.group(1)) if m else None

    def _r_num(linha: str) -> Decimal | None:
        """Valor após 'R$' na linha; fallback = último número."""
        m = re.search(r'[Rr]\$\s*([\d.,]+)', linha)
        return _parse_valor_br(m.group(1)) if m else _ultimo_num(linha)

    try:
        with pdfplumber.open(pdf_path, password=password or '') as pdf:
            texto_total = ''
            for pagina in pdf.pages:
                try:
                    texto_total += (pagina.extract_text() or '') + '\n'
                except Exception:
                    pass
    except Exception:
        return None, None

    # Sessao 20: PDFs vetoriais (Inter via Microsoft Print To PDF) → 0 chars.
    # Cair no OCR fallback. Cache evita custo repetido.
    if len(texto_total.strip()) < 50:
        from .ocr_fallback import extrair_texto_via_ocr
        texto_total = extrair_texto_via_ocr(pdf_path, senha=password)

    linhas = texto_total.splitlines()
    banco = banco_key.lower()
    ini: Decimal | None = None
    fim: Decimal | None = None

    # ─── Nubank ──────────────────────────────────────────────────────────────
    # "Saldo inicial\n422,94" e "Saldo final do período\n51,83" (valor na próxima linha)
    if banco == 'nubank':
        m = re.search(r'saldo\s+final\s+do\s+per[ií]odo\s*\n\s*([\d.,]+)',
                      texto_total, re.IGNORECASE)
        if m:
            fim = _parse_valor_br(m.group(1))
        m = re.search(r'saldo\s+inicial\s*\n\s*([\d.,]+)',
                      texto_total, re.IGNORECASE)
        if m:
            ini = _parse_valor_br(m.group(1))
        # Fallback inline (alguns PDFs Nubank têm na mesma linha)
        for linha in linhas:
            ll = linha.lower()
            if ini is None and 'saldo inicial' in ll:
                v = _ultimo_num(linha)
                if v is not None:
                    ini = v
            if fim is None and 'saldo final' in ll:
                v = _ultimo_num(linha)
                if v is not None:
                    fim = v
        return ini, fim

    # ─── Itaú (PF) ───────────────────────────────────────────────────────────
    # ini: "Saldo anterior 1.234,56" (primeira ocorrência)
    # fim: "SALDO TOTAL DISPONÍVEL DIA X" (último) ou "Saldo em DD/mmm X" ou "Saldo final X"
    # Fallback fim: fim_candidato = último "saldo anterior" de página
    if banco == 'itau':
        _re_ant   = re.compile(r'saldo\s+anterior\s+([\d.,]+)', re.IGNORECASE)
        # "DISPON#VEL" = encoding issue no PDF onde Í → #; \S* aceita qualquer variante
        _re_std   = re.compile(r'saldo\s+total\s+dispon\S*\s+dia\s+([\d.,]+)', re.IGNORECASE)
        _re_em    = re.compile(r'saldo\s+em\s+\d{2}[/\s]\w+\s+([\d.,]+)', re.IGNORECASE)
        _re_sf    = re.compile(r'saldo\s+final(?:\s+do\s+per[ií]odo)?\s+([\d.,]+)', re.IGNORECASE)
        _re_sal   = re.compile(r's\s+a\s+l\s+d\s+o\s+([\d.,]+)', re.IGNORECASE)
        fim_candidato: Decimal | None = None
        for linha in linhas:
            m = _re_ant.search(linha)
            if m:
                v = _parse_valor_br(m.group(1))
                if v is not None:
                    if ini is None:
                        ini = v
                    fim_candidato = v
            for pat in (_re_std, _re_em, _re_sf, _re_sal):
                m = pat.search(linha)
                if m:
                    v = _parse_valor_br(m.group(1))
                    if v is not None:
                        fim = v
        if fim is None:
            fim = fim_candidato
        return ini, fim

    # ─── Itaú Empresas (PJ) ──────────────────────────────────────────────────
    # ini: "Saldo anterior X" (primeira ocorrência)
    # fim: "Saldo final X" (última ocorrência) — aparece explicitamente no extrato PJ
    # Fallback: "Saldo em C/C X" ou último "SALDO APLIC AUT MAIS" (aproximação)
    if banco == 'itau_empresas':
        _re_ant_pj = re.compile(r'saldo\s+anterior\s+([\d.,]+)', re.IGNORECASE)
        _re_sf_pj  = re.compile(r'saldo\s+final\s+([\d.,]+)', re.IGNORECASE)
        _re_cc_pj  = re.compile(r'saldo\s+em\s+c/c\s+([\d.,]+)', re.IGNORECASE)
        for linha in linhas:
            m = _re_ant_pj.search(linha)
            if m:
                v = _parse_valor_br(m.group(1))
                if v is not None and ini is None:
                    ini = v
            for pat in (_re_sf_pj, _re_cc_pj):
                m = pat.search(linha)
                if m:
                    v = _parse_valor_br(m.group(1))
                    if v is not None:
                        fim = v
        return ini, fim

    # ─── Bradesco ────────────────────────────────────────────────────────────
    # ini: "SALDO ANTERIOR X" (primeira ocorrência)
    # fim: PRIMEIRA linha "Total X -Y Z" — o terceiro valor (Z) é o saldo final
    #      do período principal. Ignora seções "Últimos Lançamentos" e
    #      "Saldos Invest Fácil" que são pós-período.
    # Fallback fim: "Saldo final X" se explícito.
    if banco == 'bradesco':
        _re_bra_total = re.compile(
            r'^total\s+[\d.,]+\s+[-]?[\d.,]+\s+([\d.,]+)\s*$',
            re.IGNORECASE
        )
        _bra_stop = False
        for linha in linhas:
            ll = linha.lower()
            # Para ao encontrar seções pós-período
            if any(m in ll for m in ('últimos lançamentos', 'ultimos lancamentos',
                                      'os dados acima', 'saldos invest')):
                _bra_stop = True
            if _bra_stop:
                continue
            if ini is None and ('saldo anterior' in ll or 'saldo inicial' in ll):
                v = _ultimo_num(linha)
                if v is not None:
                    ini = v
            m = _re_bra_total.match(linha.strip())
            if m:
                v = _parse_valor_br(m.group(1))
                if v is not None:
                    fim = v
                continue
            if 'saldo final' in ll:
                v = _ultimo_num(linha)
                if v is not None:
                    fim = v
        return ini, fim

    # ─── Banco do Brasil ─────────────────────────────────────────────────────
    # Formato: "Saldo Anterior 1.141,05 (-)" com (+) ou (-) no final
    # Saldo do Dia: "NNNNN Saldo do dia 647,87 (-)"
    if banco == 'bb':
        _re_bb_val = re.compile(r'([\d]+(?:\.[\d]{3})*,\d{2})')  # valor BR
        for linha in linhas:
            ll = linha.lower()
            if ini is None and 'saldo anterior' in ll:
                m = _re_bb_val.search(linha)
                if m:
                    ini = _parse_valor_br(m.group(1))
            if 'saldo do dia' in ll or 'saldo em' in ll:
                m = _re_bb_val.search(linha)
                if m:
                    fim = _parse_valor_br(m.group(1))
        return ini, fim

    # ─── Inter ───────────────────────────────────────────────────────────────
    # Formato real: "N de Mês de AAAA Saldo do dia: R$ X,XX Valor Saldo por transação"
    # Primeiro "Saldo do dia" = ini; último = fim.
    # Fallback: "Saldo inicial R$ X" e "Saldo final R$ X" (formatos alternativos).
    if banco in ('inter', 'inter_n2'):
        _re_dia_inter = re.compile(r'saldo\s+do\s+dia:\s*(?:-?R\$\s*)?([\d.,]+)', re.IGNORECASE)
        for linha in linhas:
            ll = linha.lower()
            # "Saldo total" é cabeçalho de resumo — ignorar
            if 'saldo total' in ll:
                continue
            m = _re_dia_inter.search(linha)
            if m:
                v = _parse_valor_br(m.group(1))
                # Sessao 20: aceitar saldos zero ("Saldo do dia: R$ 0,00") —
                # contas Inter zeram com aplicacoes automaticas, similar ao
                # mecanismo ContaMax do Santander. Pular zero descartava o SI
                # legitimo do extrato_ABRIL.pdf (16/01/2026 começa em 0,00).
                if v is not None:
                    if ini is None:
                        ini = v
                    fim = v
                continue
            if ini is None and 'saldo inicial' in ll:
                v = _r_num(linha)
                if v is not None:
                    ini = v
            if 'saldo final' in ll and 'saldo final do' not in ll:
                v = _r_num(linha)
                if v is not None:
                    fim = v
        return ini, fim

    # ─── Cora ────────────────────────────────────────────────────────────────
    # "DD/MM/YYYY Saldo do dia R$ X" por dia; "Saldo inicial" / "Saldo final" explícito
    if banco == 'cora':
        _re_dia = re.compile(
            r'\d{2}/\d{2}/\d{4}\s+saldo\s+do\s+dia\s+[Rr]\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        for linha in linhas:
            ll = linha.lower()
            if ini is None and 'saldo inicial' in ll:
                v = _r_num(linha)
                if v is not None:
                    ini = v
            if 'saldo final' in ll:
                v = _r_num(linha)
                if v is not None:
                    fim = v
            m = _re_dia.search(linha)
            if m:
                v = _parse_valor_br(m.group(1))
                if v is not None:
                    if ini is None:
                        ini = v
                    fim = v
        return ini, fim

    # ─── Caixa ───────────────────────────────────────────────────────────────
    # ini: "SALDO ANTERIOR R$ X" ou "Saldo anterior ao período R$ X"
    # fim: "SALDO DIA R$ X C" (sem "do"), "Saldo do Dia R$ X" ou "Saldo final R$ X"
    #      "SALDO EM CONTA CORRENTE X" → fim alternativo
    if banco == 'caixa':
        for linha in linhas:
            ll = linha.lower()
            if ini is None and ('saldo anterior' in ll or 'saldo inicial' in ll):
                v = _r_num(linha) or _ultimo_num(linha)
                if v is not None:
                    ini = v
            # "SALDO DIA" (sem "do") ou "SALDO DO DIA" ou "SALDO FINAL" ou "SALDO EM CONTA"
            if ('saldo dia' in ll or 'saldo do dia' in ll
                    or 'saldo final' in ll or 'saldo em conta' in ll):
                v = _r_num(linha) or _ultimo_num(linha)
                if v is not None:
                    fim = v
        return ini, fim

    # ─── Sicredi ─────────────────────────────────────────────────────────────
    # Tabela com coluna Saldo; linhas de texto: "Saldo anterior X" e "Saldo do dia X"
    if banco == 'sicredi':
        for linha in linhas:
            ll = linha.lower()
            if ini is None and ('saldo anterior' in ll or 'saldo inicial' in ll):
                v = _ultimo_num(linha)
                if v is not None:
                    ini = v
            if 'saldo final' in ll or 'saldo do dia' in ll:
                v = _ultimo_num(linha)
                if v is not None:
                    fim = v
        return ini, fim

    # ─── Stone ───────────────────────────────────────────────────────────────
    # Formato Stone: transações com coluna SALDO. Último saldo = SF.
    # SI não é extraível de forma confiável (saldo na coluna é pós-transação).
    if banco == 'stone':
        _re_n1 = re.compile(
            r'^\d{2}/\d{2}/\d{2,4}\s+(?:Entrada|Sa[ií]da).*[Rr]\$\s*([\d.,]+)\s*$',
            re.IGNORECASE
        )
        _re_n2 = re.compile(
            r'^\d{2}/\d{2}/\d{2,4}\s+(?:Cr[eé]dito|D[eé]bito).*\s+([\d.]+,\d{2})\s*$',
            re.IGNORECASE
        )
        for linha in linhas:
            for rx in (_re_n1, _re_n2):
                m = rx.search(linha)
                if m:
                    v = _parse_valor_br(m.group(1))
                    if v is not None:
                        fim = v
                    break
        return ini, fim

    # ─── C6Bank ──────────────────────────────────────────────────────────────
    # "Saldo do dia DD/MM/YY R$ X,XX" aparece por dia; primeiro = ini, último = fim.
    # Ignora a linha de cabeçalho "Saldo do dia → 3 de janeiro → R$ X" (usa setas →).
    if banco == 'c6bank':
        _re_c6_dia = re.compile(
            r'saldo\s+do\s+dia\s+\d{2}/\d{2}/?\d{0,4}\s+R\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        for linha in linhas:
            if 'saldo do dia' not in linha.lower():
                continue
            # Pula linhas de cabeçalho que usam bullet (•, \u2022) como separador
            # Ex: "Saldo do dia • 3 de janeiro de 2026 • R$ 4.813,94"
            if '\u2022' in linha or '\u2192' in linha:
                continue
            m = _re_c6_dia.search(linha)
            if m:
                v = _parse_valor_br(m.group(1))
            else:
                v = _r_num(linha) or _ultimo_num(linha)
            if v is not None:
                if ini is None:
                    ini = v
                fim = v
        return ini, fim

    # ─── PagBank ─────────────────────────────────────────────────────────────
    # "Saldo do dia" no PagBank é saldo de FECHAMENTO (após tx do dia).
    # NÃO usar como ini — o primeiro "Saldo do dia" NÃO é o saldo de abertura.
    # O parser injeta saldo fantasma (dia anterior) nos intermediários para que
    # o fallback do orquestrador use o SI correto.
    if banco == 'pagbank':
        _re_pgb_dia = re.compile(
            r'\d{2}/\d{2}/\d{4}\s+saldo\s+do\s+dia\s+R\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        for linha in linhas:
            ll = linha.lower()
            m = _re_pgb_dia.search(linha)
            if m:
                v = _parse_valor_br(m.group(1))
                if v is not None:
                    fim = v
                continue
            if 'saldo final' in ll:
                v = _r_num(linha)
                if v is not None:
                    fim = v
        return ini, fim

    # ─── Mercado Pago ────────────────────────────────────────────────────────
    # "Saldo inicial: R$ X,XX Saldo final: R$ X,XX" podem estar na MESMA linha.
    # Usa regex específico para extrair cada valor pelo rótulo correto.
    if banco == 'mercado_pago':
        _re_mp_ini = re.compile(r'saldo\s+inicial[:\s]+R?\$?\s*([\d.,]+)', re.IGNORECASE)
        _re_mp_fim = re.compile(r'saldo\s+final[:\s]+R?\$?\s*([\d.,]+)', re.IGNORECASE)
        for linha in linhas:
            if ini is None:
                m = _re_mp_ini.search(linha)
                if m:
                    v = _parse_valor_br(m.group(1))
                    if v is not None:
                        ini = v
            m = _re_mp_fim.search(linha)
            if m:
                v = _parse_valor_br(m.group(1))
                if v is not None:
                    fim = v
        return ini, fim

    # ─── BS2 ─────────────────────────────────────────────────────────────────
    # "Saldo Inicial  R$ X,XX" e "Saldo Final  R$ X,XX" (mesma linha ou próxima)
    if banco == 'bs2':
        for linha in linhas:
            ll = linha.lower()
            if ini is None and 'saldo inicial' in ll:
                v = _r_num(linha) or _ultimo_num(linha)
                if v is not None:
                    ini = v
            if 'saldo final' in ll:
                v = _r_num(linha) or _ultimo_num(linha)
                if v is not None:
                    fim = v
        return ini, fim

    # ─── BTG Pactual ───────────────────────────────────────────────────────
    # Layout BTG: "Saldo de abertura em DD/MM/YYYY:Saldo de fechamento em DD/MM/YYYY:"
    # seguido por: "R$ 32.837,65 R$ 0,00" (ambos valores na MESMA linha seguinte)
    if banco == 'btg':
        _re_btg_vals = re.compile(
            r'R\$\s*([\d.,]+)\s+R\$\s*([\d.,]+)', re.IGNORECASE
        )
        for i_l, linha in enumerate(linhas):
            ll = linha.lower()
            if 'saldo de abertura' in ll and 'saldo de fechamento' in ll:
                # Ambos rótulos na mesma linha — valores na próxima
                if i_l + 1 < len(linhas):
                    m = _re_btg_vals.search(linhas[i_l + 1])
                    if m:
                        ini = _parse_valor_br(m.group(1))
                        fim = _parse_valor_br(m.group(2))
                        return ini, fim
            # Fallback: rótulos em linhas separadas
            if ini is None and 'saldo de abertura' in ll:
                m = re.search(r'R\$\s*([\d.,]+)', linha, re.IGNORECASE)
                if m:
                    ini = _parse_valor_br(m.group(1))
                elif i_l + 1 < len(linhas):
                    v = _r_num(linhas[i_l + 1])
                    if v is not None:
                        ini = v
            if 'saldo de fechamento' in ll:
                m = re.search(r'R\$\s*([\d.,]+)', linha, re.IGNORECASE)
                if m:
                    fim = _parse_valor_br(m.group(1))
                elif i_l + 1 < len(linhas):
                    v = _r_num(linhas[i_l + 1])
                    if v is not None:
                        fim = v
        return ini, fim

    # ─── Santander IB Novo (Internet Banking Empresarial layout NOVO) ───────
    # Sessão 19 — extrato não expõe "Saldo Anterior"/"Saldo Final" nominais;
    # apenas linhas "DD/MM/YYYY Saldo do dia R$ X,XX" — saldo de FECHAMENTO
    # de cada dia. Convenção:
    #   SI (do período) = "Saldo do dia" do dia mais ANTIGO (menor data)
    #   SF (do período) = "Saldo do dia" do dia mais RECENTE (maior data)
    # Tradeoff: SI assim é tecnicamente o saldo de fechamento de D_min (não
    # saldo de abertura do período). A equação SI+E-S=SF então só bate
    # exatamente quando net_tx(D_min)=0 (caso típico do padrão "contamax
    # com resgate automático" em que a conta corrente fica zerada e cada
    # dia tem aplicação compensando movimentos). Em PDFs reais auditados
    # (VILA PET, IB N2 e IB N3) essa condição se cumpre — gap=0. Em casos
    # onde net_tx(D_min) != 0, o validador da Sessão 18 detecta via Check 1.
    if banco == 'santander_ib_novo':
        from datetime import datetime as _dt
        _re_ibn_dia = re.compile(
            r'^\s*(\d{2}/\d{2}/\d{4})\s+Saldo\s+do\s+dia\s+R\$\s*([\d.]+,\d{2})',
            re.IGNORECASE,
        )
        # Strip de glifos da Private Use Area (bullet do Wingdings) para que
        # o anchor `^` case mesmo se a linha começar com U+F12E/U+F131.
        def _strip_pua_local(s: str) -> str:
            return ''.join(ch for ch in s if not (0xF000 <= ord(ch) <= 0xF999))

        saldos_dia: list[tuple[_dt, Decimal]] = []
        for linha in linhas:
            limpa = _strip_pua_local(linha).lstrip()
            m = _re_ibn_dia.match(limpa)
            if not m:
                continue
            try:
                dt = _dt.strptime(m.group(1), '%d/%m/%Y')
            except ValueError:
                continue
            v = _parse_valor_br(m.group(2))
            if v is None:
                continue
            saldos_dia.append((dt, v))

        if saldos_dia:
            saldos_dia.sort(key=lambda x: x[0])
            ini = saldos_dia[0][1]
            fim = saldos_dia[-1][1]

        try:
            si_log = f'{float(ini):.2f}' if ini is not None else 'None'
            sf_log = f'{float(fim):.2f}' if fim is not None else 'None'
            print(
                f'[EXTRATOR-SALDOS] banco=santander_ib_novo '
                f'si={si_log} sf={sf_log} '
                f'dias_com_saldo={len(saldos_dia)}'
            )
        except Exception:
            pass

        return ini, fim

    # ─── Santander Empresas: reutiliza lógica do Santander genérico ─────────
    if banco == 'santander_empresas':
        # Internet Banking Empresarial não expõe saldo do período de forma padronizada
        return None, None

    # ─── Bradesco Net Empresas ──────────────────────────────────────────────
    # Sessão 16: branch específica para preservar sinal negativo em SALDO ANTERIOR
    # (caso CW TOUR EIRELI jan/2026, onde fallback genérico via _ultimo_num
    # descartava o '-' e produzia SI=918.38 em vez de -918.38).
    #
    # Hipótese D: SF depende do formato do cabeçalho:
    #   - Cabeçalho com coluna "Investimento sem Baixa" (3 valores na linha
    #     "Ag|Conta") → SF = ÚLTIMO Total da seção principal (antes de
    #     "Últimos Lançamentos"). Caso SEOLIN jan/2025: cabeçalho reflete
    #     saldo de hoje + investimentos, não o saldo do fim do período.
    #   - Cabeçalho com 2 valores → SF = primeiro valor da linha "Ag|Conta"
    #     (Total Disponível). Casos CW TOUR, TANIA nov/dez.
    if banco == 'bradesco_net_empresas':
        def _parse_br_signed(s: str) -> Decimal | None:
            """Converte '1.234,56' ou '-918,38' preservando sinal."""
            if not s:
                return None
            s = s.strip().replace(' ', '')
            negativo = s.startswith('-')
            if negativo:
                s = s[1:]
            if ',' in s:
                s = s.replace('.', '').replace(',', '.')
            try:
                v = Decimal(s)
                return -v if negativo else v
            except (InvalidOperation, ValueError, TypeError):
                return None

        # SI: primeira ocorrência de "[DD/MM/YYYY] SALDO ANTERIOR <valor>"
        # com sinal preservado. PRIMEIRA = início do período pedido (não a
        # da seção "Últimos Lançamentos", que usa SI = saldo final do período).
        _re_bne_si = re.compile(
            r'(?:\d{2}/\d{2}/\d{4}\s+)?SALDO\s+ANTERIOR\s+(-?\d[\d.]*,\d{2})',
            re.IGNORECASE,
        )
        # Linha do cabeçalho "Ag|Conta" pode ter 2 ou 3 valores numéricos.
        _re_bne_cab = re.compile(
            r'^\d{4,5}\s*\|\s*\d{6,8}-\d\s+(-?\d[\d.]*,\d{2})'
            r'(?:\s+(-?\d[\d.]*,\d{2}))?'
            r'(?:\s+(-?\d[\d.]*,\d{2}))?\s*$'
        )
        # "Total <crédito> <débito> <saldo>" — pega o terceiro valor (saldo)
        _re_bne_total = re.compile(
            r'^total\s+-?\d[\d.,]*\s+-?\d[\d.,]*\s+(-?\d[\d.]*,\d{2})\s*$',
            re.IGNORECASE,
        )

        # Detecta presença de coluna "Investimento" no cabeçalho.
        tem_investimento = bool(
            re.search(r'investiment[oa]s?\s+(sem|com)\s+baixa', texto_total, re.IGNORECASE)
        )
        # Sessão 18 — heurística de SF estendida para Bradesco com 'Últimos
        # Lançamentos' / 'Saldos Invest Fácil' (caso CW TOUR jan/2026, TANIA
        # nov/dez 2025, Agosto 2025). Quando o PDF tem essas seções pós-período,
        # o cabeçalho `Ag|Conta` reflete o saldo APÓS a seção pós-período, não
        # o saldo do fim do período pedido. SF correto = último Total da
        # seção principal (antes do marcador). Sem esses marcadores, mantém a
        # regra original da Sessão 16 (cabeçalho).
        _tlow = texto_total.lower()
        tem_ultimos_lancamentos = (
            'últimos lançamentos' in _tlow or 'ultimos lancamentos' in _tlow
        )
        tem_saldos_invest = (
            'saldos invest fácil' in _tlow or 'saldos invest facil' in _tlow
        )

        # Captura SI (primeira ocorrência).
        for linha in linhas:
            m = _re_bne_si.search(linha)
            if m:
                v = _parse_br_signed(m.group(1))
                if v is not None:
                    ini = v
                    break

        # Sessão 18 — escolha do ramo de SF (4 valores possíveis para regra_sf).
        regra_sf = None  # será preenchida abaixo

        # Ramo 1 — coluna "Investimento" no cabeçalho (Sessão 16 / SEOLIN):
        # SF = último Total da seção principal antes de "Últimos Lançamentos".
        # Ramo 2 — Sessão 18 — sem coluna Investimento mas COM "Últimos
        # Lançamentos": SF = último Total da seção principal antes do marcador.
        # Ramo 3 — Sessão 18 — sem "Últimos Lançamentos" mas COM "Saldos
        # Invest Fácil": SF = último Total antes desse marcador.
        # Ramo 4 — fallback (CW TOUR-like sem nenhum desses): SF = primeiro
        # valor da linha "Ag|Conta" (Total Disponível). Caso raro pós-Sessão 18.
        usar_total_secao_principal = (
            tem_investimento or tem_ultimos_lancamentos or tem_saldos_invest
        )

        if not usar_total_secao_principal:
            # Ramo 4 — Total Disponível do cabeçalho (mantido só quando o PDF
            # NÃO tem nenhum marcador de seção pós-período).
            for linha in linhas:
                m = _re_bne_cab.match(linha.strip())
                if m:
                    v = _parse_br_signed(m.group(1))
                    if v is not None:
                        fim = v
                        regra_sf = 'cabecalho_total_disponivel'
                        break

        if fim is None:
            # Ramos 1/2/3 — SF = ÚLTIMO Total ANTES de qualquer marcador
            # pós-período (Últimos Lançamentos OU Saldos Invest Fácil).
            stop = False
            for linha in linhas:
                ll = linha.lower()
                if (
                    'últimos lançamentos' in ll or 'ultimos lancamentos' in ll
                    or 'saldos invest fácil' in ll or 'saldos invest facil' in ll
                ):
                    stop = True
                if stop:
                    continue
                m = _re_bne_total.match(linha.strip())
                if m:
                    v = _parse_br_signed(m.group(1))
                    if v is not None:
                        fim = v
            # Define regra_sf de acordo com o gatilho mais específico que se
            # aplicou (precedência: investimento > últimos lançamentos > invest fácil).
            if regra_sf is None:
                if tem_investimento:
                    regra_sf = 'ultimo_total_secao_principal_por_coluna_investimento'
                elif tem_ultimos_lancamentos:
                    regra_sf = 'ultimo_total_secao_principal_por_ultimos_lancamentos'
                elif tem_saldos_invest:
                    regra_sf = 'ultimo_total_secao_principal_por_saldos_invest_facil'
                else:
                    # Caso o cabeçalho não case e nenhum marcador presente —
                    # caiu aqui via fim==None apenas se o regex de cabeçalho falhou.
                    regra_sf = 'ultimo_total_secao_principal'

        try:
            si_log = f"{float(ini):.2f}" if ini is not None else "None"
            sf_log = f"{float(fim):.2f}" if fim is not None else "None"
            print(
                f"[EXTRATOR-SALDOS] banco=bradesco_net_empresas "
                f"si={si_log} sf={sf_log} "
                f"regra_sf={regra_sf} "
                f"tem_coluna_investimento={tem_investimento} "
                f"tem_ultimos_lancamentos={tem_ultimos_lancamentos} "
                f"tem_saldos_invest_facil={tem_saldos_invest}"
            )
        except Exception:
            pass

        return ini, fim

    # ─── Bradesco Net Empresas (alias legado): mesma lógica do Bradesco ─────
    if banco == 'bradesco_empresas':
        banco = 'bradesco'
        # re-executa o bloco Bradesco acima reutilizando o fallback genérico abaixo

    # ─── Santander PF/PJ ────────────────────────────────────────────────────
    # SI: "SALDO ANTERIOR X" (primeira ocorrência nas transações)
    # SF: "SALDO FINAL X" ou "SALDO ATUAL X" (NÃO usar "Saldo disponível" — é saldo corrente, não do período)
    if banco == 'santander':
        for linha in linhas:
            ll = linha.lower()
            if ini is None and 'saldo anterior' in ll:
                v = _ultimo_num(linha)
                if v is not None:
                    ini = v
            if 'saldo final' in ll or 'saldo atual' in ll:
                v = _r_num(linha) or _ultimo_num(linha)
                if v is not None:
                    fim = v

        # Sessão 19, Iter 3 — Fallbacks para variantes legacy sem
        # "SALDO ANTERIOR"/"SALDO FINAL" nominais.
        #
        # Fallback A — "DD/MM/YYYY Saldo do dia [...] R$ valor" por dia
        # (caso "santander problema.pdf" KKS PROMOCOES — IB Empresarial
        # com "Saldo do dia Cc + ContaMax principal R$"). Mesma convenção
        # da Iter 1: SI = saldo do dia mais antigo, SF = saldo do dia
        # mais recente. Ativa só se ini/fim ainda None.
        if ini is None and fim is None:
            from datetime import datetime as _dt
            _re_sant_saldo_dia = re.compile(
                r'^\s*(\d{2}/\d{2}/\d{4})\s+Saldo\s+do\s+dia\b.*?R\$\s*([\d.]+,\d{2})',
                re.IGNORECASE,
            )
            saldos_dia: list[tuple[_dt, Decimal]] = []
            for linha in linhas:
                m = _re_sant_saldo_dia.match(linha.lstrip())
                if not m:
                    continue
                try:
                    dt = _dt.strptime(m.group(1), '%d/%m/%Y')
                except ValueError:
                    continue
                v = _parse_valor_br(m.group(2))
                if v is None:
                    continue
                saldos_dia.append((dt, v))
            if saldos_dia:
                saldos_dia.sort(key=lambda x: x[0])
                d_min_dt, saldo_d_min = saldos_dia[0]
                _, saldo_d_max = saldos_dia[-1]
                fim = saldo_d_max

                # Sessão 19, Iter 3 — Ajuste do SI: o "Saldo do dia D_min" é
                # saldo de FECHAMENTO de D_min, não de abertura do período.
                # Para gap=0: SI_periodo = saldo_dia(D_min) - net_tx(D_min).
                # Reparseamos tx do D_min localmente (formato KKS:
                # "DD/MM/YYYY <desc> [- ]R$ valor"). Ignora linhas "Saldo do
                # dia" para evitar contar saldo como tx.
                d_min_str = d_min_dt.strftime('%d/%m/%Y')
                _re_kks_tx = re.compile(
                    r'^\s*' + re.escape(d_min_str) +
                    r'\s+(.+?)(\s+-)?\s+R\$\s*([\d.]+,\d{2})\s*$',
                    re.IGNORECASE,
                )
                net_d_min = Decimal('0')
                tx_d_min_count = 0
                for linha in linhas:
                    m = _re_kks_tx.match(linha)
                    if not m:
                        continue
                    desc_m = (m.group(1) or '').lower()
                    if 'saldo do dia' in desc_m:
                        continue
                    is_saida = bool(m.group(2))
                    v = _parse_valor_br(m.group(3))
                    if v is None:
                        continue
                    if is_saida:
                        net_d_min -= v
                    else:
                        net_d_min += v
                    tx_d_min_count += 1
                ini = saldo_d_min - net_d_min
                try:
                    print(
                        f'[EXTRATOR-SALDOS] banco=santander '
                        f'fallback=saldo_do_dia_por_dia '
                        f'si={float(ini):.2f} sf={float(fim):.2f} '
                        f'dias_com_saldo={len(saldos_dia)} '
                        f'd_min={d_min_str} net_tx_d_min={float(net_d_min):.2f} '
                        f'tx_d_min={tx_d_min_count}'
                    )
                except Exception:
                    pass

        # Fallback B — tabela com coluna Saldo (R$) por linha (casos
        # "Santander empresas 2.pdf" MARTINS — Aplicativo Santander
        # Empresas; e DLS / IB N1 — Internet Banking Empresarial layout
        # antigo). Cabeçalho típico:
        #   "Data Histórico Documento Valor (R$) Saldo (R$)"
        # Cada linha tx: "DD/MM/YYYY <desc> [-]<valor> <saldo>".
        # PDF lista tx em ordem DESCENDENTE cronológica dentro do dia,
        # então:
        #   SF = saldo da PRIMEIRA linha do PDF onde data == D_max
        #        (saldo após a tx mais recente cronológica do D_max).
        #   SI = saldo da ÚLTIMA linha do PDF onde data == D_min,
        #        MENOS o valor dessa linha (saldo antes da tx mais
        #        antiga cronológica do D_min = saldo de abertura).
        #
        # Sessão 19, Iter 4 — ativa quando `fim is None` mesmo se `ini`
        # já foi extraído pelo branch principal (caso DLS/IB N1 que têm
        # `SALDO ANTERIOR` no PDF dando SI correto, mas não têm "Saldo
        # Final"/"Saldo Atual" — antes do fix, SF era calculado pelo
        # pipeline como SI + sum(tx_extraídas), gerando VERDE fake quando
        # o parser perdia transações). Preserva `ini` se já extraído.
        if fim is None:
            tem_cabecalho_tabela = any(
                'valor (r$)' in linha.lower() and 'saldo (r$)' in linha.lower()
                for linha in linhas
            )
            if tem_cabecalho_tabela:
                from datetime import datetime as _dt
                # Captura: data, valor (com sinal opcional), saldo
                _re_sant_tab = re.compile(
                    r'^\s*(\d{2}/\d{2}/\d{4})\s+.+?\s+(-?\d[\d.]*,\d{2})\s+(-?\d[\d.]*,\d{2})\s*$'
                )
                # Lista de (idx_linha, data_dt, valor_signed, saldo)
                linhas_tx: list[tuple[int, _dt, Decimal, Decimal]] = []
                for idx, linha in enumerate(linhas):
                    m = _re_sant_tab.match(linha)
                    if not m:
                        continue
                    try:
                        dt = _dt.strptime(m.group(1), '%d/%m/%Y')
                    except ValueError:
                        continue
                    # Preserva sinal do valor (entrada/saída)
                    val_raw = m.group(2)
                    saldo_raw = m.group(3)
                    val_neg = val_raw.startswith('-')
                    sal_neg = saldo_raw.startswith('-')
                    val_abs = _parse_valor_br(val_raw.lstrip('-'))
                    sal_abs = _parse_valor_br(saldo_raw.lstrip('-'))
                    if val_abs is None or sal_abs is None:
                        continue
                    val = -val_abs if val_neg else val_abs
                    sal = -sal_abs if sal_neg else sal_abs
                    linhas_tx.append((idx, dt, val, sal))
                if linhas_tx:
                    # D_max = data mais recente; D_min = data mais antiga.
                    datas = [t[1] for t in linhas_tx]
                    d_max = max(datas)
                    d_min = min(datas)
                    # Primeira linha do PDF onde data == D_max → SF
                    for _idx, dt, _val, sal in linhas_tx:
                        if dt == d_max:
                            fim = sal
                            break
                    # SI: só calcula se ainda não foi extraído pelo branch
                    # principal (preserva `SALDO ANTERIOR` quando presente).
                    if ini is None:
                        # Última linha do PDF onde data == D_min → SI = saldo - valor
                        ultima_d_min: tuple | None = None
                        for t in linhas_tx:
                            if t[1] == d_min:
                                ultima_d_min = t
                        if ultima_d_min is not None:
                            _idx, _dt, val, sal = ultima_d_min
                            ini = sal - val
                    try:
                        si_log = f'{float(ini):.2f}' if ini is not None else 'None'
                        sf_log = f'{float(fim):.2f}' if fim is not None else 'None'
                        print(
                            f'[EXTRATOR-SALDOS] banco=santander '
                            f'fallback=tabela_aplicativo_saldo_coluna '
                            f'si={si_log} sf={sf_log} '
                            f'd_min={d_min.strftime("%d/%m/%Y")} '
                            f'd_max={d_max.strftime("%d/%m/%Y")} '
                            f'linhas_tx={len(linhas_tx)}'
                        )
                    except Exception:
                        pass

        return ini, fim

    # ─── XP: sem saldo do período ────────────────────────────────────────────
    if banco in ('xp_extrato', 'xp_posicao'):
        return None, None

    # ─── Fallback genérico ───────────────────────────────────────────────────
    for linha in linhas:
        ll = linha.lower()
        if ini is None and ('saldo inicial' in ll or 'saldo anterior' in ll):
            v = _r_num(linha) or _ultimo_num(linha)
            if v is not None:
                ini = v
        if 'saldo final' in ll or 'saldo do período' in ll or 'saldo do periodo' in ll:
            v = _r_num(linha) or _ultimo_num(linha)
            if v is not None:
                fim = v
    return ini, fim

from .parsers.inter import ParserInter
from .parsers.cora import ParserCora
from .parsers.sicredi import ParserSicredi
from .parsers.c6bank import ParserC6Bank
from .parsers.pagbank import ParserPagBank
from .parsers.mercado_pago import ParserMercadoPago
from .parsers.caixa import ParserCaixa
from .parsers.itau import ParserItau
from .parsers.itau_empresas import ParserItauEmpresas
from .parsers.bradesco import ParserBradesco
from .parsers.stone import ParserStone
from .parsers.sumup import ParserSumUp
from .parsers.bb import ParserBB
from .parsers.santander import ParserSantander
from .parsers.santander_empresarial import ParserSantanderEmpresas
from .parsers.xp_extrato import ParserXPExtrato
from .parsers.xp_posicao import ParserXPPosicao
from .parsers.nubank import ParserNubank
from .parsers.bs2 import ParserBS2
from .parsers.santander_consolidado import ParserSantanderConsolidado
from .parsers.santander_ib_novo import ParserSantanderIBNovo
from .parsers.bradesco_empresas.bradesco_net_empresas import ParserBradescoNetEmpresas
from .parsers.n2.itau_n2 import ParserItauN2
from .parsers.n2.inter_n2 import ParserInterN2
from .parsers.n2.itau_empresas_n2 import ParserItauEmpresasN2
from .parsers.santander_empresas.santander_empresas_v1 import ParserSantanderEmpresasV1
from .parsers.santander_empresas.santander_empresas_v2 import ParserSantanderEmpresasV2
from .parsers.safra import ParserSafra
from .parsers.btg import ParserBTG


# Mapeamento banco_key -> classe parser
PARSERS: dict[str, type] = {
    'inter': ParserInter,
    'cora': ParserCora,
    'sicredi': ParserSicredi,
    'c6bank': ParserC6Bank,
    'pagbank': ParserPagBank,
    'mercado_pago': ParserMercadoPago,
    'caixa': ParserCaixa,
    'itau': ParserItau,
    'itau_empresas': ParserItauEmpresas,
    'bradesco': ParserBradesco,
    'bradesco_empresas': ParserBradesco,        # Net Empresas — mesmo parser, formato detectado por 'dcto.'
    'stone': ParserStone,
    'sumup': ParserSumUp,
    'bb': ParserBB,
    'santander': ParserSantander,
    'santander_empresas': ParserSantanderEmpresas,  # Internet Banking Empresarial direto (sem N1)
    'xp_extrato': ParserXPExtrato,
    'xp_posicao': ParserXPPosicao,
    'nubank': ParserNubank,
    'bs2': ParserBS2,
    'santander_consolidado': ParserSantanderConsolidado,
    'santander_ib_novo': ParserSantanderIBNovo,
    'bradesco_net_empresas': ParserBradescoNetEmpresas,
    'itau_n2': ParserItauN2,
    'inter_n2': ParserInterN2,
    'itau_empresas_n2': ParserItauEmpresasN2,
    'santander_empresas_v1': ParserSantanderEmpresasV1,
    'santander_empresas_v2': ParserSantanderEmpresasV2,
    'safra': ParserSafra,
    'btg': ParserBTG,
}

# Mapeamento de parsers de fallback.
# Se o parser primário retornar 0 transações, o parser n2 é tentado.
FALLBACK_PARSERS: dict[str, str] = {
    'itau':           'itau_n2',
    'itau_empresas':  'itau_empresas_n2',
    'inter':          'inter_n2',
    'bradesco':       'bradesco_net_empresas',
    'santander':      'santander_consolidado',
}

# Assinaturas de texto por banco.
# Cada banco tem uma lista de "conjuntos de termos" (term_sets).
# Um banco é detectado quando TODOS os termos de QUALQUER conjunto estão presentes.
# Ordem importa: mais específico primeiro para evitar falsos positivos.
#
# Estrutura: list[tuple[banco_key, list[list[str]]]]
#   term_sets = lista de alternativas (OR entre sets)
#   cada set = lista de termos obrigatórios (AND dentro do set)
_ASSINATURAS: list[tuple[str, list[list[str]]]] = [
    # xp_posicao: frase única e específica — vem ANTES de xp_extrato
    ('xp_posicao',   [['historico posicao consolidada'], ['histórico posição consolidada']]),
    # mercado_pago: exige termo + contexto exclusivo para evitar falso positivo
    # (PDFs de outros bancos mencionam "mercado pago" e "10.573.521" em transações Pix)
    # Sessão 17: o set ['mercadopago'] sozinho era frágil — capturava extratos
    # Santander Consolidado (caso LEKE jan/2025) que mencionam "MERCADOPAGO COM
    # REPRESENT" em descrições de PIX. Agora exige domínio para evitar substring
    # match em descrições.
    ('mercado_pago', [['mercado pago', 'extrato de conta'], ['mercado pago', 'detalhe dos movimentos'],
                      ['mercadopago.com'], ['10.573.521', 'detalhe dos movimentos']]),
    # xp_extrato: 'xp investimentos' é único da XP — any XP file not matched above
    ('xp_extrato',   [['xp investimentos']]),
    # sumup: maquininha de pagamento — detecta pelo nome e pelo formato do extrato
    ('sumup',        [['sumup'], ['sum up'], ['extrato de depósitos', 'resumo da transação'],
                      ['extrato de depositos', 'resumo da transacao']]),
    # stone: usa nome da instituição (evita falso positivo de 'stones' em outros PDFs)
    ('stone',        [['stone institui'], ['stone pagamentos']]),
    # nubank: ANTES do bradesco porque "BCO BRADESCO S.A." aparece em descrições de Pix
    # em extratos Nubank. 'nu pagamentos' é exclusivo do Nubank.
    ('nubank',       [['nu pagamentos'], ['nu financeira'], ['nubank.com'], ['nu.com.br']]),
    # btg: BTG Pactual — CNPJ e domínio; "conta corrente - pj" + "banco 208" exclusivo
    ('btg', [
        ['btgpactual'], ['btg pactual'],
        ['30.306.294'],                           # CNPJ BTG Pactual
        ['conta corrente - pj', 'banco 208'],     # código COMPE 208 = BTG
        ['sac@btgpactual'],
    ]),
    # bradesco_net_empresas: Net Empresas — detectado por 'total disponível (r$)' + 'bradesco'
    # Encoding do PDF pode corromper "Disponível" → "Dispon\ufffdvel": usar prefixo sem acento
    ('bradesco_net_empresas', [
        ['bradesco', 'total disponível (r$)'],
        ['bradesco', 'total disponivel (r$)'],
        ['bradesco', 'net empresa'],
        ['bradesco', 'total dispon'],              # fallback encoding-safe
        # Sessão 17: assinatura sem 'bradesco' — cabeçalho exclusivo do formato
        # Net Empresas ("Agência | Conta Total Disponível (R$)"). Cobre casos
        # onde "bradesco" não aparece nas primeiras 3 páginas (SEOLIN, TANIA
        # dez/nov, Extrato dec25/nov25, Agosto 2025, Bradesco_24032026). 9 PDFs
        # Bradesco Net Empresas validados, 0 falso positivo cross-banco. Tem que
        # vir ANTES da regra 'bradesco' genérica (que tem 'dcto.' como atalho)
        # para evitar que ParserBradesco PF capture o caso.
        ['| conta total'],
    ]),
    # bradesco: 'dcto.' é o cabeçalho de coluna único do Bradesco;
    # 'bradesco' nem sempre está no texto visível do PDF
    ('bradesco',     [['bradesco'], ['dcto.'], ['rentab.invest facilcred']]),
    # santander_ib_novo: Internet Banking Empresarial layout NOVO.
    # Distingue dos outros 3 layouts Santander pela presença de
    # 'saldo do dia r$' (linha por dia, ausente no DLS antigo, no
    # Consolidado e no formato App "por dia da semana") em conjunto
    # com o cabeçalho 'internet banking empresarial'.
    # Inserido ANTES de santander_consolidado / santander_empresas /
    # santander para impedir que 'contamax' (presente em descrições
    # do IB novo) capture esse extrato no roteador genérico.
    ('santander_ib_novo', [
        ['internet banking empresarial', 'saldo do dia r$'],
    ]),
    # santander_consolidado: Extrato Consolidado Inteligente
    ('santander_consolidado', [
        ['extrato consolidado inteligente'],
        ['contamax empresarial'],
    ]),
    # santander_empresas: Internet Banking Empresarial formato App (ANTES de v1)
    # Detectado por: texto contém dia da semana por extenso + CREDITO/DEBITO
    ('santander_empresas', [
        ['internet banking empresarial', 'credito r$', 'debito r$'],
    ]),
    # santander_empresas_v1: Internet Banking Empresarial formato tabular com colunas
    ('santander_empresas_v1', [
        ['santander', 'credito r$', 'debito r$'],
        ['contamax', 'credito r$'],
    ]),
    # santander: 'contamax' é produto exclusivo Santander; fallback exige
    # qualifier de domínio/nome próprio em vez de substring 'santander' solta.
    # Sessão 17: a regra ['santander'] sozinha capturava B2S.pdf (PROMOVE BRASIL),
    # que mencionava "Bco Santander SA" em descrição de TED, gerando mis-route
    # para parser santander e gap 47.748 em produção. 'santander.com.br' está
    # presente em rodapés Santander reais; 'banco santander' aparece em headers
    # do IB N1 (DLS antigo). 12 PDFs Santander validados, 0 falso positivo.
    ('santander',    [['contamax'], ['santander.com.br'], ['banco santander']]),
    # sicredi: termo único da cooperativa
    ('sicredi',      [['sicredi']]),
    # safra: Banco Safra S/A — CNPJ é super específico
    ('safra',        [['banco safra'], ['safra s/a'], ['58.160.789/0001-28']]),
    # pagbank:
    ('pagbank',      [['pagbank'], ['pagseguro']]),
    # cora: 'cora scfi' é o nome legal do banco.
    # NUNCA usar 'cora' sozinho — dá falso positivo em 'ancoradouro', 'decoração' etc.
    ('cora',         [['cora scfi'], ['banco cora'], ['cora s.a']]),
    # bb: 'bb rende' captura extratos BB corporativos; 'dia lote documento' é o
    # cabeçalho exclusivo do "Extrato de Conta Corrente" do BB (impede falso positivo
    # quando descrições de pagamento contêm 'itau', 'bradesco', etc.)
    ('bb',           [
        ['banco do brasil'], ['bb rende'], ['bb.com.br'],
        ['dia lote documento'],
    ]),
    # inter_n2: Inter com campo 'cp :' (formato N2)
    ('inter_n2', [
        ['banco inter', 'cp :'],
    ]),
    # inter: 'banco inter' ou 'bancointer'
    ('inter',        [['banco inter'], ['bancointer']]),
    # bs2: banco BS2 — usar termos compostos (evitar 'bs2' sozinho = substring frágil)
    ('bs2',          [['bs2 banco'], ['banco bs2'], ['bs2.com.br'], ['empresas.bs2'],
                      ['bs2 s.a'], ['bs2 dtvm']]),
    # caixa: 'sac caixa' aparece no rodapé dos PDFs da CEF
    ('caixa',        [['caixa econômica'], ['caixa economica'], ['sac caixa'], ['cef']]),
    # c6bank: adicionar 'extrato exportado' + contexto de agência curta (formato C6 web)
    ('c6bank',       [['c6 bank'], ['c6bank'], ['banco c6'],
                      ['extrato exportado', 'saldo do dia']]),
    # itau_n2: formato ANTARTI.CO com colunas Razão Social e CNPJ/CPF
    # Encoding do PDF pode corromper "Razão" → "Raz\ufffdo": usar prefixo 'raz' + 'cnpj/cpf'
    ('itau_n2', [
        ['itaú', 'razão social', 'cnpj/cpf'],
        ['itau', 'razao social', 'cnpj/cpf'],
        ['itaú', 'saldo total disponível dia', 'lançamentos'],
        # Fallback encoding-safe: coluna "CNPJ/CPF" + layout Itaú N2
        ['cnpj/cpf', 'saldo anterior', 'valor (r$)', 'saldo (r$)'],
    ]),
    # itau_empresas: vem ANTES do itau genérico — assinaturas específicas de conta PJ
    ('itau_empresas', [
        ['itaú empresas'], ['itau empresas'],
        ['itaúempresas'], ['itauempresas'],
        ['gerenciador financeiro', 'itaú'], ['gerenciador financeiro', 'itau'],
        ['conta corrente pj', 'itaú'], ['conta corrente pj', 'itau'],
        ['extrato empresas', 'itaú'], ['extrato empresas', 'itau'],
        # Rodapé do PDF de conta corrente PJ online do Itaú
        ['itau.com.br/empresas'],
        # Conta corrente PJ com encoding corrompido (sem 'itaú' mas com 'conta corrente - pj')
        ['conta corrente - pj', 'saldo de abertura'],
    ]),
    # itau: mais genérico — verifica por último
    # 'saldo aplic aut mais' e 'extrato mensal ag' são exclusivos do Itaú
    # e aparecem nas primeiras páginas de qualquer extrato mensal Itaú
    ('itau',         [
        ['itaú'], ['itau'], ['banco itaú'], ['banco itau'],
        ['saldo aplic aut mais'],
        ['extrato mensal ag'],
    ]),
]


def detectar_banco(pdf_path: str, password: str | None = None,
                   texto_pre_extraido: str | None = None) -> str:
    """
    Detecta o banco do extrato lendo o texto das primeiras 3 páginas.

    Cada banco possui conjuntos de termos. O banco é detectado quando
    TODOS os termos de QUALQUER conjunto estiverem presentes no texto.

    Args:
        pdf_path: Caminho para o arquivo PDF.
        texto_pre_extraido: opcional. Se fornecido (ex.: vindo do OCR
            fallback para PDFs vetoriais), pula a leitura via pdfplumber.

    Returns:
        Chave do banco (ex: 'itau', 'inter') ou 'desconhecido'.
    """
    if texto_pre_extraido is not None:
        texto = texto_pre_extraido.lower() + ' '
    else:
        texto = ''
        try:
            with pdfplumber.open(pdf_path, password=password or '') as pdf:
                for pagina in pdf.pages[:3]:
                    try:
                        t = pagina.extract_text() or ''
                        texto += t.lower() + ' '
                    except Exception:
                        pass
        except Exception:
            return 'desconhecido'

    for banco_key, term_sets in _ASSINATURAS:
        for terms in term_sets:
            if all(termo in texto for termo in terms):
                return banco_key

    # Fallback: detecção pelo nome do arquivo (PDFs escaneados sem texto)
    # Normaliza acentos para que 'Itaú' → 'itau', 'Bradésco' → 'bradesco', etc.
    import os
    _nome_raw = os.path.basename(pdf_path).lower()
    nome_arquivo = unicodedata.normalize('NFKD', _nome_raw).encode('ascii', 'ignore').decode()
    _FILENAME_HINTS = {
        'nubank':    'nubank',
        'sicredi':   'sicredi',
        'itau':      'itau',
        'inter':     'inter',
        'bradesco':  'bradesco',
        'santander': 'santander',
        'caixa':     'caixa',
        'bb':        'banco do brasil',
        'c6bank':    'c6',
        'pagbank':   'pagbank',
        'stone':     'stone',
        'sumup':     'sumup',
        'cora':      'cora',
        'bs2':       'bs2',
        'btg':       'btg',
        'safra':     'safra',
    }
    for banco_key, hint in _FILENAME_HINTS.items():
        if hint in nome_arquivo:
            return banco_key

    return 'desconhecido'


def detectar_banco_com_confianca(
    pdf_path: str, password: str | None = None,
) -> dict:
    """
    Detecta o banco e retorna nível de confiança da detecção.

    Returns:
        {
            "banco_detectado": str | None,
            "banco_nome_exibicao": str | None,
            "confianca": "alta" | "media" | "nenhuma",
            "erro": str | None,
        }
    """
    texto = ''
    try:
        with pdfplumber.open(pdf_path, password=password or '') as pdf:
            for pagina in pdf.pages[:3]:
                try:
                    t = pagina.extract_text() or ''
                    texto += t.lower() + ' '
                except Exception:
                    pass
    except Exception as e:
        err_msg = str(e).lower()
        if 'password' in err_msg or 'encrypted' in err_msg:
            return {
                'banco_detectado': None,
                'banco_nome_exibicao': None,
                'confianca': 'nenhuma',
                'erro': 'PDF protegido por senha',
            }
        return {
            'banco_detectado': None,
            'banco_nome_exibicao': None,
            'confianca': 'nenhuma',
            'erro': f'Erro ao abrir PDF: {str(e)[:100]}',
        }

    # Detecção por assinaturas (confiança alta)
    for banco_key, term_sets in _ASSINATURAS:
        for terms in term_sets:
            if all(termo in texto for termo in terms):
                return {
                    'banco_detectado': banco_key,
                    'banco_nome_exibicao': _NOME_BANCO_EXIBICAO.get(
                        banco_key, banco_key.capitalize()
                    ),
                    'confianca': 'alta',
                    'erro': None,
                }

    # Fallback: detecção pelo nome do arquivo (confiança média)
    import os
    _nome_raw = os.path.basename(pdf_path).lower()
    nome_arquivo = unicodedata.normalize('NFKD', _nome_raw).encode('ascii', 'ignore').decode()
    _FILENAME_HINTS = {
        'nubank': 'nubank', 'sicredi': 'sicredi', 'itau': 'itau',
        'inter': 'inter', 'bradesco': 'bradesco', 'santander': 'santander',
        'caixa': 'caixa', 'bb': 'banco do brasil', 'c6bank': 'c6',
        'pagbank': 'pagbank', 'stone': 'stone', 'sumup': 'sumup',
        'cora': 'cora', 'bs2': 'bs2', 'btg': 'btg', 'safra': 'safra',
    }
    for banco_key, hint in _FILENAME_HINTS.items():
        if hint in nome_arquivo:
            return {
                'banco_detectado': banco_key,
                'banco_nome_exibicao': _NOME_BANCO_EXIBICAO.get(
                    banco_key, banco_key.capitalize()
                ),
                'confianca': 'media',
                'erro': None,
            }

    return {
        'banco_detectado': None,
        'banco_nome_exibicao': None,
        'confianca': 'nenhuma',
        'erro': None,
    }


def extrair_extrato(pdf_path: str, banco_id: str = '', password: str | None = None) -> dict:
    """
    Ponto de entrada principal para extração de extratos bancários.

    Detecta o banco, instancia o parser correto, extrai transações,
    aplica categorias e calcula totais.

    Args:
        pdf_path: Caminho para o arquivo PDF.

    Returns:
        Dict com:
            banco         – nome do banco detectado
            transacoes    – lista de transações categorizadas
            total_entradas – soma das entradas
            total_saidas   – soma das saídas
            saldo_periodo  – total_entradas - total_saidas
            avisos         – lista de mensagens de aviso
            erro           – mensagem de erro (str) ou None
    """
    resultado: dict = {
        'banco': 'desconhecido',
        'transacoes': [],
        'total_entradas': 0.0,
        'total_saidas': 0.0,
        'total_posicao': 0.0,
        'saldo_periodo': 0.0,
        'saldo_inicial': None,
        'saldo_final': None,
        'avisos': [],
        'erro': None,
    }

    try:
        # Verifica se PDF está protegido e se a senha foi fornecida
        try:
            import pikepdf
            import os as _os_prepipeline
            try:
                pikepdf.open(pdf_path, password=password or '')
            except pikepdf.PasswordError:
                resultado['erro'] = 'PDF protegido por senha. Informe a senha correta para processar este extrato.'
                resultado['requer_senha'] = True
                return resultado
            except Exception as _e_prepipeline:
                print(
                    f"[PRE-PIPELINE-ERROR] arquivo={_os_prepipeline.path.basename(pdf_path)} "
                    f"erro_tipo={type(_e_prepipeline).__name__} "
                    f"erro_msg={str(_e_prepipeline)} "
                    f"pikepdf_version={pikepdf.__version__}",
                    flush=True,
                )
                raise
        except ImportError:
            pass  # pikepdf não instalado; prossegue com pdfplumber que lança erro similar

        # Verifica limite de páginas antes de processar
        try:
            with pdfplumber.open(pdf_path, password=password or '') as _pdf_check:
                n_paginas = len(_pdf_check.pages)
                if n_paginas > MAX_PAGINAS_PDF:
                    resultado['erro'] = (
                        f'PDF com {n_paginas} páginas excede o limite de '
                        f'{MAX_PAGINAS_PDF} páginas por arquivo. '
                        'Divida o extrato em arquivos menores.'
                    )
                    return resultado
        except Exception:
            pass  # Se falhar aqui, tenta processar mesmo assim

        # Usa banco_id fornecido manualmente; senão, detecta automaticamente
        banco_key = banco_id.strip().lower() if banco_id else detectar_banco(pdf_path, password=password)
        resultado['banco'] = banco_key

        if banco_key == 'desconhecido':
            resultado['erro'] = 'Banco não reconhecido. Verifique se o PDF é um extrato bancário suportado.'
            return resultado

        parser_cls = PARSERS.get(banco_key)
        if not parser_cls:
            resultado['erro'] = f'Parser não implementado para: {banco_key}'
            return resultado

        parser = parser_cls(pdf_path, password=password)
        transacoes_brutas = parser.extrair()
        resultado['avisos'] = parser.avisos

        # Se o parser primário não encontrou transações, tenta o fallback
        if not transacoes_brutas and banco_key in FALLBACK_PARSERS:
            fallback_key = FALLBACK_PARSERS[banco_key]
            fallback_cls = PARSERS.get(fallback_key)
            if fallback_cls:
                try:
                    parser_fb = fallback_cls(pdf_path, password=password)
                    transacoes_fb = parser_fb.extrair()
                    if transacoes_fb:
                        transacoes_brutas = transacoes_fb
                        resultado['avisos'] = parser_fb.avisos
                        resultado['avisos'].append(
                            f'Parser primário ({banco_key}) retornou 0 transações. '
                            f'Usando parser alternativo ({fallback_key}).'
                        )
                        banco_key = fallback_key
                        resultado['banco'] = banco_key
                except Exception as e_fb:
                    resultado['avisos'].append(f'Fallback {fallback_key} falhou: {e_fb}')

        # Filtra transações marcadas como 'ignorar'
        transacoes = [t for t in transacoes_brutas if t.get('tipo') != 'ignorar']

        # Aplica categorias
        transacoes = aplicar_categorias(transacoes)

        # Calcula totais (Decimal para precisão financeira)
        total_entradas = sum((t['valor'] for t in transacoes if t['tipo'] == 'entrada'), Decimal('0'))
        total_saidas = sum((t['valor'] for t in transacoes if t['tipo'] == 'saida'), Decimal('0'))
        total_posicao = sum((t['valor'] for t in transacoes if t['tipo'] == 'posicao'), Decimal('0'))
        # Soma do valor originalmente aplicado (campo extra presente em xp_posicao)
        total_aplicado = sum(
            (Decimal(str(t.get('valor_aplicado') or 0))
             for t in transacoes if t['tipo'] == 'posicao'),
            Decimal('0'),
        )

        # Extrai saldo_inicial e saldo_final diretamente do texto do PDF
        saldo_inicial, saldo_final = _extrair_saldos_pdf(pdf_path, banco_key, password=password)

        # Converte valor Decimal → float nas transações para serialização JSON
        for t in transacoes:
            if isinstance(t.get('valor'), Decimal):
                t['valor'] = float(t['valor'])
            if isinstance(t.get('valor_aplicado'), Decimal):
                t['valor_aplicado'] = float(t['valor_aplicado'])
        resultado['transacoes'] = transacoes
        resultado['total_entradas'] = float(round(total_entradas, 2))
        resultado['total_saidas'] = float(round(total_saidas, 2))
        resultado['total_posicao'] = float(round(total_posicao, 2))
        resultado['total_aplicado'] = float(round(total_aplicado, 2))
        resultado['saldo_periodo'] = float(round(total_entradas - total_saidas, 2))
        resultado['saldo_inicial'] = float(round(saldo_inicial, 2)) if saldo_inicial is not None else None
        # saldo_final: usa o valor extraído do PDF se disponível;
        # caso contrário calcula como saldo_inicial + saldo_periodo (se saldo_inicial presente)
        if saldo_final is not None:
            resultado['saldo_final'] = float(round(saldo_final, 2))
        elif saldo_inicial is not None:
            resultado['saldo_final'] = float(round(saldo_inicial + (total_entradas - total_saidas), 2))
        else:
            resultado['saldo_final'] = None

        # ── Verificação progressiva de saldos (informativa, nunca bloqueia) ──
        try:
            saldos_inter = parser._extrair_saldos_intermediarios()
            if saldos_inter:
                _si = Decimal(str(saldo_inicial)) if saldo_inicial is not None else None
                # Usa ULTIMO saldo de cada data
                ultimo_saldo_por_data: dict[str, Decimal] = {}
                for s in saldos_inter:
                    ultimo_saldo_por_data[s['data']] = Decimal(str(s['saldo']))
                # Agrupa transações por data
                tx_por_data: dict[str, list] = {}
                for t in transacoes:
                    tx_por_data.setdefault(t['data'], []).append(t)
                datas_ordenadas = sorted(
                    set(t['data'] for t in transacoes) | set(ultimo_saldo_por_data.keys()),
                    key=lambda d: (int(d[6:10]), int(d[3:5]), int(d[0:2]))
                )
                num_verificados = len(ultimo_saldo_por_data)

                # Se SI é None, tentar usar primeiro saldo intermediário como ponto de partida
                si_usado = _si
                si_fonte = 'pdf'
                if si_usado is None and ultimo_saldo_por_data:
                    primeira_data = datas_ordenadas[0] if datas_ordenadas else None
                    if primeira_data and primeira_data in ultimo_saldo_por_data:
                        si_usado = ultimo_saldo_por_data[primeira_data]
                        si_fonte = 'primeiro_saldo_intermediario'

                if si_usado is None:
                    # Não é possível verificar sem ponto de partida
                    resultado['verificacao_saldos'] = {
                        'saldo_inicial': None,
                        'saldo_inicial_encontrado': False,
                        'saldo_final_informado': float(round(Decimal(str(saldo_final)), 2)) if saldo_final is not None else None,
                        'saldo_final_calculado': None,
                        'conferencia_ok': None,
                        'divergencias': [],
                        'saldos_intermediarios_verificados': num_verificados,
                        'saldos_intermediarios_ok': 0,
                        'modo_saldo': 'indisponivel',
                        'aviso': 'Saldo inicial nao identificado neste extrato.',
                    }
                else:
                    # Bancos diferem: "Saldo do dia" pode ser ABERTURA (antes das tx)
                    # ou FECHAMENTO (após tx). Testamos ambos e usamos o melhor.
                    def _verificar(modo_pre: bool):
                        sc = Decimal(str(si_usado))
                        divs = []
                        ok_count = 0
                        started = si_fonte == 'pdf'  # Se SI veio do primeiro saldo, pular esse saldo
                        for data in datas_ordenadas:
                            if not started and data in ultimo_saldo_por_data:
                                started = True
                                # Pula o primeiro saldo (que é nosso ponto de partida)
                                for t in tx_por_data.get(data, []):
                                    v = Decimal(str(t['valor']))
                                    if t['tipo'] == 'entrada': sc += v
                                    elif t['tipo'] == 'saida': sc -= v
                                continue
                            if modo_pre and data in ultimo_saldo_por_data:
                                esperado = ultimo_saldo_por_data[data]
                                if abs(sc - esperado) > Decimal('0.02'):
                                    divs.append({'data': data, 'saldo_esperado': float(esperado),
                                                 'saldo_calculado': float(round(sc, 2)),
                                                 'diferenca': float(round(sc - esperado, 2))})
                                else:
                                    ok_count += 1
                            for t in tx_por_data.get(data, []):
                                v = Decimal(str(t['valor']))
                                if t['tipo'] == 'entrada': sc += v
                                elif t['tipo'] == 'saida': sc -= v
                            if not modo_pre and data in ultimo_saldo_por_data:
                                esperado = ultimo_saldo_por_data[data]
                                if abs(sc - esperado) > Decimal('0.02'):
                                    divs.append({'data': data, 'saldo_esperado': float(esperado),
                                                 'saldo_calculado': float(round(sc, 2)),
                                                 'diferenca': float(round(sc - esperado, 2))})
                                else:
                                    ok_count += 1
                        return sc, divs, ok_count

                    sc_post, divs_post, ok_post = _verificar(modo_pre=False)
                    sc_pre, divs_pre, ok_pre = _verificar(modo_pre=True)

                    if ok_post >= ok_pre:
                        saldo_calc, divergencias, saldos_ok, modo = sc_post, divs_post, ok_post, 'fechamento'
                    else:
                        saldo_calc, divergencias, saldos_ok, modo = sc_pre, divs_pre, ok_pre, 'abertura'

                _sf_info = float(round(Decimal(str(saldo_final)), 2)) if saldo_final is not None else None
                if si_usado is not None and 'verificacao_saldos' not in resultado:
                    resultado['verificacao_saldos'] = {
                        'saldo_inicial': float(round(si_usado, 2)),
                        'saldo_inicial_encontrado': si_fonte == 'pdf',
                        'saldo_final_informado': _sf_info,
                        'saldo_final_calculado': float(round(saldo_calc, 2)),
                        'conferencia_ok': len(divergencias) == 0,
                        'divergencias': divergencias,
                        'saldos_intermediarios_verificados': num_verificados,
                        'saldos_intermediarios_ok': saldos_ok,
                        'modo_saldo': modo,
                    }
        except Exception:
            pass  # Verificação é informativa, nunca bloqueia o fluxo

        # Backfill: se _extrair_saldos_pdf não encontrou saldo_inicial mas a
        # verificação progressiva inferiu um SI válido (ex: PagBank via saldo
        # fantasma), propaga para o campo principal do resultado.
        if saldo_inicial is None and 'verificacao_saldos' in resultado:
            _vs_si = resultado['verificacao_saldos'].get('saldo_inicial')
            if _vs_si is not None:
                saldo_inicial = Decimal(str(_vs_si))
                resultado['saldo_inicial'] = float(round(saldo_inicial, 2))
                # Recalcula saldo_final se estava None
                if resultado.get('saldo_final') is None:
                    resultado['saldo_final'] = float(round(
                        saldo_inicial + (total_entradas - total_saidas), 2
                    ))

        # Garante aviso padronizado para extratos sem transações
        if not transacoes:
            _aviso_zero = 'Extrato com saldo zero — nenhuma transação encontrada.'
            if not any('saldo zero' in av or 'nenhuma transação' in av
                       for av in resultado['avisos']):
                resultado['avisos'].append(_aviso_zero)

    except Exception as e:
        resultado['erro'] = f'Erro ao processar extrato: {str(e)}'

    return resultado


def processar_extrato(caminho_pdf: str, banco_id: str = '', password: str | None = None) -> dict:
    """
    Interface unificada para extração de extratos bancários.
    Chama extrair_extrato() e formata o resultado para a API.

    Returns:
        {
            "banco": str,
            "banco_id": str,
            "total_transacoes": int,
            "total_entradas": float,
            "total_saidas": float,   # valor absoluto (positivo)
            "saldo": float,
            "transacoes": list,
            "avisos": list,
            "erro": str | None
        }
    """
    resultado = extrair_extrato(caminho_pdf, banco_id=banco_id, password=password)

    if resultado.get("erro"):
        return resultado

    transacoes = resultado["transacoes"]
    total_entradas = resultado["total_entradas"]
    total_saidas = resultado["total_saidas"]

    total_posicao = resultado.get("total_posicao", 0.0)
    total_aplicado = resultado.get("total_aplicado", 0.0)

    return {
        "banco": resultado["banco"],
        "banco_id": resultado["banco"],
        "total_transacoes": len(transacoes),
        "total_entradas": round(total_entradas, 2),
        "total_saidas": round(abs(total_saidas), 2),
        "total_posicao": round(total_posicao, 2),
        "total_aplicado": round(total_aplicado, 2),
        "saldo": round(total_entradas - total_saidas, 2),
        "saldo_inicial": resultado.get("saldo_inicial"),
        "saldo_final": resultado.get("saldo_final"),
        "transacoes": transacoes,
        "avisos": resultado.get("avisos", []),
        "erro": None,
        **({"verificacao_saldos": resultado["verificacao_saldos"]} if "verificacao_saldos" in resultado else {}),
    }


_MESES_PT = [
    '', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
]

# Nomes de exibição por banco_key
_NOME_BANCO_EXIBICAO: dict[str, str] = {
    'inter': 'Inter',
    'cora': 'Cora',
    'sicredi': 'Sicredi',
    'c6bank': 'C6 Bank',
    'pagbank': 'PagBank',
    'mercado_pago': 'Mercado Pago',
    'caixa': 'Caixa',
    'itau': 'Itaú',
    'itau_empresas': 'Itaú Empresas',
    'bradesco': 'Bradesco',
    'bradesco_empresas': 'Bradesco Net Empresas',
    'stone': 'Stone',
    'sumup': 'SumUp',
    'bb': 'Banco do Brasil',
    'santander': 'Santander',
    'santander_empresas': 'Santander Empresas',
    'xp_extrato': 'XP',
    'xp_posicao': 'XP Posição',
    'nubank': 'Nubank',
    'bs2': 'BS2',
    'itau_n2': 'Itaú',
    'inter_n2': 'Inter',
    'itau_empresas_n2': 'Itaú Empresas',
    'santander_consolidado': 'Santander',
    'santander_ib_novo': 'Santander Empresas',
    'bradesco_net_empresas': 'Bradesco Net Empresas',
    'santander_empresas_v1': 'Santander Empresas',
    'santander_empresas_v2': 'Santander Empresas',
    'stone_n2': 'Stone',
    'safra': 'Banco Safra',
    'btg': 'BTG Pactual',
}


def gerar_nome_extrato(banco_key: str, transacoes: list) -> str:
    """
    Gera um nome descritivo para o extrato com base no banco e no período das transações.

    Exemplos:
        transações em março/2025                 → "Itaú Mar 2025"
        transações de jan/2025 a mar/2025         → "Itaú Jan - Mar 2025"
        transações de nov/2024 a fev/2025         → "Inter Nov 2024 - Fev 2025"

    Args:
        banco_key: chave interna do banco (ex: 'itau', 'inter')
        transacoes: lista de transações extraídas

    Returns:
        Nome sugerido para o arquivo (sem extensão).
    """
    nome_banco = _NOME_BANCO_EXIBICAO.get(banco_key, banco_key.capitalize())

    if not transacoes:
        return nome_banco

    datas_validas: list[tuple[int, int, int]] = []  # (ano, mes, dia)
    for t in transacoes:
        data_str = str(t.get('data') or '')
        partes = data_str.split('/')
        if len(partes) == 3:
            try:
                dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
                if 1 <= mes <= 12 and 2000 <= ano <= 2100:
                    datas_validas.append((ano, mes, dia))
            except (ValueError, TypeError):
                pass

    if not datas_validas:
        return nome_banco

    datas_validas.sort()
    ano_ini, mes_ini, _ = datas_validas[0]
    ano_fim, mes_fim, _ = datas_validas[-1]

    if ano_ini == ano_fim and mes_ini == mes_fim:
        # Período de um único mês
        return f'{nome_banco} {_MESES_PT[mes_ini]} {ano_ini}'

    if ano_ini == ano_fim:
        # Mesmo ano, meses diferentes
        return f'{nome_banco} {_MESES_PT[mes_ini]} - {_MESES_PT[mes_fim]} {ano_ini}'

    # Anos diferentes
    return f'{nome_banco} {_MESES_PT[mes_ini]} {ano_ini} - {_MESES_PT[mes_fim]} {ano_fim}'


def aplicar_categorias(transacoes: list) -> list:
    """
    Aplica categorias inteligentes às transações com base nas descrições.

    Usa dois níveis de classificação:
    1ª camada – dicionários temáticos por palavra-chave
    2ª camada – análise de transferências (PJ vs PF)

    Args:
        transacoes: Lista de dicts de transação (modificada in-place).

    Returns:
        A mesma lista com o campo 'categoria' preenchido.
    """
    regras_saida = {
        'Alimentação / Restaurantes': [
            'ifood', 'rappi', 'restaurante', 'padaria', 'pizzaria', 'lanchonete',
            'mcdonalds', 'burger king', 'rotisserie', 'rotisseria', 'snack', 'bar',
            'oakberry', 'starbucks', 'kfc', 'subway', 'outback', 'habibs', 'bobs',
            'comercio de alimentos', 'doceria', 'sorveteria'
        ],
        'Supermercado / Mercearia': [
            'mercado', 'supermercado', 'sonda', 'carrefour', 'extra', 'pao de acucar',
            'atacadao', 'assai', 'tenda', 'dia%', 'hortifruti', 'atacadista', 'mercearia',
            'sams club', 'makro'
        ],
        'Transporte / Mobilidade': [
            'uber', '99app', '99 pop', 'posto', 'combustivel', 'estacionamento',
            'concessionaria', 'pedagio', 'sem parar', 'veloe', 'conectcar', 'localiza',
            'movida', 'ipiranga', 'shell', 'petrobras', 'br distribuidora', 'nupay uber',
            '99tecnologia', 'app de transporte'
        ],
        'Saúde / Farmácia': [
            'drogaria', 'farmacia', 'hospital', 'clinica', 'unimed', 'odontologico',
            'drogasil', 'droga raia', 'pague menos', 'sao paulo', 'panvel', 'ultrafarma',
            'pacheco', 'onofre', 'exames', 'laboratorio'
        ],
        'Tecnologia / Assinaturas': [
            'google', 'aws', 'microsoft', 'apple', 'vercel', 'github', 'hostgator',
            'software', 'chatgpt', 'openai', 'netflix', 'spotify', 'amazon prime',
            'adobe', 'canva', 'digitalocean', 'rd station', 'mailchimp'
        ],
        'Marketing / Tráfego': [
            'facebook', 'meta', 'ads', 'instagram', 'tiktok', 'google ads', 'taboola'
        ],
        'Impostos / Taxas Bancárias': [
            'darf', 'das', 'simples nacional', 'fgts', 'inss', 'iptu', 'ipva',
            'taxa', 'tarifa', 'iof', 'pacote', 'manutencao conta', 'juros', 'multa', 'anuidade'
        ],
        'Folha de Pagamento / RH': [
            'salario', 'adiantamento', 'rescisao', 'holerite', 'pro labore',
            'adiantamento salarial', 'vale transporte', 'vale refeicao', 'ticket', 'sodexo', 'alelo'
        ],
        'Despesas de Escritório / Utilidades': [
            'kalunga', 'papelaria', 'enel', 'sabesp', 'copel', 'cemig', 'light',
            'vivo', 'claro', 'tim', 'oi', 'correios', 'internet', 'energia', 'agua'
        ]
    }

    termos_transferencia = [
        'pix', 'ted', 'doc', 'transferencia', 'pagamento de boleto', 'nupay', 'pagseguro', 'mercado pago'
    ]

    for t in transacoes:
        desc_lower = t['descricao'].lower()
        categoria_definida = 'Outras Despesas'

        if t['tipo'] == 'entrada':
            if any(x in desc_lower for x in ['rendimento', 'aplicacao', 'cdb', 'poupanca', 'tesouro']):
                t['categoria'] = 'Rendimento de Investimentos'
            elif any(x in desc_lower for x in ['estorno', 'devolucao', 'reembolso']):
                t['categoria'] = 'Estornos e Reembolsos'
            else:
                t['categoria'] = 'Receita Operacional'
        elif t['tipo'] == 'posicao':
            t['categoria'] = 'Posição de Investimentos'
        else:
            encontrou = False

            # 1ª CAMADA: dicionários temáticos
            for categoria, palavras in regras_saida.items():
                if any(palavra in desc_lower for palavra in palavras):
                    categoria_definida = categoria
                    encontrou = True
                    break

            # 2ª CAMADA: análise de transferências
            if not encontrou:
                if any(termo in desc_lower for termo in termos_transferencia):
                    termos_pj = ['ltda', 's.a.', ' s/a', 'comercio', 'servicos', 'pagamentos', 'tecnologia', 'solucoes']
                    if any(cnpj_term in desc_lower for cnpj_term in termos_pj):
                        categoria_definida = 'Pagamento a Fornecedores (PIX/Boleto)'
                    else:
                        categoria_definida = 'Transferências / PIX (Pessoas)'
                else:
                    categoria_definida = 'Outras Despesas'

            t['categoria'] = categoria_definida

    return transacoes
