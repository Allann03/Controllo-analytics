"""
Testes determinísticos do parser Santander Internet Banking Empresarial,
layout NOVO (Turno 3 da sprint de parsers).
"""

from pathlib import Path

import pytest

from services.parsers.santander_ib_novo import ParserSantanderIBNovo
from services.extrator_pdf import detectar_banco, _ASSINATURAS


FIXTURE_PATH = (
    Path(__file__).parent / 'fixtures' / 'santander_ib_novo_raw.txt'
)
SAMPLE_DLS_ANTIGO = (
    Path(__file__).parents[2]
    / 'docs' / 'diagnostico-parsers' / 'samples' / 'santander_ib_antigo.txt'
)
SAMPLE_CONSOLIDADO = (
    Path(__file__).parents[2]
    / 'docs' / 'diagnostico-parsers' / 'samples' / 'santander_consolidado.txt'
)


def _make_parser() -> ParserSantanderIBNovo:
    """Instancia o parser sem abrir PDF (uso direto de _parse_texto)."""
    p = ParserSantanderIBNovo.__new__(ParserSantanderIBNovo)
    p.pdf_path = ''
    p.password = None
    p.avisos = []
    return p


def _parse_fixture() -> list[dict]:
    p = _make_parser()
    return p._parse_texto(FIXTURE_PATH.read_text(encoding='utf-8'))


# ---------------------------------------------------------------------- #
# Bug 8a — bullet "•" / glifos PUA Wingdings                             #
# ---------------------------------------------------------------------- #


def test_remove_pua_prefix_e_extrai_descricao_limpa():
    """Glifos PUA (U+F12E crédito, U+F131 débito) no início da linha
    são descartados — não aparecem na descrição final."""
    p = _make_parser()
    linha = ' 31/01/2025 Resgate contamax automatico R$ 217,40'
    txs = p._parse_texto(linha)
    assert len(txs) == 1
    desc = txs[0]['descricao']
    assert desc == 'Resgate contamax automatico'
    assert '' not in desc
    assert '' not in desc


def test_pua_credito_e_debito_classificam_pelo_sinal_nao_pelo_glifo():
    """O tipo é determinado pelo sinal '- R$', não pelo glifo PUA.
    O glifo é apenas decorativo após o pdfplumber emiti-lo."""
    p = _make_parser()
    # Glifo de "crédito" (U+F12E) MAS com sinal '- R$' → deve ser saída.
    linha = ' 31/01/2025 Inversao deliberada R$ teste - R$ 100,00'
    txs = p._parse_texto(linha)
    assert len(txs) == 1
    assert txs[0]['tipo'] == 'saida'


def test_linha_sem_pua_ainda_e_parseada():
    """As linhas L60 e L122 do fixture chegam sem PUA (artefato do
    pdfplumber em quebras de página). Mesmo sem o glifo, devem ser
    interpretadas como transação."""
    p = _make_parser()
    linha = (
        '22/01/2025 Pagamento de boleto outros bancos '
        'Sindicato dos trabalhador - R$ 129,74'
    )
    txs = p._parse_texto(linha)
    assert len(txs) == 1
    assert txs[0]['data'] == '22/01/2025'
    assert txs[0]['tipo'] == 'saida'
    assert float(txs[0]['valor']) == pytest.approx(129.74)


# ---------------------------------------------------------------------- #
# Bug 8b — sinal "- R$" com espaço                                       #
# ---------------------------------------------------------------------- #


def test_credito_sem_sinal_eh_entrada():
    p = _make_parser()
    linha = ' 31/01/2025 Pix recebido 06825343157 R$ 165,00'
    txs = p._parse_texto(linha)
    assert len(txs) == 1
    assert txs[0]['tipo'] == 'entrada'
    assert float(txs[0]['valor']) == pytest.approx(165.00)
    assert txs[0]['descricao'] == 'Pix recebido 06825343157'


