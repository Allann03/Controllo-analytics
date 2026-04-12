"""
Setup de fixtures para validação funcional Fase 2.
Cria 2 tenants, usuários e empresas via API REST.
Servidor: http://127.0.0.1:8001
Script idempotente — reutiliza recursos existentes.
"""
import httpx
import json
import os
import tempfile

CTX_FILE = os.path.join(tempfile.gettempdir(), "fase2_ctx.json")

BASE = "http://127.0.0.1:8001"
MASTER_USER = "allan"
MASTER_PASS = "TestMaster@2026!!"

# ── helpers ──────────────────────────────────────────────────────────

def _login(username: str, password: str, slug: str = "controllobpo") -> str:
    r = httpx.post(f"{BASE}/api/auth/login", data={
        "username": f"{username}@{slug}",
        "password": password,
    }, follow_redirects=True)
    assert r.status_code == 200, f"Login failed for {username}@{slug}: {r.text}"
    return r.json()["access_token"]

def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

# ── 1. Login como master ──────────────────────────────────────────────
print("\n=== SETUP FIXTURES ===")
master_token = _login(MASTER_USER, MASTER_PASS)
print(f"[OK] Master login: {MASTER_USER}")

# ── 2. Criar ou recuperar Escritório Alpha ────────────────────────────
r = httpx.post(f"{BASE}/api/master/escritorios", headers=_hdr(master_token), json={
    "nome": "Escritório Alpha Teste",
    "slug": "alpha-teste",
    "plano": "profissional",
    "usuario_admin": "admin_alpha",
    "senha_admin": "Admin@Alpha1",
    "nome_admin": "Admin Alpha",
})
if r.status_code in (200, 201):
    alpha = r.json()
    esc_alpha_id = alpha.get("escritorio", {}).get("id") or alpha.get("id")
    print(f"[OK] Escritório Alpha criado ID={esc_alpha_id}")
else:
    # Já existe — buscar pelo slug
    rl = httpx.get(f"{BASE}/api/master/escritorios", headers=_hdr(master_token))
    escritorios = rl.json() if rl.status_code == 200 else []
    esc = next((e for e in escritorios if e.get("slug") == "alpha-teste"), None)
    assert esc, f"Não encontrou alpha-teste: {r.text}"
    esc_alpha_id = esc["id"]
    print(f"[OK] Escritório Alpha já existe ID={esc_alpha_id}")

# ── 3. Criar ou recuperar Escritório Beta ─────────────────────────────
r = httpx.post(f"{BASE}/api/master/escritorios", headers=_hdr(master_token), json={
    "nome": "Escritório Beta Teste",
    "slug": "beta-teste",
    "plano": "profissional",
    "usuario_admin": "admin_beta",
    "senha_admin": "Admin@Beta1!",
    "nome_admin": "Admin Beta",
})
if r.status_code in (200, 201):
    beta = r.json()
    esc_beta_id = beta.get("escritorio", {}).get("id") or beta.get("id")
    print(f"[OK] Escritório Beta criado ID={esc_beta_id}")
else:
    rl = httpx.get(f"{BASE}/api/master/escritorios", headers=_hdr(master_token))
    escritorios = rl.json() if rl.status_code == 200 else []
    esc = next((e for e in escritorios if e.get("slug") == "beta-teste"), None)
    assert esc, f"Não encontrou beta-teste: {r.text}"
    esc_beta_id = esc["id"]
    print(f"[OK] Escritório Beta já existe ID={esc_beta_id}")

# ── 4. Aprovar admin_alpha ────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/master/usuarios?escritorio_id={esc_alpha_id}", headers=_hdr(master_token))
alpha_users = r.json() if r.status_code == 200 else []
admin_alpha_id = next((u["id"] for u in alpha_users if u.get("nome") == "admin_alpha"), None)
if admin_alpha_id:
    r2 = httpx.patch(f"{BASE}/api/master/usuarios/{admin_alpha_id}/aprovar?escritorio_id={esc_alpha_id}",
                     headers=_hdr(master_token), json={"is_aprovado": True})
    print(f"[OK] admin_alpha aprovado (id={admin_alpha_id}): {r2.status_code}")
else:
    print("[WARN] admin_alpha não encontrado via master API")

