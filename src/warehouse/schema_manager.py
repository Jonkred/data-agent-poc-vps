"""Inferência de schema e evolução aditiva de colunas."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from src.core.logging_utils import get_logger
from src.warehouse.clickhouse_client import ClickHouseClient

METADATA_COLUMNS: dict[str, str] = {
    "_run_id": "String",
    "_loaded_at": "DateTime DEFAULT now()",
    "_record_hash": "String",
    "_schema_version": "String",
    "_extraction_key": "String",
    "payload": "String",
}

SAFE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class SchemaManager:
    def __init__(self, client: ClickHouseClient | None = None) -> None:
        self.client = client or ClickHouseClient()
        self.log = get_logger(__name__)

    @staticmethod
    def flatten_record(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for key, value in record.items():
            column = f"{prefix}{key}" if not prefix else f"{prefix}_{key}"
            column = _sanitize_column_name(column)
            if isinstance(value, dict):
                flat.update(SchemaManager.flatten_record(value, column))
            elif isinstance(value, list):
                flat[column] = json.dumps(value, ensure_ascii=False)
            else:
                flat[column] = value
        return flat

    @staticmethod
    def infer_clickhouse_type(value: Any) -> str:
        if value is None:
            return "Nullable(String)"
        if isinstance(value, bool):
            return "UInt8"
        if isinstance(value, int):
            return "Int64"
        if isinstance(value, float):
            return "Float64"
        return "String"

    @staticmethod
    def schema_hash(columns: dict[str, str]) -> str:
        payload = json.dumps(columns, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def ensure_table(
        self,
        table: str,
        sample_records: list[dict[str, Any]],
    ) -> dict[str, str]:
        inferred = self._infer_columns(sample_records)
        full_schema = {**METADATA_COLUMNS, **inferred}
        qualified = f"{self.client.config.database}.{table}"

        if not self.client.table_exists(table):
            ddl = self._build_create_table_ddl(qualified, full_schema)
            self.log.info(
                "creating_table",
                extra={
                    "table": qualified,
                    "column_count": len(full_schema),
                    "schema_hash": self.schema_hash(full_schema),
                },
            )
            self.client.execute(ddl)
            return full_schema

        existing = self.client.describe_table(qualified)
        missing = {
            name: ch_type
            for name, ch_type in inferred.items()
            if name not in existing
        }
        if missing:
            self.log.info(
                "evolving_schema",
                extra={
                    "table": qualified,
                    "new_columns": sorted(missing.keys()),
                    "schema_hash": self.schema_hash({**existing, **missing}),
                },
            )
            for name, ch_type in missing.items():
                ddl = (
                    f"ALTER TABLE {qualified} "
                    f"ADD COLUMN IF NOT EXISTS {name} {ch_type}"
                )
                self.client.execute(ddl)
        return {**existing, **missing}

    def _infer_columns(
        self,
        records: list[dict[str, Any]],
    ) -> dict[str, str]:
        columns: dict[str, str] = {}
        for record in records:
            flat = self.flatten_record(record)
            for name, value in flat.items():
                if name in METADATA_COLUMNS:
                    continue
                if not _is_valid_column_name(name):
                    continue
                inferred = self.infer_clickhouse_type(value)
                current = columns.get(name)
                if current is None:
                    columns[name] = inferred
                elif current != inferred:
                    columns[name] = "String"
        return columns

    @staticmethod
    def _build_create_table_ddl(
        qualified_table: str,
        columns: dict[str, str],
    ) -> str:
        body = ",\n    ".join(
            f"{name} {ch_type}" for name, ch_type in columns.items()
        )
        return (
            f"CREATE TABLE IF NOT EXISTS {qualified_table} (\n"
            f"    {body}\n"
            f") ENGINE = MergeTree\n"
            f"ORDER BY (_run_id, _extraction_key)"
        )


def _sanitize_column_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
    if not cleaned:
        cleaned = "field"
    if cleaned[0].isdigit():
        cleaned = f"col_{cleaned}"
    return cleaned[:128]


def _is_valid_column_name(name: str) -> bool:
    return bool(SAFE_NAME.match(name)) and len(name) <= 128