def test_debito_com_traco_espaco_R_eh_saida():
    p = _make_parser()
    linha = (
        ' 31/01/2025 Pix enviado Joice roberta alves - R$ 862,40'
    )
    txs = p._parse_texto(linha)
    assert len(txs) == 1
    assert txs[0]['tipo'] == 'saida'
    assert float(txs[0]['valor']) == pytest.approx(862.40)
    # O hífen separador NÃO deve sobrar no fim da descrição.
    assert txs[0]['descricao'] == 'Pix enviado Joice roberta alves'
    assert not txs[0]['descricao'].endswith('-')


def test_aplicacao_contamax_e_saida_nao_filtrada():
    """Movimentações ContaMax (Aplicação/Resgate) são transações reais
    no IB novo e devem ser preservadas, ao contrário do parser
    DLS antigo que as filtra como movimentação interna."""
    p = _make_parser()
    txt = (
        ' 30/01/2025 Aplicacao contamax - R$ 480,00\n'
        ' 31/01/2025 Resgate contamax automatico R$ 217,40\n'
    )
    txs = p._parse_texto(txt)
    assert len(txs) == 2
    aplic = next(t for t in txs if 'Aplicacao' in t['descricao'])
    resgate = next(t for t in txs if 'Resgate' in t['descricao'])
    assert aplic['tipo'] == 'saida'
    assert float(aplic['valor']) == pytest.approx(480.00)
    assert resgate['tipo'] == 'entrada'
    assert float(resgate['valor']) == pytest.approx(217.40)


# ---------------------------------------------------------------------- #
# Bug 8c — datas em ordem descendente no PDF                             #
# ---------------------------------------------------------------------- #


def test_ordena_transacoes_ascendente_apos_parse():
    """O PDF lista 31/01 → 30/01 → ... → 02/01. Após parse a primeira
    tx deve ter a menor data e a última a maior."""
    txs = _parse_fixture()
    assert txs[0]['data'] == '02/01/2025'
    assert txs[-1]['data'] == '31/01/2025'
    # Datas estritamente não-decrescentes.
    def chave(t):
        d = t['data']
        return (int(d[6:10]), int(d[3:5]), int(d[0:2]))
    for i in range(1, len(txs)):
        assert chave(txs[i - 1]) <= chave(txs[i])


def test_sort_estavel_preserva_ordem_dentro_do_dia():
    """Sort por data deve ser estável: dentro do mesmo dia a ordem
    relativa do PDF (top-down) é preservada."""
    p = _make_parser()
    txt = (
        ' 30/01/2025 Aplicacao contamax - R$ 480,00\n'
        ' 30/01/2025 Pix recebido 09591302843 R$ 240,00\n'
        ' 30/01/2025 Pix recebido 33382229803 R$ 140,00\n'
    )
    txs = p._parse_texto(txt)
    assert [t['descricao'] for t in txs] == [
        'Aplicacao contamax',
        'Pix recebido 09591302843',
        'Pix recebido 33382229803',
    ]


# ---------------------------------------------------------------------- #
# Bug 8d — filtro "Saldo do dia" ancorado à data                          #
# ---------------------------------------------------------------------- #


def test_filtra_saldo_do_dia():
    p = _make_parser()
    txt = (
        '31/01/2025 Saldo do dia R$ 0,00\n'
        ' 31/01/2025 Pix recebido 06825343157 R$ 165,00\n'
        '30/01/2025 Saldo do dia R$ 1.234,56\n'
    )
    txs = p._parse_texto(txt)
    assert len(txs) == 1
    assert txs[0]['descricao'] == 'Pix recebido 06825343157'


