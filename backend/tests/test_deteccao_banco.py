"""
Sessão 17 — Testes de regressão para `detectar_banco` em `extrator_pdf.py`.

3 mis-routes corrigidos via endurecimento de assinaturas:
- B2S.pdf (PROMOVE BRASIL): santander -> bs2
- Bradesco_Net_Empresas.PDF (SEOLIN jan/2025): bradesco -> bradesco_net_empresas
- Santander_N1.pdf (LEKE Consolidado): mercado_pago -> santander_consolidado

A função `detectar_banco` recebe um path para PDF e abre via pdfplumber. Para
testar contra fixtures `.txt` raw (políticas da casa: zero PDFs binários no
git), os testes replicam EXATAMENTE a lógica de matching de `_ASSINATURAS` em
texto pré-extraído (lowercase). Não testam o fallback de filename hint, que é
testado pela detecção real em `pdfs_reais/` quando os PDFs estão presentes.
"""
from __future__ import annotations

import os

from services.extrator_pdf import _ASSINATURAS

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def detectar_banco_de_texto(texto: str) -> str:
    """Replica a lógica de matching de assinaturas em `detectar_banco`,
    operando direto sobre texto (sem abrir PDF)."""
    texto = texto.lower()
    for banco_key, term_sets in _ASSINATURAS:
        for terms in term_sets:
            if all(t in texto for t in terms):
                return banco_key
    return 'desconhecido'


def _load(name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, name), 'r', encoding='utf-8') as f:
        return f.read()


# ─────────────────────────────────────────────────────────────────────────────
# Testes positivos: cada mis-route deve agora detectar o banco correto
# ─────────────────────────────────────────────────────────────────────────────

def test_b2s_detecta_bs2():
    """B2S.pdf (PROMOVE BRASIL): antes caía em 'santander' por substring de
    'Bco Santander SA' em descrição de TED. Agora a regra santander exige
    'santander.com.br' ou 'banco santander', e bs2 é capturado por
    'empresas.bs2' / 'bs2.com.br'."""
    texto = _load('b2s_raw.txt')
    assert detectar_banco_de_texto(texto) == 'bs2'


def test_seolin_detecta_bradesco_net_empresas():
    """SEOLIN jan/2025 (Bradesco_Net_Empresas.PDF): antes caía em 'bradesco'
    via 'dcto.' porque 'bradesco' não aparece nas primeiras 3 páginas. Agora
    o set ['| conta total'] (cabeçalho 'Agência | Conta Total Disponível')
    captura todos os Net Empresas."""
    texto = _load('seolin_jan2025_raw.txt')
    assert detectar_banco_de_texto(texto) == 'bradesco_net_empresas'


def test_santander_n1_detecta_santander_consolidado():
    """Santander N1 (LEKE jan/2025): antes caía em 'mercado_pago' por
    substring 'mercadopago' em 'MERCADOPAGO COM REPRESENT' (descrição de
    PIX). Agora mercado_pago exige 'mercadopago.com'."""
    texto = _load('santander_consolidado_jan2025_raw.txt')
    assert detectar_banco_de_texto(texto) == 'santander_consolidado'


# ─────────────────────────────────────────────────────────────────────────────
# Testes de regressão: bancos já corretamente detectados continuam OK
# ─────────────────────────────────────────────────────────────────────────────

def test_regressao_cw_tour_continua_bradesco_net_empresas():
    """CW TOUR (fixture da Sessão 16) deve continuar detectando como
    bradesco_net_empresas (já casava antes via 'bradesco' + 'total dispon';
    agora também casa via '| conta total')."""
    texto = _load('cw_tour_jan2026_raw.txt')
    assert detectar_banco_de_texto(texto) == 'bradesco_net_empresas'


def test_regressao_tania_dez_continua_bradesco_net_empresas():
    """TANIA dez/2025 — fixture da Sessão 16. Antes era roteado para
    'bradesco' (genérico, ParserBradesco PF), agora vai para
    bradesco_net_empresas (parser correto)."""
    texto = _load('tania_dez2025_raw.txt')
    assert detectar_banco_de_texto(texto) == 'bradesco_net_empresas'


