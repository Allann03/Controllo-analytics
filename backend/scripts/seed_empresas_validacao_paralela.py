"""
Seed de empresas sinteticas para validacao paralela DRE (BLOCO 3B.2 Fase B).

Cria 2 empresas novas em controllo_test.db:
  - Empresa Comercio Teste (CMV alto ~60%, D&A baixa, DFin=5000)
  - Empresa Industria Teste (CMV alto, D&A alta ~20k, IRPJ=variado)

Alpha ja existe com 12 meses de lancamentos.
Script idempotente — verifica existencia antes de criar.
"""

import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.database.config import Base
from data.database import models
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "data", "data", "controllo_test.db")
DB_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
agora = datetime.now(timezone.utc).isoformat()


def seed():
    db = Session()
    try:
        # Escritorio 1 (controllobpo, id=1) ja existe
        esc = db.query(models.Escritorio).filter(models.Escritorio.id == 1).first()
        if not esc:
            print("[ERRO] Escritorio id=1 nao encontrado em controllo_test.db")
            return

        # Usuario master (id=1) ja existe
        master = db.query(models.Usuario).filter(models.Usuario.id == 1).first()
        if not master:
            print("[ERRO] Usuario master id=1 nao encontrado")
            return

        # ── Empresa Comercio Teste ────────────────────────────────────
        emp_com = db.query(models.Empresa).filter(
            models.Empresa.nome == "Empresa Comercio Teste"
        ).first()

        if not emp_com:
            emp_com = models.Empresa(
                nome="Empresa Comercio Teste",
                escritorio_id=esc.id,
                usuario_id=master.id,
                cnpj="77.888.999/0001-10",
                status="ativa",
                ativa=True,
                criado_em=agora,
                atualizado_em=agora,
            )
            db.add(emp_com)
            db.flush()
            print(f"[OK] Empresa Comercio Teste criada id={emp_com.id}")
        else:
            print(f"[OK] Empresa Comercio Teste ja existe id={emp_com.id}")

        # Lancamentos Comercio: CMV alto (~60%), sazonalidade no fim de ano
        existing = db.query(models.LancamentoMensal).filter(
            models.LancamentoMensal.empresa_id == emp_com.id
        ).count()
        if existing == 0:
            for mes in range(1, 13):
                sazon = 1.0 + (0.3 if mes in (11, 12) else (-0.1 if mes in (1, 2) else 0.0))
                rb = round(300000 * sazon)
                db.add(models.LancamentoMensal(
                    empresa_id=emp_com.id, ano=2025, mes=mes,
                    receita_bruta=rb,
                    deducoes_receita=round(rb * 0.10),
                    custo_servicos=round(rb * 0.60),
                    despesas_adm=18000,
                    despesas_comerciais=12000,
                    despesas_financeiras=5000,
                    outras_despesas=3000,
                    ir_csll=round(rb * 0.04),
                    depreciacao_amortizacao=500,
                    entradas_caixa=round(rb * 0.95),
                    saidas_caixa=round(rb * 0.80),
                    saldo_inicial_caixa=50000,
                    caixa_equivalentes=60000,
                    contas_receber=round(rb * 0.15),
                    estoques=round(rb * 0.20),
                    outros_ativo_circ=5000,
                    ativo_nao_circulante=40000,
                    fornecedores=round(rb * 0.12),
                    emprestimos_cp=20000,
                    tributos_pagar=round(rb * 0.05),
                    outros_passivo_circ=3000,
                    passivo_nao_circulante=30000,
                    capital_social=80000,
                    reservas=10000,
                    lucros_acumulados=round(mes * 5000),
                    folha_pagamento=25000,
                    criado_em=agora,
                    atualizado_em=agora,
                ))
            print(f"[OK] 12 lancamentos criados para Comercio Teste")
        else:
            print(f"[OK] Comercio Teste ja tem {existing} lancamentos")

        # ── Empresa Industria Teste ───────────────────────────────────
        emp_ind = db.query(models.Empresa).filter(
            models.Empresa.nome == "Empresa Industria Teste"
        ).first()

        if not emp_ind:
            emp_ind = models.Empresa(
                nome="Empresa Industria Teste",
                escritorio_id=esc.id,
                usuario_id=master.id,
                cnpj="88.999.111/0001-20",
                status="ativa",
                ativa=True,
                criado_em=agora,
                atualizado_em=agora,
            )
            db.add(emp_ind)
            db.flush()
            print(f"[OK] Empresa Industria Teste criada id={emp_ind.id}")
        else:
            print(f"[OK] Empresa Industria Teste ja existe id={emp_ind.id}")

        # Lancamentos Industria: CMV alto, D&A alta, crescimento linear
        existing = db.query(models.LancamentoMensal).filter(
            models.LancamentoMensal.empresa_id == emp_ind.id
        ).count()
        if existing == 0:
            for mes in range(1, 13):
                rb = 800000 + mes * 15000  # crescimento linear
                db.add(models.LancamentoMensal(
                    empresa_id=emp_ind.id, ano=2025, mes=mes,
                    receita_bruta=rb,
                    deducoes_receita=round(rb * 0.12),
                    custo_servicos=round(rb * 0.50),
                    despesas_adm=40000,
                    despesas_comerciais=25000,
                    despesas_financeiras=12000,
                    outras_despesas=8000,
                    ir_csll=round(rb * 0.05),
                    depreciacao_amortizacao=20000,
                    entradas_caixa=round(rb * 0.92),
                    saidas_caixa=round(rb * 0.85),
                    saldo_inicial_caixa=150000,
                    caixa_equivalentes=180000,
                    contas_receber=round(rb * 0.10),
                    estoques=round(rb * 0.08),
                    outros_ativo_circ=15000,
                    ativo_nao_circulante=350000,
                    fornecedores=round(rb * 0.08),
                    emprestimos_cp=50000,
                    tributos_pagar=round(rb * 0.06),
                    outros_passivo_circ=10000,
                    passivo_nao_circulante=200000,
                    capital_social=300000,
                    reservas=50000,
                    lucros_acumulados=round(mes * 15000),
                    folha_pagamento=60000,
                    criado_em=agora,
                    atualizado_em=agora,
                ))
            print(f"[OK] 12 lancamentos criados para Industria Teste")
        else:
            print(f"[OK] Industria Teste ja tem {existing} lancamentos")

        db.commit()
        print("\n[OK] Seed concluido com sucesso.")

        # Verificacao final
        for emp_nome in ["Empresa Alpha S/A", "Empresa Comercio Teste", "Empresa Industria Teste"]:
            emp = db.query(models.Empresa).filter(models.Empresa.nome == emp_nome).first()
            if emp:
                cnt = db.query(models.LancamentoMensal).filter(
                    models.LancamentoMensal.empresa_id == emp.id
                ).count()
                print(f"  {emp_nome} (id={emp.id}): {cnt} meses")
            else:
                print(f"  {emp_nome}: NAO ENCONTRADA")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