# ── 5. Aprovar admin_beta ─────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/master/usuarios?escritorio_id={esc_beta_id}", headers=_hdr(master_token))
beta_users = r.json() if r.status_code == 200 else []
admin_beta_id = next((u["id"] for u in beta_users if u.get("nome") == "admin_beta"), None)
if admin_beta_id:
    r2 = httpx.patch(f"{BASE}/api/master/usuarios/{admin_beta_id}/aprovar?escritorio_id={esc_beta_id}",
                     headers=_hdr(master_token), json={"is_aprovado": True})
    print(f"[OK] admin_beta aprovado (id={admin_beta_id}): {r2.status_code}")
else:
    print("[WARN] admin_beta não encontrado via master API")

# ── 6. Login nos tenants ──────────────────────────────────────────────
token_alpha = _login("admin_alpha", "Admin@Alpha1", "alpha-teste")
print(f"[OK] Login admin_alpha token obtido")
token_beta = _login("admin_beta", "Admin@Beta1!", "beta-teste")
print(f"[OK] Login admin_beta token obtido")

# ── 7. Criar empresa no Alpha (ou recuperar existente) ────────────────
r = httpx.post(f"{BASE}/api/carteira", headers=_hdr(token_alpha), json={
    "nome": "Empresa Alpha S/A",
    "cnpj": "11.222.333/0001-81",
    "regime_tributario": "simples",
    "segmento": "Serviços",
    "porte": "ME",
})
if r.status_code in (200, 201):
    empresa_alpha_id = r.json()["empresa"]["id"]
    print(f"[OK] Empresa Alpha criada ID={empresa_alpha_id}")
else:
    # CNPJ já existe — listar e recuperar
    rl = httpx.get(f"{BASE}/api/carteira", headers=_hdr(token_alpha))
    data = rl.json() if rl.status_code == 200 else {}
    empresas = data.get("items", data) if isinstance(data, dict) else data
    emp = next((e for e in empresas if "Alpha" in e.get("nome", "")), None)
    assert emp, f"Não encontrou Empresa Alpha: {r.text}"
    empresa_alpha_id = emp["id"]
    print(f"[OK] Empresa Alpha já existe ID={empresa_alpha_id}")

# ── 8. Criar empresa no Beta ──────────────────────────────────────────
r = httpx.post(f"{BASE}/api/carteira", headers=_hdr(token_beta), json={
    "nome": "Empresa Beta Ltda",
    "cnpj": "44.555.666/0001-81",
    "regime_tributario": "presumido",
    "segmento": "Comércio",
    "porte": "EPP",
})
if r.status_code in (200, 201):
    empresa_beta_id = r.json()["empresa"]["id"]
    print(f"[OK] Empresa Beta criada ID={empresa_beta_id}")
else:
    rl = httpx.get(f"{BASE}/api/carteira", headers=_hdr(token_beta))
    data = rl.json() if rl.status_code == 200 else {}
    empresas = data.get("items", data) if isinstance(data, dict) else data
    emp = next((e for e in empresas if "Beta" in e.get("nome", "")), None)
    assert emp, f"Não encontrou Empresa Beta: {r.text}"
    empresa_beta_id = emp["id"]
    print(f"[OK] Empresa Beta já existe ID={empresa_beta_id}")

# ── 9. Criar lançamentos na empresa Alpha (12 meses) ──────────────────
for mes in range(1, 13):
    r = httpx.post(f"{BASE}/api/financeiro/lancamentos/{empresa_alpha_id}",
                   headers=_hdr(token_alpha), json={
        "ano": 2025, "mes": mes,
        "receita_bruta": 100000.0 + mes * 5000,
        "deducoes_receita": 5000.0,
        "custo_servicos": 30000.0,
        "despesas_adm": 15000.0,
        "despesas_comerciais": 5000.0,
        "despesas_financeiras": 2000.0,
        "outras_despesas": 1000.0,
        "ir_csll": 3000.0,
        "entradas_caixa": 95000.0 + mes * 5000,
        "saidas_caixa": 55000.0,
        "saldo_inicial_caixa": 20000.0 * mes,
        "caixa_equivalentes": 20000.0 * mes,
        "contas_receber": 15000.0,
        "estoques": 5000.0,
        "fornecedores": 8000.0,
        "emprestimos_cp": 10000.0,
        "tributos_pagar": 5000.0,
        "capital_social": 50000.0,
        "lucros_acumulados": 10000.0 * mes,
        "ativo_nao_circulante": 30000.0,
        "folha_pagamento": 25000.0,
        "depreciacao_amortizacao": 1500.0,
    })
    # 200 = updated, 201 = created
    assert r.status_code in (200, 201), f"Lancamento mes={mes}: {r.text}"
