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

from .extracao.registro import PARSERS, FALLBACK_PARSERS, _NOME_BANCO_EXIBICAO
from .extracao.detector import detectar_banco, detectar_banco_com_confianca, _ASSINATURAS

from .extracao.orquestrador import (
    extrair_extrato, processar_extrato, gerar_nome_extrato, aplicar_categorias,
    MAX_PAGINAS_PDF, _MESES_PT,
)
