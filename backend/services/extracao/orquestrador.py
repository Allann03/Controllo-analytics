"""
orquestrador.py – Orquestracao de extracao de extratos bancarios.

Fluxo principal:
  extrair_extrato() -> detecta banco, instancia parser, valida saldos
  processar_extrato() -> wrapper para API que formata o resultado
  gerar_nome_extrato() -> nome amigavel baseado em banco + periodo
  aplicar_categorias() -> categorizacao heuristica de transacoes

Origem: extraido de services/extrator_pdf.py em S30 (Opcao A enxuta).

Re-import de _extrair_saldos_pdf vindo do modulo legado extrator_pdf:
intencional. Esta funcao (818 linhas) permanece em extrator_pdf.py
ate decomposicao dedicada em S30.5.
"""

from decimal import Decimal
import pdfplumber

from .registro import PARSERS, FALLBACK_PARSERS, _NOME_BANCO_EXIBICAO
from .detector import detectar_banco
from ..extrator_pdf import _extrair_saldos_pdf


# Limite de páginas por PDF processado (protege contra PDFs muito grandes)
MAX_PAGINAS_PDF = 500


_MESES_PT = [
    '', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
]


def extrair_extrato(pdf_path: str, banco_id: str = '', password: str | None = None) -> dict:
    """
    Ponto de entrada principal para extração de extratos bancários.

    Detecta o banco, instancia o parser correto, extrai transações,
    aplica categorias e calcula totais.

    Args:
        pdf_path: Caminho para o arquivo PDF.

    Returns:
        Dict com:
            banco         – nome do banco detectado
            transacoes    – lista de transações categorizadas
            total_entradas – soma das entradas
            total_saidas   – soma das saídas
            saldo_periodo  – total_entradas - total_saidas
            avisos         – lista de mensagens de aviso
            erro           – mensagem de erro (str) ou None
    """
    resultado: dict = {
        'banco': 'desconhecido',
        'transacoes': [],
        'total_entradas': 0.0,
        'total_saidas': 0.0,
        'total_posicao': 0.0,
        'saldo_periodo': 0.0,
        'saldo_inicial': None,
        'saldo_final': None,
        'avisos': [],
        'erro': None,
    }

    try:
        # Verifica se PDF está protegido e se a senha foi fornecida
        try:
            import pikepdf
            import os as _os_prepipeline
            try:
                pikepdf.open(pdf_path, password=password or '')
            except pikepdf.PasswordError:
                resultado['erro'] = 'PDF protegido por senha. Informe a senha correta para processar este extrato.'
                resultado['requer_senha'] = True
                return resultado
            except Exception as _e_prepipeline:
                print(
                    f"[PRE-PIPELINE-ERROR] arquivo={_os_prepipeline.path.basename(pdf_path)} "
                    f"erro_tipo={type(_e_prepipeline).__name__} "
                    f"erro_msg={str(_e_prepipeline)} "
                    f"pikepdf_version={pikepdf.__version__}",
                    flush=True,
                )
                raise
        except ImportError:
            pass  # pikepdf não instalado; prossegue com pdfplumber que lança erro similar

        # Verifica limite de páginas antes de processar
        try:
            with pdfplumber.open(pdf_path, password=password or '') as _pdf_check:
                n_paginas = len(_pdf_check.pages)
                if n_paginas > MAX_PAGINAS_PDF:
                    resultado['erro'] = (
                        f'PDF com {n_paginas} páginas excede o limite de '
                        f'{MAX_PAGINAS_PDF} páginas por arquivo. '
                        'Divida o extrato em arquivos menores.'
                    )
                    return resultado
        except Exception:
            pass  # Se falhar aqui, tenta processar mesmo assim

        # Usa banco_id fornecido manualmente; senão, detecta automaticamente
        banco_key = banco_id.strip().lower() if banco_id else detectar_banco(pdf_path, password=password)
        resultado['banco'] = banco_key

        if banco_key == 'desconhecido':
            resultado['erro'] = 'Banco não reconhecido. Verifique se o PDF é um extrato bancário suportado.'
            return resultado

        parser_cls = PARSERS.get(banco_key)
        if not parser_cls:
            resultado['erro'] = f'Parser não implementado para: {banco_key}'
            return resultado

        parser = parser_cls(pdf_path, password=password)
        transacoes_brutas = parser.extrair()
        resultado['avisos'] = parser.avisos

        # Se o parser primário não encontrou transações, tenta o fallback
        if not transacoes_brutas and banco_key in FALLBACK_PARSERS:
            fallback_key = FALLBACK_PARSERS[banco_key]
            fallback_cls = PARSERS.get(fallback_key)
            if fallback_cls:
                try:
                    parser_fb = fallback_cls(pdf_path, password=password)
                    transacoes_fb = parser_fb.extrair()
                    if transacoes_fb:
                        transacoes_brutas = transacoes_fb
                        resultado['avisos'] = parser_fb.avisos
                        resultado['avisos'].append(
                            f'Parser primário ({banco_key}) retornou 0 transações. '
                            f'Usando parser alternativo ({fallback_key}).'
                        )
                        banco_key = fallback_key
                        resultado['banco'] = banco_key
                except Exception as e_fb:
                    resultado['avisos'].append(f'Fallback {fallback_key} falhou: {e_fb}')

        # Filtra transações marcadas como 'ignorar'
        transacoes = [t for t in transacoes_brutas if t.get('tipo') != 'ignorar']

        # Aplica categorias
        transacoes = aplicar_categorias(transacoes)

        # Calcula totais (Decimal para precisão financeira)
        total_entradas = sum((t['valor'] for t in transacoes if t['tipo'] == 'entrada'), Decimal('0'))
        total_saidas = sum((t['valor'] for t in transacoes if t['tipo'] == 'saida'), Decimal('0'))
        total_posicao = sum((t['valor'] for t in transacoes if t['tipo'] == 'posicao'), Decimal('0'))
        # Soma do valor originalmente aplicado (campo extra presente em xp_posicao)
        total_aplicado = sum(
            (Decimal(str(t.get('valor_aplicado') or 0))
             for t in transacoes if t['tipo'] == 'posicao'),
            Decimal('0'),
        )

        # Extrai saldo_inicial e saldo_final diretamente do texto do PDF
        saldo_inicial, saldo_final = _extrair_saldos_pdf(pdf_path, banco_key, password=password)

        # Converte valor Decimal → float nas transações para serialização JSON
        for t in transacoes:
            if isinstance(t.get('valor'), Decimal):
                t['valor'] = float(t['valor'])
            if isinstance(t.get('valor_aplicado'), Decimal):
                t['valor_aplicado'] = float(t['valor_aplicado'])
        resultado['transacoes'] = transacoes
        resultado['total_entradas'] = float(round(total_entradas, 2))
        resultado['total_saidas'] = float(round(total_saidas, 2))
        resultado['total_posicao'] = float(round(total_posicao, 2))
        resultado['total_aplicado'] = float(round(total_aplicado, 2))
        resultado['saldo_periodo'] = float(round(total_entradas - total_saidas, 2))
        resultado['saldo_inicial'] = float(round(saldo_inicial, 2)) if saldo_inicial is not None else None
        # saldo_final: usa o valor extraído do PDF se disponível;
        # caso contrário calcula como saldo_inicial + saldo_periodo (se saldo_inicial presente)
        if saldo_final is not None:
            resultado['saldo_final'] = float(round(saldo_final, 2))
        elif saldo_inicial is not None:
            resultado['saldo_final'] = float(round(saldo_inicial + (total_entradas - total_saidas), 2))
        else:
            resultado['saldo_final'] = None

        # ── Verificação progressiva de saldos (informativa, nunca bloqueia) ──
        try:
            saldos_inter = parser._extrair_saldos_intermediarios()
            if saldos_inter:
                _si = Decimal(str(saldo_inicial)) if saldo_inicial is not None else None
                # Usa ULTIMO saldo de cada data
                ultimo_saldo_por_data: dict[str, Decimal] = {}
                for s in saldos_inter:
                    ultimo_saldo_por_data[s['data']] = Decimal(str(s['saldo']))
                # Agrupa transações por data
                tx_por_data: dict[str, list] = {}
                for t in transacoes:
                    tx_por_data.setdefault(t['data'], []).append(t)
                datas_ordenadas = sorted(
                    set(t['data'] for t in transacoes) | set(ultimo_saldo_por_data.keys()),
                    key=lambda d: (int(d[6:10]), int(d[3:5]), int(d[0:2]))
                )
                num_verificados = len(ultimo_saldo_por_data)

                # Se SI é None, tentar usar primeiro saldo intermediário como ponto de partida
                si_usado = _si
                si_fonte = 'pdf'
                if si_usado is None and ultimo_saldo_por_data:
                    primeira_data = datas_ordenadas[0] if datas_ordenadas else None
                    if primeira_data and primeira_data in ultimo_saldo_por_data:
                        si_usado = ultimo_saldo_por_data[primeira_data]
                        si_fonte = 'primeiro_saldo_intermediario'

                if si_usado is None:
                    # Não é possível verificar sem ponto de partida
                    resultado['verificacao_saldos'] = {
                        'saldo_inicial': None,
                        'saldo_inicial_encontrado': False,
                        'saldo_final_informado': float(round(Decimal(str(saldo_final)), 2)) if saldo_final is not None else None,
                        'saldo_final_calculado': None,
                        'conferencia_ok': None,
                        'divergencias': [],
                        'saldos_intermediarios_verificados': num_verificados,
                        'saldos_intermediarios_ok': 0,
                        'modo_saldo': 'indisponivel',
                        'aviso': 'Saldo inicial nao identificado neste extrato.',
                    }
                else:
                    # Bancos diferem: "Saldo do dia" pode ser ABERTURA (antes das tx)
                    # ou FECHAMENTO (após tx). Testamos ambos e usamos o melhor.
                    def _verificar(modo_pre: bool):
                        sc = Decimal(str(si_usado))
                        divs = []
                        ok_count = 0
                        started = si_fonte == 'pdf'  # Se SI veio do primeiro saldo, pular esse saldo
                        for data in datas_ordenadas:
                            if not started and data in ultimo_saldo_por_data:
                                started = True
                                # Pula o primeiro saldo (que é nosso ponto de partida)
                                for t in tx_por_data.get(data, []):
                                    v = Decimal(str(t['valor']))
                                    if t['tipo'] == 'entrada': sc += v
                                    elif t['tipo'] == 'saida': sc -= v
                                continue
                            if modo_pre and data in ultimo_saldo_por_data:
                                esperado = ultimo_saldo_por_data[data]
                                if abs(sc - esperado) > Decimal('0.02'):
                                    divs.append({'data': data, 'saldo_esperado': float(esperado),
                                                 'saldo_calculado': float(round(sc, 2)),
                                                 'diferenca': float(round(sc - esperado, 2))})
                                else:
                                    ok_count += 1
                            for t in tx_por_data.get(data, []):
                                v = Decimal(str(t['valor']))
                                if t['tipo'] == 'entrada': sc += v
                                elif t['tipo'] == 'saida': sc -= v
                            if not modo_pre and data in ultimo_saldo_por_data:
                                esperado = ultimo_saldo_por_data[data]
                                if abs(sc - esperado) > Decimal('0.02'):
                                    divs.append({'data': data, 'saldo_esperado': float(esperado),
                                                 'saldo_calculado': float(round(sc, 2)),
                                                 'diferenca': float(round(sc - esperado, 2))})
                                else:
                                    ok_count += 1
                        return sc, divs, ok_count

                    sc_post, divs_post, ok_post = _verificar(modo_pre=False)
                    sc_pre, divs_pre, ok_pre = _verificar(modo_pre=True)

                    if ok_post >= ok_pre:
                        saldo_calc, divergencias, saldos_ok, modo = sc_post, divs_post, ok_post, 'fechamento'
                    else:
                        saldo_calc, divergencias, saldos_ok, modo = sc_pre, divs_pre, ok_pre, 'abertura'

                _sf_info = float(round(Decimal(str(saldo_final)), 2)) if saldo_final is not None else None
                if si_usado is not None and 'verificacao_saldos' not in resultado:
                    resultado['verificacao_saldos'] = {
                        'saldo_inicial': float(round(si_usado, 2)),
                        'saldo_inicial_encontrado': si_fonte == 'pdf',
                        'saldo_final_informado': _sf_info,
                        'saldo_final_calculado': float(round(saldo_calc, 2)),
                        'conferencia_ok': len(divergencias) == 0,
                        'divergencias': divergencias,
                        'saldos_intermediarios_verificados': num_verificados,
                        'saldos_intermediarios_ok': saldos_ok,
                        'modo_saldo': modo,
                    }
        except Exception:
            pass  # Verificação é informativa, nunca bloqueia o fluxo

        # Backfill: se _extrair_saldos_pdf não encontrou saldo_inicial mas a
        # verificação progressiva inferiu um SI válido (ex: PagBank via saldo
        # fantasma), propaga para o campo principal do resultado.
        if saldo_inicial is None and 'verificacao_saldos' in resultado:
            _vs_si = resultado['verificacao_saldos'].get('saldo_inicial')
            if _vs_si is not None:
                saldo_inicial = Decimal(str(_vs_si))
                resultado['saldo_inicial'] = float(round(saldo_inicial, 2))
                # Recalcula saldo_final se estava None
                if resultado.get('saldo_final') is None:
                    resultado['saldo_final'] = float(round(
                        saldo_inicial + (total_entradas - total_saidas), 2
                    ))

        # Garante aviso padronizado para extratos sem transações
        if not transacoes:
            _aviso_zero = 'Extrato com saldo zero — nenhuma transação encontrada.'
            if not any('saldo zero' in av or 'nenhuma transação' in av
                       for av in resultado['avisos']):
                resultado['avisos'].append(_aviso_zero)

    except Exception as e:
        resultado['erro'] = f'Erro ao processar extrato: {str(e)}'

    return resultado


