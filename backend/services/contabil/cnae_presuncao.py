"""
Tabela de mapeamento CNAE -> bases de presuncao do Lucro Presumido.

Cada entrada documenta a fundamentacao normativa (Lei 9.249/95) que
justifica a base de presuncao atribuida a atividade economica.

Fase 1 (BLOCO 3F.2): tabela hardcoded com os ~20 CNAEs mais comuns.
Fase 2 (futuro): campos base_presuncao_irpj / base_presuncao_csll
  no EmpresaFiscal, editaveis pelo contador via UI.
"""

from decimal import Decimal
from typing import NamedTuple


class BasesPresuncao(NamedTuple):
    """Resultado da inferencia de bases de presuncao para um CNAE."""
    base_irpj: Decimal
    base_csll: Decimal
    norma_aplicada: str
    eh_fallback: bool


# -- Fallback conservador (servicos em geral) ---------------------------------
_FALLBACK_IRPJ = Decimal("0.32")
_FALLBACK_CSLL = Decimal("0.32")
_FALLBACK_NORMA = (
    "Fallback conservador: Lei 9.249/95 art. 15 §1º III + art. 20 (servicos em geral)"
)

# -- Tabela CNAE -> bases de presuncao ----------------------------------------
# Fundamentacao:
#   IRPJ: Lei 9.249/95 art. 15 (caput = 8%) e art. 15 §1º (bases especificas)
#   CSLL: Lei 9.249/95 art. 20 (12% comercio/industria, 32% servicos)
#   Consolidacao: RIR/2018 art. 591 (tabela de presuncoes)
#
# Cada entrada cita o dispositivo legal especifico.

