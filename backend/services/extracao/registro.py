"""
registro.py – Mapas de identificação e dispatch de parsers de banco.

Centraliza:
- Imports de todas as classes de parser
- PARSERS: banco_key -> classe (dispatch)
- FALLBACK_PARSERS: banco_key primario -> banco_key fallback (n2)
- _NOME_BANCO_EXIBICAO: banco_key -> nome amigavel para exibicao

Origem: extraido de services/extrator_pdf.py em S30 (Opcao A enxuta).
"""

from ..parsers.inter import ParserInter
from ..parsers.cora import ParserCora
from ..parsers.sicredi import ParserSicredi
from ..parsers.c6bank import ParserC6Bank
from ..parsers.pagbank import ParserPagBank
from ..parsers.mercado_pago import ParserMercadoPago
from ..parsers.caixa import ParserCaixa
from ..parsers.itau import ParserItau
from ..parsers.itau_empresas import ParserItauEmpresas
from ..parsers.bradesco import ParserBradesco
from ..parsers.stone import ParserStone
from ..parsers.sumup import ParserSumUp
from ..parsers.bb import ParserBB
from ..parsers.santander import ParserSantander
from ..parsers.santander_empresarial import ParserSantanderEmpresas
from ..parsers.xp_extrato import ParserXPExtrato
from ..parsers.xp_posicao import ParserXPPosicao
from ..parsers.nubank import ParserNubank
from ..parsers.bs2 import ParserBS2
from ..parsers.santander_consolidado import ParserSantanderConsolidado
from ..parsers.santander_ib_novo import ParserSantanderIBNovo
from ..parsers.bradesco_empresas.bradesco_net_empresas import ParserBradescoNetEmpresas
from ..parsers.n2.itau_n2 import ParserItauN2
from ..parsers.n2.inter_n2 import ParserInterN2
from ..parsers.n2.itau_empresas_n2 import ParserItauEmpresasN2
from ..parsers.santander_empresas.santander_empresas_v1 import ParserSantanderEmpresasV1
from ..parsers.santander_empresas.santander_empresas_v2 import ParserSantanderEmpresasV2
from ..parsers.safra import ParserSafra
from ..parsers.btg import ParserBTG


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
