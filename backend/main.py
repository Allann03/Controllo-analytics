import math
import os
import re
import time
import uuid
import pdfplumber
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status, Request, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

# Importações dos serviços  (alias para evitar colisão de nomes com rotas)
from services.extrator_pdf import (
    processar_extrato as _processar_extrato_pdf,
    gerar_nome_extrato,
    detectar_banco_com_confianca as _detectar_banco_com_confianca,
)
from services.gerador_excel import gerar_excel
from services.leitor_excel import ler_planilhas_excel
from services.categorizacao_extrato import categorizar_transacoes, resumo_por_categoria
from services.storage import storage as _file_storage

# Verificação contábil (camada adicional — NUNCA impede o fluxo principal)
import logging as _logging
_verification_logger = _logging.getLogger('verification')
try:
    from services.verification import executar_verificacao as _executar_verificacao
except ImportError:
    _executar_verificacao = None
    _verification_logger.warning('Modulo de verificacao contabil nao disponivel')

# Importações do Banco de Dados
from data.database.config import get_db, engine, SessionLocal
from data.database import models

# Utilitários
from sqlalchemy import or_, text
from services.cnpj_validator import validar_cnpj, formatar_cnpj

# Routers
from routers.financeiro import router as financeiro_router
from routers.importacao import router as importacao_router
from routers.conciliacao import router as conciliacao_router
from routers.orcamento import router as orcamento_router
from routers.relatorios import router as relatorios_router
from routers.alertas import router as alertas_router
from routers.auditoria import router as auditoria_router
from routers.auditoria import registrar_auditoria
from routers.empresas import router as empresas_router
from routers.equipe import router as equipe_router
from routers.classificacao import router as classificacao_router
from routers.master import router as master_router
from services.auth_utils import (
    validar_forca_senha, verificar_forca_senha_silencioso, SenhaFracaError,
)
from data.database.models import UsuarioMestreProtegidoError

# ------------------------------------------------------------------ #
#  BANCO DE DADOS E DIRETÓRIOS                                       #
# ------------------------------------------------------------------ #

models.Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------------ #
#  AUTO-MIGRAÇÃO — detecta e adiciona colunas ausentes automaticamente #
# ------------------------------------------------------------------ #

def _auto_migrate() -> None:
    """Compara o schema dos modelos com o banco e adiciona colunas faltantes via ALTER TABLE."""
    from sqlalchemy import inspect as sa_inspect, text as sa_text
    from sqlalchemy.dialects import sqlite as _sqlite_dialect

    insp = sa_inspect(engine)
    existing_tables = set(insp.get_table_names())

    with engine.begin() as conn:
        for mapper in models.Base.registry.mappers:
            table = mapper.persist_selectable
            tname = table.name

            if tname not in existing_tables:
                continue  # create_all já cria tabelas novas

            db_cols = {c["name"] for c in insp.get_columns(tname)}

            for col in table.columns:
                if col.name in db_cols:
                    continue
                # Determina tipo SQLite
                col_type = col.type.compile(dialect=engine.dialect)
                default_clause = ""
                if col.default is not None and col.default.is_scalar:
                    val = col.default.arg
                    default_clause = f" DEFAULT {repr(val)}" if isinstance(val, str) else f" DEFAULT {val}"
                elif not col.nullable:
                    # Inferir default seguro pelo tipo
                    type_str = str(col_type).upper()
                    if "INT" in type_str or "REAL" in type_str or "FLOAT" in type_str or "NUMERIC" in type_str:
                        default_clause = " DEFAULT 0"
                    elif "BOOL" in type_str:
                        default_clause = " DEFAULT 0"
                    else:
                        default_clause = " DEFAULT ''"

                # SEGURANÇA: tname e col.name vêm de modelos SQLAlchemy (hardcoded), não de input do usuário
                sql = f"ALTER TABLE {tname} ADD COLUMN {col.name} {col_type}{default_clause}"
                try:
                    conn.execute(sa_text(sql))
                    print(f"[CONTROLLO] Migração: coluna '{col.name}' adicionada a '{tname}'")
                except Exception as exc:
                    print(f"[CONTROLLO] Migração ignorada ({tname}.{col.name}): {exc}")

_auto_migrate()

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------------ #
#  SEED — dados iniciais para tabelas financeiras                    #
# ------------------------------------------------------------------ #

def _seed_financeiro() -> None:
    """Popula benchmarks e regras tributárias caso ainda não existam."""
    db = SessionLocal()
    try:
        # Benchmarks por setor (CNAE)
        if db.query(models.SetorBenchmark).count() == 0:
            benchmarks = [
                ("6201500", "Desenvolvimento de Software",   12.0, 14.5, 32.0),
                ("6920601", "Contabilidade e Auditoria",     18.0, 13.0, 35.0),
                ("4711301", "Supermercados",                  3.5, 10.0, 18.0),
                ("5611201", "Restaurantes e Similares",       8.0, 12.0, 28.0),
                ("4120400", "Construção de Edifícios",        7.5, 11.5, 22.0),
                ("8630501", "Clínicas Médicas",              20.0, 12.0, 38.0),
                ("6911701", "Escritórios de Advocacia",      25.0, 13.5, 30.0),
                ("4512901", "Comércio de Veículos",           4.0, 10.5, 15.0),
                ("4751200", "Lojas de Artigos Elétricos",    6.5, 11.0, 20.0),
                ("7320300", "Publicidade e Propaganda",      15.0, 13.0, 40.0),
            ]
            for cnae, desc, margem, carga, folha in benchmarks:
                db.add(models.SetorBenchmark(
                    cnae=cnae, descricao=desc,
                    margem_liquida_media=margem,
                    carga_tributaria_media=carga,
                    folha_sobre_receita_media=folha,
                ))

        # Regras tributárias (alíquotas configuráveis)
        if db.query(models.RegrasTributarias).count() == 0:
            regras = [
                # Simples Nacional (faixa inicial típica)
                ("simples", "Simples Nacional", 0.060, "receita_bruta"),
                # Lucro Presumido
                ("presumido", "IRPJ",    0.150, "receita_bruta"),
                ("presumido", "CSLL",    0.090, "receita_bruta"),
                ("presumido", "PIS",     0.0065, "receita_bruta"),
                ("presumido", "COFINS",  0.030, "receita_bruta"),
                ("presumido", "ISS",     0.050, "receita_bruta"),
                # Lucro Real
                ("real",      "IRPJ",   0.150, "receita_bruta"),
                ("real",      "CSLL",   0.090, "receita_bruta"),
                ("real",      "PIS",    0.0165, "receita_bruta"),
                ("real",      "COFINS", 0.076,  "receita_bruta"),
                ("real",      "ISS",    0.050,  "receita_bruta"),
            ]
            for regime, tributo, aliq, base in regras:
                db.add(models.RegrasTributarias(
                    regime=regime, tributo=tributo,
                    aliquota=aliq, base_calculo=base,
                    vigencia_inicio="2025-01-01",
                    vigencia_fim=None,
                ))

        # Parâmetros da Reforma Tributária
        if db.query(models.ReformaParametros).count() == 0:
            db.add(models.ReformaParametros(
                tributo_novo="CBS (federal)",
                aliquota_estimada=0.088,
                regra_credito="Crédito integral sobre insumos e serviços",
                regime_aplicavel="todos",
                vigencia_inicio="2026-01-01",
            ))
            db.add(models.ReformaParametros(
                tributo_novo="IBS (estadual/municipal)",
                aliquota_estimada=0.177,
                regra_credito="Crédito integral sobre insumos e serviços",
                regime_aplicavel="todos",
                vigencia_inicio="2026-01-01",
            ))

        # Plano de Contas Referencial
        if db.query(models.PlanoContasReferencial).count() == 0:
            plano = [
                # (codigo, descricao, grupo, nivel, ordem)
                ("1",     "ATIVO",                                 "ativo",         1,  1),
                ("1.1",   "Ativo Circulante",                      "ativo",         2,  2),
                ("1.1.1", "Disponibilidades (Caixa e Bancos)",     "ativo",         3,  3),
                ("1.1.2", "Créditos (Clientes / Contas a Receber)","ativo",         3,  4),
                ("1.1.3", "Estoques",                              "ativo",         3,  5),
                ("1.1.4", "Outros Ativos Circulantes",             "ativo",         3,  6),
                ("1.2",   "Ativo Não Circulante",                  "ativo",         2,  7),
                ("1.2.1", "Investimentos",                         "ativo",         3,  8),
                ("1.2.2", "Imobilizado",                           "ativo",         3,  9),
                ("1.2.3", "Intangível",                            "ativo",         3, 10),
                ("2",     "PASSIVO E PATRIMÔNIO LÍQUIDO",          "passivo",       1, 11),
                ("2.1",   "Passivo Circulante",                    "passivo",       2, 12),
                ("2.1.1", "Fornecedores",                          "passivo",       3, 13),
                ("2.1.2", "Empréstimos e Financiamentos CP",       "passivo",       3, 14),
                ("2.1.3", "Obrigações Trabalhistas",               "passivo",       3, 15),
                ("2.1.4", "Obrigações Tributárias",                "passivo",       3, 16),
                ("2.1.5", "Outros Passivos Circulantes",           "passivo",       3, 17),
                ("2.2",   "Passivo Não Circulante",                "passivo",       2, 18),
                ("2.2.1", "Empréstimos e Financiamentos LP",       "passivo",       3, 19),
                ("2.3",   "Patrimônio Líquido",                    "pl",            2, 20),
                ("2.3.1", "Capital Social",                        "pl",            3, 21),
                ("2.3.2", "Reservas",                              "pl",            3, 22),
                ("2.3.3", "Lucros / Prejuízos Acumulados",         "pl",            3, 23),
                ("3",     "RECEITAS",                              "receita",       1, 24),
                ("3.1",   "Receita Bruta de Vendas / Serviços",   "receita",       2, 25),
                ("3.2",   "Deduções da Receita",                   "receita",       2, 26),
                ("3.3",   "Outras Receitas Operacionais",          "receita",       2, 27),
                ("4",     "CUSTOS E DESPESAS",                     "custo_despesa", 1, 28),
                ("4.1",   "Custos (CMV / CSV / CSP)",              "custo_despesa", 2, 29),
                ("4.2",   "Despesas Administrativas",              "custo_despesa", 2, 30),
                ("4.3",   "Despesas Comerciais",                   "custo_despesa", 2, 31),
                ("4.4",   "Despesas Financeiras",                  "custo_despesa", 2, 32),
                ("4.5",   "Depreciação e Amortização",             "custo_despesa", 2, 33),
                ("4.6",   "Impostos sobre o Lucro (IR / CSLL)",    "custo_despesa", 2, 34),
            ]
            for codigo, desc, grupo, nivel, ordem in plano:
                db.add(models.PlanoContasReferencial(
                    codigo=codigo, descricao=desc, grupo=grupo, nivel=nivel, ordem=ordem,
                ))

        db.commit()
        print("[CONTROLLO] Seed financeiro concluído.")
    except Exception as exc:
        db.rollback()
        print(f"[CONTROLLO] Erro no seed financeiro: {exc}")
    finally:
        db.close()

_seed_financeiro()


def _migrar_carteira():
    """Migra atribuições existentes (Empresa.usuario_id) para CarteiraMembro."""
    db = SessionLocal()
    try:
        empresas = db.query(models.Empresa).filter(
            models.Empresa.usuario_id.isnot(None)
        ).all()
        migrados = 0
        for empresa in empresas:
            existing = db.query(models.CarteiraMembro).filter(
                models.CarteiraMembro.empresa_id == empresa.id
            ).first()
            if not existing:
                db.add(models.CarteiraMembro(
                    empresa_id=empresa.id,
                    usuario_id=empresa.usuario_id,
                    adicionado_em=empresa.criado_em or datetime.now(timezone.utc).isoformat(),
                ))
                migrados += 1
        db.commit()
        if migrados:
            print(f"[CONTROLLO] Migração CarteiraMembro: {migrados} empresa(s) migrada(s).")
    except Exception as exc:
        db.rollback()
        print(f"[CONTROLLO] Erro na migração CarteiraMembro: {exc}")
    finally:
        db.close()


_migrar_carteira()


