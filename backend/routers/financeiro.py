"""
Router financeiro — todos os endpoints dos módulos analíticos.

Endpoints:
  GET  /api/financeiro/empresas                        → lista empresas do usuário (com dados fiscais)
  GET  /api/financeiro/dashboard/{empresa_id}          → KPIs + gráfico 12 meses
  GET  /api/financeiro/dre/{empresa_id}                → DRE cascata + insights
  GET  /api/financeiro/fluxo-caixa/{empresa_id}        → fluxo histórico + projeção
  GET  /api/financeiro/balanco/{empresa_id}            → balanço estruturado + insights
  GET  /api/financeiro/insights/{empresa_id}           → todos os insights consolidados
  GET  /api/financeiro/simulacao/{empresa_id}          → simulação reforma tributária
  GET  /api/financeiro/lancamentos/{empresa_id}        → lista lançamentos mensais
  POST /api/financeiro/lancamentos/{empresa_id}        → upsert lançamento mensal
  PUT  /api/financeiro/fiscal/{empresa_id}             → upsert dados fiscais da empresa
  GET  /api/financeiro/benchmarks                      → lista benchmarks do setor
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models
from services import financeiro_service as fs
from services import simulacao_tributaria_service as sts
from services.score_saude import ScoreSaude
from services.motor_narrativa import MotorNarrativa

_score_engine = ScoreSaude()
_narrativa_engine = MotorNarrativa()

router = APIRouter(prefix="/api/financeiro", tags=["financeiro"])

# ─── Dependência de autenticação (importada pelo main.py via injeção) ─────────
# O main.py injeta get_current_user ao incluir o router.
# Aqui declaramos a dependência diretamente para simplicidade.

from services.auth_utils import get_current_user as _get_user, resolve_empresa_or_403


# ─── Schemas ─────────────────────────────────────────────────────────────────

class LancamentoUpsert(BaseModel):
    ano: int
    mes: int
    receita_bruta: float = 0.0
    deducoes_receita: float = 0.0
    custo_servicos: float = 0.0
    despesas_adm: float = 0.0
    despesas_comerciais: float = 0.0
    despesas_financeiras: float = 0.0
    outras_despesas: float = 0.0
    ir_csll: float = 0.0
    entradas_caixa: float = 0.0
    saidas_caixa: float = 0.0
    saldo_inicial_caixa: float = 0.0
    caixa_equivalentes: float = 0.0
    contas_receber: float = 0.0
    estoques: float = 0.0
    outros_ativo_circ: float = 0.0
    ativo_nao_circulante: float = 0.0
    fornecedores: float = 0.0
    emprestimos_cp: float = 0.0
    tributos_pagar: float = 0.0
    outros_passivo_circ: float = 0.0
    passivo_nao_circulante: float = 0.0
    capital_social: float = 0.0
    reservas: float = 0.0
    lucros_acumulados: float = 0.0
    folha_pagamento: float = 0.0
    depreciacao_amortizacao: float = 0.0


class FiscalUpsert(BaseModel):
    cnae: str = ""
    cnae_descricao: str = ""
    regime_tributario: str = "simples"
    atividade_principal: str = ""
    atividade_secundaria: str = ""
    anexo_simples: str = "III"   # I | II | III | IV | V


class SimulacaoInput(BaseModel):
    receita_bruta: Optional[float] = None
    custo_servicos: Optional[float] = None


# ─── Rotas ───────────────────────────────────────────────────────────────────

@router.get("/empresas")
def listar_empresas_financeiro(
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Lista as empresas do usuário com dados fiscais (regime, CNAE)."""
    if getattr(usuario, "is_master", False):
        empresas = db.query(models.Empresa).order_by(models.Empresa.nome.asc()).all()
    elif usuario.is_admin:
        empresas = (
            db.query(models.Empresa)
            .filter(models.Empresa.escritorio_id == usuario.escritorio_id)
            .order_by(models.Empresa.nome.asc())
            .all()
        )
    else:
        # Empresas próprias + empresas da carteira do usuário
        ids_proprias = {
            e.id for e in db.query(models.Empresa.id)
            .filter(models.Empresa.usuario_id == usuario.id).all()
        }
        ids_carteira = {
            m.empresa_id for m in db.query(models.CarteiraMembro)
            .filter(models.CarteiraMembro.usuario_id == usuario.id).all()
        }
        todos_ids = ids_proprias | ids_carteira
        empresas = (
            db.query(models.Empresa)
            .filter(models.Empresa.id.in_(todos_ids))
            .order_by(models.Empresa.nome.asc())
            .all()
        )

    resultado = []
    for e in empresas:
        fiscal = (
            db.query(models.EmpresaFiscal)
            .filter(models.EmpresaFiscal.empresa_id == e.id)
            .first()
        )
        # Conta lançamentos
        total_lanc = (
            db.query(models.LancamentoMensal)
            .filter(models.LancamentoMensal.empresa_id == e.id)
            .count()
        )
        resultado.append({
            "id": e.id,
            "nome": e.nome,
            "cnpj": e.cnpj,
            "status": e.status,
            "regime_tributario": fiscal.regime_tributario if fiscal else "simples",
            "cnae": fiscal.cnae if fiscal else "",
            "cnae_descricao": fiscal.cnae_descricao if fiscal else "",
            "atividade_principal": fiscal.atividade_principal if fiscal else "",
            "atividade_secundaria": fiscal.atividade_secundaria if fiscal else "",
            "anexo_simples": fiscal.anexo_simples if fiscal else "III",
            "total_lancamentos": total_lanc,
        })
    return resultado