def test_saldo_do_dia_so_filtra_quando_logo_apos_data():
    """O filtro é ancorado: 'Saldo do dia' apenas dentro de descrição
    de tx legítima (improvável, mas possível em produção) NÃO deve
    derrubar a transação."""
    p = _make_parser()
    linha = (
        ' 22/01/2025 Estorno saldo do dia anterior - R$ 50,00'
    )
    txs = p._parse_texto(linha)
    assert len(txs) == 1
    assert txs[0]['tipo'] == 'saida'
    assert txs[0]['descricao'] == 'Estorno saldo do dia anterior'
    assert float(txs[0]['valor']) == pytest.approx(50.00)


# ---------------------------------------------------------------------- #
# Filtro de headers de fixture (padrão Turno 1)                           #
# ---------------------------------------------------------------------- #


def test_filtra_headers_de_fixture():
    p = _make_parser()
    txt = (
        '# SOURCE: arquivo.pdf\n'
        '# PAGES: 4\n'
        '\n'
        '===== PAGE 1 =====\n'
        'Internet Banking Empresarial\n'
        ' 31/01/2025 Pix recebido 06825343157 R$ 165,00\n'
        '===== PAGE 2 =====\n'
        ' 30/01/2025 Aplicacao contamax - R$ 480,00\n'
    )
    txs = p._parse_texto(txt)
    assert len(txs) == 2
    assert {t['descricao'] for t in txs} == {
        'Pix recebido 06825343157',
        'Aplicacao contamax',
    }


def test_filtra_rodape_saldos_finais_da_pagina_4():
    """Linhas como 'A - Saldo de Conta Corrente R$ 0,00' NÃO começam
    com data DD/MM/YYYY, portanto não casam com o regex de transação."""
    p = _make_parser()
    txt = (
        'A - Saldo de Conta Corrente R$ 0,00\n'
        'B - Saldo Bloqueio Dia R$ 0,00\n'
        'L - Saldo disponível de Conta Corrente + Saldo R$ 6.929,84\n'
        'Central de Atendimento Santander Empresarial SAC\n'
        '4004-2125 (Regiões Metropolitanas) 0800 762 7777\n'
    )
    txs = p._parse_texto(txt)
    assert txs == []


# ---------------------------------------------------------------------- #
# Dedup cross-page                                                         #
# ---------------------------------------------------------------------- #


def test_dedup_cross_page_remove_duplicata_em_quebra_de_pagina():
    """Quando a última tx de uma página é idêntica à primeira da
    próxima, a duplicata é removida."""
    p = _make_parser()
    txt = (
        '===== PAGE 1 =====\n'
        '22/01/2025 Pagamento de boleto outros bancos '
        'Sindicato dos trabalhador - R$ 129,74\n'
        '===== PAGE 2 =====\n'
        ' 22/01/2025 Pagamento de boleto outros bancos '
        'Sindicato dos trabalhador - R$ 129,74\n'
        ' 22/01/2025 Compra cartao deb mc 22/01 autopostop3ltda - '
        'R$ 100,00\n'
    )
    txs = p._parse_texto(txt)
    assert len(txs) == 2
    assert float(txs[0]['valor']) == pytest.approx(129.74)
    assert txs[1]['descricao'].startswith('Compra cartao deb')


def test_mantem_duplicatas_legitimas_mesma_pagina():
    """L38 e L39 do fixture (27/01 Conselho Regional R$ 537,20 x2) são
    pagamentos repetidos reais, não artefato de quebra de página.
    Devem ser preservadas."""
    p = _make_parser()
    txt = (
        '===== PAGE 1 =====\n'
        ' 27/01/2025 Pagamento de boleto outros bancos '
        'Conselho regional de medi - R$ 537,20\n'
        ' 27/01/2025 Pagamento de boleto outros bancos '
        'Conselho regional de medi - R$ 537,20\n'
        ' 27/01/2025 Pagamento de boleto outros bancos '
        'Conselho regional de medi - R$ 1.506,20\n'
    )
    txs = p._parse_texto(txt)
    assert len(txs) == 3
    assert sum(1 for t in txs if float(t['valor']) == pytest.approx(537.20)) == 2
    assert sum(1 for t in txs if float(t['valor']) == pytest.approx(1506.20)) == 1