def _migrar_schema():
    """Garante que colunas adicionadas após criação inicial do SQLite existam."""
    if "sqlite" not in str(engine.url):
        return  # PostgreSQL usa migrations próprias
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(empresas)"))
            cols = {row[1] for row in result.fetchall()}
            novos = [
                ("nome_fantasia", "TEXT DEFAULT ''"),
                ("ccm",           "TEXT DEFAULT ''"),
                ("status",        "TEXT DEFAULT 'iniciada'"),
                ("ativa",         "BOOLEAN DEFAULT 1"),
                ("observacoes",   "TEXT DEFAULT ''"),
            ]
            for col, tipo in novos:
                if col not in cols:
                    # SEGURANÇA: col e tipo vêm de lista hardcoded acima, não de input do usuário
                    conn.execute(text(f"ALTER TABLE empresas ADD COLUMN {col} {tipo}"))
                    print(f"[CONTROLLO] Migração: coluna 'empresas.{col}' adicionada.")

            # Garante observacoes em carteira_membros
            cm_cols_result = conn.execute(text("PRAGMA table_info(carteira_membros)"))
            cm_cols = {row[1] for row in cm_cols_result.fetchall()}
            if "observacoes" not in cm_cols:
                conn.execute(text("ALTER TABLE carteira_membros ADD COLUMN observacoes TEXT DEFAULT ''"))
                print("[CONTROLLO] Migração: coluna 'carteira_membros.observacoes' adicionada.")

            # Garante nome_exibicao e cargo em usuarios
            u_cols_result = conn.execute(text("PRAGMA table_info(usuarios)"))
            u_cols = {row[1] for row in u_cols_result.fetchall()}
            for col, tipo in [
                ("nome_exibicao", "TEXT DEFAULT ''"),
                ("cargo", "TEXT DEFAULT ''"),
                ("is_gestor", "BOOLEAN DEFAULT 0"),
            ]:
                if col not in u_cols:
                    # SEGURANÇA: col e tipo vêm de lista hardcoded acima, não de input do usuário
                    conn.execute(text(f"ALTER TABLE usuarios ADD COLUMN {col} {tipo}"))
                    print(f"[CONTROLLO] Migração: coluna 'usuarios.{col}' adicionada.")

            # Multi-tenant: usuarios.nome unique deve ser per-escritorio, não global
            idx_result = conn.execute(text("PRAGMA index_list(usuarios)"))
            for row in idx_result.fetchall():
                if row[1] == "ix_usuarios_nome" and row[2] == 1:  # unique=True
                    conn.execute(text("DROP INDEX ix_usuarios_nome"))
                    conn.execute(text("CREATE INDEX ix_usuarios_nome ON usuarios (nome)"))
                    try:
                        conn.execute(text("CREATE UNIQUE INDEX uq_usuario_escritorio_nome ON usuarios (escritorio_id, nome)"))
                    except Exception:
                        pass  # já existe
                    print("[CONTROLLO] Migração: usuarios.nome unique → per-escritorio.")
                    break

            conn.commit()
    except Exception as exc:
        print(f"[CONTROLLO] Aviso na migração de schema: {exc}")


_migrar_schema()

# ------------------------------------------------------------------ #
#  SEGURANÇA                                                         #
# ------------------------------------------------------------------ #

_DEFAULT_SECRET = "controllo-fpa-dev-secret-key-change-in-production-2025"
SECRET_KEY = os.environ.get("CONTROLLO_SECRET_KEY", _DEFAULT_SECRET)
if SECRET_KEY == _DEFAULT_SECRET and os.environ.get("CONTROLLO_ENV") != "test":
    import warnings
    warnings.warn("CONTROLLO_SECRET_KEY não definida — usando chave de desenvolvimento. NÃO use em produção.", stacklevel=1)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("CONTROLLO_TOKEN_EXPIRE_MINUTES", str(60 * 8))
)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

USUARIO_MESTRE = os.environ.get("CONTROLLO_MASTER_USER", "allan")
SENHA_MESTRE   = os.environ.get("CONTROLLO_MASTER_PASSWORD", "Allan@2018")

IS_PROD = os.environ.get("CONTROLLO_ENV", "development") == "production"

# Falha segura em produção: impede inicialização com segredos padrão
if IS_PROD:
    if SECRET_KEY == _DEFAULT_SECRET:
        raise RuntimeError(
            "CONTROLLO_SECRET_KEY não foi definida. "
            "Defina esta variável de ambiente antes de iniciar em produção."
        )
    if SENHA_MESTRE in ("Allan123", "Allan@2018"):
        raise RuntimeError(
            "CONTROLLO_MASTER_PASSWORD está com o valor padrão inseguro. "
            "Defina uma senha forte via variável de ambiente antes de iniciar em produção."
        )

# ── Rate limiting — Redis com fallback em memória ────────────────────
# Redis é usado quando REDIS_URL estiver definida (escalável em múltiplos containers).
# Sem Redis, usa dicionário em memória (apenas desenvolvimento / instância única).
_LIMITE_TENTATIVAS = 10   # tentativas por janela
_JANELA_SEGUNDOS   = 600  # 10 minutos

try:
    import redis as _redis_lib
    _redis_client = _redis_lib.from_url(
        os.environ.get("REDIS_URL", ""),
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    _redis_client.ping()
    _USE_REDIS = True
    print("[CONTROLLO] Rate limiting: Redis conectado.")
except Exception:
    _redis_client = None  # type: ignore[assignment]
    _USE_REDIS = False
    print("[CONTROLLO] Rate limiting: usando memória local (Redis indisponível).")

# Fallback em memória: { ip: [timestamps] }
_login_tentativas: dict[str, list[float]] = {}
_last_rl_cleanup: float = 0.0


def _rate_limit_check(ip: str) -> None:
    """Verifica e registra tentativa de login. Levanta 429 se limite excedido."""
    global _last_rl_cleanup
    agora = time.time()
    if _USE_REDIS and _redis_client is not None:
        key = f"rl:login:{ip}"
        pipe = _redis_client.pipeline()
        pipe.zadd(key, {str(agora): agora})
        pipe.zremrangebyscore(key, 0, agora - _JANELA_SEGUNDOS)
        pipe.zcard(key)
        pipe.expire(key, _JANELA_SEGUNDOS)
        _, _, count, _ = pipe.execute()
        if count > _LIMITE_TENTATIVAS:
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Aguarde 10 minutos antes de tentar novamente.",
            )
    else:
        # Periodic cleanup to prevent memory leak (every 30 min)
        if agora - _last_rl_cleanup > 1800:
            stale_ips = [k for k, v in _login_tentativas.items() if all(agora - t > _JANELA_SEGUNDOS for t in v)]
            for k in stale_ips:
                del _login_tentativas[k]
            _last_rl_cleanup = agora

        janela = _login_tentativas.get(ip, [])
        janela = [t for t in janela if agora - t < _JANELA_SEGUNDOS]
        if len(janela) >= _LIMITE_TENTATIVAS:
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Aguarde 10 minutos antes de tentar novamente.",
            )
        _login_tentativas[ip] = janela + [agora]

# ------------------------------------------------------------------ #
#  USUÁRIO MESTRE — cria ou atualiza no startup                      #
# ------------------------------------------------------------------ #

ESCRITORIO_MASTER_SLUG = os.environ.get("CONTROLLO_MASTER_SLUG", "controllobpo")

# ── Limites por plano (label informativo — não bloqueia por pagamento) ──
PLANOS = {
    "trial":         {"max_empresas": 10,   "max_usuarios": 2},
    "basico":        {"max_empresas": 50,   "max_usuarios": 5},
    "profissional":  {"max_empresas": 500,  "max_usuarios": 30},
    "enterprise":    {"max_empresas": 1500, "max_usuarios": 150},
}


def _garantir_escritorio_master() -> models.Escritorio:
    """Garante que o escritório master existe e retorna a instância."""
    db = SessionLocal()
    try:
        esc = db.query(models.Escritorio).filter(
            models.Escritorio.slug == ESCRITORIO_MASTER_SLUG
        ).first()
        agora = datetime.now(timezone.utc).isoformat()

        if esc:
            esc.plano = "enterprise"
            esc.max_empresas = 1500
            esc.max_usuarios = 150
            esc.ativo = True
            esc.atualizado_em = agora
            db.commit()
            db.refresh(esc)
            print(f"[CONTROLLO] Escritorio master atualizado: {ESCRITORIO_MASTER_SLUG}")
        else:
            esc = models.Escritorio(
                nome="Controllo BPO Analytics",
                slug=ESCRITORIO_MASTER_SLUG,
                plano="enterprise",
                max_empresas=1500,
                max_usuarios=150,
                data_expiracao=None,
                ativo=True,
                criado_em=agora,
                atualizado_em=agora,
            )
            db.add(esc)
            db.commit()
            db.refresh(esc)
            print(f"[CONTROLLO] Escritorio master criado: {ESCRITORIO_MASTER_SLUG}")

        esc_id = esc.id
    except Exception as exc:
        db.rollback()
        print(f"[CONTROLLO] Erro ao garantir escritorio master: {exc}")
        esc_id = 1
    finally:
        db.close()
    return esc_id  # type: ignore[return-value]


_MASTER_ESCRITORIO_ID = _garantir_escritorio_master()


def _garantir_usuario_mestre() -> None:
    """
    Cria o usuário mestre se e somente se ainda não existir.

    GARANTIA R2: se o registro já existir, NUNCA modifica senha_hash
    nem escritorio_id — apenas corrige flags de permissão caso
    divirjam do esperado (proteção contra corrupção acidental de role).
    """
    db = SessionLocal()
    try:
        user = db.query(models.Usuario).filter(
            models.Usuario.nome == USUARIO_MESTRE,
            models.Usuario.escritorio_id == _MASTER_ESCRITORIO_ID,
        ).first()

        if user:
            # Corrige apenas flags — NUNCA toca senha_hash nem escritorio_id
            dirty = False
            for attr, val in [
                ("is_master", True), ("is_dono", True), ("is_admin", True),
                ("is_ceo", True), ("is_gestor", True), ("is_aprovado", True),
            ]:
                if getattr(user, attr) != val:
                    setattr(user, attr, val)
                    dirty = True
            user.nome_exibicao = user.nome_exibicao or "Allan"
            user.cargo = user.cargo or "Administrador Master"
            if dirty:
                db.commit()
                print(f"[CONTROLLO] Flags do usuario mestre corrigidas: {USUARIO_MESTRE}")
            else:
                print(f"[CONTROLLO] Usuario mestre OK (sem alteracoes): {USUARIO_MESTRE}")
        else:
            db.add(models.Usuario(
                nome=USUARIO_MESTRE,
                senha_hash=pwd_context.hash(SENHA_MESTRE),  # hash SOMENTE na criação
                is_master=True,
                is_dono=True,
                is_admin=True,
                is_ceo=True,
                is_gestor=True,
                is_aprovado=True,
                nome_exibicao="Allan",
                cargo="Administrador Master",
                escritorio_id=_MASTER_ESCRITORIO_ID,
            ))
            db.commit()
            print(f"[CONTROLLO] Usuario mestre criado: {USUARIO_MESTRE}")
    except Exception as exc:
        db.rollback()
        print(f"[CONTROLLO] Erro ao garantir usuario mestre: {exc}")
    finally:
        db.close()

_garantir_usuario_mestre()


def _migrar_usuarios_sem_escritorio():
    """Migra usuários existentes sem escritorio_id para o escritório master."""
    db = SessionLocal()
    try:
        sem_esc = db.query(models.Usuario).filter(
            models.Usuario.escritorio_id.is_(None)
        ).all()
        if sem_esc:
            for u in sem_esc:
                u.escritorio_id = _MASTER_ESCRITORIO_ID
            db.commit()
            print(f"[CONTROLLO] Migração multi-tenant: {len(sem_esc)} usuário(s) associado(s) ao escritório master.")

        # Migra empresas sem escritorio_id
        sem_esc_emp = db.query(models.Empresa).filter(
            models.Empresa.escritorio_id.is_(None)
        ).all()
        if sem_esc_emp:
            for e in sem_esc_emp:
                e.escritorio_id = _MASTER_ESCRITORIO_ID
            db.commit()
            print(f"[CONTROLLO] Migração multi-tenant: {len(sem_esc_emp)} empresa(s) associada(s) ao escritório master.")
    except Exception as exc:
        db.rollback()
        print(f"[CONTROLLO] Aviso migração multi-tenant: {exc}")
    finally:
        db.close()

_migrar_usuarios_sem_escritorio()

# ------------------------------------------------------------------ #
#  APP FASTAPI                                                       #
# ------------------------------------------------------------------ #

app = FastAPI(
    title="Controllo BPO API",
    description="Plataforma de Inteligência Financeira - Controllo BPO Analytics",
    version="3.0.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

# ── Security headers ────────────────────────────────────────────────
_MAX_UPLOAD_MB = int(os.environ.get("CONTROLLO_MAX_UPLOAD_MB", "25"))

class _SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Bloqueia uploads acima do limite antes de processar
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_UPLOAD_MB * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Arquivo muito grande. Limite: {_MAX_UPLOAD_MB} MB."},
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]   = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]            = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]         = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"]    = (
            "default-src 'none'; "
            "frame-ancestors 'none';"
        )
        response.headers["Cache-Control"]              = "no-store"
        if IS_PROD:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response

app.add_middleware(_SecurityHeadersMiddleware)

# Origens permitidas.
# CORS_ORIGINS aceita origens extras separadas por vírgula (ex: Vercel preview URLs).
_extra_origins = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "").split(",")
    if o.strip()
]
origens_permitidas = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "https://saas-controllo.vercel.app",
] + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_permitidas,
    # Aceita apenas previews do projeto Controllo no Vercel (prefixo saas-controllo-)
    allow_origin_regex=r"https://saas-controllo[a-zA-Z0-9\-]*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
)

# Inclui router dos módulos financeiros
app.include_router(financeiro_router)
app.include_router(importacao_router)
app.include_router(conciliacao_router)
app.include_router(orcamento_router)
app.include_router(relatorios_router)
app.include_router(alertas_router)
app.include_router(auditoria_router)
app.include_router(empresas_router)
app.include_router(equipe_router)
app.include_router(classificacao_router)
app.include_router(master_router)


# ── Exception handlers globais ──────────────────────────────────────

