"""
expectativas_extratos.py — Expectativas individuais por PDF de extrato.

Cada PDF tem expectativas definidas: banco esperado, faixa de transacoes,
gap esperado, confianca minima, e opcionalmente SI/SF.

Sem expectativa = sem garantia = bug futuro.

BLOCO 8 FINAL.
"""

# Niveis de confianca para comparacao
NIVEIS = {"BAIXA": 0, "MEDIA": 1, "ALTA": 2}

EXPECTATIVAS = {
    # ═══ BRADESCO ═══════════════════════════════════════════════════════
    "Bradesco net.pdf": {
        "banco_contem": "bradesco",
        "transacoes_min": 70,
        "confianca_minima": "ALTA",
    },
    "Bradesco net2.pdf": {
        "banco_contem": "bradesco",
        "transacoes_min": 70,
        "confianca_minima": "ALTA",
    },
    "Bradesco5.pdf": {
        "banco_contem": "bradesco",
        "transacoes_min": 30,
        "confianca_minima": "ALTA",
    },
    "Bradesco_24032026_085239.pdf": {
        "banco_contem": "bradesco",
        "transacoes_min": 3,
        "confianca_minima": "ALTA",
    },
    "Agosto 2025.pdf": {
        "banco_contem": "bradesco",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    "Extrato dec25.pdf": {
        "banco_contem": "bradesco",
        "transacoes_min": 25,
        "confianca_minima": "ALTA",
    },
    "Extrato nov25.pdf": {
        "banco_contem": "bradesco",
        "transacoes_min": 15,
        "confianca_minima": "ALTA",
    },

    # ═══ ITAU ═══════════════════════════════════════════════════════════
    "Extrato Mensal_Fevereiro2025 - Consolidado.pdf": {
        "banco": "itau",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    "Extrato Mensal_Marco2025 - Consolidado.pdf": {
        "banco": "itau",
        "transacoes_min": 15,
        "confianca_minima": "ALTA",
    },
    "08_2025 Extrato Mensal.pdf": {
        "banco": "itau",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    "Extrato Mensal_Janeiro2025.pdf": {
        "banco": "itau",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    "Extrato Mensal_Maio2025.pdf": {
        "banco": "itau",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    "Extrato Mensal_Julho2025.pdf": {
        "banco": "itau",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    "Extrato Mensal_Junho2025.pdf": {
        "banco": "itau",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    "Extrato consolidado Setembro 2025.pdf": {
        "banco": "itau",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    # Itau com issues de saldo
    "Itaú .pdf": {
        "banco": "itau",
        "transacoes_min": 40,
        "confianca_minima": "MEDIA",
    },
    "Itaú 2.pdf": {
        "banco": "itau",
        "transacoes_min": 290,
        "confianca_minima": "MEDIA",
    },
    # Itau Empresas
    "Extrato_023700700976_04-03-2026_Parte1.pdf": {
        "banco": "itau_empresas",
        "transacoes_min": 3,
        "confianca_minima": "ALTA",
    },
    "Itaú empresas.pdf": {
        "banco": "itau_empresas",
        "transacoes_min": 290,
        "confianca_minima": "MEDIA",
    },
    # Itau N2
    "Extrato_0349_998856_27-01-2026.pdf": {
        "banco": "itau_n2",
        "transacoes_min": 0,
        "confianca_minima": "MEDIA",
        "nota": "desconhecido por encoding, agora detecta como itau_n2",
    },
    "Extrato_0349_998856_27-01-2026_1.pdf": {
        "banco_contem": "santander",  # detected as santander due to content
        "transacoes_min": 150,
        "confianca_minima": "MEDIA",
    },
    "Extrato_8886_998841_27-03-2026.pdf": {
        "banco": "itau_n2",
        "transacoes_min": 200,
        "confianca_minima": "ALTA",
    },
    # Itau OCR
    "Itaú 07828-5.pdf": {"ocr_necessario": True},
    "Itaú 07828-5_1.pdf": {"ocr_necessario": True},
    "Itaú 09089-2.pdf": {"ocr_necessario": True},
    # Itau CID-encoded
    "Extrato Mensal_Novembro2025 - Consolidado.pdf": {"ocr_necessario": True},
    "Extrato Mensal_Outubro2025 - Consolidado.pdf": {"ocr_necessario": True},
    "Extrato Mensal_Setembro2025 - Consolidado.pdf": {"ocr_necessario": True},

    # ═══ NUBANK ═════════════════════════════════════════════════════════
    "Nubank.pdf": {
        "banco": "nubank",
        "transacoes_min": 80,
        "confianca_minima": "ALTA",
    },
    "Nubank 2.pdf": {
        "banco": "nubank",
        "transacoes_min": 70,
        "confianca_minima": "ALTA",
    },
    "NU_115179195_01DEZ2025_31DEZ2025.pdf": {
        "banco": "nubank",
        "transacoes_min": 190,
        "confianca_minima": "ALTA",
    },
    "NU_115179195_01NOV2025_30NOV2025.pdf": {
        "banco": "nubank",
        "transacoes_min": 190,
        "confianca_minima": "ALTA",
    },
    "NU_115179195_01SET2025_30SET2025.pdf": {
        "banco": "nubank",
        "transacoes_min": 180,
        "confianca_minima": "ALTA",
    },
    "NU_587637138_01JAN2025_31JAN2025.pdf": {
        "banco": "nubank",
        "transacoes_min": 80,
        "confianca_minima": "ALTA",
    },
    "NU_658487598_01JAN2025_31DEZ2025.pdf": {
        "banco": "nubank",
        "transacoes_min": 55,
        "confianca_minima": "ALTA",
    },

    # ═══ BB ══════════════════════════════════════════════════════════════
    "Extrato Dezembro de 2025.pdf": {
        "banco": "bb",
        "transacoes_min": 185,
        "confianca_minima": "MEDIA",
    },
    "Extrato Junho.pdf": {
        "banco": "bb",
        "transacoes_min": 55,
        "confianca_minima": "MEDIA",
    },
    "Extrato Outubro de 2025.pdf": {
        "banco": "bb",
        "transacoes_min": 128,
        "confianca_minima": "MEDIA",
    },
    "Extrato de Agosto de 2025.pdf": {
        "banco": "bb",
        "transacoes_min": 65,
        "confianca_minima": "MEDIA",
    },
    "Extrato de setembro de 2025.pdf": {
        "banco": "bb",
        "transacoes_min": 100,
        "confianca_minima": "MEDIA",
    },
    "Extrato novembro de 2025.pdf": {
        "banco": "bb",
        "transacoes_min": 120,
        "confianca_minima": "ALTA",
    },

    # ═══ SANTANDER ═══════════════════════════════════════════════════════
    "Santander pf .pdf": {
        "banco": "santander_consolidado",
        "transacoes_min": 220,
        "confianca_minima": "ALTA",
    },
    "Santander pf 2.pdf": {
        "banco": "santander_consolidado",
        "transacoes_min": 190,
        "confianca_minima": "ALTA",
    },
    "Santander DLS 13006797-5.pdf": {
        "banco": "santander",
        "transacoes_min": 14,
        "confianca_minima": "MEDIA",
    },
    "Santander DLS 13006797-5_1.pdf": {
        "banco": "santander",
        "transacoes_min": 8,
        "confianca_minima": "MEDIA",
    },
    "Santander empresas 2.pdf": {
        "banco": "santander",
        "transacoes_min": 25,
        "confianca_minima": "MEDIA",
    },
    "B2S.pdf": {
        "banco": "santander",
        "transacoes_min": 44,
        "confianca_minima": "MEDIA",
    },
    "Empresarial 3.pdf": {
        "banco": "santander_empresas",
        "transacoes_min": 1,
        "confianca_minima": "MEDIA",
    },
    "Santander empresarial .pdf": {
        "banco": "santander_empresas",
        "transacoes_min": 1,
        "confianca_minima": "MEDIA",
    },
    "Santander empresarial 2.pdf": {
        "banco": "santander_empresas",
        "transacoes_min": 1,
        "confianca_minima": "MEDIA",
    },
    "junho 2025.pdf": {
        "banco": "santander_empresas",
        "transacoes_min": 1,
        "confianca_minima": "MEDIA",
    },
    "extrato-pj-12_02_2026-15h49m23s.pdf": {
        "banco": "santander",
        "transacoes_min": 25,
        "confianca_minima": "MEDIA",
    },
    "extrato-pj-12_02_2026-15h54m06s.pdf": {
        "banco": "santander",
        "transacoes_min": 40,
        "confianca_minima": "MEDIA",
    },
    "pdf_gerado.pdf": {
        "banco": "mercado_pago",
        "transacoes_min": 0,
        "confianca_minima": "BAIXA",
        "nota": "PDF gerado por sistema, sem transacoes reais",
    },
    "pdf_gerado__1_.pdf": {
        "banco": "santander_consolidado",
        "transacoes_min": 220,
        "confianca_minima": "ALTA",
    },
    "pdf_gerado__2_.pdf": {
        "banco": "santander_consolidado",
        "transacoes_min": 190,
        "confianca_minima": "ALTA",
    },

    # ═══ PAGBANK ═════════════════════════════════════════════════════════
    "Extrato da Conta - Julho.2025.pdf": {
        "banco": "pagbank",
        "transacoes_min": 210,
        "confianca_minima": "MEDIA",
    },
    "Extrato da Conta - Junho.2025.pdf": {
        "banco": "pagbank",
        "transacoes_min": 210,
        "confianca_minima": "MEDIA",
    },

    # ═══ STONE ═══════════════════════════════════════════════════════════
    "Extrato Jan a Mar.pdf": {
        "banco": "stone",
        "transacoes_min": 100,
        "confianca_minima": "MEDIA",
    },
    "Extrato Stone.pdf": {
        "banco": "stone",
        "transacoes_min": 200,
        "confianca_minima": "MEDIA",
    },
    "Extrato.pdf": {
        "banco": "stone",
        "transacoes_min": 180,
        "confianca_minima": "MEDIA",
    },
    "Stone.pdf": {
        "banco": "stone",
        "transacoes_min": 450,
        "confianca_minima": "MEDIA",
    },
    "Outubro extrato-80EFCACA-84BF-450B-8269-F00090E6C79A.pdf": {
        "banco": "stone",
        "transacoes_min": 460,
        "confianca_minima": "MEDIA",
    },
    "extrato-26172B0E-E801-4EB1-99C5-13D61F66FDAD.pdf": {
        "banco": "stone",
        "transacoes_min": 600,
        "confianca_minima": "MEDIA",
    },
    "extrato-26172B0E-E801-4EB1-99C5-13D61F66FDAD_1.pdf": {
        "banco": "stone",
        "transacoes_min": 600,
        "confianca_minima": "MEDIA",
    },
    "extrato-BF509BF9-636E-45D5-94E2-C84F5113A0CF.pdf": {
        "banco": "stone",
        "transacoes_min": 450,
        "confianca_minima": "MEDIA",
    },
    "extrato-D1A65663-62E9-4992-94DC-1EAA5A8B498D.pdf": {
        "banco": "stone",
        "transacoes_min": 170,
        "confianca_minima": "MEDIA",
    },
    "extrato-D1A65663-62E9-4992-94DC-1EAA5A8B498D_1.pdf": {
        "banco": "stone",
        "transacoes_min": 170,
        "confianca_minima": "MEDIA",
    },

    # ═══ CORA ════════════════════════════════════════════════════════════
    "Extrato Mensal_Janeiro2025.pdf": {
        "banco": "itau",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
        "nota": "anteriormente detectado como cora (falso positivo ancoradouro)",
    },

    # ═══ BTG ═════════════════════════════════════════════════════════════
    "11 - novembro 2025.pdf": {
        "banco": "btg",
        "transacoes_min": 10,
        "confianca_minima": "MEDIA",
    },
    "12 - dezembro 2025 .pdf": {
        "banco": "btg",
        "transacoes_min": 10,
        "confianca_minima": "MEDIA",
    },

    # ═══ C6 BANK ═════════════════════════════════════════════════════════
    "Abr- Set 2025.pdf": {
        "banco": "c6bank",
        "transacoes_min": 230,
        "confianca_minima": "MEDIA",
    },

    # ═══ CAIXA ═══════════════════════════════════════════════════════════
    # ═══ SAFRA ═══════════════════════════════════════════════════════════
    "Safra.pdf": {
        "banco": "safra",
        "transacoes_min": 700,
        "confianca_minima": "MEDIA",
    },

    # ═══ INTER ═══════════════════════════════════════════════════════════
    "Inter.pdf": {"ocr_necessario": True},

    # ═══ SICREDI ═════════════════════════════════════════════════════════
    "EXTRATO SICREDI.pdf": {"ocr_necessario": True},

    # ═══ MERCADO PAGO ════════════════════════════════════════════════════
    # ═══ XP ══════════════════════════════════════════════════════════════

    # ═══ VETORIAL/OCR ════════════════════════════════════════════════════
    "Extrato Jan à Jul.pdf": {"ocr_necessario": True},
    "extrato 01.07.25 até 11.02.26.pdf": {"ocr_necessario": True},

    # ═══ test_extratos/ ═════════════════════════════════════════════════
    "2026 08 - Itau.pdf": {
        "banco": "itau_empresas",
        "transacoes_min": 8,
        "confianca_minima": "ALTA",
    },
    "BB Extrato Abril de 2025.pdf": {
        "banco": "bb",
        "transacoes_min": 85,
        "confianca_minima": "MEDIA",
    },
    "EXTRATO DEZ 2025.pdf": {
        "banco": "caixa",
        "transacoes_min": 10,
        "confianca_minima": "ALTA",
    },
    "Extrato Bradesco TLA - 11.25.pdf": {
        "banco_contem": "bradesco",
        "transacoes_min": 70,
        "confianca_minima": "ALTA",
    },
    "Extrato c6 Bank Dez.pdf": {
        "banco": "c6bank",
        "transacoes_min": 20,
        "confianca_minima": "MEDIA",
    },
    "Extrato mercado pago Nov.pdf": {
        "banco": "mercado_pago",
        "transacoes_min": 40,
        "confianca_minima": "ALTA",
    },
    "Extrato PagBank Novembro.pdf": {
        "banco": "pagbank",
        "transacoes_min": 20,
        "confianca_minima": "MEDIA",
    },
    "NU_446175809_01DEZ2023_31DEZ2023.pdf": {
        "banco": "nubank",
        "transacoes_min": 160,
        "confianca_minima": "ALTA",
    },
    "PA ITAU Extrato Mensal_Dezembro2025.pdf": {
        "banco": "itau",
        "transacoes_min": 60,
        "confianca_minima": "ALTA",
    },
    "XP Investimentos - Extrato Investimentos.pdf": {
        "banco": "xp_posicao",
        "transacoes_min": 30,
        "confianca_minima": "MEDIA",
    },
    "XP Investimentos - extrato de conta corrente.pdf": {
        "banco": "xp_extrato",
        "transacoes_min": 30,
        "confianca_minima": "MEDIA",
    },
    "20-867-988-fernando-augusto-iaconis-mauro_01012025_a_31122025_2caf22bc.pdf": {
        "banco": "cora",
        "transacoes_min": 80,
        "confianca_minima": "ALTA",
    },
    "EXTRATO SANTANDER CONTA MAX.pdf": {
        "banco": "santander_consolidado",
        "transacoes_min": 0,
        "confianca_minima": "BAIXA",
        "nota": "ContaMax sem transacoes extraiveis",
    },
    "12 - EXTRATO NX TRAVEL DEZEMBRO  2025.pdf": {
        "banco": "bb",
        "transacoes_min": 0,
        "confianca_minima": "BAIXA",
        "nota": "BB formato web com C/D — requer parser BB v2",
    },
    "ExtratoMY - zerado 0251_994174_12-03-2026.pdf": {
        "banco": "itau_n2",
        "transacoes_min": 0,
        "confianca_minima": "MEDIA",
        "nota": "Extrato legitimamente vazio (zerado)",
    },
    "Extrato-01-12-2025-a-31-12-2025-PDF.pdf": {
        "banco_contem": "inter",
        "transacoes_min": 5,
        "confianca_minima": "MEDIA",
    },
    "extrato-26172B0E-E801-4EB1-99C5-13D61F66FDAD.pdf": {
        "banco": "stone",
        "transacoes_min": 600,
        "confianca_minima": "MEDIA",
    },
}
