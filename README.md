# POC Data Agent VPS

Setup completo de um ambiente de engenharia de dados numa VPS Ubuntu, orquestrado por scripts idempotentes.

## Stack

| Serviço | Papel | Porta |
|---|---|---|
| **Apache Airflow 2.9.3** | Orquestração de pipelines | 8080 |
| **MinIO** | Object storage (raw, bronze, screenshots, pdfs) | 9001 (console) |
| **ClickHouse 24.5** | Data warehouse analítico | 8123 (HTTP) |
| **FastAPI** | API de ferramentas do agente | 8000 |
| **PostgreSQL 16** | Metadata do Airflow | interno |
| **dbt-core** | Transformações SQL (bronze→silver→gold) | — |
| **Qdrant** *(opcional)* | Vector store para RAG | 6333 |
| **Ollama** *(opcional)* | Modelo local (qwen2.5:1.5b) | 11434 |

## Pré-requisitos

- VPS Ubuntu 22.04 ou 24.04 LTS
- Acesso root via SSH
- Mínimo: 4 vCPU · 8 GB RAM · 50 GB disco

## Instalação

```bash
# 1. Clone diretamente para o diretório do projeto
git clone https://github.com/SEU_USER/data-agent-poc-vps.git ~/data-agent-poc
cd ~/data-agent-poc

# 2. Execute o setup completo (idempotente)
bash setup.sh
```

> O repositório **é** o projeto. Não há diretório separado de deploy.
> Todos os arquivos (docker-compose.yml, api.py, dbt_project.yml) são usados
> diretamente do clone — sem cópias manuais.

O orquestrador verifica cada etapa antes de executar. Se uma etapa já estiver concluída, pula para a próxima.

## Atualização após mudanças no repo

```bash
cd ~/data-agent-poc
git pull
bash setup.sh   # reaaplica apenas o que mudou
```

## Estrutura

```
data-agent-poc-vps/
├── setup.sh                    # Orquestrador principal
├── scripts/
│   ├── 00-base-vps.sh          # UFW, pacotes base
│   ├── 01-docker.sh            # Docker CE
│   ├── 02-swap.sh              # Swap 8 GB
│   ├── 03-structure.sh         # Diretórios + .env
│   ├── 04-compose.sh           # Copia docker-compose.yml
│   ├── 05-run-stack.sh         # Sobe containers
│   ├── 07-minio-buckets.sh     # Cria buckets
│   ├── 08-clickhouse-init.sh   # Cria tabelas
│   ├── 09-dbt-setup.sh         # Instala dbt no venv
│   └── 10-validate.sh          # Validação Sprint 1
├── infra/compose-core/
│   ├── docker-compose.yml      # Stack completa
│   └── clickhouse-config.xml   # Limites de memória
├── src/agent_tools/
│   └── api.py                  # FastAPI endpoint
├── dbt/
│   ├── dbt_project.yml
│   └── models/{bronze,silver,gold}/
└── .env.example                # Template de variáveis
```

## Credenciais de estudo

| Serviço | Usuário | Senha |
|---|---|---|
| Airflow | admin | admin2024 |
| MinIO | minioadmin | minio2024 |
| ClickHouse | poc_user | click2024 |

> Altere as senhas para ambientes não-estudo. Veja `.env.example`.

## Pular etapas específicas

```bash
SKIP_STEPS="00,01" bash setup.sh
```

## Ativar perfis opcionais (RAG / IA)

```bash
cd ~/data-agent-poc/infra/compose-core
docker compose --profile rag up -d   # Qdrant
docker compose --profile ai  up -d   # Ollama
```

## dbt

```bash
# Ativa o ambiente dbt
source ~/data-agent-poc/.venv/dbt/bin/activate
cd ~/data-agent-poc/dbt

dbt debug    # testa conexão
dbt run      # executa modelos
dbt test     # roda testes
```

## Arquitetura de dados

```
Fontes → raw (MinIO) → bronze (ClickHouse) → silver → gold
                                  ↑
                            dbt transforma
                                  ↓
                         Airflow orquestra
```

Veja [docs/architecture.md](docs/architecture.md) para detalhes.