CNAE_PARA_PRESUNCAO: dict[str, dict] = {
    # ── Comercio varejista (8% IRPJ, 12% CSLL) ──────────────────────
    "4711-3/02": {
        "descricao": "Comercio varejista de mercadorias em geral, com predominancia de produtos alimenticios - supermercados",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "4712-1/00": {
        "descricao": "Comercio varejista de mercadorias em geral, com predominancia de produtos alimenticios - minimercados, mercearias e armazens",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "4713-0/01": {
        "descricao": "Lojas de departamentos ou magazines",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "4751-2/01": {
        "descricao": "Comercio varejista especializado de equipamentos e suprimentos de informatica",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "4753-9/00": {
        "descricao": "Comercio varejista especializado de eletrodomesticos e equipamentos de audio e video",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "4761-0/03": {
        "descricao": "Comercio varejista de artigos de papelaria",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "4771-7/01": {
        "descricao": "Comercio varejista de produtos farmaceuticos, sem manipulacao de formulas",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "4781-4/00": {
        "descricao": "Comercio varejista de artigos do vestuario e acessorios",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },

    # ── Comercio atacadista (8% IRPJ, 12% CSLL) ─────────────────────
    "4637-1/07": {
        "descricao": "Comercio atacadista de chocolates, confeitos, balas, bombons e semelhantes",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "4691-5/00": {
        "descricao": "Comercio atacadista de mercadorias em geral, com predominancia de produtos alimenticios",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },

    # ── Industria (8% IRPJ, 12% CSLL) ───────────────────────────────
    "1091-1/01": {
        "descricao": "Fabricacao de produtos de panificacao industrial",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },
    "2511-0/00": {
        "descricao": "Fabricacao de estruturas metalicas",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 caput + art. 20",
    },

    # ── Combustiveis (1.6% IRPJ, 12% CSLL) ──────────────────────────
    "4731-8/00": {
        "descricao": "Comercio varejista de combustiveis para veiculos automotores",
        "base_irpj": Decimal("0.016"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 §1º I + art. 20",
    },
    "4732-6/00": {
        "descricao": "Comercio varejista de lubrificantes",
        "base_irpj": Decimal("0.016"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 §1º I + art. 20",
    },

    # ── Transporte de passageiros (16% IRPJ, 12% CSLL) ──────────────
    "4921-3/01": {
        "descricao": "Transporte rodoviario coletivo de passageiros, com itinerario fixo, municipal",
        "base_irpj": Decimal("0.16"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 §1º II-a + art. 20",
    },
    "4922-1/01": {
        "descricao": "Transporte rodoviario coletivo de passageiros, com itinerario fixo, intermunicipal em regiao metropolitana",
        "base_irpj": Decimal("0.16"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 §1º II-a + art. 20",
    },

    # ── Servicos em geral (32% IRPJ, 32% CSLL) ─────────────────────
    "6201-5/01": {
        "descricao": "Desenvolvimento de programas de computador sob encomenda",
        "base_irpj": Decimal("0.32"),
        "base_csll": Decimal("0.32"),
        "norma": "Lei 9.249/95 art. 15 §1º III-a + art. 20",
    },
    "6202-3/00": {
        "descricao": "Desenvolvimento e licenciamento de programas de computador customizaveis",
        "base_irpj": Decimal("0.32"),
        "base_csll": Decimal("0.32"),
        "norma": "Lei 9.249/95 art. 15 §1º III-a + art. 20",
    },
    "6920-6/01": {
        "descricao": "Atividades de contabilidade",
        "base_irpj": Decimal("0.32"),
        "base_csll": Decimal("0.32"),
        "norma": "Lei 9.249/95 art. 15 §1º III-a + art. 20",
    },
    "6911-7/01": {
        "descricao": "Servicos advocaticios",
        "base_irpj": Decimal("0.32"),
        "base_csll": Decimal("0.32"),
        "norma": "Lei 9.249/95 art. 15 §1º III-a + art. 20",
    },

    # ── Servicos hospitalares (8% IRPJ, 12% CSLL) ───────────────────
    # IN RFB 1.234/2012 art. 30: servicos hospitalares — base 8% IRPJ
    "8610-1/01": {
        "descricao": "Atividades de atendimento hospitalar, exceto pronto-socorro e unidades para atendimento a urgencias",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 §1º III-a c/c IN RFB 1.234/2012 art. 30 + art. 20",
    },
    "8630-5/01": {
        "descricao": "Atividade medica ambulatorial com recursos para realizacao de procedimentos cirurgicos",
        "base_irpj": Decimal("0.08"),
        "base_csll": Decimal("0.12"),
        "norma": "Lei 9.249/95 art. 15 §1º III-a c/c IN RFB 1.234/2012 art. 30 + art. 20",
    },
}


def inferir_bases(cnae: str) -> BasesPresuncao:
    """
    Infere as bases de presuncao IRPJ e CSLL a partir do CNAE.

    Retorna BasesPresuncao com:
      - base_irpj: Decimal (0.016, 0.08, 0.16 ou 0.32)
      - base_csll: Decimal (0.12 ou 0.32)
      - norma_aplicada: str com citacao legal
      - eh_fallback: bool (True se CNAE nao encontrado na tabela)

    Quando eh_fallback=True, aplica-se o padrao conservador 32%/32%
    (servicos em geral). Isso garante que empresas com CNAE desconhecido
    nunca tenham tributo SUBESTIMADO, embora possam ter tributo
    superestimado ate que o cadastro seja corrigido.
    """
    cnae_limpo = cnae.strip() if cnae else ""

    if cnae_limpo in CNAE_PARA_PRESUNCAO:
        entry = CNAE_PARA_PRESUNCAO[cnae_limpo]
        return BasesPresuncao(
            base_irpj=entry["base_irpj"],
            base_csll=entry["base_csll"],
            norma_aplicada=entry["norma"],
            eh_fallback=False,
        )

    # Fallback conservador — servicos em geral (maior carga)
    return BasesPresuncao(
        base_irpj=_FALLBACK_IRPJ,
        base_csll=_FALLBACK_CSLL,
        norma_aplicada=_FALLBACK_NORMA,
        eh_fallback=True,
    )
