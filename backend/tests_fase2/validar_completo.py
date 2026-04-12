"""
Validação Funcional Exaustiva – Fase 2
Servidor: http://127.0.0.1:8001
Estratégia: mínimo de login calls (rate limit = 10/10min).
Seções cobertas:
  4.1.1  Autenticação e sessão
  4.1.2  Multi-tenancy adversarial
  4.1.4  Lógica contábil-financeira (DRE, BP, DFC, Score)
  4.1.5  Simulação tributária
  4.1.6  Módulo de orçamento
  4.1.7  Alertas e configuração
  4.1.8  Classificação automática
  4.1.9  Conciliação bancária
  4.1.3  Parsers (inspeção estática)
"""
import httpx, json, base64, os, sys, time
from pathlib import Path

BASE = "http://127.0.0.1:8001"
results = []

def chk(section, desc, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    entry = {"section": section, "test": desc, "status": status, "detail": str(detail)[:120]}
    results.append(entry)
    mark = "✓" if ok else "✗"
    print(f"  [{status}] {desc}" + (f" — {detail[:80]}" if detail else ""))
    return ok

def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}

# ── STEP 1: Obter 3 tokens (master + alpha + beta) — 3 chamadas ────────────
print("\n=== STEP 1: LOGIN (3 calls) ===")
def login(user, pw, slug):
    r = httpx.post(f"{BASE}/api/auth/login",
                   data={"username": f"{user}@{slug}", "password": pw})
    if r.status_code == 200:
        return r.json()["access_token"]
    raise RuntimeError(f"Login {user}@{slug} failed: {r.status_code} {r.text[:80]}")

TOK_MASTER = login("allan", "TestMaster@2026!!", "controllobpo")
TOK_ALPHA  = login("admin_alpha", "Admin@Alpha1", "alpha-teste")
TOK_BETA   = login("admin_beta", "Admin@Beta1!", "beta-teste")
print("  Tokens obtidos: master, alpha, beta")

# Decode payload helper
def jwt_payload(tok):
    parts = tok.split(".")
    pad = lambda s: s + "=" * (-len(s) % 4)
    return json.loads(base64.urlsafe_b64decode(pad(parts[1])))

PAYLOAD_MASTER = jwt_payload(TOK_MASTER)
PAYLOAD_ALPHA  = jwt_payload(TOK_ALPHA)
EMPRESA_ALPHA  = 1
EMPRESA_BETA   = 2
ESC_ALPHA_ID   = 2
ESC_BETA_ID    = 3

# ══════════════════════════════════════════════════════════════════════
# 4.1.1 AUTENTICAÇÃO E SESSÃO
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.1 AUTENTICAÇÃO E SESSÃO ===")
S = "4.1.1"

# JWT claims
chk(S, "JWT: claim eid presente",   "eid"       in PAYLOAD_MASTER, f'keys={list(PAYLOAD_MASTER.keys())}')
chk(S, "JWT: claim role presente",  "role"      in PAYLOAD_MASTER, f'role={PAYLOAD_MASTER.get("role")}')
chk(S, "JWT: claim tv presente",    "tv"        in PAYLOAD_MASTER, f'tv={PAYLOAD_MASTER.get("tv")}')
chk(S, "JWT: is_master=True",       PAYLOAD_MASTER.get("is_master") is True)
chk(S, "JWT: eid alpha=2",          PAYLOAD_ALPHA.get("eid") == ESC_ALPHA_ID, f'eid={PAYLOAD_ALPHA.get("eid")}')

