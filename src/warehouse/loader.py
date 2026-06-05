"""Carga em lotes pequenos para VPS com memória limitada."""

from __future__ import annotations

from typing import Any

from src.core.config import PipelineConfig, PublicApiConfig
from src.core.logging_utils import get_logger
from src.core.pipeline_context import PipelineContext
from src.warehouse.clickhouse_client import ClickHouseClient
from src.warehouse.schema_manager import SchemaManager
from src.warehouse.validators import validate_load_batch


class BronzeLoader:
    def __init__(
        self,
        client: ClickHouseClient | None = None,
        schema_manager: SchemaManager | None = None,
    ) -> None:
        self.client = client or ClickHouseClient()
        self.schema = schema_manager or SchemaManager(self.client)
        self.log = get_logger(__name__)

    def load(
        self,
        rows: list[dict[str, Any]],
        *,
        context: PipelineContext,
        pipeline_config: PipelineConfig,
        api_config: PublicApiConfig,
        source_records: list[dict[str, Any]],
    ) -> dict[str, int]:
        validation = validate_load_batch(rows)
        if validation.errors:
            self.log.warning(
                "load_batch_validation_issues",
                extra={
                    **context.bind(),
                    "invalid_count": len(validation.invalid_records),
                    "errors": validation.errors[:5],
                },
            )

        valid_rows = validation.valid_records
        if not valid_rows and source_records:
            self.schema.ensure_table(
                pipeline_config.target_table,
                source_records[:1],
            )
            return {
                "records_loaded": 0,
                "batches": 0,
                "invalid_rows": len(validation.invalid_records),
            }

        self.schema.ensure_table(
            pipeline_config.target_table,
            source_records[: min(20, len(source_records))],
        )

        loaded = 0
        batches = 0
        batch_size = max(1, api_config.batch_size)
        for start in range(0, len(valid_rows), batch_size):
            batch = valid_rows[start : start + batch_size]
            inserted = self.client.insert_json_each_row(
                pipeline_config.target_table,
                batch,
            )
            loaded += inserted
            batches += 1
            self.log.info(
                "batch_loaded",
                extra={
                    **context.bind(),
                    "batch_number": batches,
                    "batch_size": inserted,
                    "loaded_total": loaded,
                },
            )

        return {
            "records_loaded": loaded,
            "batches": batches,
            "invalid_rows": len(validation.invalid_records),
        }

    def verify_load(
        self,
        *,
        context: PipelineContext,
        pipeline_config: PipelineConfig,
        expected_min: int,
    ) -> int:
        count_sql = (
            f"SELECT count() FROM {pipeline_config.target_table} "
            f"WHERE _run_id = '{context.run_id}'"
        )
        value = self.client.query_one(count_sql)
        loaded = int(value or 0)
        if expected_min > 0 and loaded < expected_min:
            raise RuntimeError(
                f"Verificação falhou: esperado >= {expected_min}, "
                f"encontrado {loaded} para run_id={context.run_id}"
            )
        return loaded
