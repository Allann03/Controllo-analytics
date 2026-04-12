# Deploy Controllo BPO Analytics — AWS Lightsail 8GB

Guia completo para subir o sistema do zero em producao.

---

## Pre-requisitos

- Conta AWS ativa com metodo de pagamento
- Dominio registrado (Registro.br, GoDaddy, Namecheap)
- Repositorio do Controllo no GitHub (push feito)
- Par de chaves SSH gerado localmente

---

## Passo 0 — Configuracao previa do GitHub (OBRIGATORIO antes de tudo)

1. Faca push do codigo para o repositorio GitHub.
2. Va em **Settings > Secrets and variables > Actions**.
3. Adicione o secret `DOMAIN_PRODUCAO` com o dominio escolhido (ex: `controllo.com.br`).
4. Va em **Actions** e dispare manualmente o workflow `Build and Push Docker Images` (Run workflow).
5. Aguarde conclusao (~5-8 min). Imagens publicadas em:
   - `ghcr.io/SEU_USUARIO/controllo-backend:latest`
   - `ghcr.io/SEU_USUARIO/controllo-frontend:latest`

**Importante:** mudanca futura do dominio exige re-executar este passo (rebuild do frontend).

---

## Passo 1 — Criar instancia Lightsail

- **Regiao:** sa-east-1 (Sao Paulo) — latencia e conformidade LGPD
- **Blueprint:** Ubuntu 24.04 LTS
- **Plano:** 8 GB RAM, 2 vCPUs, 160 GB SSD, 5 TB transferencia (~US$ 40/mes)
- Criar **IP estatico** e associar a instancia

---

## Passo 2 — Firewall Lightsail

No console Lightsail, aba Networking:

