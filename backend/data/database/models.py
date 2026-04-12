import logging
from sqlalchemy import Column, Integer, String, Boolean, Float, Numeric, ForeignKey, UniqueConstraint, Text, Index, event
from sqlalchemy.orm.attributes import get_history
from data.database.config import Base

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
#  MULTI-TENANT — Escritório (tenant raiz)
# ──────────────────────────────────────────────────────────────────

class Escritorio(Base):
    """Cada escritório de contabilidade é um tenant isolado."""
    __tablename__ = "escritorios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)                        # "Controllo BPO Analytics"
    slug = Column(String, unique=True, nullable=False, index=True)  # "controllobpo" — usado na URL/login
    plano = Column(String, default="trial")                      # trial | basico | profissional | enterprise
    max_empresas = Column(Integer, default=10)
    max_usuarios = Column(Integer, default=2)
    data_expiracao = Column(String, nullable=True)               # ISO date ou None = sem expiração
    ativo = Column(Boolean, default=True)
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    escritorio_id = Column(Integer, ForeignKey("escritorios.id"), nullable=True, index=True)
    nome = Column(String, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    is_master = Column(Boolean, default=False)    # N1: superadmin da plataforma inteira
    is_dono = Column(Boolean, default=False)      # Dono do escritório (primeiro admin criado)
    is_admin = Column(Boolean, default=False)
    is_ceo = Column(Boolean, default=False)       # CEO: nível acima de Admin, pode promover/revogar outros CEOs
    is_gestor = Column(Boolean, default=False)    # Gestor: acesso total exceto auditoria + pode designar tarefas
    is_aprovado = Column(Boolean, default=False)
    token_version = Column(Integer, default=0, nullable=False, server_default="0")
    nome_exibicao = Column(String, default="")   # nome de exibição / apelido
    cargo = Column(String, default="")            # cargo/função opcional

    __table_args__ = (
        UniqueConstraint("escritorio_id", "nome", name="uq_usuario_escritorio_nome"),
    )


class Lembrete(Base):
    __tablename__ = "lembretes"
    __table_args__ = (
        Index("ix_lembretes_usuario_id", "usuario_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String, nullable=False)
    descricao = Column(String, default="")
    data_vencimento = Column(String, nullable=False)   # DD/MM/AAAA
    hora = Column(String, default="09:00")
    prioridade = Column(String, default="media")       # baixa | media | alta | urgente
    status = Column(String, default="pendente")        # pendente | concluido | atrasado
    empresa_vinculada = Column(String, default="")
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(String, nullable=False)         # ISO datetime string


class Empresa(Base):
    __tablename__ = "empresas"
    __table_args__ = (
        Index("ix_empresas_cnpj",  "cnpj"),
        Index("ix_empresas_ativa", "ativa"),
        Index("ix_empresas_usuario_ativa", "usuario_id", "ativa"),
        Index("ix_empresas_escritorio", "escritorio_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    escritorio_id = Column(Integer, ForeignKey("escritorios.id"), nullable=True, index=True)
    nome = Column(String, nullable=False)
    nome_fantasia = Column(String, default="")         # Nome de fantasia / nome comercial
    cnpj = Column(String, default="")
    ccm = Column(String, default="")                   # Inscrição Municipal
    ie = Column(String, default="")                    # Inscrição Estadual
    status = Column(String, default="iniciada")        # Ver STATUSES no main.py
    ativa = Column(Boolean, default=True)              # False = inativada (não deletada)
    observacoes = Column(String, default="")

    # ── Dados adicionais para carteiras de 500+ empresas ──────────
    segmento = Column(String, default="")              # Ex: "Comércio Varejista", "Serviços"
    porte = Column(String, default="")                 # MEI | ME | EPP | Médio | Grande
    faturamento_medio_mensal = Column(Numeric(15, 2), default=0.0)  # Faturamento médio em R$
    regime_tributario = Column(String, default="simples")  # simples | presumido | real
    telefone = Column(String, default="")
    email_contato = Column(String, default="")
    responsavel_financeiro = Column(String, default="")    # Nome do responsável do cliente

    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(String, nullable=False)         # ISO datetime string
    atualizado_em = Column(String, nullable=False)     # ISO datetime string


# ──────────────────────────────────────────────────────────────────
#  MÓDULOS FINANCEIROS — tabelas novas
# ──────────────────────────────────────────────────────────────────

class EmpresaFiscal(Base):
    """Dados fiscais complementares — relação 1-para-1 com Empresa."""
    __tablename__ = "empresas_fiscal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), unique=True, nullable=False)
    cnae = Column(String, default="")
    cnae_descricao = Column(String, default="")
    regime_tributario = Column(String, default="simples")  # simples | presumido | real
    # Atividade da empresa — usado para determinar o Anexo correto do Simples Nacional
    atividade_principal = Column(Text, default="")   # descrição da atividade principal
    atividade_secundaria = Column(Text, default="")  # descrição das atividades secundárias
    # Anexo do Simples Nacional: I | II | III | IV | V (padrão III — serviços)
    anexo_simples = Column(String, default="III")
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


class EmpresaBanco(Base):
    """Contas bancárias da empresa — até 3 bancos por empresa (carteira de 500 clientes)."""
    __tablename__ = "empresas_bancos"
    __table_args__ = (
        Index("ix_empresas_bancos_empresa_id", "empresa_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)

    # ── Dados da conta bancária ───────────────────────────────────
    banco = Column(String, nullable=False)             # "Itaú", "Bradesco", "BB", etc.
    banco_codigo = Column(String, default="")          # Código COMPE: "341", "237", "001"
    agencia = Column(String, default="")               # Agência sem dígito
    conta = Column(String, default="")                 # Conta com dígito
    tipo_conta = Column(String, default="corrente")    # corrente | poupança | pagamento | investimento
    chave_pix = Column(String, default="")             # Chave PIX (CNPJ, e-mail, celular ou aleatória)
    saldo_inicial = Column(Numeric(15, 2), default=0.0)         # Saldo de abertura para conciliação
    data_saldo_inicial = Column(String, default="")    # YYYY-MM-DD — data do saldo inicial
    ativo = Column(Boolean, default=True)              # False = conta encerrada
    observacoes = Column(String, default="")
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


class LancamentoMensal(Base):
    """Dados financeiros mensais por empresa — base de todos os módulos analíticos."""
    __tablename__ = "lancamentos_mensais"
    __table_args__ = (
        UniqueConstraint("empresa_id", "ano", "mes", name="uq_empresa_ano_mes"),
        Index("ix_lancamentos_empresa_ano", "empresa_id", "ano"),
        Index("ix_lancamentos_ano_mes", "ano", "mes"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)   # 1–12

    # ── DRE ──────────────────────────────────────────────────────
    receita_bruta = Column(Numeric(15, 2), default=0.0)
    deducoes_receita = Column(Numeric(15, 2), default=0.0)       # impostos s/ receita, devoluções
    custo_servicos = Column(Numeric(15, 2), default=0.0)         # CMV / CSV / CSP
    despesas_adm = Column(Numeric(15, 2), default=0.0)
    despesas_comerciais = Column(Numeric(15, 2), default=0.0)
    despesas_financeiras = Column(Numeric(15, 2), default=0.0)
    outras_despesas = Column(Numeric(15, 2), default=0.0)
    ir_csll = Column(Numeric(15, 2), default=0.0)

    # ── Fluxo de Caixa ───────────────────────────────────────────
    entradas_caixa = Column(Numeric(15, 2), default=0.0)
    saidas_caixa = Column(Numeric(15, 2), default=0.0)
    saldo_inicial_caixa = Column(Numeric(15, 2), default=0.0)

    # ── Balanço — Ativo ──────────────────────────────────────────
    caixa_equivalentes = Column(Numeric(15, 2), default=0.0)
    contas_receber = Column(Numeric(15, 2), default=0.0)
    estoques = Column(Numeric(15, 2), default=0.0)
    outros_ativo_circ = Column(Numeric(15, 2), default=0.0)
    ativo_nao_circulante = Column(Numeric(15, 2), default=0.0)

    # ── Balanço — Passivo ────────────────────────────────────────
    fornecedores = Column(Numeric(15, 2), default=0.0)
    emprestimos_cp = Column(Numeric(15, 2), default=0.0)
    tributos_pagar = Column(Numeric(15, 2), default=0.0)
    outros_passivo_circ = Column(Numeric(15, 2), default=0.0)
    passivo_nao_circulante = Column(Numeric(15, 2), default=0.0)

    # ── Patrimônio Líquido ───────────────────────────────────────
    capital_social = Column(Numeric(15, 2), default=0.0)
    reservas = Column(Numeric(15, 2), default=0.0)
    lucros_acumulados = Column(Numeric(15, 2), default=0.0)

    # ── Depreciação e Amortização (para EBITDA) ──────────────────
    depreciacao_amortizacao = Column(Numeric(15, 2), default=0.0)  # D&A do período

    # ── RH ───────────────────────────────────────────────────────
    folha_pagamento = Column(Numeric(15, 2), default=0.0)

    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


class SetorBenchmark(Base):
    """Benchmarks financeiros médios por setor/CNAE (dados estáticos seed)."""
    __tablename__ = "setor_benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cnae = Column(String, nullable=False, unique=True, index=True)
    descricao = Column(String, nullable=False)
    margem_liquida_media = Column(Float, default=0.0)       # em %
    carga_tributaria_media = Column(Float, default=0.0)     # em %
    folha_sobre_receita_media = Column(Float, default=0.0)  # em %


class RegrasTributarias(Base):
    """Alíquotas tributárias por regime — configuráveis pelo administrador."""
    __tablename__ = "regras_tributarias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    regime = Column(String, nullable=False)           # simples | presumido | real
    tributo = Column(String, nullable=False)          # IRPJ | CSLL | PIS | COFINS | ISS | Simples
    aliquota = Column(Float, nullable=False)          # ex: 0.065 para 6,5%
    base_calculo = Column(String, default="receita_bruta")
    vigencia_inicio = Column(String, nullable=False)  # YYYY-MM-DD
    vigencia_fim = Column(String, nullable=True)      # null = ainda vigente


class ReformaParametros(Base):
    """Parâmetros da Reforma Tributária (IBS + CBS) para simulação."""
    __tablename__ = "reforma_parametros"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tributo_novo = Column(String, nullable=False)          # IBS | CBS
    aliquota_estimada = Column(Float, nullable=False)      # ex: 0.177
    regra_credito = Column(String, default="")             # descrição da regra de crédito
    regime_aplicavel = Column(String, default="todos")     # todos | simples | presumido | real
    vigencia_inicio = Column(String, nullable=False)       # YYYY-MM-DD
    vigencia_fim = Column(String, nullable=True)


# ──────────────────────────────────────────────────────────────────
#  MOTOR DE IMPORTAÇÃO — tabelas de controle
# ──────────────────────────────────────────────────────────────────

class Importacao(Base):
    """Registro de cada importação de arquivo realizada."""
    __tablename__ = "importacoes"
    __table_args__ = (
        Index("ix_importacoes_usuario_id", "usuario_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nome_arquivo = Column(String, nullable=False)
    tipo_dado = Column(String, nullable=False)   # faturamento | folha | impostos | dre | fluxo | balanco | generico
    status = Column(String, default="processando")  # processando | concluido | erro
    linhas_processadas = Column(Integer, default=0)
    linhas_com_erro = Column(Integer, default=0)
    resumo_json = Column(Text, default="")       # JSON com preview/resumo do processamento
    mensagem_erro = Column(Text, default="")
    criado_em = Column(String, nullable=False)


class MapeamentoTemplate(Base):
    """Templates salvos de mapeamento de colunas para reuso futuro."""
    __tablename__ = "mapeamento_templates"
    __table_args__ = (
        Index("ix_mapeamento_templates_usuario_id", "usuario_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    tipo_dado = Column(String, nullable=False)   # mesmo enum de Importacao.tipo_dado
    mapeamento_json = Column(Text, nullable=False)  # JSON: {coluna_original: campo_destino}
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


# ──────────────────────────────────────────────────────────────────
#  ORÇAMENTO MENSAL
# ──────────────────────────────────────────────────────────────────

class OrcamentoMensal(Base):
    """Metas orçamentárias mensais por empresa — espelho do LancamentoMensal."""
    __tablename__ = "orcamentos_mensais"
    __table_args__ = (
        UniqueConstraint("empresa_id", "ano", "mes", name="uq_orc_empresa_ano_mes"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False)   # 1–12

    # ── DRE ──────────────────────────────────────────────────────
    receita_bruta = Column(Numeric(15, 2), default=0.0)
    deducoes_receita = Column(Numeric(15, 2), default=0.0)
    custo_servicos = Column(Numeric(15, 2), default=0.0)
    despesas_adm = Column(Numeric(15, 2), default=0.0)
    despesas_comerciais = Column(Numeric(15, 2), default=0.0)
    despesas_financeiras = Column(Numeric(15, 2), default=0.0)
    outras_despesas = Column(Numeric(15, 2), default=0.0)
    ir_csll = Column(Numeric(15, 2), default=0.0)

    # ── Fluxo de Caixa ───────────────────────────────────────────
    entradas_caixa = Column(Numeric(15, 2), default=0.0)
    saidas_caixa = Column(Numeric(15, 2), default=0.0)

    # ── RH ───────────────────────────────────────────────────────
    folha_pagamento = Column(Numeric(15, 2), default=0.0)

    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


# ──────────────────────────────────────────────────────────────────
#  CONCILIAÇÃO BANCÁRIA
# ──────────────────────────────────────────────────────────────────

class TransacaoBancaria(Base):
    """Transações individuais extraídas do extrato bancário para conciliação."""
    __tablename__ = "transacoes_bancarias"
    __table_args__ = (
        Index("ix_transacoes_empresa_data", "empresa_id", "data_transacao"),
        Index("ix_transacoes_usuario_id", "usuario_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    data_transacao = Column(String, nullable=False)   # YYYY-MM-DD
    descricao = Column(String, nullable=False)
    valor = Column(Numeric(15, 2), nullable=False)     # sempre positivo
    tipo = Column(String, nullable=False)             # "credito" | "debito"
    categoria = Column(String, default="")
    status = Column(String, default="pendente")       # "pendente" | "conciliado" | "ignorado"
    observacao = Column(String, default="")
    criado_em = Column(String, nullable=False)


# ──────────────────────────────────────────────────────────────────
#  CONFIGURAÇÃO DE ALERTAS POR E-MAIL
# ──────────────────────────────────────────────────────────────────

class ConfigAlerta(Base):
    """Configurações de alertas financeiros por e-mail por empresa/usuário."""
    __tablename__ = "config_alertas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "usuario_id", name="uq_alerta_empresa_usuario"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    email_destino = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)
    alertar_margem_negativa = Column(Boolean, default=True)
    alertar_caixa_negativo = Column(Boolean, default=True)
    alertar_desvio_orcamento = Column(Boolean, default=True)
    threshold_desvio_pct = Column(Float, default=20.0)
    resumo_mensal_ativo = Column(Boolean, default=False)
    dia_resumo_mensal = Column(Integer, default=1)
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


# ──────────────────────────────────────────────────────────────────
#  PLANO DE CONTAS REFERENCIAL + DE-PARA
# ──────────────────────────────────────────────────────────────────

class PlanoContasReferencial(Base):
    """Plano de contas padrão do sistema — independente de empresa."""
    __tablename__ = "plano_contas_referencial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String, nullable=False, unique=True, index=True)  # ex: "1.1.1"
    descricao = Column(String, nullable=False)                         # ex: "Disponibilidades"
    grupo = Column(String, nullable=False)   # ativo | passivo | pl | receita | custo_despesa
    nivel = Column(Integer, nullable=False)  # 1=grupo, 2=subgrupo, 3=conta analítica
    ordem = Column(Integer, default=0)       # ordem de exibição


# ──────────────────────────────────────────────────────────────────
#  LOG DE AUDITORIA
# ──────────────────────────────────────────────────────────────────

class AuditoriaLog(Base):
    """Registro imutável de ações relevantes realizadas no sistema."""
    __tablename__ = "auditoria_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id   = Column(Integer, ForeignKey("usuarios.id"), nullable=True)  # null = ação anônima
    usuario_nome = Column(String, default="")
    escritorio_id = Column(Integer, ForeignKey("escritorios.id"), nullable=True, index=True)
    acao         = Column(String, nullable=False, index=True)   # ex: login | criar_empresa | importar
    recurso      = Column(String, default="")                   # ex: empresa | importacao | usuario
    recurso_id   = Column(Integer, nullable=True)               # id do objeto afetado
    detalhes     = Column(Text, default="")                     # JSON livre com contexto extra
    ip           = Column(String, default="")
    criado_em    = Column(String, nullable=False, index=True)   # ISO datetime


class CarteiraMembro(Base):
    """Relação usuário-empresa: quem tem qual empresa na carteira.
    UNIQUE em empresa_id garante exclusividade (uma empresa, um contador)."""
    __tablename__ = "carteira_membros"
    __table_args__ = (
        UniqueConstraint("empresa_id", name="uq_carteira_empresa"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    adicionado_em = Column(String, nullable=False)
    observacoes = Column(String, default="")    # notas privadas do analista sobre o cliente


class MapeamentoContas(Base):
    """De-Para entre plano do cliente e plano referencial, por empresa."""
    __tablename__ = "mapeamento_contas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "conta_cliente", name="uq_empresa_conta_cliente"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    conta_cliente = Column(String, nullable=False)    # código no plano do cliente
    descricao_cliente = Column(String, default="")    # descrição no balancete do cliente
    conta_referencial_id = Column(Integer, ForeignKey("plano_contas_referencial.id"), nullable=True)
    sugestao_automatica = Column(Boolean, default=False)  # True = mapeado por heurística, não pelo usuário
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


# ──────────────────────────────────────────────────────────────────
#  GESTÃO DE EQUIPE — tarefas designadas por gestores/admins
# ──────────────────────────────────────────────────────────────────

class TarefaEquipe(Base):
    """Tarefas designadas por gestores ou administradores para colaboradores."""
    __tablename__ = "tarefas_equipe"
    __table_args__ = (
        Index("ix_tarefas_equipe_destinatario", "destinatario_id"),
        Index("ix_tarefas_equipe_criador", "criador_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    destinatario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    titulo = Column(String, nullable=False)
    descricao = Column(String, default="")
    prioridade = Column(String, default="media")   # baixa | media | alta | urgente
    categoria = Column(String, default="")
    data_entrega = Column(String, default="")      # DD/MM/AAAA
    hora = Column(String, default="09:00")
    concluida = Column(Boolean, default=False)
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


# ────────────────────────────────────────────────���─────────────────
#  CLASSIFICAÇÃO CONTÁBIL — Plano de Contas por Empresa
# ───────────────────────────────��──────────────────────────────────

class PlanoContasEmpresa(Base):
    """Plano de contas completo e hierárquico por empresa (árvore com máscara numérica)."""
    __tablename__ = "plano_contas_empresa"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_plano_empresa_codigo"),
        Index("ix_plano_contas_empresa_empresa_id", "empresa_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    codigo = Column(String, nullable=False)           # ex: "1.1.1.02.0001"
    descricao = Column(String, nullable=False)        # ex: "Banco Itaú - C/C"
    tipo = Column(String, nullable=False)             # "sintetica" | "analitica"
    natureza = Column(String, nullable=False)         # "ativo" | "passivo" | "receita" | "despesa"
    codigo_pai = Column(String, default="")           # código da conta pai (vazio = raiz)
    ordem = Column(Integer, default=0)
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


class RegraClassificacao(Base):
    """Regras customizadas de classificação de transações por empresa (De-Para descrição→conta)."""
    __tablename__ = "regras_classificacao"
    __table_args__ = (
        Index("ix_regras_classificacao_empresa_id", "empresa_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    padrao = Column(String, nullable=False)           # texto/regex para match na descrição
    tipo_transacao = Column(String, default="ambos")  # "entrada" | "saida" | "ambos"
    conta_debito_codigo = Column(String, default="")  # código da conta analítica para débito
    conta_credito_codigo = Column(String, default="") # código da conta analítica para crédito
    prioridade = Column(Integer, default=0)           # maior = verificado antes
    ativo = Column(Boolean, default=True)
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


class ContaBancoEmpresa(Base):
    """Mapeamento banco→conta analítica do plano de contas da empresa."""
    __tablename__ = "conta_banco_empresa"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nome_banco", name="uq_conta_banco_empresa"),
        Index("ix_conta_banco_empresa_empresa_id", "empresa_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nome_banco = Column(String, nullable=False)       # "Itaú", "Bradesco", etc.
    conta_codigo = Column(String, nullable=False)     # código analítico, ex: "1.1.1.02.0001"
    conta_descricao = Column(String, default="")      # ex: "Banco Itaú - C/C"
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


class ClienteFornecedorEmpresa(Base):
    """Cadastro de clientes/fornecedores por empresa para classificação automática."""
    __tablename__ = "clientes_fornecedores_empresa"
    __table_args__ = (
        Index("ix_clf_empresa_id", "empresa_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nome = Column(String, nullable=False)             # nome da pessoa/empresa
    documento = Column(String, default="")            # CPF ou CNPJ
    tipo = Column(String, nullable=False)             # "cliente" | "fornecedor"
    conta_codigo = Column(String, default="")         # conta analítica associada
    conta_descricao = Column(String, default="")
    criado_em = Column(String, nullable=False)
    atualizado_em = Column(String, nullable=False)


# ──────────────────────────────────────────────────────────────────
#  PROTEÇÃO R2 — Usuário Mestre é imutável por automação
# ──────────────────────────────────────────────────────────────────

class UsuarioMestreProtegidoError(Exception):
    """
    Levantada quando código tenta modificar campos críticos do usuário
    mestre (is_master=True) via ORM sem passar pelo endpoint autenticado.
    Campos protegidos: senha_hash, escritorio_id, is_master (demotion)
    """
    pass


_MASTER_CAMPOS_IMUTAVEIS = frozenset({"senha_hash", "escritorio_id"})


@event.listens_for(Usuario, "before_update")
def _proteger_campos_mestre_update(mapper, connection, target: "Usuario") -> None:
    # ── Determinar original_is_master via DB ─────────────────────────
    # Em SQLAlchemy 2.x, atributos expirados após commit têm `deleted=[]`
    # em get_history() mesmo quando o valor foi alterado. Solução: consultar
    # o estado persistido diretamente via connection, que ainda reflete o
    # valor pré-UPDATE (evento dispara antes do SQL ser emitido).
    table = mapper.persist_selectable
    row = connection.execute(
        table.select().where(table.c.id == target.id)
    ).fetchone()

    if row is None:
        return

    original_is_master = bool(row._mapping["is_master"])
    if not original_is_master:
        return

    # ── Bloquear rebaixamento de is_master ───────────────────────────
    # Verifica via `added` (change untracked: expired attr) e via `deleted`
    # (change tracked: attr was loaded before being set).
    is_master_hist = get_history(target, "is_master")
    new_is_master = (
        is_master_hist.added[0]
        if is_master_hist.added
        else row._mapping["is_master"]
    )
    if not new_is_master:
        logger.warning(
            "R2 VIOLATION BLOCKED: tentativa de rebaixar is_master do usuário mestre. "
            "usuario_id=%s campo_violado=is_master valor_tentado=False",
            target.id,
        )
        raise UsuarioMestreProtegidoError(
            "O campo 'is_master' do usuário mestre não pode ser revogado por "
            "automação. Use o endpoint autenticado /api/master/credenciais."
        )

    # ── Bloquear alteração de senha_hash e escritorio_id ────────────
    # `h.deleted` → atributo foi carregado antes de ser alterado (tracked)
    # `h.added`   → atributo foi setado (pode ser expired antes do set)
    for campo in _MASTER_CAMPOS_IMUTAVEIS:
        h = get_history(target, campo)
        if h.deleted or h.added:
            valor_log = "[MASKED]" if campo == "senha_hash" else (h.added[0] if h.added else "?")
            logger.warning(
                "R2 VIOLATION BLOCKED: tentativa de alterar campo imutável do usuário mestre. "
                "usuario_id=%s campo_violado=%s valor_tentado=%s",
                target.id,
                campo,
                valor_log,
            )
            raise UsuarioMestreProtegidoError(
                f"O campo '{campo}' do usuário mestre é imutável por automação. "
                f"Use o endpoint autenticado /api/master/credenciais."
            )


@event.listens_for(Usuario, "before_delete")
def _proteger_usuario_mestre_delete(mapper, connection, target: "Usuario") -> None:
    if target.is_master:
        logger.warning(
            "R2 VIOLATION BLOCKED: tentativa de excluir usuário mestre. "
            "usuario_id=%s",
            getattr(target, "id", "?"),
        )
        raise UsuarioMestreProtegidoError(
            "O usuário mestre não pode ser excluído."
        )
