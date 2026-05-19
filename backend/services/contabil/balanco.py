"""
Motor de calculo do Balanco Patrimonial (BP).

Modulo isolado -- depende apenas de services.contabil.core.
Sem dependencia de database, models, routers, ou qualquer ORM.

Produz BP gerencial a partir dos saldos informados no LancamentoMensal.
Valida invariante Ativo == Passivo + PL, reporta gap sem corrigir.

Limitacoes transitorias (modelo atual):
  - ANC como bucket unico (sem desdobramento imobilizado/investimentos/intangivel)
  - Depreciacao acumulada inexistente no modelo (apenas D&A mensal = fluxo)
  - Lucros Acumulados informado manualmente (sem vinculo DRE -> PL)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from services.contabil.core import (
    money,
    to_decimal,
    MemoriaCalculo,
    ResultadoCalculo,
    NormaContabil,
    IntegridadeContabilError,
    assertir_invariante,
    VERSAO_CALCULO,
)

_ZERO = Decimal("0")
_TOL = money("0.01")


# -- Estruturas ----------------------------------------------------------------

@dataclass
class LinhaBP:
    """Uma linha do Balanco Patrimonial."""
    codigo: str
    descricao: str
    valor: Decimal
    grupo: str   # ativo_circulante | ativo_nao_circulante | passivo_circulante | passivo_nao_circulante | patrimonio_liquido
    nivel: int   # 1=total do grupo, 2=conta individual


@dataclass
class DepreciacaoAcumuladaObservada:
    """Acumulador parcial de D&A observada no historico do sistema."""
    valor: Decimal
    desde_periodo: str
    ate_periodo: str
    aviso: str


@dataclass
class BalancoPatrimonial:
    """BP completo com invariante e diagnostico."""
    periodo: str
    linhas: list[LinhaBP]
    # Totalizadores
    ativo_circulante: Decimal
    ativo_nao_circulante: Decimal
    ativo_total: Decimal
    passivo_circulante: Decimal
    passivo_nao_circulante: Decimal
    passivo_total: Decimal
    patrimonio_liquido: Decimal
    passivo_mais_pl: Decimal
    # Invariante
    invariante_atendida: bool
    gap_valor: Decimal
    gap_percentual: Decimal
    gap_natureza: str  # "equilibrado" | "ativo_maior" | "passivo_pl_maior"
    # D&A acumulada observada (informativo)
    depreciacao_acumulada_observada: Optional[DepreciacaoAcumuladaObservada]

    def assertir_fechamento(self, tolerancia: Decimal = _ZERO) -> None:
        """
        Levanta IntegridadeContabilError se Ativo != Passivo + PL.

        Uso:
          - Apresentacao (BP gerencial): NAO chamar. Reportar gap via campos.
          - Processos downstream (DFC reconciliado, encerramento de exercicio):
            chamar com tolerancia=money("0.01") para garantir base solida.
        """
        if abs(self.gap_valor) > tolerancia:
            raise IntegridadeContabilError(
                mensagem=f"Invariante BP violada: Ativo != Passivo + PL",
                esperado=self.passivo_mais_pl,
                obtido=self.ativo_total,
                diferenca=abs(self.gap_valor),
                contexto=f"BP {self.periodo} gap={self.gap_valor} natureza={self.gap_natureza}",
            )


# -- Extracao de campos --------------------------------------------------------

def _get(dados: dict[str, Any], campo: str) -> Decimal:
    v = dados.get(campo)
    if v is None:
        return _ZERO
    return to_decimal(v)


# -- Motor de calculo ----------------------------------------------------------

def calcular_balanco(
    dados: dict[str, Any],
    periodo: str = "",
    dados_anterior: Optional[dict[str, Any]] = None,
    dre_periodo: Optional[ResultadoCalculo] = None,
    historico_da: Optional[list[dict[str, Any]]] = None,
) -> ResultadoCalculo:
    """
    Calcula BP gerencial a partir de um dict de saldos.

    Parametros:
      dados: dict com chaves de LancamentoMensal (saldos do periodo).
      periodo: string descritiva ("2025-10").
      dados_anterior: saldos do mes anterior (para validacao cruzada DRE->LA).
      dre_periodo: ResultadoCalculo do motor DRE do mesmo periodo
                   (para validacao cruzada e avisos de D&A).
      historico_da: lista de dicts com pelo menos 'ano', 'mes',
                    'depreciacao_amortizacao' para calcular D&A acumulada observada.

    Retorna ResultadoCalculo com BalancoPatrimonial.
    Invariante reportada sem excecao (BP gerencial).
    """
    avisos: list[str] = []

    # -- Ativo Circulante ------------------------------------------------------
    cx = money(_get(dados, "caixa_equivalentes"))
    cr = money(_get(dados, "contas_receber"))
    est = money(_get(dados, "estoques"))
    oac = money(_get(dados, "outros_ativo_circ"))
    ativo_circulante = money(cx + cr + est + oac)

    # -- Ativo Nao Circulante (bucket unico) -----------------------------------
    anc = money(_get(dados, "ativo_nao_circulante"))

    ativo_total = money(ativo_circulante + anc)

    # -- Passivo Circulante ----------------------------------------------------
    forn = money(_get(dados, "fornecedores"))
    emp_cp = money(_get(dados, "emprestimos_cp"))
    trib = money(_get(dados, "tributos_pagar"))
    opc = money(_get(dados, "outros_passivo_circ"))
    passivo_circulante = money(forn + emp_cp + trib + opc)

    # -- Passivo Nao Circulante (bucket unico) ---------------------------------
    pnc = money(_get(dados, "passivo_nao_circulante"))

    passivo_total = money(passivo_circulante + pnc)

    # -- Patrimonio Liquido ----------------------------------------------------
    cap = money(_get(dados, "capital_social"))
    res = money(_get(dados, "reservas"))
    la = money(_get(dados, "lucros_acumulados"))
    patrimonio_liquido = money(cap + res + la)

    passivo_mais_pl = money(passivo_total + patrimonio_liquido)

    # -- Invariante Ativo == Passivo + PL --------------------------------------
    gap_valor = money(ativo_total - passivo_mais_pl)
    gap_abs = abs(gap_valor)
    invariante_atendida = gap_abs <= _TOL

    if gap_valor > _TOL:
        gap_natureza = "ativo_maior"
    elif gap_valor < -_TOL:
        gap_natureza = "passivo_pl_maior"
    else:
        gap_natureza = "equilibrado"

    gap_percentual = money(_ZERO)
    if passivo_mais_pl > _ZERO:
        gap_percentual = money(gap_abs / passivo_mais_pl * Decimal("100"))

    if not invariante_atendida:
        avisos.append(
            f"Balanco em desequilibrio. Diferenca de R$ {gap_abs:,.2f} entre "
            f"Ativo (R$ {ativo_total:,.2f}) e Passivo+PL (R$ {passivo_mais_pl:,.2f}). "
            f"BP gerencial — nao utilizar para fins legais ou fiscais sem reconciliacao contabil."
        )

    # -- Limitacoes transitorias -----------------------------------------------
    limitacoes = [
        "Ativo Nao Circulante apresentado como linha unica sem desdobramento em "
        "Realizavel a Longo Prazo, Investimentos, Imobilizado, Intangivel. "
        "CPC 26 (R2) par. 66 exige desdobramento para BP legal — "
        "disponivel apenas apos migracao do modelo (BLOCO 3K).",
    ]

    da_mensal = _get(dados, "depreciacao_amortizacao")
    if da_mensal > _ZERO:
        limitacoes.append(
            "Depreciacao acumulada nao disponivel no modelo. "
            f"D&A do periodo = R$ {da_mensal:,.2f}. "
            "ANC pode estar sobreavaliado."
        )

    limitacoes.append(
        "Lucros Acumulados informado manualmente, sem vinculo automatico "
        "com encerramento da DRE. Consistencia nao garantida."
    )

    # -- D&A acumulada observada (refinamento 1) --------------------------------
    depreciacao_acumulada_obs: Optional[DepreciacaoAcumuladaObservada] = None
    if historico_da and len(historico_da) > 0:
        total_da = _ZERO
        primeiro = None
        ultimo = None
        for h in historico_da:
            da_val = _get(h, "depreciacao_amortizacao")
            total_da += da_val
            p = f"{h.get('ano', '?')}-{int(h.get('mes', 0)):02d}"
            if primeiro is None:
                primeiro = p
            ultimo = p
        if total_da > _ZERO:
            depreciacao_acumulada_obs = DepreciacaoAcumuladaObservada(
                valor=money(total_da),
                desde_periodo=primeiro or "?",
                ate_periodo=ultimo or "?",
                aviso=(
                    "Acumulador parcial — reflete apenas D&A observada desde o primeiro "
                    "registro no sistema. Nao inclui depreciacao anterior a entrada da empresa "
                    "no Controllo. Imobilizado liquido real pode diferir."
                ),
            )

    # -- Validacao cruzada DRE -> Lucros Acumulados (refinamento 2) -------------
    if dados_anterior is not None and dre_periodo is not None:
        la_anterior = _get(dados_anterior, "lucros_acumulados")
        delta_la = la - money(la_anterior)
        rl_dre = dre_periodo.valor.resultado_liquido
        diff_la = abs(delta_la - rl_dre)
        if diff_la > _TOL:
            avisos.append(
                f"Lucros Acumulados variou R$ {delta_la:,.2f} no periodo, "
                f"mas o Resultado Liquido do mesmo periodo foi R$ {rl_dre:,.2f}. "
                f"Diferenca de R$ {diff_la:,.2f} nao explicada. Possiveis causas: "
                f"distribuicao de dividendos, ajuste manual, erro de digitacao."
            )

    # -- Aviso cruzado D&A vs ANC (refinamento 4) ------------------------------
    if dre_periodo is not None:
        da_dre = dre_periodo.valor.depreciacao_amortizacao
        if da_dre > _ZERO:
            avisos.append(
                f"Resultado Liquido foi impactado por D&A = R$ {da_dre:,.2f} no periodo. "
                f"Se esta D&A incide sobre ativos fora do sistema, imobilizado bruto real "
                f"pode estar significativamente acima do ANC exibido."
            )

    # -- Montar linhas ---------------------------------------------------------
    linhas = [
        # Ativo Circulante
        LinhaBP("AC.01", "Caixa e Equivalentes", cx, "ativo_circulante", 2),
        LinhaBP("AC.02", "Contas a Receber", cr, "ativo_circulante", 2),
        LinhaBP("AC.03", "Estoques", est, "ativo_circulante", 2),
        LinhaBP("AC.04", "Outros Ativos Circulantes", oac, "ativo_circulante", 2),
        LinhaBP("AC", "Total Ativo Circulante", ativo_circulante, "ativo_circulante", 1),
        # Ativo Nao Circulante
        LinhaBP("ANC.01", "Ativo Nao Circulante (nao desdobrado)", anc, "ativo_nao_circulante", 2),
        LinhaBP("ANC", "Total Ativo Nao Circulante", anc, "ativo_nao_circulante", 1),
        # Ativo Total
        LinhaBP("AT", "ATIVO TOTAL", ativo_total, "ativo_total", 1),
        # Passivo Circulante
        LinhaBP("PC.01", "Fornecedores", forn, "passivo_circulante", 2),
        LinhaBP("PC.02", "Emprestimos (CP)", emp_cp, "passivo_circulante", 2),
        LinhaBP("PC.03", "Tributos a Pagar", trib, "passivo_circulante", 2),
        LinhaBP("PC.04", "Outros Passivos Circulantes", opc, "passivo_circulante", 2),
        LinhaBP("PC", "Total Passivo Circulante", passivo_circulante, "passivo_circulante", 1),
        # Passivo Nao Circulante
        LinhaBP("PNC.01", "Passivo Nao Circulante", pnc, "passivo_nao_circulante", 2),
        LinhaBP("PNC", "Total Passivo Nao Circulante", pnc, "passivo_nao_circulante", 1),
        # Passivo Total
        LinhaBP("PT", "PASSIVO TOTAL", passivo_total, "passivo_total", 1),
        # Patrimonio Liquido
        LinhaBP("PL.01", "Capital Social", cap, "patrimonio_liquido", 2),
        LinhaBP("PL.02", "Reservas", res, "patrimonio_liquido", 2),
        LinhaBP("PL.03", "Lucros/Prejuizos Acumulados", la, "patrimonio_liquido", 2),
        LinhaBP("PL", "Total Patrimonio Liquido", patrimonio_liquido, "patrimonio_liquido", 1),
        # Passivo + PL
        LinhaBP("PPL", "PASSIVO + PATRIMONIO LIQUIDO", passivo_mais_pl, "passivo_mais_pl", 1),
    ]

    # -- Resultado -------------------------------------------------------------
    bp = BalancoPatrimonial(
        periodo=periodo,
        linhas=linhas,
        ativo_circulante=ativo_circulante,
        ativo_nao_circulante=anc,
        ativo_total=ativo_total,
        passivo_circulante=passivo_circulante,
        passivo_nao_circulante=pnc,
        passivo_total=passivo_total,
        patrimonio_liquido=patrimonio_liquido,
        passivo_mais_pl=passivo_mais_pl,
        invariante_atendida=invariante_atendida,
        gap_valor=gap_valor,
        gap_percentual=gap_percentual,
        gap_natureza=gap_natureza,
        depreciacao_acumulada_observada=depreciacao_acumulada_obs,
    )

    insumos = {
        "caixa_equivalentes": cx, "contas_receber": cr, "estoques": est,
        "outros_ativo_circ": oac, "ativo_nao_circulante": anc,
        "fornecedores": forn, "emprestimos_cp": emp_cp, "tributos_pagar": trib,
        "outros_passivo_circ": opc, "passivo_nao_circulante": pnc,
        "capital_social": cap, "reservas": res, "lucros_acumulados": la,
    }

    memoria = MemoriaCalculo(
        insumos=insumos,
        formula="AT = AC + ANC; PT = PC + PNC; PL = CS + Res + LA; Gap = AT - (PT + PL)",
        norma=NormaContabil.CPC_26_BP,
        resultado=gap_valor,
    )

    return ResultadoCalculo(
        valor=bp,
        memoria=memoria,
        avisos=avisos + limitacoes,
    )
