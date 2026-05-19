"""
Comparador de Regimes Tributarios.

Calcula carga tributaria em Simples, Presumido, Real e Reforma usando os
4 motores ja prontos. Retorna regime otimo + economia + alertas.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from services.contabil.core import (
    money_fiscal, rate, to_decimal,
    MemoriaCalculo, ResultadoCalculo, NormaContabil, VERSAO_CALCULO,
)
from services.contabil.simples_nacional import calcular_simples
from services.contabil.lucro_presumido import calcular_lucro_presumido, ReceitaPorAtividade
from services.contabil.lucro_real import calcular_lucro_real
from services.contabil.reforma import calcular_reforma, OperacaoReforma

_ZERO = Decimal("0")
_TETO_SIMPLES = Decimal("4800000")

ATIVIDADES_VALIDAS = frozenset({
    "comercio", "industria", "servicos", "transporte_cargas",
    "transporte_passageiros", "saude", "educacao", "combustiveis",
})

# Mapeamento atividade -> bases de presuncao LP
_MAPA_BASES_LP: dict[str, tuple[Decimal, Decimal]] = {
    "comercio":               (Decimal("0.08"), Decimal("0.12")),
    "industria":              (Decimal("0.08"), Decimal("0.12")),
    "transporte_cargas":      (Decimal("0.08"), Decimal("0.12")),
    "saude":                  (Decimal("0.08"), Decimal("0.12")),
    "transporte_passageiros": (Decimal("0.16"), Decimal("0.12")),
    "combustiveis":           (Decimal("0.016"), Decimal("0.12")),
    "servicos":               (Decimal("0.32"), Decimal("0.32")),
    "educacao":               (Decimal("0.32"), Decimal("0.32")),
}

# Mapeamento atividade -> anexo Simples
_MAPA_ANEXO: dict[str, str] = {
    "comercio": "I", "industria": "II", "servicos": "III",
    "saude": "III", "educacao": "III",
    "transporte_cargas": "III", "transporte_passageiros": "III",
    "combustiveis": "I",
}


@dataclass(frozen=True)
class PerfilEmpresa:
    receita_anual_projetada: Decimal
    atividade: str
    folha_pagamento_anual: Decimal
    margem_bruta_estimada: Decimal
    creditos_pis_cofins_anuais: Decimal = Decimal("0")
    despesas_indedutiveis_anuais: Decimal = Decimal("0")

    def __post_init__(self):
        if not isinstance(self.receita_anual_projetada, Decimal):
            object.__setattr__(self, "receita_anual_projetada", to_decimal(self.receita_anual_projetada))
        if not isinstance(self.folha_pagamento_anual, Decimal):
            object.__setattr__(self, "folha_pagamento_anual", to_decimal(self.folha_pagamento_anual))
        if not isinstance(self.margem_bruta_estimada, Decimal):
            object.__setattr__(self, "margem_bruta_estimada", to_decimal(self.margem_bruta_estimada))
        if not isinstance(self.creditos_pis_cofins_anuais, Decimal):
            object.__setattr__(self, "creditos_pis_cofins_anuais", to_decimal(self.creditos_pis_cofins_anuais))
        if not isinstance(self.despesas_indedutiveis_anuais, Decimal):
            object.__setattr__(self, "despesas_indedutiveis_anuais", to_decimal(self.despesas_indedutiveis_anuais))
        if self.atividade not in ATIVIDADES_VALIDAS:
            raise ValueError(f"atividade invalida: {self.atividade}. Permitidas: {sorted(ATIVIDADES_VALIDAS)}")
        if self.receita_anual_projetada < _ZERO:
            raise ValueError("receita_anual_projetada nao pode ser negativa")


@dataclass
class ComparativoRegimes:
    perfil_atividade: str
    simples: Optional[Decimal]
    presumido: Decimal
    real: Decimal
    reforma: Decimal
    regime_otimo: str
    economia_vs_pior: Decimal
    alertas: list[str]


def comparar_regimes(
    perfil: PerfilEmpresa,
    regime_atual: str = "",
    ano_reforma: int = 2033,
    periodo: str = "",
) -> ResultadoCalculo:
    avisos: list[str] = []
    rec_anual = money_fiscal(perfil.receita_anual_projetada)
    rec_mensal = money_fiscal(rec_anual / Decimal("12"))
    rec_trimestral = money_fiscal(rec_anual / Decimal("4"))

    resultados: dict[str, Decimal] = {}

    # -- Simples Nacional (se elegivel) ----------------------------------------
    simples_val: Optional[Decimal] = None
    if rec_anual <= _TETO_SIMPLES:
        anexo = _MAPA_ANEXO.get(perfil.atividade, "III")
        r_sn = calcular_simples(
            receita_mensal=rec_mensal, rbt12=rec_anual,
            anexo=anexo, folha_12m=perfil.folha_pagamento_anual,
        )
        das_anual = money_fiscal(r_sn.valor.das * Decimal("12"))
        simples_val = das_anual
        resultados["simples"] = das_anual

        if r_sn.valor.fator_r_aplicado:
            avisos.append(
                f"Fator R aplicado: folha >= 28% da receita. Redirecionado de Anexo V para III."
            )
        if rec_anual > Decimal("3600000"):
            avisos.append("Proximo do sublimite R$ 3.6M — ISS/ICMS excluidos do DAS.")
        if rec_anual > Decimal("4300000"):
            avisos.append("Proximo do teto R$ 4.8M — risco de exclusao do Simples Nacional.")
    else:
        avisos.append(f"Receita anual R$ {float(rec_anual):,.0f} > R$ 4.8M — Simples nao elegivel.")

    # -- Lucro Presumido -------------------------------------------------------
    base_irpj, base_csll = _MAPA_BASES_LP.get(perfil.atividade, (Decimal("0.32"), Decimal("0.32")))
    receita_lp = ReceitaPorAtividade(
        descricao=perfil.atividade, valor=rec_trimestral,
        base_presuncao_irpj=base_irpj, base_presuncao_csll=base_csll,
    )
    r_lp = calcular_lucro_presumido([receita_lp], trimestral=True)
    lp_anual = money_fiscal(r_lp.valor.total_tributos * Decimal("4"))
    resultados["presumido"] = lp_anual

    # -- Lucro Real ------------------------------------------------------------
    custos_trim = money_fiscal(rec_trimestral * (Decimal("1") - perfil.margem_bruta_estimada))
    lucro_contabil_trim = money_fiscal(rec_trimestral - custos_trim)
    adicoes_trim = []
    if perfil.despesas_indedutiveis_anuais > _ZERO:
        from services.contabil.lucro_real import AjusteLALUR
        adicoes_trim = [AjusteLALUR(
            "Despesas indedutiveis estimadas",
            money_fiscal(perfil.despesas_indedutiveis_anuais / Decimal("4")),
            "adicao", "RIR/2018 art. 352",
        )]
    creditos = []
    if perfil.creditos_pis_cofins_anuais > _ZERO:
        from services.contabil.lucro_real import CreditoPISCofins
        creditos = [CreditoPISCofins(
            "Creditos PIS/COFINS estimados",
            money_fiscal(perfil.creditos_pis_cofins_anuais / Decimal("4")),
            "insumos",
        )]
    r_lr = calcular_lucro_real(
        lucro_contabil=lucro_contabil_trim, receita_liquida=rec_trimestral,
        adicoes=adicoes_trim, creditos_pis_cofins=creditos, trimestral=True,
    )
    lr_anual = money_fiscal(r_lr.valor.total_tributos * Decimal("4"))
    resultados["real"] = lr_anual

    # -- Reforma Tributaria ----------------------------------------------------
    regime_reforma = "geral"
    if perfil.atividade in ("saude", "educacao"):
        regime_reforma = perfil.atividade
    op_ref = OperacaoReforma(perfil.atividade, rec_anual, regime_reforma)
    r_ref = calcular_reforma(
        [op_ref], ano=ano_reforma,
        base_credito=perfil.creditos_pis_cofins_anuais,
    )
    resultados["reforma"] = money_fiscal(r_ref.valor.total_tributos)

    # -- Regime otimo (INV-COMP-2) ---------------------------------------------
    candidatos = {k: v for k, v in resultados.items()}
    regime_otimo = min(candidatos, key=lambda k: candidatos[k])
    pior = max(candidatos.values())
    economia = money_fiscal(pior - candidatos[regime_otimo])

    comparativo = ComparativoRegimes(
        perfil_atividade=perfil.atividade,
        simples=simples_val, presumido=lp_anual,
        real=lr_anual, reforma=resultados["reforma"],
        regime_otimo=regime_otimo, economia_vs_pior=economia,
        alertas=avisos,
    )

    insumos = {k: v for k, v in resultados.items()}
    insumos["receita_anual"] = rec_anual
    memoria = MemoriaCalculo(
        insumos=insumos, formula="min(simples, presumido, real, reforma)",
        norma=NormaContabil.COSTUME, resultado=candidatos[regime_otimo],
    )
    return ResultadoCalculo(valor=comparativo, memoria=memoria, avisos=avisos)