@app.exception_handler(SenhaFracaError)
async def _handler_senha_fraca(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(UsuarioMestreProtegidoError)
async def _handler_mestre_protegido(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ------------------------------------------------------------------ #
#  SCHEMAS PYDANTIC                                                  #
# ------------------------------------------------------------------ #

class UsuarioCreate(BaseModel):
    nome: str
    senha: str

    @property
    def nome_normalizado(self) -> str:
        return self.nome.strip().lower()

    def validar(self) -> None:
        nome = self.nome.strip()
        if not re.match(r'^[a-zA-Z0-9._-]{3,30}$', nome):
            raise HTTPException(400, "Nome deve ter 3–30 caracteres. Use apenas letras, números, '.', '_' ou '-'.")
        validar_forca_senha(self.senha, nome_usuario=nome)

class AtualizarAprovacao(BaseModel):
    is_aprovado: bool

class AtualizarAdmin(BaseModel):
    is_admin: bool

class AtualizarGestor(BaseModel):
    is_gestor: bool

class AtualizarCEO(BaseModel):
    is_ceo: bool

class UsuarioResponse(BaseModel):
    id: int
    nome: str
    is_admin: bool
    is_ceo: bool = False
    is_gestor: bool = False
    is_aprovado: bool
    avatar_id: Optional[str] = None
    class Config:
        from_attributes = True

_DATE_BR_RE  = re.compile(r'^\d{2}/\d{2}/\d{4}$')
_HORA_RE     = re.compile(r'^\d{2}:\d{2}$')
_PRIORIDADES = {"baixa", "media", "alta", "urgente"}

class LembreteCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = ""
    data_vencimento: str          # DD/MM/AAAA
    hora: Optional[str] = "09:00"
    prioridade: Optional[str] = "media"
    empresa_vinculada: Optional[str] = ""

    def validar(self) -> None:
        if not self.titulo or len(self.titulo.strip()) < 2:
            raise HTTPException(400, "Título deve ter pelo menos 2 caracteres.")
        if len(self.titulo) > 200:
            raise HTTPException(400, "Título muito longo (máx. 200 caracteres).")
        if not _DATE_BR_RE.match(self.data_vencimento or ""):
            raise HTTPException(400, "Data de vencimento deve estar no formato DD/MM/AAAA.")
        hora = (self.hora or "09:00").strip()
        if not _HORA_RE.match(hora):
            raise HTTPException(400, "Hora deve estar no formato HH:MM.")
        if (self.prioridade or "media") not in _PRIORIDADES:
            raise HTTPException(400, "Prioridade inválida.")

class LembreteUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    data_vencimento: Optional[str] = None
    hora: Optional[str] = None
    prioridade: Optional[str] = None
    status: Optional[str] = None
    empresa_vinculada: Optional[str] = None

# Status possíveis para empresas
EMPRESA_STATUSES = [
    "iniciada",
    "em_andamento",
    "extratos_pendentes",
    "pendencia_fiscal",
    "pendencia_juridica",
    "finalizada",
    "aguardando_documentos",
    "documentacao_pendente",
    "em_revisao",
    "entregue",
    "suspenso",
    "concluida",
    "defis_entregue",
    "erro_integracao_fiscal",
    "erro_integracao_folha",
]

class EmpresaCreate(BaseModel):
    nome: str
    nome_fantasia: Optional[str] = ""
    cnpj: Optional[str] = ""
    ccm: Optional[str] = ""
    status: Optional[str] = "iniciada"
    observacoes: Optional[str] = ""

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None
    ccm: Optional[str] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None

class EmpresaStatusUpdate(BaseModel):
    status: str

# ------------------------------------------------------------------ #
#  AUTENTICAÇÃO — helpers                                            #
# ------------------------------------------------------------------ #

def _decodificar_token(token: str) -> dict:
    """Decodifica e valida o JWT. Lança HTTPException em caso de falha."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise ValueError("sub ausente")
        return payload
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas ou expiradas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    payload = _decodificar_token(token)
    eid = payload.get("eid")
    q = db.query(models.Usuario).filter(models.Usuario.nome == payload["sub"])
    if eid:
        q = q.filter(models.Usuario.escritorio_id == eid)
    user = q.first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
    if not user.is_aprovado:
        raise HTTPException(status_code=403, detail="Conta nao aprovada.")
    user._escritorio_id = user.escritorio_id or _MASTER_ESCRITORIO_ID  # type: ignore[attr-defined]
    user._is_master = getattr(user, "is_master", False)  # type: ignore[attr-defined]
    return user

async def get_current_admin_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    payload = _decodificar_token(token)
    eid = payload.get("eid")
    q = db.query(models.Usuario).filter(models.Usuario.nome == payload["sub"])
    if eid:
        q = q.filter(models.Usuario.escritorio_id == eid)
    user = q.first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
    if not user.is_aprovado:
        raise HTTPException(status_code=403, detail="Conta nao aprovada.")
    # Master bypasses admin check
    if not user.is_admin and not getattr(user, "is_master", False):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores aprovados.")
    user._escritorio_id = user.escritorio_id or _MASTER_ESCRITORIO_ID  # type: ignore[attr-defined]
    user._is_master = getattr(user, "is_master", False)  # type: ignore[attr-defined]
    return user

async def get_current_gestor_or_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """Permite acesso a administradores, gestores e master."""
    payload = _decodificar_token(token)
    eid = payload.get("eid")
    q = db.query(models.Usuario).filter(models.Usuario.nome == payload["sub"])
    if eid:
        q = q.filter(models.Usuario.escritorio_id == eid)
    user = q.first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
    if not user.is_aprovado:
        raise HTTPException(status_code=403, detail="Conta nao aprovada.")
    _is_master = getattr(user, "is_master", False)
    if not (user.is_admin or getattr(user, "is_gestor", False) or _is_master):
        raise HTTPException(status_code=403, detail="Acesso restrito a gestores e administradores.")
    user._escritorio_id = user.escritorio_id or _MASTER_ESCRITORIO_ID  # type: ignore[attr-defined]
    user._is_master = _is_master  # type: ignore[attr-defined]
    return user

# ------------------------------------------------------------------ #
#  ROTAS — HEALTH                                                    #
# ------------------------------------------------------------------ #

@app.get("/")
def root():
    return {"status": "online", "sistema": "Controllo BPO Analytics v3.0"}


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check para AWS ALB / ECS / qualquer load balancer."""
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    if not db_ok:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "healthy", "db": "ok"}

# ------------------------------------------------------------------ #
#  ROTAS — VERIFICAÇÃO DE ESCRITÓRIO (público, pré-login)            #
# ------------------------------------------------------------------ #

@app.get("/api/auth/verificar-escritorio")
def verificar_escritorio(slug: str = "", db: Session = Depends(get_db)):
    """Verifica se um slug de escritório é válido. Não requer autenticação."""
    slug = slug.strip().lower()
    if not slug:
        return {"existe": False}
    esc = db.query(models.Escritorio).filter(
        models.Escritorio.slug == slug, models.Escritorio.ativo == True  # noqa: E712
    ).first()
    if esc:
        return {"existe": True, "nome": esc.nome}
    return {"existe": False}

# ------------------------------------------------------------------ #
#  ROTAS — AUTENTICAÇÃO                                              #
# ------------------------------------------------------------------ #

class SolicitarAcessoBody(BaseModel):
    nome: str
    senha: str
    escritorio: Optional[str] = None  # slug do escritório (None = master)

@app.post("/api/auth/solicitar-acesso")
def solicitar_acesso(request: Request, body: SolicitarAcessoBody, db: Session = Depends(get_db)):
    ip = (request.client.host if request.client else "unknown")
    _rate_limit_check(ip)
    # Reutiliza validação de UsuarioCreate
    uc = UsuarioCreate(nome=body.nome, senha=body.senha)
    uc.validar()
    nome = body.nome.strip().lower()
    if nome == USUARIO_MESTRE:
        raise HTTPException(status_code=400, detail="Este nome nao esta disponivel.")

    # Resolve escritório
    slug = (body.escritorio or "").strip().lower() or ESCRITORIO_MASTER_SLUG
    escritorio = db.query(models.Escritorio).filter(
        models.Escritorio.slug == slug, models.Escritorio.ativo == True
    ).first()
    if not escritorio:
        raise HTTPException(status_code=400, detail="Escritório não encontrado.")

    # Verifica limite de usuários do plano
    count_users = db.query(models.Usuario).filter(
        models.Usuario.escritorio_id == escritorio.id
    ).count()
    if count_users >= escritorio.max_usuarios:
        raise HTTPException(status_code=400, detail=f"Este escritório atingiu o limite de {escritorio.max_usuarios} usuários.")

    existente = db.query(models.Usuario).filter(
        models.Usuario.nome == nome,
        models.Usuario.escritorio_id == escritorio.id,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Este nome ja esta cadastrado ou aguardando aprovacao.")

    db.add(models.Usuario(
        nome=nome,
        senha_hash=pwd_context.hash(body.senha[:72]),
        is_admin=False,
        is_aprovado=False,
        escritorio_id=escritorio.id,
    ))
    db.commit()
    registrar_auditoria(db, "solicitar_acesso", usuario_nome=nome,
                        escritorio_id=escritorio.id, recurso="usuario",
                        detalhes={"escritorio": escritorio.slug}, ip=ip)
    return {"mensagem": "Solicitacao enviada! Aguarde a aprovacao do Administrador."}

@app.post("/api/auth/login")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # ── Rate limiting por IP ────────────────────────────────────────
    ip = (request.client.host if request.client else "unknown")
    _rate_limit_check(ip)

    raw_username = form_data.username.strip().lower()

    # ── Multi-tenant: parse user@escritorio do username ──
    # Formato: "allan@controllobpo" → nome="allan", slug="controllobpo"
    # Se sem @, tenta client_id ou escritório padrão (retrocompatível)
    if "@" in raw_username:
        parts = raw_username.rsplit("@", 1)
        nome = parts[0].strip()
        slug_raw = parts[1].strip()
    else:
        nome = raw_username
        slug_raw = (form_data.client_id or "").strip().lower() or ESCRITORIO_MASTER_SLUG

    escritorio = db.query(models.Escritorio).filter(
        models.Escritorio.slug == slug_raw, models.Escritorio.ativo == True
    ).first()
    if not escritorio:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    # Verificação de expiração do plano (preparado para futuro — nunca bloqueia se data_expiracao=None)
    if escritorio.data_expiracao:
        try:
            exp_date = datetime.fromisoformat(escritorio.data_expiracao)
            if exp_date < datetime.now(timezone.utc):
                raise HTTPException(status_code=403, detail="O plano deste escritório expirou. Entre em contato com o suporte.")
        except (ValueError, TypeError):
            pass

    # Verificação do usuário dentro do escritório
    user = db.query(models.Usuario).filter(
        models.Usuario.nome == nome,
        models.Usuario.escritorio_id == escritorio.id,
    ).first()
    senha_ok = bool(user) and pwd_context.verify(form_data.password[:72], user.senha_hash)  # type: ignore[union-attr]
    if not user or not senha_ok:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    if not user.is_aprovado:
        raise HTTPException(status_code=403, detail="Sua conta ainda não foi aprovada pelo Administrador.")

    expiracao = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    _is_master = getattr(user, "is_master", False)
    _is_ceo = getattr(user, "is_ceo", False)
    _is_gestor = getattr(user, "is_gestor", False)
    _role = "master" if _is_master else ("ceo" if _is_ceo else ("admin" if user.is_admin else ("gestor" if _is_gestor else "analista")))
    token = jwt.encode(
        {
            "sub": user.nome,
            "eid": escritorio.id,
            "is_master": _is_master,
            "is_admin": user.is_admin,
            "is_ceo": _is_ceo,
            "is_gestor": _is_gestor,
            "role": _role,
            "tv": getattr(user, "token_version", 0) or 0,
            "exp": expiracao,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    registrar_auditoria(db, "login", usuario_id=user.id, usuario_nome=user.nome,
                        recurso="usuario", recurso_id=user.id, ip=ip,
                        escritorio_id=user.escritorio_id)

    # Opção B — informar senha fraca sem bloquear login.
    # Exceção: usuário mestre nunca recebe flag (senha histórica legítima,
    # evita banner de "senha fraca" no admin principal a cada login).
    senha_requer_atualizacao = False
    senha_motivo = None
    if not _is_master:
        forte, motivo = verificar_forca_senha_silencioso(
            form_data.password[:72], nome_usuario=nome,
        )
        if not forte:
            senha_requer_atualizacao = True
            senha_motivo = motivo

    return {
        "access_token": token,
        "token_type": "bearer",
        "senha_requer_atualizacao": senha_requer_atualizacao,
        "senha_motivo": senha_motivo,
        "usuario": {
            "id": user.id,
            "nome": user.nome,
            "login": f"{user.nome}@{escritorio.slug}",
            "nome_exibicao": user.nome_exibicao or "",
            "cargo": user.cargo or "",
            "is_master": _is_master,
            "is_admin": user.is_admin,
            "is_ceo": _is_ceo,
            "is_gestor": _is_gestor,
            "is_aprovado": user.is_aprovado,
            "role": _role,
        },
        "escritorio": {
            "id": escritorio.id,
            "nome": escritorio.nome,
            "slug": escritorio.slug,
            "plano": escritorio.plano,
        },
    }

# ------------------------------------------------------------------ #
#  ROTAS — PERFIL DO USUÁRIO                                        #
# ------------------------------------------------------------------ #

class PerfilUpdate(BaseModel):
    nome_exibicao: Optional[str] = None
    cargo: Optional[str] = None
    avatar_id: Optional[str] = None
    exibir_nome_social: Optional[bool] = None

class SenhaUpdate(BaseModel):
    senha_atual: str
    nova_senha: str

@app.get("/api/auth/me")
def meu_perfil(current_user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    _is_master = getattr(current_user, "is_master", False)
    _is_ceo = getattr(current_user, "is_ceo", False)
    _is_gestor = getattr(current_user, "is_gestor", False)
    _role = "master" if _is_master else ("ceo" if _is_ceo else ("admin" if current_user.is_admin else ("gestor" if _is_gestor else "analista")))
    esc = db.query(models.Escritorio).filter(models.Escritorio.id == current_user.escritorio_id).first() if current_user.escritorio_id else None
    return {
        "id": current_user.id,
        "nome": current_user.nome,
        "login": f"{current_user.nome}@{esc.slug}" if esc else current_user.nome,
        "nome_exibicao": current_user.nome_exibicao or "",
        "cargo": current_user.cargo or "",
        "avatar_id": current_user.avatar_id,
        "exibir_nome_social": bool(getattr(current_user, "exibir_nome_social", False)),
        "is_master": _is_master,
        "is_admin": current_user.is_admin,
        "is_ceo": _is_ceo,
        "is_gestor": _is_gestor,
        "is_aprovado": current_user.is_aprovado,
        "role": _role,
        "escritorio": {
            "id": esc.id,
            "nome": esc.nome,
            "slug": esc.slug,
            "plano": esc.plano,
        } if esc else None,
    }

@app.patch("/api/auth/perfil")
def atualizar_perfil(
    body: PerfilUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.nome_exibicao is not None:
        current_user.nome_exibicao = body.nome_exibicao.strip()[:80]
    if body.cargo is not None:
        current_user.cargo = body.cargo.strip()[:80]
    if body.avatar_id is not None:
        clean = body.avatar_id.strip().lower()[:64]
        if clean and all(c in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in clean):
            current_user.avatar_id = clean
        elif clean == "":
            current_user.avatar_id = None  # permite remover avatar
        # caracteres invalidos -> ignora silenciosamente (preserva valor anterior)
    if body.exibir_nome_social is not None:
        current_user.exibir_nome_social = bool(body.exibir_nome_social)
    db.commit()
    return {
        "mensagem": "Perfil atualizado.",
        "nome_exibicao": current_user.nome_exibicao or "",
        "cargo": current_user.cargo or "",
        "avatar_id": current_user.avatar_id,
        "exibir_nome_social": bool(current_user.exibir_nome_social),
    }

@app.patch("/api/auth/senha")
def alterar_senha(
    body: SenhaUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not pwd_context.verify(body.senha_atual, current_user.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")
    validar_forca_senha(body.nova_senha, nome_usuario=current_user.nome)
    current_user.senha_hash = pwd_context.hash(body.nova_senha)
    db.commit()
    return {"mensagem": "Senha alterada com sucesso."}

# ------------------------------------------------------------------ #
#  ROTAS — ADMIN USUARIOS                                            #
# ------------------------------------------------------------------ #

@app.get("/api/admin/usuarios", response_model=List[UsuarioResponse])
def listar_usuarios(
    _admin: models.Usuario = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.Usuario)
    # Tenant isolation: non-master users only see their own escritório
    if not getattr(_admin, "is_master", False):
        eid = getattr(_admin, "_escritorio_id", None) or _admin.escritorio_id
        q = q.filter(models.Usuario.escritorio_id == eid)
    return (
        q.order_by(models.Usuario.is_aprovado.asc(), models.Usuario.nome.asc())
        .all()
    )

@app.patch("/api/admin/usuarios/{usuario_id}/aprovar")
def aprovar_usuario(
    usuario_id: int,
    body: AtualizarAprovacao,
    _admin: models.Usuario = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    # Tenant isolation: admin só opera no próprio escritório (master bypassa)
    if not getattr(_admin, "is_master", False) and user.escritorio_id != _admin.escritorio_id:
        raise HTTPException(status_code=403, detail="Acesso negado: usuario pertence a outro escritorio.")
    if user.nome == USUARIO_MESTRE:
        raise HTTPException(status_code=403, detail="O usuario mestre nao pode ser alterado.")
    user.is_aprovado = body.is_aprovado
    user.token_version = (getattr(user, "token_version", 0) or 0) + 1
    db.commit()
    db.refresh(user)
    acao_str = "aprovar_usuario" if body.is_aprovado else "bloquear_usuario"
    registrar_auditoria(db, acao_str, usuario_id=_admin.id, usuario_nome=_admin.nome,
                        recurso="usuario", recurso_id=usuario_id, detalhes={"alvo": user.nome},
                        escritorio_id=_admin.escritorio_id)
    acao = "aprovado" if body.is_aprovado else "bloqueado"
    return {"mensagem": f"Usuario {acao} com sucesso.", "usuario": UsuarioResponse.model_validate(user)}

@app.patch("/api/admin/usuarios/{usuario_id}/promover")
def promover_usuario(
    usuario_id: int,
    body: AtualizarAdmin,
    _admin: models.Usuario = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    if not getattr(_admin, "is_master", False) and user.escritorio_id != _admin.escritorio_id:
        raise HTTPException(status_code=403, detail="Acesso negado: usuario pertence a outro escritorio.")
    if user.nome == USUARIO_MESTRE:
        raise HTTPException(status_code=403, detail="O usuario mestre nao pode ser alterado.")
    user.is_admin = body.is_admin
    user.token_version = (getattr(user, "token_version", 0) or 0) + 1
    db.commit()
    db.refresh(user)
    acao_str = "promover_admin" if body.is_admin else "revogar_admin"
    registrar_auditoria(db, acao_str, usuario_id=_admin.id, usuario_nome=_admin.nome,
                        recurso="usuario", recurso_id=usuario_id, detalhes={"alvo": user.nome},
                        escritorio_id=_admin.escritorio_id)
    acao = "promovido a administrador" if body.is_admin else "rebaixado a operador"
    return {"mensagem": f"Usuario {acao} com sucesso.", "usuario": UsuarioResponse.model_validate(user)}

@app.patch("/api/admin/usuarios/{usuario_id}/gestor")
def definir_gestor(
    usuario_id: int,
    body: AtualizarGestor,
    _admin: models.Usuario = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    if not getattr(_admin, "is_master", False) and user.escritorio_id != _admin.escritorio_id:
        raise HTTPException(status_code=403, detail="Acesso negado: usuario pertence a outro escritorio.")
    if user.nome == USUARIO_MESTRE:
        raise HTTPException(status_code=403, detail="O usuario mestre nao pode ser alterado.")
    user.is_gestor = body.is_gestor
    user.token_version = (getattr(user, "token_version", 0) or 0) + 1
    db.commit()
    db.refresh(user)
    acao_str = "promover_gestor" if body.is_gestor else "revogar_gestor"
    registrar_auditoria(db, acao_str, usuario_id=_admin.id, usuario_nome=_admin.nome,
                        recurso="usuario", recurso_id=usuario_id, detalhes={"alvo": user.nome},
                        escritorio_id=_admin.escritorio_id)
    acao = "promovido a gestor" if body.is_gestor else "removido do papel de gestor"
    return {"mensagem": f"Usuario {acao} com sucesso.", "usuario": UsuarioResponse.model_validate(user)}

@app.patch("/api/admin/usuarios/{usuario_id}/ceo")
def definir_ceo(
    usuario_id: int,
    body: AtualizarCEO,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Promoção a CEO. Só é permitida pelo usuário mestre ("Allan") ou por um CEO existente."""
    caller_is_ceo = getattr(current_user, "is_ceo", False)
    caller_is_master = current_user.nome.lower() == USUARIO_MESTRE.lower()
    if not (caller_is_ceo or caller_is_master):
        raise HTTPException(status_code=403, detail="Apenas o usuário mestre ou um CEO pode promover/revogar CEOs.")
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    if not getattr(current_user, "is_master", False) and user.escritorio_id != current_user.escritorio_id:
        raise HTTPException(status_code=403, detail="Acesso negado: usuario pertence a outro escritorio.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode alterar seu próprio cargo CEO.")
    user.is_ceo = body.is_ceo
    user.token_version = (getattr(user, "token_version", 0) or 0) + 1
    db.commit()
    db.refresh(user)
    acao_str = "promover_ceo" if body.is_ceo else "revogar_ceo"
    registrar_auditoria(db, acao_str, usuario_id=current_user.id, usuario_nome=current_user.nome,
                        recurso="usuario", recurso_id=usuario_id, detalhes={"alvo": user.nome},
                        escritorio_id=current_user.escritorio_id)
    acao = "promovido a CEO" if body.is_ceo else "removido do cargo de CEO"
    return {"mensagem": f"Usuario {acao} com sucesso.", "usuario": UsuarioResponse.model_validate(user)}

@app.delete("/api/admin/usuarios/{usuario_id}")
def excluir_usuario(
    usuario_id: int,
    _admin: models.Usuario = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    if not getattr(_admin, "is_master", False) and user.escritorio_id != _admin.escritorio_id:
        raise HTTPException(status_code=403, detail="Acesso negado: usuario pertence a outro escritorio.")
    if user.nome == USUARIO_MESTRE:
        raise HTTPException(status_code=403, detail="O usuario mestre nao pode ser excluido.")
    if user.is_aprovado:
        raise HTTPException(status_code=400, detail="Nao e possivel excluir um usuario ativo. Bloqueie-o primeiro.")
    nome_alvo = user.nome
    db.delete(user)
    db.commit()
    registrar_auditoria(db, "excluir_usuario", usuario_id=_admin.id, usuario_nome=_admin.nome,
                        recurso="usuario", recurso_id=usuario_id, detalhes={"alvo": nome_alvo},
                        escritorio_id=_admin.escritorio_id)
    return {"mensagem": "Usuario removido com sucesso."}


# ─── Backup ─────────────────────────────────────────────────────────
from services.backup_service import BackupService
_backup_service = BackupService(storage=_file_storage)


@app.post("/api/admin/backup")
def executar_backup(
    _admin: models.Usuario = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Executa backup manual do banco (apenas admin)."""
    resultado = _backup_service.executar_backup()
    registrar_auditoria(
        db, "backup_manual",
        usuario_id=_admin.id, usuario_nome=_admin.nome,
        recurso="backup", detalhes=resultado,
        escritorio_id=_admin.escritorio_id,
    )
    if not resultado.get("sucesso"):
        raise HTTPException(status_code=500, detail=resultado.get("erro", "Falha no backup."))
    return resultado

# ------------------------------------------------------------------ #
#  UTILITÁRIO — EXTRAÇÃO DE NÚMERO DE CONTA                          #
# ------------------------------------------------------------------ #

def _extrair_numero_conta(pdf_path: str) -> Optional[str]:
    """Escaneia as primeiras páginas do PDF em busca de número de conta bancária."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texto = "\n".join(
                (p.extract_text() or "") for p in pdf.pages[:3]
            )

        padroes = [
            # "Conta Corrente: 07084-3" / "Conta: 07084-3"
            r'[Cc]onta(?:\s+[Cc]orrente)?[:\s]+(\d{3,8}[-]\d)',
            # "CC: 07084-3"
            r'\bCC[:\s]+(\d{3,8}[-]\d)',
            # "Nº da Conta: 07084-3"
            r'N[oº°]\.?\s*(?:da\s+)?[Cc]onta[:\s]+(\d{3,8}[-]\d)',
            # "Agência 0708  Conta 07084-3"
            r'[Aa]g[eê]ncia\s+\d+\s+[Cc]onta\s+(\d{3,8}[-]\d)',
        ]

        for padrao in padroes:
            m = re.search(padrao, texto)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


# ------------------------------------------------------------------ #
#  ROTAS — EXTRATOR DE PDF                                           #
# ------------------------------------------------------------------ #

@app.post("/api/processar-extrato")
async def rota_processar_extrato(
    arquivo: UploadFile = File(...),
    banco: str = Form(""),
    senha_pdf: str = Form(""),
    empresa_id: int = Form(0),
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not arquivo.filename or not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Formato invalido. Apenas PDFs sao aceitos.")

    # Limite de tamanho: 50 MB por arquivo (PDFs de até ~300 páginas)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    PDF_MAGIC = b"%PDF"

    job_id = str(uuid.uuid4())
    pdf_path  = os.path.join(UPLOAD_DIR, f"{job_id}.pdf")
    # Excel temporário vai em UPLOAD_DIR para não colidir com _file_storage
    # que usa OUTPUT_DIR como base. O finally apaga apenas este arquivo temporário;
    # o storage gerencia o ciclo de vida do arquivo em OUTPUT_DIR.
    excel_path = os.path.join(UPLOAD_DIR, f"{job_id}.xlsx")

    try:
        conteudo = await arquivo.read()
        if not conteudo:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")
        if len(conteudo) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo muito grande ({len(conteudo)//1024//1024} MB). Limite: 50 MB."
            )
        if not conteudo[:4].startswith(PDF_MAGIC):
            raise HTTPException(status_code=400, detail="Arquivo não é um PDF válido.")

        # Salva PDF num arquivo temporário local (necessário para o parser)
        with open(pdf_path, "wb") as f:
            f.write(conteudo)

        # Pipeline de 8 passos (executa validação estruturada)
        from services.pipeline_extracao import processar_com_pipeline as _pipeline
        _pipeline_result = _pipeline(pdf_path, banco_id=banco, senha=senha_pdf or None)

        # Chama o serviço (alias _processar_extrato_pdf para evitar colisão de nome)
        resultado = _processar_extrato_pdf(pdf_path, banco_id=banco, password=senha_pdf or None)

        if resultado.get("requer_senha"):
            return JSONResponse(status_code=422, content={"erro": resultado["erro"], "requer_senha": True})

        if resultado.get("erro"):
            raise HTTPException(status_code=422, detail=resultado["erro"])

        # Extrai número de conta antes de apagar o PDF temporário
        numero_conta = _extrair_numero_conta(pdf_path)

        transacoes = resultado["transacoes"]
        if not transacoes:
            # Extrato zerado não é erro — retorna sem Excel
            return JSONResponse({
                "sucesso": True,
                "nome_arquivo": arquivo.filename,
                "banco_detectado": resultado.get("banco", "desconhecido").capitalize(),
                "total_transacoes": 0,
                "resumo": {"entradas": 0.0, "saidas": 0.0, "posicao": 0.0, "aplicado": 0.0, "saldo": 0.0},
                "avisos": resultado.get("avisos", ["Extrato sem transacoes encontradas."]),
                "excel_id": None,
                "excel_url": None,
                "transacoes": [],
                "categorias": [],
                "numero_conta": numero_conta,
            })

        # ── Categorização automática (pós-processamento — não toca no PDF) ──
        transacoes = categorizar_transacoes(transacoes)
        categorias = resumo_por_categoria(transacoes)

        # Gera nome descritivo para o extrato (banco + período)
        banco_key = resultado.get("banco", "desconhecido")
        nome_extrato = gerar_nome_extrato(banco_key, transacoes)

        # Gera Excel num arquivo temporário local e envia para o storage
        gerar_excel(transacoes, excel_path, saldo_inicial=resultado.get("saldo_inicial"))
        with open(excel_path, "rb") as f:
            excel_bytes = f.read()
        _eid_prefix = current_user.escritorio_id or 0
        _file_storage.save(excel_bytes, f"eid{_eid_prefix}_{job_id}.xlsx")

        # >>> VERIFICAÇÃO CONTÁBIL (camada adicional — informativa, nunca bloqueia) <<<
        _verificacao_resultado = None
        if _executar_verificacao is not None:
            try:
                _verificacao_resultado = _executar_verificacao(
                    banco_key=banco_key,
                    transacoes=transacoes,
                    saldo_inicial=resultado.get("saldo_inicial"),
                    saldo_final=resultado.get("saldo_final"),
                    file_name=arquivo.filename or '',
                    pdf_path=pdf_path,
                    password=senha_pdf or None,
                )
            except Exception as _verif_err:
                _verification_logger.error(f"Erro na verificacao adicional: {_verif_err}")

        # >>> EXCEL CONTÁBIL (partida dobrada) — só se empresa_id fornecido <<<
        _excel_contabil_id = None
        if empresa_id and empresa_id > 0:
            # Tenant isolation: empresa_id must belong to the user's escritório
            from services.auth_utils import verificar_empresa_tenant as _vet
            _vet(db, current_user, empresa_id)
            try:
                from services.gerador_excel_contabil import gerar_excel_contabil
                from routers.classificacao import _carregar_dados_classificacao
                conta_banco_map, regras_usuario, cadastros, plano = _carregar_dados_classificacao(empresa_id, db)
                excel_contabil_bytes = gerar_excel_contabil(
                    transacoes=transacoes,
                    conta_banco_map=conta_banco_map,
                    regras_usuario=regras_usuario,
                    cadastros=cadastros,
                    plano=plano,
                    banco_detectado=banco_key,
                    saldo_inicial=resultado.get("saldo_inicial", 0.0),
                    saldo_final=resultado.get("saldo_final"),
                )
                _excel_contabil_id = f"{job_id}_contabil"
                _file_storage.save(excel_contabil_bytes, f"eid{_eid_prefix}_{_excel_contabil_id}.xlsx")
            except Exception as _exc_contabil:
                _verification_logger.warning(f"Excel contabil nao gerado: {_exc_contabil}")

        return JSONResponse({
            "sucesso": True,
            "nome_arquivo": arquivo.filename,
            "nome_extrato": nome_extrato,
            "banco_detectado": resultado.get("banco", "desconhecido").capitalize(),
            "total_transacoes": resultado["total_transacoes"],
            "resumo": {
                "entradas": resultado["total_entradas"],
                "saidas": resultado["total_saidas"],
                "posicao": resultado.get("total_posicao", 0.0),
                "aplicado": resultado.get("total_aplicado", 0.0),
                "saldo": resultado["saldo"],
                "saldo_inicial": resultado.get("saldo_inicial"),
                "saldo_final": resultado.get("saldo_final"),
            },
            "avisos": resultado.get("avisos", []),
            "excel_id": job_id,
            "excel_url": f"/api/download/{job_id}?filename={nome_extrato}.xlsx",
            "excel_contabil_id": _excel_contabil_id,
            "excel_contabil_url": f"/api/download/{_excel_contabil_id}?filename={nome_extrato}_contabil.xlsx" if _excel_contabil_id else None,
            "transacoes": transacoes,
            "categorias": categorias,
            "numero_conta": numero_conta,
            "verificacao_contabil": _verificacao_resultado.to_dict() if _verificacao_resultado else None,
            "pipeline": {
                "confianca": _pipeline_result.confianca,
                "reconciliacao": _pipeline_result.reconciliacao,
                "gap": _pipeline_result.gap,
                "checkpoints_ok": _pipeline_result.checkpoints_ok,
                "checkpoints_total": _pipeline_result.checkpoints_total,
                "divergencias": _pipeline_result.divergencias[:5],
                "warnings": _pipeline_result.warnings[:10],
                "log": [
                    {"passo": l.passo, "nome": l.nome, "ok": l.ok, "mensagem": l.mensagem}
                    for l in _pipeline_result.log
                ],
            },
        })

    except HTTPException:
        raise
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).error(f"Erro ao processar extrato: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar o extrato.")
    finally:
        # Remove sempre arquivos temporários locais
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(excel_path):
            os.remove(excel_path)

@app.get("/api/download/{excel_id}")
def download_excel(
    excel_id: str,
    background_tasks: BackgroundTasks,
    filename: str = "",
    current_user: models.Usuario = Depends(get_current_user),
):
    # Valida que o ID é um UUID puro (evita path traversal)
    # Aceita "uuid" e "uuid_contabil"
    clean_id = excel_id.replace("_contabil", "")
    try:
        uuid.UUID(clean_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID invalido.")

    # Ownership check: try escritório-prefixed key first
    eid = current_user.escritorio_id or 0
    storage_key = f"eid{eid}_{excel_id}.xlsx"
    if not _file_storage.exists(storage_key):
        # Fallback: legacy files without prefix (backwards compat)
        storage_key_legacy = f"{excel_id}.xlsx"
        if _file_storage.exists(storage_key_legacy):
            storage_key = storage_key_legacy
        else:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")

    excel_bytes = _file_storage.load(storage_key)
    # Apaga do storage em background após o envio
    background_tasks.add_task(_file_storage.delete, storage_key)

    # Usa filename personalizado se fornecido, senão fallback genérico
    safe_name = _sanitizar_filename(filename) if filename else "extrato_controllo.xlsx"

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


def _sanitizar_filename(nome: str) -> str:
    """Remove caracteres inválidos para nomes de arquivo e garante extensão .xlsx."""
    import unicodedata
    # Normaliza acentos → ASCII
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    # Remove caracteres proibidos em nomes de arquivo
    nome = re.sub(r'[\\/:*?"<>|]', '_', nome)
    nome = nome.strip(". ")
    if not nome:
        return "extrato_controllo.xlsx"
    if not nome.lower().endswith(".xlsx"):
        nome += ".xlsx"
    return nome[:120]   # limita tamanho


def _periodo_do_extrato(transacoes: list) -> tuple[str, str]:
    """
    Extrai o período (mês/ano) dominante a partir das transações.
    Retorna (label_curto, label_arquivo), ex: ("Janeiro 2025", "jan_2025").
    """
    _MESES = {
        1: ("Janeiro",   "jan"), 2: ("Fevereiro", "fev"), 3:  ("Março",    "mar"),
        4: ("Abril",     "abr"), 5: ("Maio",      "mai"), 6:  ("Junho",    "jun"),
        7: ("Julho",     "jul"), 8: ("Agosto",    "ago"), 9:  ("Setembro", "set"),
        10: ("Outubro",  "out"), 11: ("Novembro", "nov"), 12: ("Dezembro", "dez"),
    }
    contagem: dict[tuple, int] = {}
    for t in transacoes:
        data = t.get("data", "")
        try:
            partes = data.split("/")
            if len(partes) == 3:
                mes, ano = int(partes[1]), int(partes[2])
                contagem[(mes, ano)] = contagem.get((mes, ano), 0) + 1
        except (ValueError, IndexError):
            pass

    if not contagem:
        return ("", "")

    # Mês mais frequente
    (mes, ano) = max(contagem, key=lambda k: contagem[k])
    nome_longo, nome_curto = _MESES.get(mes, (str(mes), str(mes)))
    return (f"{nome_longo} {ano}", f"{nome_curto}_{ano}")


# ------------------------------------------------------------------ #
#  ROTA — LEITOR EM LOTE (múltiplos PDFs de bancos diferentes)       #
# ------------------------------------------------------------------ #

@app.post("/api/processar-extrato-lote")
async def rota_processar_extrato_lote(
    arquivos: List[UploadFile] = File(...),
    current_user: models.Usuario = Depends(get_current_user),
):
    """
    Processa múltiplos PDFs bancários individualmente (cada um pelo seu parser).
    Retorna um resultado separado por arquivo, com filename auto-gerado e excel_id para download.
    Segue a mesma lógica do /api/processar-extrato — sem alterações nos parsers.
    """
    MAX_FILE_SIZE = 50 * 1024 * 1024
    resultados = []

    for arquivo in arquivos:
        if not arquivo.filename or not arquivo.filename.lower().endswith(".pdf"):
            resultados.append({
                "arquivo_original": arquivo.filename or "sem_nome",
                "sucesso": False,
                "erro": "Formato inválido. Apenas PDFs são aceitos.",
            })
            continue

        job_id    = str(uuid.uuid4())
        pdf_path  = os.path.join(UPLOAD_DIR, f"{job_id}.pdf")
        excel_tmp = os.path.join(UPLOAD_DIR, f"{job_id}.xlsx")

        try:
            conteudo = await arquivo.read()
            if not conteudo:
                resultados.append({"arquivo_original": arquivo.filename, "sucesso": False, "erro": "Arquivo vazio."})
                continue
            if len(conteudo) > MAX_FILE_SIZE:
                resultados.append({
                    "arquivo_original": arquivo.filename,
                    "sucesso": False,
                    "erro": f"Arquivo muito grande ({len(conteudo)//1024//1024} MB). Limite: 50 MB.",
                })
                continue
            if not conteudo[:4].startswith(b"%PDF"):
                resultados.append({"arquivo_original": arquivo.filename, "sucesso": False, "erro": "Arquivo não é um PDF válido."})
                continue

            with open(pdf_path, "wb") as f:
                f.write(conteudo)

            resultado = _processar_extrato_pdf(pdf_path)

            if resultado.get("erro"):
                resultados.append({"arquivo_original": arquivo.filename, "sucesso": False, "erro": resultado["erro"]})
                continue

            transacoes = resultado.get("transacoes", [])
            banco = resultado.get("banco", "desconhecido").capitalize()

            if not transacoes:
                resultados.append({
                    "arquivo_original": arquivo.filename,
                    "sucesso": True,
                    "banco_detectado": banco,
                    "periodo_label": "",
                    "filename_sugerido": "",
                    "total_transacoes": 0,
                    "resumo": {"entradas": 0.0, "saidas": 0.0, "saldo": 0.0},
                    "avisos": resultado.get("avisos", ["Extrato sem transações."]),
                    "excel_id": None,
                    "excel_url": None,
                })
                continue

            # Categorização automática
            transacoes = categorizar_transacoes(transacoes)

            # Gera filename automático: extrato_{banco_slug}_{mes}_{ano}.xlsx
            _, periodo_arquivo = _periodo_do_extrato(transacoes)
            banco_slug = re.sub(r'[^a-z0-9]+', '_', banco.lower()).strip('_')
            filename_sugerido = f"extrato_{banco_slug}_{periodo_arquivo}.xlsx" if periodo_arquivo else f"extrato_{banco_slug}.xlsx"

            # Gera Excel e salva no storage
            gerar_excel(transacoes, excel_tmp, saldo_inicial=resultado.get("saldo_inicial"))
            with open(excel_tmp, "rb") as f:
                excel_bytes = f.read()
            _eid_lote = current_user.escritorio_id or 0
            _file_storage.save(excel_bytes, f"eid{_eid_lote}_{job_id}.xlsx")

            # >>> VERIFICAÇÃO CONTÁBIL (camada adicional — informativa, nunca bloqueia) <<<
            _verif_lote = None
            if _executar_verificacao is not None:
                try:
                    _verif_lote = _executar_verificacao(
                        banco_key=resultado.get("banco", "desconhecido"),
                        transacoes=transacoes,
                        saldo_inicial=resultado.get("saldo_inicial"),
                        saldo_final=resultado.get("saldo_final"),
                        file_name=arquivo.filename or '',
                        pdf_path=pdf_path,
                    )
                except Exception as _verif_err:
                    _verification_logger.error(f"Erro na verificacao adicional (lote): {_verif_err}")

            periodo_label, _ = _periodo_do_extrato(transacoes)

            resultados.append({
                "arquivo_original": arquivo.filename,
                "sucesso": True,
                "banco_detectado": banco,
                "periodo_label": periodo_label,
                "filename_sugerido": filename_sugerido,
                "total_transacoes": resultado["total_transacoes"],
                "resumo": {
                    "entradas": resultado["total_entradas"],
                    "saidas": resultado["total_saidas"],
                    "saldo": resultado["saldo"],
                },
                "avisos": resultado.get("avisos", []),
                "excel_id": job_id,
                "excel_url": f"/api/download/{job_id}?filename={filename_sugerido}",
                "verificacao_contabil": _verif_lote.to_dict() if _verif_lote else None,
            })

        except Exception as exc:
            resultados.append({"arquivo_original": arquivo.filename, "sucesso": False, "erro": str(exc)})
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            if os.path.exists(excel_tmp):
                os.remove(excel_tmp)

    return JSONResponse({"resultados": resultados})


# ------------------------------------------------------------------ #
#  ROTAS — DETECÇÃO DE BANCO E LOTE CONFIRMADO                       #
# ------------------------------------------------------------------ #

_TEMP_MAX_AGE_SECONDS = 30 * 60  # 30 minutos


def _limpar_temp_antigos():
    """Remove PDFs temporários em UPLOAD_DIR com mais de 30 minutos."""
    agora = time.time()
    try:
        for nome in os.listdir(UPLOAD_DIR):
            caminho = os.path.join(UPLOAD_DIR, nome)
            if not os.path.isfile(caminho):
                continue
            idade = agora - os.path.getmtime(caminho)
            if idade > _TEMP_MAX_AGE_SECONDS:
                try:
                    os.remove(caminho)
                except OSError:
                    pass
    except OSError:
        pass


@app.post("/api/detectar-bancos")
async def rota_detectar_bancos(
    arquivos: List[UploadFile] = File(...),
    current_user: models.Usuario = Depends(get_current_user),
):
    """
    Recebe N PDFs, detecta o banco de cada um SEM processar.
    Retorna banco detectado, confiança e caminho temporário para processamento posterior.
    """
    MAX_FILE_SIZE = 50 * 1024 * 1024

    # Limpa PDFs temporários órfãos (> 30 min)
    _limpar_temp_antigos()

    lista_arquivos = []
    por_banco: dict[str, int] = {}
    identificados = 0

    for arquivo in arquivos:
        arquivo_id = str(uuid.uuid4())

        if not arquivo.filename or not arquivo.filename.lower().endswith(".pdf"):
            lista_arquivos.append({
                "arquivo_id": arquivo_id,
                "nome_arquivo": arquivo.filename or "sem_nome",
                "banco_detectado": None,
                "banco_nome_exibicao": None,
                "confianca": "nenhuma",
                "arquivo_temp": None,
                "erro": "Formato inválido. Apenas PDFs são aceitos.",
            })
            continue

        pdf_path = os.path.join(UPLOAD_DIR, f"{arquivo_id}.pdf")

        try:
            conteudo = await arquivo.read()
            if not conteudo:
                lista_arquivos.append({
                    "arquivo_id": arquivo_id,
                    "nome_arquivo": arquivo.filename,
                    "banco_detectado": None,
                    "banco_nome_exibicao": None,
                    "confianca": "nenhuma",
                    "arquivo_temp": None,
                    "erro": "Arquivo vazio.",
                })
                continue
            if len(conteudo) > MAX_FILE_SIZE:
                lista_arquivos.append({
                    "arquivo_id": arquivo_id,
                    "nome_arquivo": arquivo.filename,
                    "banco_detectado": None,
                    "banco_nome_exibicao": None,
                    "confianca": "nenhuma",
                    "arquivo_temp": None,
                    "erro": f"Arquivo muito grande ({len(conteudo) // 1024 // 1024} MB). Limite: 50 MB.",
                })
                continue

            # Salva PDF temporário para detecção e processamento posterior
            with open(pdf_path, "wb") as f:
                f.write(conteudo)

            # Detecta banco com confiança
            det = _detectar_banco_com_confianca(pdf_path)

            item = {
                "arquivo_id": arquivo_id,
                "nome_arquivo": arquivo.filename,
                "banco_detectado": det["banco_detectado"],
                "banco_nome_exibicao": det["banco_nome_exibicao"],
                "confianca": det["confianca"],
                "arquivo_temp": f"{UPLOAD_DIR}/{arquivo_id}.pdf",
                "erro": det.get("erro"),
            }
            lista_arquivos.append(item)

            if det["banco_detectado"]:
                identificados += 1
                nome_exib = det["banco_nome_exibicao"] or det["banco_detectado"]
                por_banco[nome_exib] = por_banco.get(nome_exib, 0) + 1

        except Exception as exc:
            lista_arquivos.append({
                "arquivo_id": arquivo_id,
                "nome_arquivo": arquivo.filename or "sem_nome",
                "banco_detectado": None,
                "banco_nome_exibicao": None,
                "confianca": "nenhuma",
                "arquivo_temp": None,
                "erro": str(exc),
            })

    total = len(lista_arquivos)
    return JSONResponse({
        "arquivos": lista_arquivos,
        "resumo": {
            "total": total,
            "identificados": identificados,
            "nao_identificados": total - identificados,
            "por_banco": por_banco,
        },
    })


class _ArquivoConfirmado(BaseModel):
    arquivo_id: str
    arquivo_temp: str
    banco: str
    senha: str | None = None


class _LoteConfirmadoRequest(BaseModel):
    arquivos: List[_ArquivoConfirmado]


@app.post("/api/processar-lote-confirmado")
async def rota_processar_lote_confirmado(
    body: _LoteConfirmadoRequest,
    current_user: models.Usuario = Depends(get_current_user),
):
    """
    Processa extratos a partir de PDFs temporários já salvos pelo /api/detectar-bancos.
    O usuário confirmou/corrigiu o banco de cada arquivo antes de chamar este endpoint.
    """
    resultados = []

    for item in body.arquivos:
        pdf_path = os.path.join(UPLOAD_DIR, f"{item.arquivo_id}.pdf")
        job_id = str(uuid.uuid4())
        excel_tmp = os.path.join(UPLOAD_DIR, f"{job_id}.xlsx")

        try:
            if not os.path.exists(pdf_path):
                resultados.append({
                    "arquivo_id": item.arquivo_id,
                    "sucesso": False,
                    "erro": "PDF temporário não encontrado. Reenvie o arquivo.",
                })
                continue

            resultado = _processar_extrato_pdf(
                pdf_path, banco_id=item.banco, password=item.senha or None,
            )

            if resultado.get("requer_senha"):
                resultados.append({
                    "arquivo_id": item.arquivo_id,
                    "sucesso": False,
                    "erro": "PDF protegido por senha.",
                    "requer_senha": True,
                })
                continue

            if resultado.get("erro"):
                resultados.append({
                    "arquivo_id": item.arquivo_id,
                    "sucesso": False,
                    "erro": resultado["erro"],
                })
                continue

            transacoes = resultado.get("transacoes", [])
            banco_display = resultado.get("banco", item.banco).capitalize()

            if not transacoes:
                resultados.append({
                    "arquivo_id": item.arquivo_id,
                    "sucesso": True,
                    "banco_detectado": banco_display,
                    "periodo_label": "",
                    "filename_sugerido": "",
                    "total_transacoes": 0,
                    "resumo": {"entradas": 0.0, "saidas": 0.0, "saldo": 0.0},
                    "avisos": resultado.get("avisos", ["Extrato sem transações."]),
                    "excel_id": None,
                    "excel_url": None,
                    "verificacao_contabil": None,
                })
                continue

            # Categorização automática
            transacoes = categorizar_transacoes(transacoes)

            # Gera filename automático
            _, periodo_arquivo = _periodo_do_extrato(transacoes)
            banco_slug = re.sub(r'[^a-z0-9]+', '_', banco_display.lower()).strip('_')
            filename_sugerido = (
                f"extrato_{banco_slug}_{periodo_arquivo}.xlsx"
                if periodo_arquivo
                else f"extrato_{banco_slug}.xlsx"
            )

            # Gera Excel e salva no storage
            gerar_excel(transacoes, excel_tmp, saldo_inicial=resultado.get("saldo_inicial"))
            with open(excel_tmp, "rb") as f:
                excel_bytes = f.read()
            _eid_conf = current_user.escritorio_id or 0
            _file_storage.save(excel_bytes, f"eid{_eid_conf}_{job_id}.xlsx")

            # Verificação contábil
            _verif = None
            if _executar_verificacao is not None:
                try:
                    _verif = _executar_verificacao(
                        banco_key=resultado.get("banco", item.banco),
                        transacoes=transacoes,
                        saldo_inicial=resultado.get("saldo_inicial"),
                        saldo_final=resultado.get("saldo_final"),
                        file_name=f"{item.arquivo_id}.pdf",
                        pdf_path=pdf_path,
                        password=item.senha or None,
                    )
                except Exception as _verif_err:
                    _verification_logger.error(f"Erro na verificacao (lote confirmado): {_verif_err}")

            periodo_label, _ = _periodo_do_extrato(transacoes)

            resultados.append({
                "arquivo_id": item.arquivo_id,
                "sucesso": True,
                "banco_detectado": banco_display,
                "periodo_label": periodo_label,
                "filename_sugerido": filename_sugerido,
                "total_transacoes": resultado["total_transacoes"],
                "resumo": {
                    "entradas": resultado["total_entradas"],
                    "saidas": resultado["total_saidas"],
                    "saldo": resultado["saldo"],
                },
                "avisos": resultado.get("avisos", []),
                "excel_id": job_id,
                "excel_url": f"/api/download/{job_id}?filename={filename_sugerido}",
                "verificacao_contabil": _verif.to_dict() if _verif else None,
            })

        except Exception as exc:
            resultados.append({
                "arquivo_id": item.arquivo_id,
                "sucesso": False,
                "erro": str(exc),
            })
        finally:
            # Limpa PDF temporário e Excel temporário
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            if os.path.exists(excel_tmp):
                os.remove(excel_tmp)

    return JSONResponse({"resultados": resultados})


# ------------------------------------------------------------------ #
#  ROTAS — PROCESSAR EXCEL                                           #
# ------------------------------------------------------------------ #

@app.post("/api/processar-excel")
async def rota_processar_excel(
    files: List[UploadFile] = File(...),
    current_user: models.Usuario = Depends(get_current_user),
):
    try:
        arquivos_bytes = [await f.read() for f in files]
        transacoes = ler_planilhas_excel(arquivos_bytes)
        entradas = sum(abs(t["valor"]) for t in transacoes if t["tipo"] == "entrada")
        saidas = sum(abs(t["valor"]) for t in transacoes if t["tipo"] == "saida")
        return {
            "transacoes": transacoes,
            "resumo": {"entradas": entradas, "saidas": saidas, "saldo": entradas - saidas},
        }
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).error(f"Falha ao processar planilhas: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar planilhas.")

# ------------------------------------------------------------------ #
#  ROTAS — DASHBOARD TEMPLATE (SAZONAL)                             #
# ------------------------------------------------------------------ #

@app.get("/api/dashboard/template")
def baixar_template_dashboard(
    demo: bool = False,
    current_user: models.Usuario = Depends(get_current_user),
):
    """
    Retorna um modelo Excel para o dashboard sazonal.
    - demo=false → planilha em branco (o usuário preenche).
    - demo=true  → planilha pré-preenchida com dados de exemplo.
    """
    import io as _io
    from services.template_dashboard import gerar_template_sazonal
    conteudo = gerar_template_sazonal(com_demo=demo)
    filename = "Controllo_Dashboard_Demo.xlsx" if demo else "Controllo_Dashboard_Modelo.xlsx"
    return StreamingResponse(
        _io.BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/dashboard/upload-template")
async def processar_template_dashboard(
    arquivo: UploadFile = File(...),
    current_user: models.Usuario = Depends(get_current_user),
):
    """
    Lê uma planilha de template sazonal preenchida pelo usuário e retorna
    os dados estruturados para o frontend renderizar o dashboard.
    """
    from services.template_dashboard import ler_template_sazonal
    try:
        conteudo = await arquivo.read()
        dados = ler_template_sazonal(conteudo)
        return dados
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:200])
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).error(f"Erro ao processar planilha: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar planilha.")


# ------------------------------------------------------------------ #
#  ROTAS — AGENDA / LEMBRETES                                        #
# ------------------------------------------------------------------ #

@app.get("/api/agenda/lembretes")
def listar_lembretes(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lembretes = (
        db.query(models.Lembrete)
        .filter(models.Lembrete.usuario_id == current_user.id)
        .order_by(models.Lembrete.data_vencimento.asc())
        .all()
    )
    return [
        {
            "id": l.id,
            "titulo": l.titulo,
            "descricao": l.descricao,
            "data_vencimento": l.data_vencimento,
            "hora": l.hora,
            "prioridade": l.prioridade,
            "status": l.status,
            "empresa_vinculada": l.empresa_vinculada,
            "criado_em": l.criado_em,
        }
        for l in lembretes
    ]

@app.post("/api/agenda/lembretes", status_code=201)
def criar_lembrete(
    body: LembreteCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body.validar()
    lembrete = models.Lembrete(
        titulo=body.titulo.strip()[:200],
        descricao=(body.descricao or "").strip(),
        data_vencimento=body.data_vencimento.strip(),
        hora=body.hora or "09:00",
        prioridade=body.prioridade or "media",
        status="pendente",
        empresa_vinculada=(body.empresa_vinculada or "").strip(),
        usuario_id=current_user.id,
        criado_em=datetime.now(timezone.utc).isoformat(),
    )
    db.add(lembrete)
    db.commit()
    db.refresh(lembrete)
    return {"mensagem": "Lembrete criado com sucesso.", "id": lembrete.id}

@app.put("/api/agenda/lembretes/{lembrete_id}")
def atualizar_lembrete(
    lembrete_id: int,
    body: LembreteUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lembrete = db.query(models.Lembrete).filter(
        models.Lembrete.id == lembrete_id,
        models.Lembrete.usuario_id == current_user.id,
    ).first()
    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete nao encontrado.")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(lembrete, campo, valor)
    db.commit()
    return {"mensagem": "Lembrete atualizado."}

@app.put("/api/agenda/lembretes/{lembrete_id}/concluir")
def concluir_lembrete(
    lembrete_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lembrete = db.query(models.Lembrete).filter(
        models.Lembrete.id == lembrete_id,
        models.Lembrete.usuario_id == current_user.id,
    ).first()
    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete nao encontrado.")
    lembrete.status = "concluido"
    db.commit()
    return {"mensagem": "Lembrete marcado como concluido."}

@app.delete("/api/agenda/lembretes/{lembrete_id}")
def excluir_lembrete(
    lembrete_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lembrete = db.query(models.Lembrete).filter(
        models.Lembrete.id == lembrete_id,
        models.Lembrete.usuario_id == current_user.id,
    ).first()
    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete nao encontrado.")
    db.delete(lembrete)
    db.commit()
    return {"mensagem": "Lembrete excluido."}

# ------------------------------------------------------------------ #
#  ROTAS — CARTEIRA DE EMPRESAS                                      #
# ------------------------------------------------------------------ #

def _empresa_to_dict(e: models.Empresa) -> dict:
    return {
        "id": e.id,
        "nome": e.nome,
        "nome_fantasia": e.nome_fantasia or "",
        "cnpj": e.cnpj,
        "ccm": e.ccm,
        "status": e.status,
        "ativa": e.ativa if e.ativa is not None else True,
        "observacoes": e.observacoes,
        "usuario_id": e.usuario_id,
        "criado_em": e.criado_em,
        "atualizado_em": e.atualizado_em,
    }

@app.get("/api/carteira")
def listar_carteira(
    page: int = 1,
    per_page: int = 20,
    busca: str = "",
    status: str = "",
    ativa: Optional[bool] = None,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    per_page = min(max(per_page, 1), 500)
    page = max(page, 1)

    membro_ids = [
        m.empresa_id
        for m in db.query(models.CarteiraMembro)
        .filter(models.CarteiraMembro.usuario_id == current_user.id)
        .all()
    ]
    query = db.query(models.Empresa).filter(models.Empresa.id.in_(membro_ids))

    # Por padrão mostra só ativas; ativa=false mostra inativas; ativa=none mostra todas
    if ativa is True:
        query = query.filter(models.Empresa.ativa == True)   # noqa: E712
    elif ativa is False:
        query = query.filter(models.Empresa.ativa == False)  # noqa: E712
    else:
        # ativa não informado → só ativas (comportamento padrão seguro)
        query = query.filter(models.Empresa.ativa == True)   # noqa: E712

    if status and status in EMPRESA_STATUSES:
        query = query.filter(models.Empresa.status == status)

    if busca.strip():
        b = busca.strip()
        b_nums = "".join(c for c in b if c.isdigit())
        conditions = [
            models.Empresa.nome.ilike(f"%{b}%"),
            models.Empresa.nome_fantasia.ilike(f"%{b}%"),
        ]
        if b_nums:
            conditions.append(models.Empresa.cnpj.contains(b_nums))
        query = query.filter(or_(*conditions))

    total = query.count()
    empresas = (
        query
        .order_by(models.Empresa.nome.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Monta mapa de observacoes do usuário (carteira_membros.observacoes)
    ids_retornados = [e.id for e in empresas]
    membros_obs = {
        m.empresa_id: (m.observacoes or "")
        for m in db.query(models.CarteiraMembro)
        .filter(
            models.CarteiraMembro.empresa_id.in_(ids_retornados),
            models.CarteiraMembro.usuario_id == current_user.id,
        ).all()
    } if ids_retornados else {}

    # Score de saúde para cada empresa (se houver dados financeiros)
    from services.score_saude import ScoreSaude
    from services import financeiro_service as _fs
    _score = ScoreSaude()
    scores_map: dict = {}
    for e in empresas:
        try:
            hist = _fs.get_historico(db, e.id, limite=12)
            if hist:
                scores_map[e.id] = _score.calcular(hist[-1], hist)
        except Exception:
            pass

    def to_dict_with_notas(e):
        d = _empresa_to_dict(e)
        d["carteira_observacoes"] = membros_obs.get(e.id, "")
        score_data = scores_map.get(e.id)
        if score_data:
            d["score_saude"] = score_data["score"]
            d["score_classificacao"] = score_data["classificacao"]
            d["score_cor"] = score_data["cor"]
            d["score_resumo"] = score_data["resumo"]
        else:
            d["score_saude"] = None
            d["score_classificacao"] = None
            d["score_cor"] = None
            d["score_resumo"] = None
        return d

    return {
        "items": [to_dict_with_notas(e) for e in empresas],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, math.ceil(total / per_page)),
    }


@app.get("/api/carteira/disponiveis")
def listar_empresas_disponiveis(
    busca: str = "",
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna todas as empresas ativas com status de carteira (quem tem cada uma)."""
    _eid = getattr(current_user, "_escritorio_id", None)
    _is_master = getattr(current_user, "_is_master", False)
    query = db.query(models.Empresa).filter(models.Empresa.ativa == True)   # noqa: E712
    if _eid and not _is_master:
        query = query.filter(models.Empresa.escritorio_id == _eid)

    if busca.strip():
        b = busca.strip()
        b_nums = "".join(c for c in b if c.isdigit())
        conds = [
            models.Empresa.nome.ilike(f"%{b}%"),
            models.Empresa.nome_fantasia.ilike(f"%{b}%"),
        ]
        if b_nums:
            conds.append(models.Empresa.cnpj.contains(b_nums))
        query = query.filter(or_(*conds))

    empresas = query.order_by(models.Empresa.nome.asc()).all()

    membros = {
        m.empresa_id: m
        for m in db.query(models.CarteiraMembro)
        .filter(models.CarteiraMembro.empresa_id.in_([e.id for e in empresas]))
        .all()
    }
    usuarios = {u.id: u.nome for u in db.query(models.Usuario).all()}

    # Score de saúde para cada empresa (se houver dados financeiros)
    from services.score_saude import ScoreSaude as _ScoreSaudeD
    from services import financeiro_service as _fsD
    _scoreD = _ScoreSaudeD()
    scores_mapD: dict = {}
    for e in empresas:
        try:
            hist = _fsD.get_historico(db, e.id, limite=12)
            if hist:
                scores_mapD[e.id] = _scoreD.calcular(hist[-1], hist)
        except Exception:
            pass

    resultado = []
    for e in empresas:
        m = membros.get(e.id)
        minha = m is not None and m.usuario_id == current_user.id
        em_uso_id = m.usuario_id if m and not minha else None
        em_uso_nome = usuarios.get(em_uso_id) if em_uso_id else None
        score_data = scores_mapD.get(e.id)
        resultado.append({
            "id": e.id,
            "nome": e.nome,
            "nome_fantasia": e.nome_fantasia or "",
            "cnpj": e.cnpj or "",
            "ccm": e.ccm or "",
            "observacoes": e.observacoes or "",
            "status": e.status or "iniciada",
            "na_minha_carteira": minha,
            "carteira_observacoes": (m.observacoes or "") if minha and m else "",
            "em_uso_por_id": em_uso_id,
            "em_uso_por": em_uso_nome,
            "score_saude": score_data["score"] if score_data else None,
            "score_classificacao": score_data["classificacao"] if score_data else None,
            "score_cor": score_data["cor"] if score_data else None,
        })
    return resultado


@app.post("/api/carteira/{empresa_id}", status_code=200)
def adicionar_a_carteira(
    empresa_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adiciona empresa à carteira do usuário logado (checkbox marcado)."""
    from services.auth_utils import verificar_empresa_tenant as _vet_cart
    empresa = _vet_cart(db, current_user, empresa_id)
    if not empresa.ativa:
        raise HTTPException(status_code=400, detail="Empresa inativa.")

    membro_existente = db.query(models.CarteiraMembro).filter(
        models.CarteiraMembro.empresa_id == empresa_id,
    ).first()

    if membro_existente:
        if membro_existente.usuario_id == current_user.id:
            return {"mensagem": "Empresa já está na sua carteira."}
        dono = db.query(models.Usuario).filter(
            models.Usuario.id == membro_existente.usuario_id
        ).first()
        nome_dono = dono.nome if dono else "outro usuário"
        raise HTTPException(
            status_code=409,
            detail=f"Empresa já está na carteira de {nome_dono}.",
        )

    db.add(models.CarteiraMembro(
        empresa_id=empresa_id,
        usuario_id=current_user.id,
        adicionado_em=datetime.now(timezone.utc).isoformat(),
    ))
    db.commit()
    return {"mensagem": "Empresa adicionada à carteira."}


@app.post("/api/carteira", status_code=201)
def criar_empresa(
    body: EmpresaCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cnpj_formatado = ""
    if body.cnpj and body.cnpj.strip():
        cnpj_raw = body.cnpj.strip()
        cnpj_nums = "".join(c for c in cnpj_raw if c.isdigit())
        if cnpj_nums:
            if not validar_cnpj(cnpj_nums):
                raise HTTPException(status_code=400, detail="CNPJ inválido — verifique os dígitos verificadores.")
            cnpj_formatado = formatar_cnpj(cnpj_nums)
            duplicado = db.query(models.Empresa).filter(
                models.Empresa.cnpj == cnpj_formatado,
                models.Empresa.usuario_id == current_user.id,
            ).first()
            if duplicado:
                raise HTTPException(status_code=400, detail="Já existe uma empresa com este CNPJ na sua carteira.")

    agora = datetime.now(timezone.utc).isoformat()
    empresa = models.Empresa(
        nome=body.nome.strip(),
        nome_fantasia=(body.nome_fantasia or "").strip(),
        cnpj=cnpj_formatado,
        ccm=(body.ccm or "").strip(),
        escritorio_id=current_user.escritorio_id,
        status=body.status if body.status in EMPRESA_STATUSES else "iniciada",
        ativa=True,
        observacoes=(body.observacoes or "").strip(),
        usuario_id=current_user.id,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    # Cria automaticamente o vínculo CarteiraMembro para que a empresa apareça
    # no seletor lateral e nos endpoints filtrados por carteira do usuário.
    membro_existente = db.query(models.CarteiraMembro).filter(
        models.CarteiraMembro.empresa_id == empresa.id,
        models.CarteiraMembro.usuario_id == current_user.id,
    ).first()
    if not membro_existente:
        membro = models.CarteiraMembro(
            empresa_id=empresa.id,
            usuario_id=current_user.id,
            adicionado_em=agora,
            observacoes="",
        )
        db.add(membro)
        db.commit()

    registrar_auditoria(db, "criar_empresa", usuario_id=current_user.id, usuario_nome=current_user.nome,
                        recurso="empresa", recurso_id=empresa.id,
                        detalhes={"nome": empresa.nome, "cnpj": empresa.cnpj},
                        escritorio_id=current_user.escritorio_id)
    return {"mensagem": "Empresa adicionada.", "empresa": _empresa_to_dict(empresa)}

def _checar_acesso_empresa(empresa_id: int, current_user, db) -> "models.Empresa":
    """Delega para resolve_empresa_or_403 (garante isolamento multi-tenant CRÍTICO-1)."""
    from services.auth_utils import resolve_empresa_or_403
    return resolve_empresa_or_403(db, empresa_id, current_user)


@app.put("/api/carteira/{empresa_id}")
def atualizar_empresa(
    empresa_id: int,
    body: EmpresaUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa = _checar_acesso_empresa(empresa_id, current_user, db)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")

    # Valida CNPJ se estiver sendo atualizado
    if body.cnpj is not None and body.cnpj.strip():
        cnpj_nums = "".join(c for c in body.cnpj if c.isdigit())
        if cnpj_nums:
            if not validar_cnpj(cnpj_nums):
                raise HTTPException(status_code=400, detail="CNPJ inválido — verifique os dígitos verificadores.")
            cnpj_formatado = formatar_cnpj(cnpj_nums)
            duplicado = db.query(models.Empresa).filter(
                models.Empresa.cnpj == cnpj_formatado,
                models.Empresa.usuario_id == current_user.id,
                models.Empresa.id != empresa_id,
            ).first()
            if duplicado:
                raise HTTPException(status_code=400, detail="Já existe outra empresa com este CNPJ na sua carteira.")
            body = body.model_copy(update={"cnpj": cnpj_formatado})

    campos_alterados = body.model_dump(exclude_unset=True)
    for campo, valor in campos_alterados.items():
        setattr(empresa, campo, valor)
    empresa.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(empresa)
    registrar_auditoria(db, "atualizar_empresa", usuario_id=current_user.id, usuario_nome=current_user.nome,
                        recurso="empresa", recurso_id=empresa_id, detalhes=campos_alterados,
                        escritorio_id=current_user.escritorio_id)
    return {"mensagem": "Empresa atualizada.", "empresa": _empresa_to_dict(empresa)}

@app.put("/api/carteira/{empresa_id}/status")
def atualizar_status_empresa(
    empresa_id: int,
    body: EmpresaStatusUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa = _checar_acesso_empresa(empresa_id, current_user, db)
    if body.status not in EMPRESA_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status invalido. Opcoes: {EMPRESA_STATUSES}")
    empresa.status = body.status
    empresa.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"mensagem": "Status atualizado.", "status": empresa.status}

@app.patch("/api/carteira/{empresa_id}/inativar")
def inativar_empresa(
    empresa_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa = _checar_acesso_empresa(empresa_id, current_user, db)
    empresa.ativa = False
    empresa.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    registrar_auditoria(db, "inativar_empresa", usuario_id=current_user.id, usuario_nome=current_user.nome,
                        recurso="empresa", recurso_id=empresa_id, detalhes={"nome": empresa.nome},
                        escritorio_id=current_user.escritorio_id)
    return {"mensagem": "Empresa inativada. Os dados foram preservados."}


@app.patch("/api/carteira/{empresa_id}/ativar")
def ativar_empresa(
    empresa_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa = _checar_acesso_empresa(empresa_id, current_user, db)
    empresa.ativa = True
    empresa.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"mensagem": "Empresa reativada com sucesso.", "empresa": _empresa_to_dict(empresa)}


class CarteiraNotasUpdate(BaseModel):
    observacoes: str = ""


@app.patch("/api/carteira/{empresa_id}/notas")
def atualizar_notas_carteira(
    empresa_id: int,
    body: CarteiraNotasUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atualiza as notas privadas do analista sobre uma empresa na sua carteira."""
    membro = db.query(models.CarteiraMembro).filter(
        models.CarteiraMembro.empresa_id == empresa_id,
        models.CarteiraMembro.usuario_id == current_user.id,
    ).first()
    if not membro:
        raise HTTPException(status_code=404, detail="Empresa não está na sua carteira.")
    membro.observacoes = body.observacoes.strip()[:1000]
    db.commit()
    return {"mensagem": "Notas atualizadas.", "observacoes": membro.observacoes}


@app.delete("/api/carteira/{empresa_id}")
def remover_da_carteira(
    empresa_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove empresa da carteira do usuário (checkbox desmarcado). Não exclui a empresa."""
    membro = db.query(models.CarteiraMembro).filter(
        models.CarteiraMembro.empresa_id == empresa_id,
        models.CarteiraMembro.usuario_id == current_user.id,
    ).first()
    if not membro:
        # Admin pode remover de qualquer carteira
        if current_user.is_admin:
            membro = db.query(models.CarteiraMembro).filter(
                models.CarteiraMembro.empresa_id == empresa_id,
            ).first()
        if not membro:
            raise HTTPException(status_code=404, detail="Empresa não está na sua carteira.")
    db.delete(membro)
    db.commit()
    return {"mensagem": "Empresa removida da carteira."}

# ------------------------------------------------------------------ #
#  ROTAS — PLANO DE CONTAS REFERENCIAL + DE-PARA                    #
# ------------------------------------------------------------------ #

def _sugerir_conta_referencial(codigo: str, descricao: str, db: Session) -> Optional[int]:
    """Heurística: sugere conta referencial pelo código e palavras-chave da descrição."""
    desc = descricao.lower()

    keywords_map = [
        (["caixa", "banco", "disponib", "aplicacao", "aplicação"], "1.1.1"),
        (["cliente", "receber", "crédito", "credito", "duplicata", "títulos a receber"], "1.1.2"),
        (["estoque", "mercadoria", "produto acabado", "matéria"], "1.1.3"),
        (["fornecedor", "pagar", "a pagar"], "2.1.1"),
        (["empréstimo cp", "financiamento cp", "curto prazo"], "2.1.2"),
        (["trabalhista", "folha", "fgts", "salário", "salario", "férias", "ferias", "13"], "2.1.3"),
        (["tributo", "imposto", "ir", "csll", "pis", "cofins", "iss", "icms", "ipi"], "2.1.4"),
        (["capital social"], "2.3.1"),
        (["reserva"], "2.3.2"),
        (["lucro", "prejuízo", "prejuizo", "resultado acumulado"], "2.3.3"),
        (["receita bruta", "faturamento", "vendas de"], "3.1"),
        (["dedução", "deducao", "desconto incondicional", "devolução", "abatimento"], "3.2"),
        (["outras receitas", "receitas diversas"], "3.3"),
        (["custo", "cmv", "csv", "csp", "custo de mercadoria", "custo de serviço"], "4.1"),
        (["administrativa", "adm", "aluguel", "energia", "água", "agua", "telefone"], "4.2"),
        (["comercial", "vendas", "marketing", "publicidade", "comissão", "comissao"], "4.3"),
        (["financeira", "juros", "multa", "tarifa bancária", "iof"], "4.4"),
        (["depreci", "amortiz"], "4.5"),
        (["irpj", "csll imposto", "imposto de renda", "contribuição social sobre"], "4.6"),
        (["imobilizado", "bem imobilizado"], "1.2.2"),
        (["intangível", "intangivel", "software", "marca"], "1.2.3"),
        (["empréstimo lp", "financiamento lp", "longo prazo"], "2.2.1"),
    ]

    for keywords, cod_ref in keywords_map:
        if any(kw in desc for kw in keywords):
            conta = db.query(models.PlanoContasReferencial).filter(
                models.PlanoContasReferencial.codigo == cod_ref
            ).first()
            if conta:
                return conta.id

    # Fallback: primeiro dígito do código do cliente
    primeiro = codigo[0] if codigo else ""
    fallback = {"1": "1.1", "2": "2.1", "3": "3.1", "4": "4.1"}
    if primeiro in fallback:
        conta = db.query(models.PlanoContasReferencial).filter(
            models.PlanoContasReferencial.codigo == fallback[primeiro]
        ).first()
        if conta:
            return conta.id

    return None


class MapeamentoContaItem(BaseModel):
    conta_cliente: str
    descricao_cliente: Optional[str] = ""
    conta_referencial_id: Optional[int] = None


class ContaClienteCreate(BaseModel):
    conta_cliente: str
    descricao_cliente: Optional[str] = ""


@app.get("/api/plano-contas")
def listar_plano_referencial(
    _user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista todas as contas do plano referencial do sistema."""
    contas = db.query(models.PlanoContasReferencial).order_by(
        models.PlanoContasReferencial.ordem
    ).all()
    return [
        {
            "id": c.id,
            "codigo": c.codigo,
            "descricao": c.descricao,
            "grupo": c.grupo,
            "nivel": c.nivel,
            "label": f"{c.codigo} — {c.descricao}",
        }
        for c in contas
    ]


@app.get("/api/plano-contas/mapeamento/{empresa_id}")
def listar_mapeamentos(
    empresa_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista os mapeamentos De-Para de uma empresa."""
    empresa = db.query(models.Empresa).filter(
        models.Empresa.id == empresa_id,
        models.Empresa.usuario_id == current_user.id,
    ).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    mapeamentos = (
        db.query(models.MapeamentoContas)
        .filter(models.MapeamentoContas.empresa_id == empresa_id)
        .order_by(models.MapeamentoContas.conta_cliente)
        .all()
    )

    # Busca contas referenciais em lote para montar resposta
    ref_ids = [m.conta_referencial_id for m in mapeamentos if m.conta_referencial_id]
    refs = {}
    if ref_ids:
        for c in db.query(models.PlanoContasReferencial).filter(
            models.PlanoContasReferencial.id.in_(ref_ids)
        ).all():
            refs[c.id] = {"id": c.id, "codigo": c.codigo, "descricao": c.descricao}

    return [
        {
            "id": m.id,
            "conta_cliente": m.conta_cliente,
            "descricao_cliente": m.descricao_cliente,
            "conta_referencial_id": m.conta_referencial_id,
            "conta_referencial": refs.get(m.conta_referencial_id),
            "sugestao_automatica": m.sugestao_automatica,
            "mapeado": m.conta_referencial_id is not None,
        }
        for m in mapeamentos
    ]


@app.post("/api/plano-contas/conta-cliente/{empresa_id}", status_code=201)
def adicionar_conta_cliente(
    empresa_id: int,
    body: ContaClienteCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adiciona uma conta do cliente ao De-Para, com sugestão automática de mapeamento."""
    empresa = db.query(models.Empresa).filter(
        models.Empresa.id == empresa_id,
        models.Empresa.usuario_id == current_user.id,
    ).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    conta_cli = body.conta_cliente.strip()
    if not conta_cli:
        raise HTTPException(status_code=400, detail="Código da conta não pode ser vazio.")

    existente = db.query(models.MapeamentoContas).filter(
        models.MapeamentoContas.empresa_id == empresa_id,
        models.MapeamentoContas.conta_cliente == conta_cli,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Conta já cadastrada para esta empresa.")

    sugestao_id = _sugerir_conta_referencial(conta_cli, body.descricao_cliente or "", db)
    agora = datetime.now(timezone.utc).isoformat()

    mapeamento = models.MapeamentoContas(
        empresa_id=empresa_id,
        conta_cliente=conta_cli,
        descricao_cliente=(body.descricao_cliente or "").strip(),
        conta_referencial_id=sugestao_id,
        sugestao_automatica=sugestao_id is not None,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(mapeamento)
    db.commit()
    db.refresh(mapeamento)

    ref = None
    if mapeamento.conta_referencial_id:
        c = db.query(models.PlanoContasReferencial).get(mapeamento.conta_referencial_id)
        if c:
            ref = {"id": c.id, "codigo": c.codigo, "descricao": c.descricao}

    return {
        "id": mapeamento.id,
        "conta_cliente": mapeamento.conta_cliente,
        "descricao_cliente": mapeamento.descricao_cliente,
        "conta_referencial_id": mapeamento.conta_referencial_id,
        "conta_referencial": ref,
        "sugestao_automatica": mapeamento.sugestao_automatica,
        "mapeado": mapeamento.conta_referencial_id is not None,
    }


@app.patch("/api/plano-contas/mapeamento/{mapeamento_id}")
def atualizar_mapeamento(
    mapeamento_id: int,
    body: MapeamentoContaItem,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atualiza o vínculo De-Para de um mapeamento (usuário confirma/corrige sugestão)."""
    mapeamento = db.query(models.MapeamentoContas).filter(
        models.MapeamentoContas.id == mapeamento_id
    ).first()
    if not mapeamento:
        raise HTTPException(status_code=404, detail="Mapeamento não encontrado.")

    # Verifica que a empresa pertence ao usuário
    empresa = db.query(models.Empresa).filter(
        models.Empresa.id == mapeamento.empresa_id,
        models.Empresa.usuario_id == current_user.id,
    ).first()
    if not empresa:
        raise HTTPException(status_code=403, detail="Sem permissão.")

    if body.conta_referencial_id is not None:
        ref = db.query(models.PlanoContasReferencial).get(body.conta_referencial_id)
        if not ref:
            raise HTTPException(status_code=400, detail="Conta referencial não encontrada.")

    mapeamento.conta_referencial_id = body.conta_referencial_id
    mapeamento.sugestao_automatica = False  # usuário confirmou manualmente
    mapeamento.atualizado_em = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"mensagem": "Mapeamento atualizado."}


@app.delete("/api/plano-contas/mapeamento/{mapeamento_id}")
def remover_mapeamento(
    mapeamento_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove uma conta do De-Para."""
    mapeamento = db.query(models.MapeamentoContas).filter(
        models.MapeamentoContas.id == mapeamento_id
    ).first()
    if not mapeamento:
        raise HTTPException(status_code=404, detail="Mapeamento não encontrado.")

    empresa = db.query(models.Empresa).filter(
        models.Empresa.id == mapeamento.empresa_id,
        models.Empresa.usuario_id == current_user.id,
    ).first()
    if not empresa:
        raise HTTPException(status_code=403, detail="Sem permissão.")

    db.delete(mapeamento)
    db.commit()
    return {"mensagem": "Mapeamento removido."}


# ------------------------------------------------------------------ #
#  ROTAS — ADMIN: CARTEIRAS CONSOLIDADAS                             #
# ------------------------------------------------------------------ #

@app.get("/api/admin/carteiras")
def listar_todas_carteiras(
    usuario_id: Optional[int] = None,
    _admin: models.Usuario = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Lista todas as carteiras agrupadas por usuário (via CarteiraMembro)."""
    # Tenant isolation: non-master admins see only their own escritório
    if getattr(_admin, "is_master", False):
        usuarios = {u.id: u for u in db.query(models.Usuario).all()}
    else:
        eid = getattr(_admin, "_escritorio_id", None) or _admin.escritorio_id
        usuarios = {u.id: u for u in db.query(models.Usuario).filter(models.Usuario.escritorio_id == eid).all()}

    query = db.query(models.CarteiraMembro)
    if usuario_id:
        query = query.filter(models.CarteiraMembro.usuario_id == usuario_id)
    # Filter by tenant: only carteiras belonging to users of the same escritório
    if not getattr(_admin, "is_master", False):
        query = query.filter(models.CarteiraMembro.usuario_id.in_(usuarios.keys()))
    membros = query.all()

    resultado = []
    for m in membros:
        empresa = db.query(models.Empresa).filter(models.Empresa.id == m.empresa_id).first()
        if not empresa:
            continue  # empresa órfã — skip silently
        u = usuarios.get(m.usuario_id)
        if not u:
            continue  # usuario órfão — skip instead of showing "Desconhecido"
        resultado.append({
            **_empresa_to_dict(empresa),
            "usuario_id": m.usuario_id,
            "usuario_nome": u.nome,
            "usuario_cargo": u.cargo or "",
            "carteira_observacoes": m.observacoes or "",
            "adicionado_em": m.adicionado_em,
        })
    resultado.sort(key=lambda x: (x["usuario_nome"], x["nome"]))
    return resultado