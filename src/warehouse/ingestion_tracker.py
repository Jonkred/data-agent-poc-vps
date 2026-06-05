"""Rastreamento de execuções nas tabelas de controle."""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Any

from src.core.config import PipelineConfig
from src.core.pipeline_context import PipelineContext
from src.warehouse.clickhouse_client import ClickHouseClient


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class IngestionTracker:
    def __init__(self, client: ClickHouseClient | None = None) -> None:
        self.client = client or ClickHouseClient()

    def start_run(self, context: PipelineContext, config: PipelineConfig) -> None:
        row = {
            "run_id": context.run_id,
            "source_name": config.source_name,
            "entity_name": config.entity_name,
            "dag_id": context.dag_id,
            "task_id": "pipeline",
            "start_time": context.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "running",
            "records_extracted": 0,
            "records_loaded": 0,
        }
        self.client.insert_json_each_row("ingestion_runs", [row])

    def finish_run(
        self,
        context: PipelineContext,
        config: PipelineConfig,
        *,
        status: str,
        records_extracted: int,
        records_loaded: int,
        error_message: str = "",
    ) -> None:
        end_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        sql = (
            "ALTER TABLE ingestion_runs UPDATE "
            f"end_time = toDateTime('{end_time}'), "
            f"status = '{_escape(status)}', "
            f"records_extracted = {records_extracted}, "
            f"records_loaded = {records_loaded}, "
            f"error_message = '{_escape(error_message)}' "
            f"WHERE run_id = '{_escape(context.run_id)}'"
        )
        self.client.execute(sql)

    def record_error(
        self,
        context: PipelineContext,
        config: PipelineConfig,
        *,
        error_type: str,
        error_message: str,
        exc: BaseException | None = None,
    ) -> None:
        stack = traceback.format_exc() if exc else ""
        row = {
            "run_id": context.run_id,
            "source_name": config.source_name,
            "entity_name": config.entity_name,
            "error_type": error_type,
            "error_message": error_message[:2000],
            "stack_trace": stack[:8000],
        }
        self.client.insert_json_each_row("ingestion_errors", [row])

    def record_invalid_records(
        self,
        context: PipelineContext,
        config: PipelineConfig,
        invalid_records: list[dict[str, Any]],
    ) -> None:
        for item in invalid_records:
            self.record_error(
                context,
                config,
                error_type="validation",
                error_message=str(item.get("reason", "invalid_record")),
            )

    def update_control(
        self,
        context: PipelineContext,
        config: PipelineConfig,
        records: list[dict[str, Any]],
    ) -> None:
        rows = []
        for record in records:
            key = record.get("_extraction_key", "")
            rows.append(
                {
                    "source_name": config.source_name,
                    "entity_name": config.entity_name,
                    "extraction_key": key,
                    "last_hash": record.get("_record_hash", ""),
                    "last_status": "loaded",
                    "last_error": "",
                    "run_id": context.run_id,
                }
            )
        if rows:
            self.client.insert_json_each_row("ingestion_control", rows)
