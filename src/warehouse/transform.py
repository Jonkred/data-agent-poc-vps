"""Transformação de registros para o formato bronze."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.core.pipeline_context import PipelineContext
from src.warehouse.schema_manager import SchemaManager


def record_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def extraction_key(record: dict[str, Any]) -> str:
    cca2 = record.get("cca2")
    if isinstance(cca2, str) and cca2:
        return cca2.upper()
    return record_hash(record)[:16]


def transform_records(
    records: list[dict[str, Any]],
    context: PipelineContext,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        flat = SchemaManager.flatten_record(record)
        row: dict[str, Any] = {
            "_run_id": context.run_id,
            "_record_hash": record_hash(record),
            "_schema_version": context.schema_version,
            "_extraction_key": extraction_key(record),
            "payload": json.dumps(record, ensure_ascii=False),
        }
        for key, value in flat.items():
            if key in row:
                continue
            if value is None:
                row[key] = None
            elif isinstance(value, (str, int, float, bool)):
                row[key] = value
            else:
                row[key] = str(value)
        rows.append(row)
    return rows