def processar_extrato(caminho_pdf: str, banco_id: str = '', password: str | None = None) -> dict:
    """
    Interface unificada para extração de extratos bancários.
    Chama extrair_extrato() e formata o resultado para a API.

    Returns:
        {
            "banco": str,
            "banco_id": str,
            "total_transacoes": int,
            "total_entradas": float,
            "total_saidas": float,   # valor absoluto (positivo)
            "saldo": float,
            "transacoes": list,
            "avisos": list,
            "erro": str | None
        }
    """
    resultado = extrair_extrato(caminho_pdf, banco_id=banco_id, password=password)

    if resultado.get("erro"):
        return resultado

    transacoes = resultado["transacoes"]
    total_entradas = resultado["total_entradas"]
    total_saidas = resultado["total_saidas"]

    total_posicao = resultado.get("total_posicao", 0.0)
    total_aplicado = resultado.get("total_aplicado", 0.0)

    return {
        "banco": resultado["banco"],
        "banco_id": resultado["banco"],
        "total_transacoes": len(transacoes),
        "total_entradas": round(total_entradas, 2),
        "total_saidas": round(abs(total_saidas), 2),
        "total_posicao": round(total_posicao, 2),
        "total_aplicado": round(total_aplicado, 2),
        "saldo": round(total_entradas - total_saidas, 2),
        "saldo_inicial": resultado.get("saldo_inicial"),
        "saldo_final": resultado.get("saldo_final"),
        "transacoes": transacoes,
        "avisos": resultado.get("avisos", []),
        "erro": None,
        **({"verificacao_saldos": resultado["verificacao_saldos"]} if "verificacao_saldos" in resultado else {}),
    }


