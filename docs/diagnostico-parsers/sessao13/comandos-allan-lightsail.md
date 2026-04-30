# Comandos a executar no Lightsail (produção) — Sessão 13

Allan: rode estes comandos via SSH no servidor de produção e cole o output completo de volta no chat.
Não precisa interpretar; apenas executar e colar.

## 1. Versões das libs no container backend de produção

```bash
cd ~/Controllo-analytics
docker compose -f docker-compose.prod.yml exec backend pip show pikepdf 2>&1
docker compose -f docker-compose.prod.yml exec backend pip show pdfplumber 2>&1
docker compose -f docker-compose.prod.yml exec backend pip show pdfminer.six 2>&1
docker compose -f docker-compose.prod.yml exec backend pip show pymupdf 2>&1
```

## 2. Stack trace real do erro `/Root dictionary` nos logs do backend

```bash
cd ~/Controllo-analytics
docker compose -f docker-compose.prod.yml logs backend --tail 2000 | grep -i -B 2 -A 20 "root dictionary"
```

Se o comando acima vier vazio, tente uma janela maior:

```bash
docker compose -f docker-compose.prod.yml logs backend --tail 10000 | grep -i -B 2 -A 20 "root dictionary"
```

## 3. (Opcional, se estiver disponível) Versão do Python no container

```bash
docker compose -f docker-compose.prod.yml exec backend python --version 2>&1
```

---

Após colar o output, eu salvo:
- versões → `docs/diagnostico-parsers/sessao13/versoes-producao.txt`
- stack trace → `docs/diagnostico-parsers/sessao13/stack-trace-root-dictionary.txt`