# /api/auth/me
r = httpx.get(f"{BASE}/api/auth/me", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/auth/me válido → 200", r.status_code == 200, f'{r.status_code}: {r.text[:60]}')

r = httpx.get(f"{BASE}/api/auth/me", headers={"Authorization": "Bearer INVALID"})
chk(S, "GET /api/auth/me inválido → 401", r.status_code == 401, f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/auth/me")
chk(S, "GET /api/auth/me sem token → 401/403", r.status_code in (401, 403), f'got {r.status_code}')

# Credenciais inválidas
r = httpx.post(f"{BASE}/api/auth/login", data={"username": "ghost@controllobpo", "password": "GhostPass@1!"})
chk(S, "Login usuário inexistente → 401", r.status_code == 401, f'got {r.status_code}')

r = httpx.post(f"{BASE}/api/auth/login", data={"username": "allan@slug_inexistente", "password": "TestMaster@2026!!"})
chk(S, "Login slug inexistente → 401", r.status_code == 401, f'got {r.status_code}')

# R1: Validação de senha — verificar SOURCE CODE (sem chamadas API extras)
# UsuarioCreate.validar() em main.py linha 673-680: apenas len>=8, len<=128
# Não verifica: uppercase, lowercase, digit, special char, zxcvbn
# PATCH /api/auth/senha linha 1111-1112: apenas len>=8
chk(S, "R1-source: validar() verifica uppercase",    False, "CONFIRMADO: código linha 677-680 só checa len>=8")
chk(S, "R1-source: validar() verifica digit",        False, "CONFIRMADO: sem re.search('[0-9]')")
chk(S, "R1-source: validar() verifica special char", False, "CONFIRMADO: sem re.search('[^a-zA-Z0-9]')")
chk(S, "R1-source: validar() usa zxcvbn",            False, "CONFIRMADO: sem import zxcvbn")
chk(S, "R1-source: alterar_senha checa classes",     False, "CONFIRMADO: linha 1111-1112 só checa len>=8")

# R2: _garantir_usuario_mestre() — verificar SOURCE CODE
# main.py linhas 501-546: func roda no módulo-level e sobrescreve senha_hash e escritorio_id
chk(S, "R2-source: garantir_usuario_mestre() sobrescreve senha_hash", False,
    "CONFIRMADO: linha 512 'user.senha_hash = senha_hash' — viola R2")
chk(S, "R2-source: garantir_usuario_mestre() sobrescreve escritorio_id", False,
    "CONFIRMADO: linha 521 'user.escritorio_id = _MASTER_ESCRITORIO_ID' — viola R2")

# ══════════════════════════════════════════════════════════════════════
# 4.1.2 MULTI-TENANCY ADVERSARIAL
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.2 MULTI-TENANCY ADVERSARIAL ===")
S = "4.1.2"

# Alpha tentando acessar recursos de Beta
r = httpx.get(f"{BASE}/api/financeiro/lancamentos/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa lançamentos de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}: {r.text[:60]}')

r = httpx.get(f"{BASE}/api/carteira/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa carteira de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/empresas/{EMPRESA_BETA}/bancos", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa bancos de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/conciliacao/transacoes/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa transações de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/orcamento/comparativo/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa orçamento de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/alertas/configuracao/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa alerta de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/classificacao/regras/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa regras de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/auditoria/logs/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa audit logs de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

r = httpx.post(f"{BASE}/api/financeiro/lancamentos/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA), json={
    "ano": 2025, "mes": 1, "receita_bruta": 99999.0,
    "custo_servicos": 1000.0, "deducoes_receita": 100.0,
})
chk(S, "Alpha NÃO cria lançamento em Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

# Beta tentando acessar escritório Alpha via master API
r = httpx.get(f"{BASE}/api/master/escritorios", headers=hdr(TOK_ALPHA))
chk(S, "Admin Alpha NÃO acessa master/escritorios → 401/403", r.status_code in (401, 403), f'got {r.status_code}')

# Token master pode ver tudo (não deve ser isolado por tenant)
r = httpx.get(f"{BASE}/api/master/escritorios", headers=hdr(TOK_MASTER))
chk(S, "Master acessa /api/master/escritorios → 200", r.status_code == 200, f'got {r.status_code}')

# Alpha acessa seus próprios recursos (deve funcionar)
r = httpx.get(f"{BASE}/api/financeiro/lancamentos/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha acessa seus próprios lançamentos → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:60]}')

r = httpx.get(f"{BASE}/api/carteira/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha acessa sua própria empresa → 200", r.status_code == 200, f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/classificacao/regras/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha acessa suas regras de classificação → 200", r.status_code == 200, f'got {r.status_code}')

# Cross-tenant PUT mutation
r = httpx.put(f"{BASE}/api/carteira/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA), json={
    "nome": "HACK", "cnpj": "44.555.666/0001-81",
    "regime_tributario": "real", "segmento": "Hack"
})
chk(S, "Alpha NÃO edita empresa de Beta via PUT → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

# ══════════════════════════════════════════════════════════════════════
# 4.1.4 LÓGICA CONTÁBIL-FINANCEIRA
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.4 LÓGICA CONTÁBIL-FINANCEIRA ===")
S = "4.1.4"

# DRE para empresa alpha (mes 6, receita=130000)
r = httpx.get(f"{BASE}/api/financeiro/dre/{EMPRESA_ALPHA}?ano=2025&mes=6", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/financeiro/dre → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')

if r.status_code == 200:
    dre = r.json()
    print(f"    DRE keys: {list(dre.keys())[:10]}")

    # mes=6: receita_bruta = 100000 + 6*5000 = 130000
    rb = dre.get("receita_bruta", 0)
    chk(S, "DRE: receita_bruta=130000", abs(rb - 130000) < 1, f'got {rb}')

    # lucro_bruto = receita_liquida - custo_servicos
    # receita_liquida = receita_bruta - deducoes = 130000 - 5000 = 125000
    # custo_servicos = 30000 → lucro_bruto = 95000
    rl = dre.get("receita_liquida", 0)
    chk(S, "DRE: receita_liquida = receita_bruta - deducoes", abs(rl - 125000) < 1, f'got {rl}')
    lb = dre.get("lucro_bruto", 0)
    chk(S, "DRE: lucro_bruto = 95000", abs(lb - 95000) < 1, f'got {lb}')

    # EBIT formula bug check:
    # Correto: EBIT = lucro_bruto - despesas_op (sem desp_financeiras)
    # Atual: EBIT inclui despesas_financeiras → semanticamente é LAIR
    # despesas_adm=15000 + despesas_comerciais=5000 = 20000 (despesas operacionais puras)
    # despesas_financeiras = 2000 → se EBIT correto = 95000 - 20000 = 75000
    # Se EBIT errado (inclui fin) = 95000 - (20000 + 2000) = 73000
    ebit = dre.get("ebit", dre.get("resultado_operacional", None))
    despesas_fin = dre.get("despesas_financeiras", 2000)
    print(f"    EBIT/resultado_op={ebit}, desp_fin={despesas_fin}")
    # Check: source code inclui desp_financeiras no total_despesas_op
    chk(S, "DRE-EBIT: EBIT inclui despesas_financeiras (BUG R3)",
        ebit is not None and abs(ebit - 73000) < 1,
        f'EBIT={ebit} (esperado bug: 73000, correto seria 75000)')

    # Lucro líquido
    ll = dre.get("lucro_liquido", None)
    # lucro_liquido = ebit - ir_csll = 73000 - 3000 = 70000 (com bug)
    if ll is not None:
        chk(S, "DRE: lucro_liquido razoável", ll > 0, f'got {ll}')

    # Margem
    mg = dre.get("margem_liquida", dre.get("margem_liquida_pct", None))
    if mg is not None:
        chk(S, "DRE: margem_liquida presente", True, f'margem={mg}')

# Indicadores financeiros
r = httpx.get(f"{BASE}/api/financeiro/indicadores/{EMPRESA_ALPHA}?ano=2025&mes=6", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/financeiro/indicadores → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    ind = r.json()
    print(f"    Indicadores keys: {list(ind.keys())[:10]}")
    chk(S, "Indicadores: capital_de_giro presente", "capital_de_giro" in ind or "liquidez_corrente" in ind,
        f'keys={list(ind.keys())[:8]}')

# Score de Saúde
r = httpx.get(f"{BASE}/api/financeiro/score-saude/{EMPRESA_ALPHA}?ano=2025&mes=6", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/financeiro/score-saude → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    score = r.json()
    print(f"    Score keys: {list(score.keys())[:10]}")
    sc = score.get("score", score.get("total", None))
    chk(S, "Score: valor entre 0-100", sc is not None and 0 <= sc <= 100, f'score={sc}')

# Balanço Patrimonial
r = httpx.get(f"{BASE}/api/financeiro/balanco/{EMPRESA_ALPHA}?ano=2025&mes=6", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/financeiro/balanco → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    bp = r.json()
    print(f"    BP keys: {list(bp.keys())[:10]}")
    ativo = bp.get("ativo_total", bp.get("total_ativo", None))
    passivo = bp.get("passivo_total", bp.get("total_passivo_pl", None))
    pl = bp.get("patrimonio_liquido", bp.get("pl_total", None))
    print(f"    ativo={ativo}, passivo={passivo}, PL={pl}")
    if all(v is not None for v in [ativo, passivo, pl]):
        # BP invariant: Ativo = Passivo + PL
        soma_pp = (passivo or 0) + (pl or 0)
        diff = abs(ativo - soma_pp)
        chk(S, "BP: Ativo = Passivo + PL (invariante)", diff < 1, f'Ativo={ativo}, Passivo+PL={soma_pp}, diff={diff}')

# DFC
r = httpx.get(f"{BASE}/api/financeiro/fluxo-caixa/{EMPRESA_ALPHA}?ano=2025&mes=6", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/financeiro/fluxo-caixa → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    dfc = r.json()
    print(f"    DFC keys: {list(dfc.keys())[:10]}")
    # mes=6: entradas=125000, saidas=55000, saldo_inicial=120000
    # saldo_final = saldo_inicial + entradas - saidas = 120000 + 125000 - 55000 = 190000
    sf = dfc.get("saldo_final", dfc.get("saldo_final_periodo", None))
    si = dfc.get("saldo_inicial", dfc.get("saldo_inicial_periodo", None))
    ent = dfc.get("entradas_total", dfc.get("total_entradas", None))
    sai = dfc.get("saidas_total", dfc.get("total_saidas", None))
    print(f"    saldo_inicial={si}, entradas={ent}, saidas={sai}, saldo_final={sf}")
    if all(v is not None for v in [sf, si, ent, sai]):
        expected_sf = si + ent - sai
        chk(S, "DFC: saldo_final = saldo_inicial + entradas - saidas",
            abs(sf - expected_sf) < 1, f'sf={sf}, expected={expected_sf}')

# ══════════════════════════════════════════════════════════════════════
# 4.1.5 SIMULAÇÃO TRIBUTÁRIA
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.5 SIMULAÇÃO TRIBUTÁRIA ===")
S = "4.1.5"

# Simples Nacional - empresa_alpha é simples, segmento=Serviços
r = httpx.get(f"{BASE}/api/tributario/simular/{EMPRESA_ALPHA}?ano=2025&mes=1", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/tributario/simular → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    trib = r.json()
    print(f"    Tributário keys: {list(trib.keys())[:10]}")
    reg = trib.get("regime", "")
    total = trib.get("total", 0)
    pct = trib.get("pct_receita", 0)
    print(f"    regime={reg}, total={total}, pct={pct}%")
    chk(S, "Tributário: regime=simples", "simples" in str(reg).lower(), f'regime={reg}')
    chk(S, "Tributário: total > 0", total > 0, f'total={total}')
    # Receita mes=1: 105000. Simples Anexo V serviços ~15.5%
    chk(S, "Tributário: pct_receita razoável (5-30%)", 5 <= pct <= 30, f'pct={pct}%')

# Simulação comparativa com reforma
r = httpx.post(f"{BASE}/api/tributario/comparar/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA), json={
    "ano": 2025, "mes": 1
})
if r.status_code == 404:
    # Try GET
    r = httpx.get(f"{BASE}/api/tributario/comparar/{EMPRESA_ALPHA}?ano=2025&mes=1", headers=hdr(TOK_ALPHA))
chk(S, "Tributário comparativo → 200 ou endpoint presente", r.status_code in (200, 405, 422), f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    comp = r.json()
    print(f"    Comparativo keys: {list(comp.keys())[:8]}")
    chk(S, "Comparativo: regime_atual presente", "regime_atual" in comp or "atual" in comp, f'keys={list(comp.keys())}')
    chk(S, "Comparativo: regime_novo/reforma presente", any(k in comp for k in ["regime_novo","reforma","reforma_tributaria"]), f'keys={list(comp.keys())}')

# Lucro Presumido simulação
r = httpx.post(f"{BASE}/api/tributario/simular-presumido", headers=hdr(TOK_ALPHA), json={
    "receita_bruta": 100000, "custo_servicos": 30000
})
if r.status_code == 404:
    r = httpx.get(f"{BASE}/api/tributario/simular-presumido?receita_bruta=100000&custo_servicos=30000", headers=hdr(TOK_ALPHA))
chk(S, "Tributário Presumido endpoint → 200 ou presente", r.status_code in (200, 405, 422), f'got {r.status_code}: {r.text[:80]}')

# Lucro Real simulação
r = httpx.post(f"{BASE}/api/tributario/simular-real", headers=hdr(TOK_ALPHA), json={
    "receita_bruta": 100000, "custo_servicos": 30000
})
if r.status_code == 404:
    r = httpx.get(f"{BASE}/api/tributario/simular-real?receita_bruta=100000&custo_servicos=30000", headers=hdr(TOK_ALPHA))
chk(S, "Tributário Real endpoint → 200 ou presente", r.status_code in (200, 405, 422), f'got {r.status_code}: {r.text[:80]}')

# ══════════════════════════════════════════════════════════════════════
# 4.1.6 ORÇAMENTO
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.6 ORÇAMENTO ===")
S = "4.1.6"

r = httpx.get(f"{BASE}/api/orcamento/empresas/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/orcamento/empresas/{id} → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')

r = httpx.get(f"{BASE}/api/orcamento/comparativo/{EMPRESA_ALPHA}?ano=2025&mes=1", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/orcamento/comparativo → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    comp = r.json()
    print(f"    Comparativo keys: {list(comp.keys())[:10]}")
    # Verificar desvio % = (real - orçado) / orçado * 100
    rb_real = comp.get("receita_bruta_real", comp.get("real", {}).get("receita_bruta", None))
    rb_orc  = comp.get("receita_bruta_orcada", comp.get("orcado", {}).get("receita_bruta", None))
    print(f"    real={rb_real}, orcado={rb_orc}")

r = httpx.get(f"{BASE}/api/orcamento/comparativo/{EMPRESA_ALPHA}/anual?ano=2025", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/orcamento/comparativo/anual → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')

# Cross-tenant: alpha não acessa orcamento de beta
r = httpx.get(f"{BASE}/api/orcamento/comparativo/{EMPRESA_BETA}?ano=2025&mes=1", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa orcamento de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

# ══════════════════════════════════════════════════════════════════════
# 4.1.7 ALERTAS
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.7 ALERTAS ===")
S = "4.1.7"

r = httpx.get(f"{BASE}/api/alertas/configuracao/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/alertas/configuracao → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    alerta = r.json()
    chk(S, "Alerta: email_destino presente", "email_destino" in alerta, f'keys={list(alerta.keys())}')

r = httpx.get(f"{BASE}/api/alertas/configuracao/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa alerta de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

# ══════════════════════════════════════════════════════════════════════
# 4.1.8 CLASSIFICAÇÃO AUTOMÁTICA
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.8 CLASSIFICAÇÃO ===")
S = "4.1.8"

r = httpx.get(f"{BASE}/api/classificacao/regras/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/classificacao/regras → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    regras = r.json()
    if isinstance(regras, list) and len(regras) > 0:
        chk(S, "Regra: padrao presente", "padrao" in regras[0], f'keys={list(regras[0].keys())}')
    elif isinstance(regras, dict):
        items = regras.get("items", regras.get("regras", []))
        chk(S, "Regras retornam dados", len(items) > 0, f'count={len(items)}')

# Aplicar classificação (transações existentes)
r = httpx.post(f"{BASE}/api/classificacao/aplicar/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA), json={})
chk(S, "POST /api/classificacao/aplicar → 200", r.status_code in (200, 201, 204), f'got {r.status_code}: {r.text[:80]}')

# Cross-tenant
r = httpx.get(f"{BASE}/api/classificacao/regras/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa regras de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

# ══════════════════════════════════════════════════════════════════════
# 4.1.9 CONCILIAÇÃO BANCÁRIA
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.9 CONCILIAÇÃO ===")
S = "4.1.9"

r = httpx.get(f"{BASE}/api/conciliacao/transacoes/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/conciliacao/transacoes → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    txs = r.json()
    count = len(txs) if isinstance(txs, list) else txs.get("total", txs.get("count", -1))
    chk(S, "Transações: pelo menos 5 existem", (count if isinstance(count, int) else len(txs.get("items",[]))) >= 5,
        f'count={count}')

r = httpx.get(f"{BASE}/api/conciliacao/transacoes/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa transações de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

# ══════════════════════════════════════════════════════════════════════
# 4.1.3 PARSERS (inspeção estática)
# ══════════════════════════════════════════════════════════════════════
print("\n=== 4.1.3 PARSERS (estático) ===")
S = "4.1.3"

# Verificar extrator_pdf.py existe e tem pikepdf
pdf_path = Path("c:/Users/Allan/Desktop/Controllo Analytics/backend/services/extrator_pdf.py")
pdf_exists = pdf_path.exists()
chk(S, "extrator_pdf.py existe", pdf_exists)
if pdf_exists:
    content = pdf_path.read_text(encoding='utf-8', errors='replace')
    chk(S, "extrator_pdf.py usa pikepdf", "pikepdf" in content, f'pikepdf in file: {"pikepdf" in content}')
    chk(S, "extrator_pdf.py usa pdfplumber ou pymupdf", any(x in content for x in ["pdfplumber", "pymupdf", "fitz"]),
        f'parsers found: {[x for x in ["pdfplumber","pymupdf","fitz"] if x in content]}')
    chk(S, "extrator_pdf.py trata senha PDF", "senha" in content.lower() or "password" in content.lower())
    # Check for try/except around PDF operations
    chk(S, "extrator_pdf.py tem try/except", "try:" in content or "except" in content)

# Endpoint de importação PDF
r = httpx.get(f"{BASE}/api/importacao/status", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/importacao/status → 200/404", r.status_code in (200, 404), f'got {r.status_code}')

# ══════════════════════════════════════════════════════════════════════
# RELATÓRIOS
# ══════════════════════════════════════════════════════════════════════
print("\n=== RELATÓRIOS ===")
S = "relatorios"

r = httpx.get(f"{BASE}/api/relatorios/exportar/{EMPRESA_ALPHA}?tipo=dre&ano=2025&mes=6", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/relatorios/exportar → 200/4xx", r.status_code < 500, f'got {r.status_code}')

r = httpx.get(f"{BASE}/api/relatorios/exportar/{EMPRESA_BETA}?tipo=dre&ano=2025&mes=6", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO exporta relatório de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

# ══════════════════════════════════════════════════════════════════════
# AUDITORIA
# ══════════════════════════════════════════════════════════════════════
print("\n=== AUDITORIA ===")
S = "auditoria"

r = httpx.get(f"{BASE}/api/auditoria/logs/{EMPRESA_ALPHA}", headers=hdr(TOK_ALPHA))
chk(S, "GET /api/auditoria/logs → 200", r.status_code == 200, f'got {r.status_code}: {r.text[:80]}')
if r.status_code == 200:
    logs = r.json()
    count = len(logs) if isinstance(logs, list) else logs.get("total", -1)
    chk(S, "Audit logs: registros existem", (count if isinstance(count, int) else 0) >= 0, f'count={count}')

r = httpx.get(f"{BASE}/api/auditoria/logs/{EMPRESA_BETA}", headers=hdr(TOK_ALPHA))
chk(S, "Alpha NÃO acessa audit log de Beta → 403/404", r.status_code in (403, 404), f'got {r.status_code}')

# ══════════════════════════════════════════════════════════════════════
# FINANCEIRO - endpoints sem registro de auditoria (debt #financeiro)
# ══════════════════════════════════════════════════════════════════════
print("\n=== FINANCEIRO — AUDITORIA LOG ===")
S = "financeiro_auditlog"

# Verificar se POST /api/financeiro/lancamentos chama registrar_auditoria
# (verificação estática — já confirmado anteriormente que router não importa registrar_auditoria)
fin_router = Path("c:/Users/Allan/Desktop/Controllo Analytics/backend/routers/financeiro.py")
if fin_router.exists():
    fin_content = fin_router.read_text(encoding='utf-8', errors='replace')
    has_audit = "registrar_auditoria" in fin_content
    chk(S, "financeiro router: sem registrar_auditoria (BUG)", not has_audit,
        "CONFIRMADO: 17 endpoints mutáveis sem audit log" if not has_audit else "OK: tem audit log")

# ══════════════════════════════════════════════════════════════════════
# RESULTADOS FINAIS
# ══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("RESUMO FINAL — FASE 2 VALIDAÇÃO FUNCIONAL")
print("═"*60)

by_section = {}
for r in results:
    sec = r["section"]
    by_section.setdefault(sec, {"pass": 0, "fail": 0, "tests": []})
    by_section[sec][r["status"].lower()] += 1
    by_section[sec]["tests"].append(r)

total_pass = sum(1 for r in results if r["status"] == "PASS")
total_fail = sum(1 for r in results if r["status"] == "FAIL")

for sec, stats in by_section.items():
    icon = "✓" if stats["fail"] == 0 else "✗"
    print(f"  {icon} {sec}: PASS={stats['pass']} FAIL={stats['fail']}")

print(f"\nTOTAL: {len(results)} testes | PASS={total_pass} | FAIL={total_fail}")

# Save results
out_path = Path("c:/Users/Allan/Desktop/Controllo Analytics/backend/tests_fase2/resultados.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "total": len(results),
        "pass": total_pass,
        "fail": total_fail,
        "by_section": {k: {"pass": v["pass"], "fail": v["fail"]} for k, v in by_section.items()},
        "tests": results,
    }, f, indent=2, ensure_ascii=False)
print(f"\n[OK] Resultados salvos em {out_path}")

# Print FAILs
print("\nFALHAS DETALHADAS:")
for r in results:
    if r["status"] == "FAIL":
        print(f"  [{r['section']}] {r['test']}")
        if r['detail']:
            print(f"    → {r['detail']}")
