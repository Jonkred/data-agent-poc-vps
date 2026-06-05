# Arquitetura — POC Data Agent VPS

## Visão Geral

```
┌─────────────────────────────────────────────────────────┐
│                      VPS Ubuntu 24.04                   │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐   │
│  │ Airflow  │   │  MinIO   │   │   ClickHouse     │   │
│  │  :8080   │──▶│  :9000   │──▶│     :8123        │   │
│  │(orquesta)│   │(raw data)│   │  (DW analítico)  │   │
│  └──────────┘   └──────────┘   └──────────────────┘   │
│       │                               ▲                 │
│       │         dbt transform         │                 │
│       └───────────────────────────────┘                 │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐   │
│  │ FastAPI  │   │ Postgres │   │  Qdrant (opt)    │   │
│  │  :8000   │   │ (meta AF)│   │  Ollama (opt)    │   │
│  └──────────┘   └──────────┘   └──────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Camadas de dados

| Camada | Onde | O que armazena |
|---|---|---|
| **raw** | MinIO `/raw` | Dados brutos da fonte (JSON, CSV, screenshots) |
| **bronze** | ClickHouse `poc_dw` | Dados ingeridos sem transformação |
| **silver** | ClickHouse `poc_dw` | Dados limpos e tipados (dbt) |
| **gold** | ClickHouse `poc_dw` | Agregações e marts analíticos (dbt) |

## Tabelas de controle

| Tabela | Propósito |
|---|---|
| `ingestion_control` | Rastreia último hash por entidade (delta detection) |
| `ingestion_runs` | Log completo de cada execução de pipeline |
| `ingestion_errors` | Erros com stack trace |
| `data_quality_results` | Resultados dos testes dbt por execução |

## Decisões técnicas

**LocalExecutor no Airflow** — evita o overhead do CeleryExecutor (Redis + workers) em VPS de estudo com 12 GB RAM.

**ClickHouse Alpine** — imagem mais leve; healthcheck usa `clickhouse-client` em vez de `wget` (wget pode não estar disponível na imagem Alpine).

**airflow-init em exec-form** — command como lista YAML evita o bug de shell duplo que ocorre quando `entrypoint: ["/bin/bash", "-c"]` é combinado com `command: "string"` (Docker interpreta como `/bin/bash -c /bin/sh -c ...`).

**FastAPI via volume** — `api.py` é montado como volume em vez de embutido no YAML. Código Python com imports no início da linha quebraria o scalar YAML do `command: >`.

**dbt em virtualenv** — Ubuntu 22.04+ com Python 3.12 aplica PEP 668 que bloqueia `pip install` global. O venv em `~/.venv/dbt` resolve sem flags `--break-system-packages`.

## Perfis Docker

```
core     → postgres, airflow, minio, clickhouse, fastapi (sempre ativo)
rag      → qdrant (sprint 5)
ai       → ollama (sprint 5)
```

## Sprints

| Sprint | Foco |
|---|---|
| 1 | Infra base: stack core + tabelas de controle + dbt |
| 2 | Primeiro scraping (partner_a) |
| 3 | Modelos dbt bronze→silver→gold |
| 4 | Extração de PDF |
| 5 | Agente + modelo local (Qdrant + Ollama) |
| 6 | Airbyte (opcional) |