def test_regressao_tania_nov_continua_bradesco_net_empresas():
    """TANIA nov/2025 — mesma situação que TANIA dez."""
    texto = _load('tania_nov2025_raw.txt')
    assert detectar_banco_de_texto(texto) == 'bradesco_net_empresas'


def test_regressao_santander_ib_novo_nao_capturado_por_santander():
    """O texto do Santander IB Novo casa em 'internet banking empresarial'
    + 'saldo do dia r$' ANTES de chegar na regra 'santander' genérica. O
    endurecimento de 'santander' não afeta isso porque sant_ib_novo vem
    antes na ordem e tem assinatura própria."""
    fixture = os.path.join(FIXTURES_DIR, 'santander_ib_novo_raw.txt')
    if not os.path.exists(fixture):
        # fixture pré-existente não obrigatório; pula se ausente
        return
    with open(fixture, 'r', encoding='utf-8') as f:
        texto = f.read()
    assert detectar_banco_de_texto(texto) == 'santander_ib_novo'


# ─────────────────────────────────────────────────────────────────────────────
# Testes de comportamento das assinaturas (cobertura inline com strings curtas)
# ─────────────────────────────────────────────────────────────────────────────

def test_santander_signature_nao_casa_so_com_substring_em_descricao():
    """Garante que mencionar 'santander' apenas em descrição de transação
    (caso B2S, Bradesco com TED para Santander) NÃO dispara santander."""
    texto = (
        "extrato bancario - empresas\n"
        "saldo inicial r$ 100,00\n"
        "07/01/2025 ted enviada outra tit ib bco santander sa - karla pinto\n"
        "saldo final r$ 50,00\n"
    )
    # Não deve casar santander (não tem santander.com.br, banco santander, contamax)
    assert detectar_banco_de_texto(texto) != 'santander'


def test_santander_signature_casa_com_dominio():
    """Garante que santander.com.br no rodapé dispara santander."""
    texto = (
        "extrato santander\n"
        "saldo inicial r$ 100,00\n"
        "ouvidoria: santander.com.br/atendimento\n"
    )
    assert detectar_banco_de_texto(texto) == 'santander'


def test_mercado_pago_nao_casa_so_com_mercadopago_em_descricao():
    """Garante que 'MERCADOPAGO COM REPRESENT' em descrição de PIX (caso
    Santander N1) NÃO dispara mercado_pago."""
    texto = (
        "extrato consolidado inteligente\n"
        "santander.com.br\n"
        "08/01 pix enviado\n"
        "mercadopago com represent - 557,97\n"
    )
    assert detectar_banco_de_texto(texto) == 'santander_consolidado'


def test_mercado_pago_casa_com_dominio():
    """Garante que mercadopago.com (rodapé/header) dispara mercado_pago."""
    texto = (
        "extrato de conta\n"
        "saldo inicial r$ 100,00\n"
        "atendimento: mercadopago.com\n"
    )
    assert detectar_banco_de_texto(texto) == 'mercado_pago'


def test_bradesco_net_empresas_casa_sem_palavra_bradesco():
    """Garante que o cabeçalho '| conta total' (típico Net Empresas) sozinho
    detecta bradesco_net_empresas, mesmo sem 'bradesco' no texto (caso
    SEOLIN, TANIA dez/nov)."""
    texto = (
        "agencia | conta total disponivel (r$) total (r$)\n"
        "00504 | 0482282-0 2.063,86 327.685,85\n"
        "31/12/2024 saldo anterior 89.479,75\n"
    )
    assert detectar_banco_de_texto(texto) == 'bradesco_net_empresas'


def test_bs2_casa_com_empresas_bs2():
    """Garante que B2S real (com 'empresas.bs2' no rodapé) dispara bs2."""
    texto = (
        "extrato bancario - empresas\n"
        "saldo inicial r$ 100,00\n"
        "empresas.bs2.com\n"
    )
    assert detectar_banco_de_texto(texto) == 'bs2'