print(f"[OK] 12 lançamentos upsert para Empresa Alpha")

# ── 10. Criar banco para empresa Alpha ───────────────────────────────
r = httpx.post(f"{BASE}/api/empresas/{empresa_alpha_id}/bancos", headers=_hdr(token_alpha), json={
    "banco": "Nubank",
    "banco_codigo": "260",
    "agencia": "0001",
    "conta": "12345-6",
    "tipo_conta": "corrente",
    "saldo_inicial": 5000.0,
    "data_saldo_inicial": "2025-01-01",
})
banco_alpha_id = r.json().get("id") if r.status_code in (200, 201) else None
if not banco_alpha_id:
    # Já existe — listar bancos
    rl = httpx.get(f"{BASE}/api/empresas/{empresa_alpha_id}/bancos", headers=_hdr(token_alpha))
    bancos = rl.json() if rl.status_code == 200 else []
    if bancos:
        banco_alpha_id = bancos[0]["id"]
print(f"[OK] Banco Alpha: id={banco_alpha_id}, status={r.status_code}")

# ── 11. Criar transações bancárias no Alpha ───────────────────────────
tx_alpha_id = None
for i in range(1, 6):
    r = httpx.post(f"{BASE}/api/conciliacao/transacoes/{empresa_alpha_id}", headers=_hdr(token_alpha), json={
        "data_transacao": f"2025-01-{i:02d}",
        "descricao": f"PIX RECEBIDO CLIENTE {i}",
        "valor": float(i * 1000),
        "tipo": "credito",
    })
    if r.status_code in (200, 201) and tx_alpha_id is None:
        tx_alpha_id = r.json().get("id")
print(f"[OK] Transações Alpha criadas, última id={tx_alpha_id}")

# ── 12. Criar orçamento Alpha (PUT = upsert, não existe POST) ─────────
r = httpx.put(f"{BASE}/api/orcamento/empresas/{empresa_alpha_id}", headers=_hdr(token_alpha), json={
    "ano": 2025, "mes": 1,
    "receita_bruta": 110000.0,
    "despesas_adm": 16000.0,
    "custo_servicos": 32000.0,
})
print(f"[OK] Orçamento Alpha: {r.status_code} {r.text[:80]}")

# ── 13. Criar alerta Alpha (PUT = upsert, não existe POST) ────────────
r = httpx.put(f"{BASE}/api/alertas/configuracao/{empresa_alpha_id}", headers=_hdr(token_alpha), json={
    "email_destino": "alpha@teste.com",
    "alertar_margem_negativa": True,
    "alertar_caixa_negativo": True,
    "alertar_desvio_orcamento": True,
    "threshold_desvio_pct": 15.0,
})
print(f"[OK] Alerta Alpha: {r.status_code} {r.text[:80]}")

# ── 14. Criar regra de classificação Alpha ────────────────────────────
r = httpx.post(f"{BASE}/api/classificacao/regras/{empresa_alpha_id}", headers=_hdr(token_alpha), json={
    "padrao": "PIX RECEBIDO",
    "tipo_transacao": "entrada",
    "conta_debito_codigo": "11202",
    "conta_credito_codigo": "31101",
    "prioridade": 10,
    "ativo": True,
})
print(f"[OK] Regra de classificação Alpha: {r.status_code}")

# ── Salvar contexto para testes ───────────────────────────────────────
ctx = {
    "master_token": master_token,
    "token_alpha": token_alpha,
    "token_beta": token_beta,
    "esc_alpha_id": esc_alpha_id,
    "esc_beta_id": esc_beta_id,
    "admin_alpha_id": admin_alpha_id,
    "admin_beta_id": admin_beta_id,
    "empresa_alpha_id": empresa_alpha_id,
    "empresa_beta_id": empresa_beta_id,
    "banco_alpha_id": banco_alpha_id,
    "tx_alpha_id": tx_alpha_id,
}
with open(CTX_FILE, "w") as f:
    json.dump(ctx, f, indent=2)
print(f"\n[OK] Contexto salvo em {CTX_FILE}")
print(json.dumps(ctx, indent=2))
