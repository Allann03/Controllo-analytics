"""
Sessão 18 — Validador de saldos pós-extração.

4 checks aplicados sobre o resultado da extração de um extrato:

1. Saldo total: SI + soma(valores assinados) ≈ SF
2. Saldos diários: para cada dia D em saldos_diarios, SI_D + soma(tx_D) ≈ SF_D
3. Continuidade: SF_D ≈ SI_{D+1}
4. Datas dentro do período pedido

Saída: dicionário com flags por check, listas de divergências e nível
preliminar (sem ainda decidir VERDE/AMARELO/VERMELHO — a decisão final fica
em `classificador_confianca.classificar`).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, TypedDict


TOL_SALDO = 0.01            # tolerância padrão de centavos
TOL_CONTINUIDADE = 0.50     # tolerância para rendimento overnight de fim de semana


class DiaSuspeito(TypedDict, total=False):
    data: date
    si_dia: float
    sf_dia: float
    sf_dia_calculado: float
    transacoes_dia: int
    gap: float


class RupturaContinuidade(TypedDict, total=False):
    data_anterior: date
    data_seguinte: date
    sf_anterior: float
    si_seguinte: float
    gap: float


class DataProblematica(TypedDict, total=False):
    data: date
    descricao: str
    motivo: str  # 'antes_periodo' | 'depois_periodo' | 'invalida'


class ResultadoValidacao(TypedDict):
    saldo_total_ok: bool
    saldo_total_gap: float
    saldos_diarios_ok: bool
    dias_suspeitos: list
    continuidade_ok: bool
    rupturas_continuidade: list
    datas_ok: bool
    datas_problematicas: list
    nivel: str          # 'VERDE' | 'AMARELO' | 'VERMELHO'  (preliminar)
    diagnostico: str


def _parse_data(d) -> Optional[date]:
    """Aceita date, datetime, 'YYYY-MM-DD', 'DD/MM/YYYY' ou 'DD/MM/YY'.
    Retorna None se inválida."""
    if d is None:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if not isinstance(d, str):
        return None
    s = d.strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _valor_assinado(tx: dict) -> float:
    """Devolve valor com sinal: entrada positivo, saída negativo. Trata NoneType
    e tipos faltantes de forma defensiva (se faltar 'tipo', assume sinal
    aparente do próprio valor; se valor já vier negativo, preserva)."""
    v = tx.get('valor')
    if v is None:
        return 0.0
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    tipo = (tx.get('tipo') or '').lower()
    if tipo in ('saida', 'saída', 'debito', 'débito'):
        return -abs(v)
    if tipo in ('entrada', 'credito', 'crédito'):
        return abs(v)
    # Sem tipo: confia no sinal do valor
    return v


def validar_extracao(
    transacoes: list,
    saldo_inicial: Optional[float],
    saldo_final: Optional[float],
    saldos_diarios: Optional[dict] = None,
    periodo_inicio: Optional[object] = None,
    periodo_fim: Optional[object] = None,
    tolerancia_saldo: float = TOL_SALDO,
    tolerancia_continuidade: float = TOL_CONTINUIDADE,
    banco: Optional[str] = None,
) -> ResultadoValidacao:
    """
    Args:
        transacoes: lista de dicts com pelo menos 'valor' e 'tipo' (entrada/saida).
            Pode ter 'data' para o Check 4.
        saldo_inicial: SI numérico (se None, Check 1 falha).
        saldo_final: SF numérico (se None, Check 1 falha).
        saldos_diarios: dict opcional `{date: {'si': float, 'sf': float}}` para
            os Checks 2 e 3. Se None ou vazio, Checks 2/3 são pulados (ok=True).
        periodo_inicio, periodo_fim: limites do período pedido para Check 4.
            Se None, Check 4 é pulado.
        tolerancia_saldo: gap máx em R$ para Checks 1 e 2.
        tolerancia_continuidade: gap máx em R$ para Check 3 (rendimento
            overnight de fim de semana entra aqui).
        banco: identificador do banco (ex: 'santander_empresas') para
            personalizar o diagnóstico quando o layout do PDF não expõe SI/SF
            (Sessão 19, Iter 2). Default None mantém comportamento genérico.

    Retorna ResultadoValidacao com flags + listas de divergências + nível
    preliminar (definitivo é decidido em classificador_confianca.classificar).
    """
    # ─── Check 1 — Saldo total ─────────────────────────────────────────────
    if saldo_inicial is None or saldo_final is None:
        saldo_total_ok = False
        saldo_total_gap = float('inf')
    else:
        soma = sum(_valor_assinado(t) for t in transacoes or [])
        sf_calc = saldo_inicial + soma
        saldo_total_gap = round(sf_calc - saldo_final, 2)
        saldo_total_ok = abs(saldo_total_gap) <= tolerancia_saldo

    # ─── Check 2 — Saldos diários ──────────────────────────────────────────
    dias_suspeitos: list = []
    if saldos_diarios:
        # Indexa transações por data parseada
        tx_por_dia: dict = {}
        for t in transacoes or []:
            d = _parse_data(t.get('data'))
            if d is None:
                continue
            tx_por_dia.setdefault(d, []).append(t)

        for d_raw, info in saldos_diarios.items():
            d = _parse_data(d_raw)
            if d is None:
                continue
            si_d = info.get('si') if isinstance(info, dict) else None
            sf_d = info.get('sf') if isinstance(info, dict) else None
            if si_d is None or sf_d is None:
                continue
            tx_dia = tx_por_dia.get(d, [])
            sf_calc = float(si_d) + sum(_valor_assinado(t) for t in tx_dia)
            gap = round(sf_calc - float(sf_d), 2)
            if abs(gap) > tolerancia_saldo:
                dias_suspeitos.append({
                    'data': d,
                    'si_dia': float(si_d),
                    'sf_dia': float(sf_d),
                    'sf_dia_calculado': round(sf_calc, 2),
                    'transacoes_dia': len(tx_dia),
                    'gap': gap,
                })
        saldos_diarios_ok = not dias_suspeitos
    else:
        saldos_diarios_ok = True  # sem dados = check pulado

    # ─── Check 3 — Continuidade entre dias ─────────────────────────────────
    rupturas: list = []
    if saldos_diarios:
        datas_ord = sorted(_parse_data(d) for d in saldos_diarios if _parse_data(d) is not None)
        for i in range(len(datas_ord) - 1):
            d_a = datas_ord[i]
            d_b = datas_ord[i + 1]
            sf_a = saldos_diarios.get(d_a, saldos_diarios.get(str(d_a), {})).get('sf')
            si_b = saldos_diarios.get(d_b, saldos_diarios.get(str(d_b), {})).get('si')
            if sf_a is None or si_b is None:
                continue
            gap = round(float(si_b) - float(sf_a), 2)
            if abs(gap) > tolerancia_continuidade:
                rupturas.append({
                    'data_anterior': d_a,
                    'data_seguinte': d_b,
                    'sf_anterior': float(sf_a),
                    'si_seguinte': float(si_b),
                    'gap': gap,
                })
        continuidade_ok = not rupturas
    else:
        continuidade_ok = True

    # ─── Check 4 — Datas dentro do período ────────────────────────────────
    datas_problematicas: list = []
    if periodo_inicio is not None or periodo_fim is not None:
        pi = _parse_data(periodo_inicio)
        pf = _parse_data(periodo_fim)
        for t in transacoes or []:
            d = _parse_data(t.get('data'))
            if d is None:
                datas_problematicas.append({
                    'data': None,
                    'descricao': str(t.get('descricao', ''))[:60],
                    'motivo': 'invalida',
                })
                continue
            if pi is not None and d < pi:
                datas_problematicas.append({
                    'data': d,
                    'descricao': str(t.get('descricao', ''))[:60],
                    'motivo': 'antes_periodo',
                })
            elif pf is not None and d > pf:
                datas_problematicas.append({
                    'data': d,
                    'descricao': str(t.get('descricao', ''))[:60],
                    'motivo': 'depois_periodo',
                })
        datas_ok = not datas_problematicas
    else:
        datas_ok = True

    # ─── Nível preliminar (definitivo decidido em classificador) ──────────
    if not saldo_total_ok or not datas_ok:
        nivel = 'VERMELHO'
    elif not saldos_diarios_ok or not continuidade_ok:
        nivel = 'AMARELO'
    else:
        nivel = 'VERDE'

    diagnostico = _diagnostico_curto(
        saldo_total_ok, saldo_total_gap,
        saldos_diarios_ok, dias_suspeitos,
        continuidade_ok, rupturas,
        datas_ok, datas_problematicas,
        banco=banco,
    )

    return {
        'saldo_total_ok': saldo_total_ok,
        'saldo_total_gap': saldo_total_gap,
        'saldos_diarios_ok': saldos_diarios_ok,
        'dias_suspeitos': dias_suspeitos,
        'continuidade_ok': continuidade_ok,
        'rupturas_continuidade': rupturas,
        'datas_ok': datas_ok,
        'datas_problematicas': datas_problematicas,
        'nivel': nivel,
        'diagnostico': diagnostico,
    }


def _diagnostico_curto(
    saldo_total_ok, saldo_total_gap,
    saldos_diarios_ok, dias_suspeitos,
    continuidade_ok, rupturas,
    datas_ok, datas_problematicas,
    banco: Optional[str] = None,
) -> str:
    """Mensagem concisa em PT-BR descrevendo o resultado da validação.

    Sessão 19, Iter 2: quando SI/SF ausentes E banco='santander_empresas',
    retorna mensagem acionável distinguindo "PDF sem dado" de "bug do parser"
    para que o usuário saiba pedir ao banco a versão correta. Não muda o
    nivel (continua VERMELHO) — apenas enriquece o diagnóstico.
    """
    if saldo_total_ok and saldos_diarios_ok and continuidade_ok and datas_ok:
        return 'Extração reconciliada: saldos e datas consistentes.'
    # Caso especial Sessão 19 — santander_empresas (formato App): layout do PDF
    # nunca expõe SI/SF, requer extrato Consolidado para reconciliação.
    if (
        not saldo_total_ok and saldo_total_gap == float('inf')
        and banco == 'santander_empresas'
    ):
        return (
            'extrato_sem_si_sf: este extrato (formato App do Santander '
            'Empresas) não inclui saldo inicial nem final, então não é '
            'possível reconciliar. Solicite ao banco o "Extrato Consolidado '
            'Inteligente" para uma análise completa.'
        )
    partes = []
    if not saldo_total_ok:
        if saldo_total_gap == float('inf'):
            partes.append('saldo inicial ou final ausente')
        else:
            partes.append(f'saldo total diverge em R$ {saldo_total_gap:+.2f}')
    if not saldos_diarios_ok:
        partes.append(f'{len(dias_suspeitos)} dia(s) com saldo divergente')
    if not continuidade_ok:
        partes.append(f'{len(rupturas)} ruptura(s) de continuidade entre dias')
    if not datas_ok:
        contagens: dict = {}
        for dp in datas_problematicas:
            contagens[dp.get('motivo', 'invalida')] = contagens.get(dp.get('motivo', 'invalida'), 0) + 1
        detalhes = ', '.join(f'{n} {m}' for m, n in contagens.items())
        partes.append(f'datas problemáticas ({detalhes})')
    return '; '.join(partes) + '.'
