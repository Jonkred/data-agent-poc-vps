"""
Pipeline REST Countries → ClickHouse (camada bronze).

Extrai dados de API pública, valida, transforma com schema resiliente
e carrega em lotes pequenos adequados à VPS.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
from airflow.operators.python import get_current_context

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT.parent))

from src.connectors.public_api import PublicApiError, fetch_public_countries
from src.core.config import ClickHouseConfig, PipelineConfig, PublicApiConfig
from src.core.logging_utils import get_logger
from src.core.pipeline_context import PipelineContext
from src.warehouse.ingestion_tracker import IngestionTracker
from src.warehouse.loader import BronzeLoader
from src.warehouse.transform import transform_records
from src.warehouse.validators import validate_api_response, validate_country_records

DAG_ID = "public_api_to_clickhouse"
DEFAULT_ARGS = {
    "owner": "poc-data-agent",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id=DAG_ID,
    description="Ingere países da REST Countries API no ClickHouse (bronze)",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["bronze", "public-api", "clickhouse", "vps"],
)
def public_api_to_clickhouse() -> None:
    @task(
        execution_timeout=timedelta(minutes=5),
        retries=2,
    )
    def extract() -> dict[str, Any]:
        context = get_current_context()
        log = get_logger("extract", dag_run_id=context["run_id"])
        api_config = PublicApiConfig.from_env()
        pipeline_config = PipelineConfig.from_env()
        run_context = PipelineContext.create(
            dag_id=DAG_ID,
            source_name=pipeline_config.source_name,
            entity_name=pipeline_config.entity_name,
            schema_version=pipeline_config.schema_version,
            run_id=context["run_id"],
        )
        tracker = IngestionTracker()
        tracker.start_run(run_context, pipeline_config)

        try:
            records = fetch_public_countries(api_config)
        except PublicApiError as exc:
            tracker.record_error(
                run_context,
                pipeline_config,
                error_type="extract",
                error_message=str(exc),
                exc=exc,
            )
            tracker.finish_run(
                run_context,
                pipeline_config,
                status="failed",
                records_extracted=0,
                records_loaded=0,
                error_message=str(exc),
            )
            raise AirflowFailException(str(exc)) from exc

        log.info(
            "extract_complete",
            extra={
                **run_context.bind(),
                "records_extracted": len(records),
            },
        )
        return {
            "run_id": run_context.run_id,
            "records": records,
            "records_extracted": len(records),
        }

    @task(execution_timeout=timedelta(minutes=3))
    def validate_extract(payload: dict[str, Any]) -> dict[str, Any]:
        api_result = validate_api_response(payload.get("records"))
        if api_result.errors:
            raise AirflowFailException(
                "Validação da extração falhou: "
                + "; ".join(api_result.errors)
            )

        country_result = validate_country_records(payload["records"])
        if not country_result.has_valid:
            raise AirflowFailException(
                "Nenhum registro válido após validação: "
                + "; ".join(country_result.errors[:5])
            )

        log = get_logger("validate_extract")
        log.info(
            "validation_complete",
            extra={
                "run_id": payload["run_id"],
                "valid_count": len(country_result.valid_records),
                "invalid_count": len(country_result.invalid_records),
            },
        )
        return {
            **payload,
            "valid_records": country_result.valid_records,
            "invalid_records": country_result.invalid_records,
            "validation_errors": country_result.errors,
        }

    @task(execution_timeout=timedelta(minutes=3))
    def transform(validated: dict[str, Any]) -> dict[str, Any]:
        pipeline_config = PipelineConfig.from_env()
        run_context = PipelineContext.create(
            dag_id=DAG_ID,
            source_name=pipeline_config.source_name,
            entity_name=pipeline_config.entity_name,
            schema_version=pipeline_config.schema_version,
            run_id=validated["run_id"],
        )
        rows = transform_records(validated["valid_records"], run_context)
        log = get_logger("transform")
        log.info(
            "transform_complete",
            extra={
                **run_context.bind(),
                "rows_prepared": len(rows),
            },
        )
        return {
            **validated,
            "rows": rows,
        }

    @task(execution_timeout=timedelta(minutes=10))
    def load(transformed: dict[str, Any]) -> dict[str, Any]:
        pipeline_config = PipelineConfig.from_env()
        api_config = PublicApiConfig.from_env()
        run_context = PipelineContext.create(
            dag_id=DAG_ID,
            source_name=pipeline_config.source_name,
            entity_name=pipeline_config.entity_name,
            schema_version=pipeline_config.schema_version,
            run_id=transformed["run_id"],
        )
        tracker = IngestionTracker()
        loader = BronzeLoader()

        if transformed.get("invalid_records"):
            tracker.record_invalid_records(
                run_context,
                pipeline_config,
                transformed["invalid_records"],
            )

        try:
            stats = loader.load(
                transformed["rows"],
                context=run_context,
                pipeline_config=pipeline_config,
                api_config=api_config,
                source_records=transformed["valid_records"],
            )
        except Exception as exc:
            tracker.record_error(
                run_context,
                pipeline_config,
                error_type="load",
                error_message=str(exc),
                exc=exc,
            )
            tracker.finish_run(
                run_context,
                pipeline_config,
                status="failed",
                records_extracted=transformed["records_extracted"],
                records_loaded=0,
                error_message=str(exc),
            )
            raise

        log = get_logger("load")
        log.info(
            "load_complete",
            extra={
                **run_context.bind(),
                **stats,
            },
        )
        return {
            **transformed,
            **stats,
        }

    @task(execution_timeout=timedelta(minutes=5))
    def verify(loaded: dict[str, Any]) -> dict[str, Any]:
        pipeline_config = PipelineConfig.from_env()
        run_context = PipelineContext.create(
            dag_id=DAG_ID,
            source_name=pipeline_config.source_name,
            entity_name=pipeline_config.entity_name,
            schema_version=pipeline_config.schema_version,
            run_id=loaded["run_id"],
        )
        loader = BronzeLoader()
        tracker = IngestionTracker()

        expected = loaded.get("records_loaded", 0)
        try:
            verified = loader.verify_load(
                context=run_context,
                pipeline_config=pipeline_config,
                expected_min=expected,
            )
        except Exception as exc:
            tracker.finish_run(
                run_context,
                pipeline_config,
                status="failed",
                records_extracted=loaded["records_extracted"],
                records_loaded=loaded.get("records_loaded", 0),
                error_message=str(exc),
            )
            raise AirflowFailException(str(exc)) from exc

        tracker.update_control(
            run_context,
            pipeline_config,
            loaded["rows"],
        )
        tracker.finish_run(
            run_context,
            pipeline_config,
            status="success",
            records_extracted=loaded["records_extracted"],
            records_loaded=verified,
        )

        log = get_logger("verify")
        log.info(
            "verify_complete",
            extra={
                **run_context.bind(),
                "records_verified": verified,
                "target_table": pipeline_config.target_table,
                "clickhouse_host": ClickHouseConfig.from_env().host,
            },
        )
        return {
            "run_id": run_context.run_id,
            "status": "success",
            "records_extracted": loaded["records_extracted"],
            "records_loaded": verified,
            "invalid_rows": loaded.get("invalid_rows", 0),
        }

    extracted = extract()
    validated = validate_extract(extracted)
    transformed = transform(validated)
    loaded_payload = load(transformed)
    verify(loaded_payload)


public_api_to_clickhouse_dag = public_api_to_clickhouse()
