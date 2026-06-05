"""Configuração centralizada via variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


@dataclass(frozen=True)
class ClickHouseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    connect_timeout: float
    read_timeout: float

    @classmethod
    def from_env(cls) -> ClickHouseConfig:
        return cls(
            host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
            port=_env_int("CLICKHOUSE_PORT", 8123),
            database=os.getenv("CLICKHOUSE_DB", "poc_dw"),
            user=os.getenv("CLICKHOUSE_USER", "poc_user"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            connect_timeout=_env_float("CLICKHOUSE_CONNECT_TIMEOUT", 10.0),
            read_timeout=_env_float("CLICKHOUSE_READ_TIMEOUT", 120.0),
        )

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass(frozen=True)
class PublicApiConfig:
    url: str
    timeout: float
    max_records: int
    batch_size: int

    @classmethod
    def from_env(cls) -> PublicApiConfig:
        return cls(
            url=os.getenv(
                "PUBLIC_API_COUNTRIES_URL",
                "https://restcountries.com/v3.1/all"
                "?fields=cca2,name,region,population,flags",
            ),
            timeout=_env_float("PUBLIC_API_TIMEOUT", 30.0),
            max_records=_env_int("PUBLIC_API_MAX_RECORDS", 300),
            batch_size=_env_int("PUBLIC_API_BATCH_SIZE", 50),
        )


@dataclass(frozen=True)
class PipelineConfig:
    source_name: str
    entity_name: str
    target_table: str
    schema_version: str

    @classmethod
    def from_env(cls) -> PipelineConfig:
        return cls(
            source_name=os.getenv("PIPELINE_SOURCE_NAME", "rest_countries"),
            entity_name=os.getenv("PIPELINE_ENTITY_NAME", "countries"),
            target_table=os.getenv(
                "PIPELINE_TARGET_TABLE",
                "bronze_rest_countries",
            ),
            schema_version=os.getenv("PIPELINE_SCHEMA_VERSION", "v1"),
        )