# ---------------------------------------------------------------------- #
# Validação completa contra o fixture                                     #
# ---------------------------------------------------------------------- #


def test_fixture_total_transacoes():
    """Fixture: 127 linhas de tx brutas - 2 dups cross-page = 125."""
    txs = _parse_fixture()
    assert len(txs) == 125


def test_fixture_total_por_data_apos_dedup():
    txs = _parse_fixture()
    from collections import Counter
    contagem = Counter(t['data'] for t in txs)
    assert dict(contagem) == {
        '02/01/2025': 7,
        '03/01/2025': 4,
        '06/01/2025': 11,
        '07/01/2025': 8,
        '08/01/2025': 3,    # 4 brutas - 1 dedup cross-page = 3
        '09/01/2025': 4,
        '10/01/2025': 3,
        '13/01/2025': 6,
        '14/01/2025': 6,
        '15/01/2025': 2,
        '16/01/2025': 7,
        '17/01/2025': 4,
        '20/01/2025': 11,
        '21/01/2025': 4,
        '22/01/2025': 6,    # 7 brutas - 1 dedup cross-page = 6
        '23/01/2025': 4,
        '24/01/2025': 3,
        '27/01/2025': 10,
        '28/01/2025': 8,
        '29/01/2025': 5,
        '30/01/2025': 4,
        '31/01/2025': 5,
    }


def test_fixture_distribuicao_entrada_saida():
    txs = _parse_fixture()
    entradas = [t for t in txs if t['tipo'] == 'entrada']
    saidas = [t for t in txs if t['tipo'] == 'saida']
    assert len(entradas) == 75
    assert len(saidas) == 50
    assert len(entradas) + len(saidas) == 125


def test_transacoes_iniciais_ascendente_lista_concreta():
    """As 10 primeiras transações em ordem ASC, conforme planejado."""
    txs = _parse_fixture()[:10]
    esperado = [
        ('02/01/2025', 'Resgate contamax automatico', 593.12, 'entrada'),
        ('02/01/2025', 'Pix recebido 28170728800', 240.00, 'entrada'),
        (
            '02/01/2025',
            'Pagamento de boleto outros bancos Elektro eletricidade e se',
            544.57, 'saida',
        ),
        (
            '02/01/2025',
            'Debito aut. telefone celular Claro movel',
            88.55, 'saida',
        ),
        (
            '02/01/2025',
            'Tarifa mensalidade pacote servicos Dezembro / 2024',
            165.00, 'saida',
        ),
        ('02/01/2025', 'Pix recebido 35472217814', 65.00, 'entrada'),
        (
            '02/01/2025',
            'Compra cartao deb mc 01/01 auto posto p3 ltda',
            100.00, 'saida',
        ),
        ('03/01/2025', 'Resgate contamax automatico', 576.00, 'entrada'),
        (
            '03/01/2025',
            'Compra cartao deb mc 03/01 dj ferramentas',
            26.00, 'saida',
        ),
        (
            '03/01/2025',
            'Compra cartao deb mc 03/01 auto posto pilott l',
            200.00, 'saida',
        ),
    ]
    obtido = [
        (t['data'], t['descricao'], float(t['valor']), t['tipo'])
        for t in txs
    ]
    assert obtido == esperado


def test_ultima_transacao_em_ordem_ascendente():
    txs = _parse_fixture()
    ultima = txs[-1]
    assert ultima['data'] == '31/01/2025'
    assert ultima['descricao'] == 'Pix recebido 36139140854'
    assert float(ultima['valor']) == pytest.approx(360.00)
    assert ultima['tipo'] == 'entrada'


def test_todas_transacoes_tem_banco_santander():
    txs = _parse_fixture()
    assert all(t['banco'] == 'Santander' for t in txs)