@router.get("/dashboard/{empresa_id}")
def dashboard(
    empresa_id: int,
    ano: int,
    mes: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)
    return fs.get_dashboard(db, empresa_id, ano, mes)


@router.get("/dre/{empresa_id}")
def dre(
    empresa_id: int,
    ano: int,
    mes: int,
    dre_engine: Optional[str] = None,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)
    # Query param dre_engine=novo restrito a master
    override = None
    if dre_engine and getattr(usuario, "is_master", False):
        override = dre_engine
    return fs.get_dre(db, empresa_id, ano, mes, dre_engine_override=override)


@router.get("/fluxo-caixa/{empresa_id}")
def fluxo_caixa(
    empresa_id: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)
    return fs.get_fluxo_caixa(db, empresa_id)


@router.get("/balanco/{empresa_id}")
def balanco(
    empresa_id: int,
    ano: int,
    mes: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)
    return fs.get_balanco(db, empresa_id, ano, mes)


@router.get("/insights/{empresa_id}")
def insights(
    empresa_id: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)
    return fs.get_todos_insights(db, empresa_id)


@router.get("/simulacao/{empresa_id}")
def simulacao(
    empresa_id: int,
    receita_bruta: Optional[float] = None,
    custo_servicos: Optional[float] = None,
    aliquota_iss: Optional[float] = None,
    rbt12: Optional[float] = None,
    lp_engine: Optional[str] = None,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)

    # Query param lp_engine=novo restrito a master (BLOCO 3F.2)
    lp_override = None
    if lp_engine and getattr(usuario, "is_master", False):
        lp_override = lp_engine

    # Se não forneceu na query, usa último lançamento disponível
    if receita_bruta is None or custo_servicos is None:
        historico = fs.get_historico(db, empresa_id, limite=1)
        if not historico:
            raise HTTPException(
                status_code=404,
                detail="Nenhum lançamento encontrado. Informe receita_bruta e custo_servicos.",
            )
        ultimo = historico[-1]
        receita_bruta = receita_bruta if receita_bruta is not None else ultimo["receita_bruta"]
        custo_servicos = custo_servicos if custo_servicos is not None else ultimo["custo_servicos"]

    return sts.simular_reforma(
        db, empresa_id, receita_bruta, custo_servicos,
        aliquota_iss=aliquota_iss, rbt12=rbt12,
        lp_engine_override=lp_override,
    )