def gerar_nome_extrato(banco_key: str, transacoes: list) -> str:
    """
    Gera um nome descritivo para o extrato com base no banco e no período das transações.

    Exemplos:
        transações em março/2025                 → "Itaú Mar 2025"
        transações de jan/2025 a mar/2025         → "Itaú Jan - Mar 2025"
        transações de nov/2024 a fev/2025         → "Inter Nov 2024 - Fev 2025"

    Args:
        banco_key: chave interna do banco (ex: 'itau', 'inter')
        transacoes: lista de transações extraídas

    Returns:
        Nome sugerido para o arquivo (sem extensão).
    """
    nome_banco = _NOME_BANCO_EXIBICAO.get(banco_key, banco_key.capitalize())

    if not transacoes:
        return nome_banco

    datas_validas: list[tuple[int, int, int]] = []  # (ano, mes, dia)
    for t in transacoes:
        data_str = str(t.get('data') or '')
        partes = data_str.split('/')
        if len(partes) == 3:
            try:
                dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
                if 1 <= mes <= 12 and 2000 <= ano <= 2100:
                    datas_validas.append((ano, mes, dia))
            except (ValueError, TypeError):
                pass

    if not datas_validas:
        return nome_banco

    datas_validas.sort()
    ano_ini, mes_ini, _ = datas_validas[0]
    ano_fim, mes_fim, _ = datas_validas[-1]

    if ano_ini == ano_fim and mes_ini == mes_fim:
        # Período de um único mês
        return f'{nome_banco} {_MESES_PT[mes_ini]} {ano_ini}'

    if ano_ini == ano_fim:
        # Mesmo ano, meses diferentes
        return f'{nome_banco} {_MESES_PT[mes_ini]} - {_MESES_PT[mes_fim]} {ano_ini}'

    # Anos diferentes
    return f'{nome_banco} {_MESES_PT[mes_ini]} {ano_ini} - {_MESES_PT[mes_fim]} {ano_fim}'


