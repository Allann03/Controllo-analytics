"""
detector.py – Deteccao de banco a partir do conteudo do PDF.

Centraliza:
- _ASSINATURAS: lista de assinaturas de texto por banco
- detectar_banco(): retorna banco_key (ou 'desconhecido')
- detectar_banco_com_confianca(): idem + nivel de confianca

Origem: extraido de services/extrator_pdf.py em S30 (Opcao A enxuta).
"""

import unicodedata
import pdfplumber

from .registro import _NOME_BANCO_EXIBICAO


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