@router.get("/comparar-regimes/{empresa_id}")
def comparar_regimes(
    empresa_id: int,
    receita_bruta: Optional[float] = None,
    custo_servicos: Optional[float] = None,
    aliquota_iss: Optional[float] = None,
    rbt12: Optional[float] = None,
    lp_engine: Optional[str] = None,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """
    Compara todos os regimes tributários (Simples, Presumido, Real + Reforma)
    para a mesma base de cálculo. Útil para planejamento tributário.
    """
    resolve_empresa_or_403(db, empresa_id, usuario)

    # Query param lp_engine=novo restrito a master (BLOCO 3F.2)
    lp_override = None
    if lp_engine and getattr(usuario, "is_master", False):
        lp_override = lp_engine

    if receita_bruta is None or custo_servicos is None:
        historico = fs.get_historico(db, empresa_id, limite=1)
        if not historico:
            raise HTTPException(
                status_code=404,
                detail="Nenhum lançamento encontrado. Informe receita_bruta e custo_servicos.",
            )
        ultimo = historico[-1]
        receita_bruta = receita_bruta if receita_bruta is not None else ultimo["receita_bruta"]
        custo_servicos = custo_servicos if custo_servicos is not None else ultimo["custo_servicos"]

    return sts.comparar_todos_regimes(
        db, empresa_id, receita_bruta, custo_servicos,
        aliquota_iss=aliquota_iss, rbt12=rbt12,
        lp_engine_override=lp_override,
    )


@router.get("/indicadores/{empresa_id}")
def indicadores_avancados(
    empresa_id: int,
    ano: int,
    mes: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """
    Retorna todos os indicadores financeiros avançados do período:
    EBITDA, Margem EBITDA, Capital de Giro, Liquidez Seca, ROE, ROA,
    Endividamento Geral e Ciclo Financeiro (PMR, PME, PMP).
    """
    resolve_empresa_or_403(db, empresa_id, usuario)
    atual = fs.get_metricas_mes(db, empresa_id, ano, mes)
    if not atual:
        return {"sem_dados": True}

    # Mês anterior para variação
    m_ant = mes - 1 if mes > 1 else 12
    a_ant = ano if mes > 1 else ano - 1
    anterior = fs.get_metricas_mes(db, empresa_id, a_ant, m_ant)

    def _var(campo: str):
        if anterior and anterior.get(campo) is not None and atual.get(campo) is not None:
            ant = anterior[campo]
            if ant and ant != 0:
                return ((atual[campo] - ant) / abs(ant)) * 100
        return None

    indicadores = {
        "periodo": f"{fs.MESES_PT[mes - 1]}/{ano}",
        "ebitda": {
            "valor": atual.get("ebitda"),
            "variacao_pct": _var("ebitda"),
            "depreciacao_amortizacao": atual.get("depreciacao_amortizacao", 0.0),
            "tooltip": "EBIT + Depreciação e Amortização. Mede a geração operacional de caixa antes de impostos e D&A.",
        },
        "margem_ebitda": {
            "valor": atual.get("margem_ebitda"),
            "variacao_pct": _var("margem_ebitda"),
            "tooltip": "EBITDA ÷ Receita Líquida × 100. Indica eficiência operacional.",
        },
        "capital_giro_liquido": {
            "valor": atual.get("capital_giro_liquido"),
            "variacao_pct": _var("capital_giro_liquido"),
            "tooltip": "Ativo Circulante − Passivo Circulante. Positivo = empresa tem folga de curto prazo.",
        },
        "liquidez_corrente": {
            "valor": atual.get("liquidez_corrente"),
            "variacao_pct": _var("liquidez_corrente"),
            "faixas": {"ok": 1.2, "atencao": 0.8},
            "tooltip": "Ativo Circulante ÷ Passivo Circulante. Ideal > 1,2. Abaixo de 1 indica risco de liquidez.",
        },
        "liquidez_seca": {
            "valor": atual.get("liquidez_seca"),
            "variacao_pct": _var("liquidez_seca"),
            "faixas": {"ok": 1.0, "atencao": 0.7},
            "tooltip": "(Ativo Circulante − Estoques) ÷ Passivo Circulante. Mais conservador que a Liquidez Corrente.",
        },
        "roe": {
            "valor": atual.get("roe"),
            "variacao_pct": _var("roe"),
            "faixas": {"ok": 15.0, "atencao": 5.0},
            "tooltip": "Lucro Líquido ÷ Patrimônio Líquido × 100. Retorno sobre o capital investido pelos sócios.",
        },
        "roa": {
            "valor": atual.get("roa"),
            "variacao_pct": _var("roa"),
            "faixas": {"ok": 8.0, "atencao": 3.0},
            "tooltip": "Lucro Líquido ÷ Ativo Total × 100. Eficiência no uso de todos os ativos.",
        },
        "endividamento_geral": {
            "valor": atual.get("endividamento_geral"),
            "variacao_pct": _var("endividamento_geral"),
            "faixas": {"ok": 40.0, "atencao": 70.0},  # invertido: menor é melhor
            "invertido": True,
            "tooltip": "Passivo Total ÷ Ativo Total × 100. Abaixo de 40% é saudável; acima de 70% é crítico.",
        },
        "ciclo_financeiro": {
            "valor": atual.get("ciclo_financeiro"),
            "pmr": atual.get("pmr"),
            "pme": atual.get("pme"),
            "pmp": atual.get("pmp"),
            "variacao_pct": _var("ciclo_financeiro"),
            "tooltip": "PMR + PME − PMP (dias). Positivo = empresa precisa de capital de giro. Negativo = financia com fornecedores.",
        },
    }

    return indicadores


@router.get("/lancamentos/{empresa_id}")
def listar_lancamentos(
    empresa_id: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)
    rows = (
        db.query(models.LancamentoMensal)
        .filter(models.LancamentoMensal.empresa_id == empresa_id)
        .order_by(
            models.LancamentoMensal.ano.desc(),
            models.LancamentoMensal.mes.desc(),
        )
        .all()
    )
    return [fs._lanc_to_metricas(r) for r in rows]


@router.post("/lancamentos/{empresa_id}", status_code=200)
def upsert_lancamento(
    empresa_id: int,
    body: LancamentoUpsert,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)

    if not (1 <= body.mes <= 12):
        raise HTTPException(status_code=400, detail="Mês inválido (1–12).")
    if body.ano < 2000 or body.ano > 2100:
        raise HTTPException(status_code=400, detail="Ano inválido.")

    agora = datetime.now(timezone.utc).isoformat()
    existing = (
        db.query(models.LancamentoMensal)
        .filter(
            models.LancamentoMensal.empresa_id == empresa_id,
            models.LancamentoMensal.ano == body.ano,
            models.LancamentoMensal.mes == body.mes,
        )
        .first()
    )

    campos = body.model_dump(exclude={"ano", "mes"})

    if existing:
        for campo, valor in campos.items():
            setattr(existing, campo, valor)
        existing.atualizado_em = agora
        db.commit()
        db.refresh(existing)
        return {"mensagem": "Lançamento atualizado.", "id": existing.id}
    else:
        lanc = models.LancamentoMensal(
            empresa_id=empresa_id,
            ano=body.ano,
            mes=body.mes,
            criado_em=agora,
            atualizado_em=agora,
            **campos,
        )
        db.add(lanc)
        db.commit()
        db.refresh(lanc)
        return {"mensagem": "Lançamento criado.", "id": lanc.id}


@router.delete("/lancamentos/{empresa_id}/{lancamento_id}")
def excluir_lancamento(
    empresa_id: int,
    lancamento_id: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)
    row = (
        db.query(models.LancamentoMensal)
        .filter(
            models.LancamentoMensal.id == lancamento_id,
            models.LancamentoMensal.empresa_id == empresa_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    db.delete(row)
    db.commit()
    return {"mensagem": "Lançamento excluído."}


@router.put("/fiscal/{empresa_id}")
def upsert_fiscal(
    empresa_id: int,
    body: FiscalUpsert,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    resolve_empresa_or_403(db, empresa_id, usuario)
    agora = datetime.now(timezone.utc).isoformat()

    fiscal = (
        db.query(models.EmpresaFiscal)
        .filter(models.EmpresaFiscal.empresa_id == empresa_id)
        .first()
    )
    if fiscal:
        fiscal.cnae = body.cnae
        fiscal.cnae_descricao = body.cnae_descricao
        fiscal.regime_tributario = body.regime_tributario
        fiscal.atividade_principal = body.atividade_principal
        fiscal.atividade_secundaria = body.atividade_secundaria
        fiscal.anexo_simples = body.anexo_simples or "III"
        fiscal.atualizado_em = agora
    else:
        fiscal = models.EmpresaFiscal(
            empresa_id=empresa_id,
            cnae=body.cnae,
            cnae_descricao=body.cnae_descricao,
            regime_tributario=body.regime_tributario,
            atividade_principal=body.atividade_principal,
            atividade_secundaria=body.atividade_secundaria,
            anexo_simples=body.anexo_simples or "III",
            criado_em=agora,
            atualizado_em=agora,
        )
        db.add(fiscal)
    db.commit()
    return {"mensagem": "Dados fiscais atualizados."}


@router.get("/score/{empresa_id}")
def score_saude(
    empresa_id: int,
    ano: Optional[int] = None,
    mes: Optional[int] = None,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Score de saúde financeira (0-100) para a empresa."""
    resolve_empresa_or_403(db, empresa_id, usuario)
    historico = fs.get_historico(db, empresa_id)
    if not historico:
        return {"sem_dados": True}

    if ano and mes:
        atual = fs.get_metricas_mes(db, empresa_id, ano, mes)
        if not atual:
            return {"sem_dados": True}
    else:
        atual = historico[-1]

    return _score_engine.calcular(atual, historico)


@router.get("/narrativa/{empresa_id}")
def narrativa(
    empresa_id: int,
    ano: int,
    mes: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Relatório narrativo automático para o período."""
    resolve_empresa_or_403(db, empresa_id, usuario)
    atual = fs.get_metricas_mes(db, empresa_id, ano, mes)
    if not atual:
        return {"sem_dados": True}

    anterior_mes = mes - 1 if mes > 1 else 12
    anterior_ano = ano if mes > 1 else ano - 1
    anterior = fs.get_metricas_mes(db, empresa_id, anterior_ano, anterior_mes)

    historico = fs.get_historico(db, empresa_id)

    empresa_fiscal = (
        db.query(models.EmpresaFiscal)
        .filter(models.EmpresaFiscal.empresa_id == empresa_id)
        .first()
    )
    benchmarks = None
    if empresa_fiscal and empresa_fiscal.cnae:
        benchmarks = fs.get_benchmarks(db, empresa_fiscal.cnae)

    return _narrativa_engine.gerar_narrativa_completa(atual, anterior, historico, benchmarks)


@router.get("/comparativo")
def comparativo_empresas(
    empresas: str,
    ano: int,
    mes: int,
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """Comparativo lado a lado de múltiplas empresas."""
    ids = [int(x.strip()) for x in empresas.split(",") if x.strip().isdigit()]
    if not ids or len(ids) > 10:
        raise HTTPException(status_code=400, detail="Informe de 1 a 10 IDs separados por vírgula.")

    resultados = []
    for empresa_id in ids:
        empresa = resolve_empresa_or_403(db, empresa_id, usuario)
        atual = fs.get_metricas_mes(db, empresa_id, ano, mes)
        if not atual:
            resultados.append({
                "empresa_id": empresa_id,
                "nome": empresa.nome,
                "sem_dados": True,
            })
            continue

        historico = fs.get_historico(db, empresa_id)
        score = _score_engine.calcular(atual, historico)

        resultados.append({
            "empresa_id": empresa_id,
            "nome": empresa.nome,
            "receita_liquida": atual.get("receita_liquida"),
            "lucro_liquido": atual.get("lucro_liquido"),
            "margem_liquida": atual.get("margem_liquida"),
            "margem_bruta": atual.get("margem_bruta"),
            "liquidez_corrente": atual.get("liquidez_corrente"),
            "endividamento_geral": atual.get("endividamento_geral"),
            "ebitda": atual.get("ebitda"),
            "roe": atual.get("roe"),
            "saldo_caixa": atual.get("saldo_caixa"),
            "score_saude": score.get("score"),
            "classificacao_saude": score.get("classificacao"),
            "cor_saude": score.get("cor"),
        })

    return {"comparativo": resultados, "periodo": f"{mes:02d}/{ano}"}


@router.get("/benchmarks")
def listar_benchmarks(
    usuario: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    rows = db.query(models.SetorBenchmark).order_by(models.SetorBenchmark.descricao.asc()).all()
    return [
        {
            "cnae": r.cnae,
            "descricao": r.descricao,
            "margem_liquida_media": r.margem_liquida_media,
            "carga_tributaria_media": r.carga_tributaria_media,
            "folha_sobre_receita_media": r.folha_sobre_receita_media,
        }
        for r in rows
    ]