def aplicar_categorias(transacoes: list) -> list:
    """
    Aplica categorias inteligentes às transações com base nas descrições.

    Usa dois níveis de classificação:
    1ª camada – dicionários temáticos por palavra-chave
    2ª camada – análise de transferências (PJ vs PF)

    Args:
        transacoes: Lista de dicts de transação (modificada in-place).

    Returns:
        A mesma lista com o campo 'categoria' preenchido.
    """
    regras_saida = {
        'Alimentação / Restaurantes': [
            'ifood', 'rappi', 'restaurante', 'padaria', 'pizzaria', 'lanchonete',
            'mcdonalds', 'burger king', 'rotisserie', 'rotisseria', 'snack', 'bar',
            'oakberry', 'starbucks', 'kfc', 'subway', 'outback', 'habibs', 'bobs',
            'comercio de alimentos', 'doceria', 'sorveteria'
        ],
        'Supermercado / Mercearia': [
            'mercado', 'supermercado', 'sonda', 'carrefour', 'extra', 'pao de acucar',
            'atacadao', 'assai', 'tenda', 'dia%', 'hortifruti', 'atacadista', 'mercearia',
            'sams club', 'makro'
        ],
        'Transporte / Mobilidade': [
            'uber', '99app', '99 pop', 'posto', 'combustivel', 'estacionamento',
            'concessionaria', 'pedagio', 'sem parar', 'veloe', 'conectcar', 'localiza',
            'movida', 'ipiranga', 'shell', 'petrobras', 'br distribuidora', 'nupay uber',
            '99tecnologia', 'app de transporte'
        ],
        'Saúde / Farmácia': [
            'drogaria', 'farmacia', 'hospital', 'clinica', 'unimed', 'odontologico',
            'drogasil', 'droga raia', 'pague menos', 'sao paulo', 'panvel', 'ultrafarma',
            'pacheco', 'onofre', 'exames', 'laboratorio'
        ],
        'Tecnologia / Assinaturas': [
            'google', 'aws', 'microsoft', 'apple', 'vercel', 'github', 'hostgator',
            'software', 'chatgpt', 'openai', 'netflix', 'spotify', 'amazon prime',
            'adobe', 'canva', 'digitalocean', 'rd station', 'mailchimp'
        ],
        'Marketing / Tráfego': [
            'facebook', 'meta', 'ads', 'instagram', 'tiktok', 'google ads', 'taboola'
        ],
        'Impostos / Taxas Bancárias': [
            'darf', 'das', 'simples nacional', 'fgts', 'inss', 'iptu', 'ipva',
            'taxa', 'tarifa', 'iof', 'pacote', 'manutencao conta', 'juros', 'multa', 'anuidade'
        ],
        'Folha de Pagamento / RH': [
            'salario', 'adiantamento', 'rescisao', 'holerite', 'pro labore',
            'adiantamento salarial', 'vale transporte', 'vale refeicao', 'ticket', 'sodexo', 'alelo'
        ],
        'Despesas de Escritório / Utilidades': [
            'kalunga', 'papelaria', 'enel', 'sabesp', 'copel', 'cemig', 'light',
            'vivo', 'claro', 'tim', 'oi', 'correios', 'internet', 'energia', 'agua'
        ]
    }

    termos_transferencia = [
        'pix', 'ted', 'doc', 'transferencia', 'pagamento de boleto', 'nupay', 'pagseguro', 'mercado pago'
    ]

    for t in transacoes:
        desc_lower = t['descricao'].lower()
        categoria_definida = 'Outras Despesas'

        if t['tipo'] == 'entrada':
            if any(x in desc_lower for x in ['rendimento', 'aplicacao', 'cdb', 'poupanca', 'tesouro']):
                t['categoria'] = 'Rendimento de Investimentos'
            elif any(x in desc_lower for x in ['estorno', 'devolucao', 'reembolso']):
                t['categoria'] = 'Estornos e Reembolsos'
            else:
                t['categoria'] = 'Receita Operacional'
        elif t['tipo'] == 'posicao':
            t['categoria'] = 'Posição de Investimentos'
        else:
            encontrou = False

            # 1ª CAMADA: dicionários temáticos
            for categoria, palavras in regras_saida.items():
                if any(palavra in desc_lower for palavra in palavras):
                    categoria_definida = categoria
                    encontrou = True
                    break

            # 2ª CAMADA: análise de transferências
            if not encontrou:
                if any(termo in desc_lower for termo in termos_transferencia):
                    termos_pj = ['ltda', 's.a.', ' s/a', 'comercio', 'servicos', 'pagamentos', 'tecnologia', 'solucoes']
                    if any(cnpj_term in desc_lower for cnpj_term in termos_pj):
                        categoria_definida = 'Pagamento a Fornecedores (PIX/Boleto)'
                    else:
                        categoria_definida = 'Transferências / PIX (Pessoas)'
                else:
                    categoria_definida = 'Outras Despesas'

            t['categoria'] = categoria_definida

    return transacoes