| Porta | Protocolo | Descricao |
|---|---|---|
| 22 | TCP | SSH (restringir ao IP do admin quando possivel) |
| 80 | TCP | HTTP (Caddy redireciona para HTTPS) |
| 443 | TCP | HTTPS (Let's Encrypt automatico via Caddy) |

---

## Passo 3 — Apontar dominio

No seu registrador de dominio:
- Criar registro **A** apontando para o IP estatico da instancia
- Aguardar propagacao DNS (5-30 min)
- Verificar: `nslookup seu-dominio.com.br` deve retornar o IP

---

## Passo 4 — SSH inicial

```bash
ssh ubuntu@SEU_IP_ESTATICO
```

---

## Passo 5 — Instalacao Docker + dependencias

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg git htop

# Docker CE
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Adicionar usuario ao grupo docker
sudo usermod -aG docker ubuntu
newgrp docker

# Verificar
docker --version
docker compose version
```

---

## Passo 6 — Criar swap 2GB (OBRIGATORIO)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
free -h  # Confirmar 2.0 GB de swap
```

---

## Passo 7 — Clonar repositorio

```bash
cd ~
git clone https://github.com/SEU_USUARIO/controllo-bpo-analytics.git
cd controllo-bpo-analytics
```

---

## Passo 8 — Configurar .env

```bash
cp .env.production.example .env
nano .env
```

Gere valores seguros e preencha:

| Variavel | Como gerar |
|---|---|
| `CONTROLLO_SECRET_KEY` | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | `openssl rand -base64 24` |
| `CONTROLLO_MASTER_PASSWORD` | Senha forte manual com 12+ caracteres, maiuscula, minuscula, digito, especial |
| `DOMAIN` | Seu dominio real (ex: `controllo.com.br`) |
| `DATABASE_URL` | Atualizar com a senha do POSTGRES_PASSWORD gerada |
| `CORS_ORIGINS` | `https://seu-dominio.com.br` |

---

## Passo 9 — Login em ghcr.io

Crie um **Personal Access Token (classic)** no GitHub com scope `read:packages`.

```bash
echo SEU_TOKEN | docker login ghcr.io -u SEU_USUARIO_GITHUB --password-stdin
```

---

## Passo 10 — Subir servicos

Edite `docker-compose.prod.yml` e substitua `SEU_USUARIO_GITHUB` pelo seu usuario real
nas linhas `image: ghcr.io/SEU_USUARIO_GITHUB/...`.

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

---

## Passo 11 — Verificar saude

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail 100
```

Aguardar:
- `db`: status `healthy`
- `backend`: status `healthy` (pode levar ate 60s para estabilizar 4 workers + auto-migracao)
- `caddy`: negocia SSL automaticamente no primeiro acesso HTTPS (30-60s)

---

## Passo 12 — Criar primeiro escritorio e usuario real

1. Acesse `https://seu-dominio.com.br`
2. Login com usuario mestre (usando `CONTROLLO_MASTER_USER` e `CONTROLLO_MASTER_PASSWORD` do `.env`)
3. Criar primeiro escritorio via interface master
4. Criar usuarios administrativos (os 2 donos)
5. Testar upload de PDF pequeno (~10 paginas) — confirma pipeline completo
6. Testar upload de PDF de 190 paginas — confirma capacidade em pico
7. `docker stats` durante processamento — backend nao deve ultrapassar 2500 MB

---

## Backup automatico diario

Criar `/home/ubuntu/backup-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR=/home/ubuntu/backups
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M)
docker compose -f /home/ubuntu/controllo-bpo-analytics/docker-compose.prod.yml exec -T db \
  pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip > $BACKUP_DIR/controllo_$DATE.sql.gz
find $BACKUP_DIR -name "controllo_*.sql.gz" -mtime +7 -delete
```

```bash
chmod +x /home/ubuntu/backup-db.sh
```

Agendar via cron as 03:00:

```bash
crontab -e
# Adicionar linha:
0 3 * * * /home/ubuntu/backup-db.sh >> /home/ubuntu/backup.log 2>&1
```

---

## Monitoramento

```bash
docker stats                    # RAM em tempo real por container
docker compose logs -f backend  # logs do backend
df -h                           # disco
free -h                         # RAM/swap
htop                            # processos
dmesg | grep -i oom             # verificar OOM killer
```

**Alerta:** se backend frequentemente acima de 2500 MB em `docker stats`, considere upgrade.

---

## Troubleshooting

### Container reiniciando em loop
```bash
docker compose -f docker-compose.prod.yml logs <servico>
```
Verificar se OOM: `dmesg | grep -i killed`

### Disco cheio
```bash
docker system prune -af --volumes
```

### SSL nao renovando
```bash
docker compose logs caddy
```
Confirmar que DNS resolve corretamente: `nslookup seu-dominio.com.br`

### OOM no backend
```bash
dmesg | grep -i killed
```
Se frequente, considere upgrade para 16GB.

### PDF nao processa
Verificar `read_timeout` do Caddy (deve ser 300s) e logs do backend.

### Postgres lento
```bash
docker compose exec db psql -U controllo -c "SELECT * FROM pg_stat_activity"
```

### Mudanca de dominio
Exige rebuild do frontend via GitHub Actions:
1. Atualizar secret `DOMAIN_PRODUCAO` no GitHub
2. Disparar workflow manualmente
3. No servidor: `docker compose pull && docker compose up -d`
4. Atualizar `DOMAIN` e `CORS_ORIGINS` no `.env`

---

## Caminho de upgrade para 16GB

Quando considerar upgrade:
- Mais de 6 usuarios ativos simultaneos
- Multiplos operacionais processando PDFs
- Necessidade de EasyOCR habilitado (OCR consome ~1.5GB extras)
- Backend frequentemente acima de 2500 MB

Procedimento (~15 min downtime):
1. Criar snapshot no console Lightsail
2. Criar nova instancia 16GB a partir do snapshot
3. Trocar IP estatico para nova instancia
4. SSH na nova instancia
5. Editar `docker-compose.prod.yml`:
   - `db mem_limit`: 1000m -> 2000m
   - `backend mem_limit`: 3000m -> 6000m
   - `frontend mem_limit`: 600m -> 1000m
6. Editar `backend/Dockerfile.prod`: `--workers 4` -> `--workers 6`
7. Rebuild e redeploy
8. Deletar instancia antiga (manter snapshot 7 dias)