def test_todas_transacoes_tem_categoria_vazia_apos_parse():
    """O parser não preenche 'categoria'; isso é responsabilidade do
    aplicar_categorias() em extrator_pdf."""
    txs = _parse_fixture()
    assert all(t['categoria'] == '' for t in txs)


# ---------------------------------------------------------------------- #
# Roteamento: detectar_banco                                              #
# ---------------------------------------------------------------------- #


def _texto_simulando_pdf(caminho_sample: Path) -> str:
    """Lê um sample do diretório docs/diagnostico-parsers/samples e
    devolve o texto sem os headers de fixture, para simular o
    extract_text() do pdfplumber."""
    raw = caminho_sample.read_text(encoding='utf-8')
    linhas = []
    for ln in raw.splitlines():
        s = ln.strip()
        if s.startswith('#') or s.startswith('====='):
            continue
        linhas.append(ln)
    return '\n'.join(linhas)


def test_assinatura_santander_ib_novo_registrada_antes_de_santander():
    """A assinatura do IB novo deve estar no _ASSINATURAS antes de
    'santander_consolidado', 'santander_empresas' e 'santander' para
    impedir captura prematura."""
    chaves = [k for k, _ in _ASSINATURAS]
    idx_ib_novo = chaves.index('santander_ib_novo')
    assert idx_ib_novo < chaves.index('santander_consolidado')
    assert idx_ib_novo < chaves.index('santander_empresas')
    assert idx_ib_novo < chaves.index('santander')


def test_detectar_banco_classifica_ib_novo(tmp_path, monkeypatch):
    """Simula o detectar_banco() injetando texto do fixture IB novo
    como 'pdf' através de monkeypatch em pdfplumber.open."""
    texto = _texto_simulando_pdf(FIXTURE_PATH)
    _patch_pdfplumber_with_text(monkeypatch, texto)
    assert detectar_banco('fake.pdf') == 'santander_ib_novo'


def test_dls_antigo_nao_classifica_como_ib_novo(monkeypatch):
    """O DLS antigo (sample santander_ib_antigo.txt) não tem
    'saldo do dia r$', portanto não casa com a assinatura do IB novo."""
    texto = _texto_simulando_pdf(SAMPLE_DLS_ANTIGO)
    _patch_pdfplumber_with_text(monkeypatch, texto)
    banco = detectar_banco('fake.pdf')
    assert banco != 'santander_ib_novo'
    # DLS antigo é roteado pelo termo 'contamax' / 'santander' genérico.
    assert banco in ('santander', 'santander_empresas')


def test_consolidado_nao_classifica_como_ib_novo(monkeypatch):
    """Consolidado Inteligente não tem 'saldo do dia r$' (usa
    'SALDO EM DD/MM'), portanto não casa com a assinatura do IB novo.
    Esta é a proteção crítica para o Turno 4: ambos os layouts têm
    'Internet Banking Empresarial' no header, mas só o IB novo tem
    'Saldo do dia r$'."""
    texto = _texto_simulando_pdf(SAMPLE_CONSOLIDADO)
    _patch_pdfplumber_with_text(monkeypatch, texto)
    banco = detectar_banco('fake.pdf')
    assert banco != 'santander_ib_novo'


# ---------------------------------------------------------------------- #
# Helper: monkeypatch de pdfplumber                                        #
# ---------------------------------------------------------------------- #


class _FakePagina:
    def __init__(self, texto: str) -> None:
        self._texto = texto

    def extract_text(self) -> str:
        return self._texto


class _FakePdf:
    def __init__(self, texto: str) -> None:
        self.pages = [_FakePagina(texto)]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _patch_pdfplumber_with_text(monkeypatch, texto: str) -> None:
    import services.extrator_pdf as mod

    def _fake_open(_path, password=''):
        return _FakePdf(texto)

    monkeypatch.setattr(mod.pdfplumber, 'open', _fake_open)
