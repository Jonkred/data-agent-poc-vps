import json
from pathlib import Path

import pytest

from src.core.pipeline_context import PipelineContext
from src.warehouse.schema_manager import SchemaManager
from src.warehouse.transform import extraction_key, record_hash, transform_records
from src.warehouse.validators import (
    validate_api_response,
    validate_country_records,
    validate_load_batch,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def sample_records() -> list[dict]:
    return json.loads((FIXTURES / "countries_sample.json").read_text(encoding="utf-8"))


@pytest.fixture
def malformed_records() -> list[dict]:
    return json.loads((FIXTURES / "countries_malformed.json").read_text(encoding="utf-8"))


def test_validate_api_response_accepts_list(sample_records: list[dict]) -> None:
    result = validate_api_response(sample_records)
    assert not result.errors


def test_validate_api_response_rejects_empty() -> None:
    result = validate_api_response([])
    assert "vazia" in result.errors[0]


def test_validate_country_records_filters_invalid(
    malformed_records: list[dict],
) -> None:
    result = validate_country_records(malformed_records)
    assert len(result.valid_records) == 1
    assert result.valid_records[0]["cca2"] == "BR"
    assert len(result.invalid_records) == 2


def test_schema_manager_flattens_nested_fields(sample_records: list[dict]) -> None:
    flat = SchemaManager.flatten_record(sample_records[0])
    assert flat["name_common"] == "Brazil"
    assert flat["cca2"] == "BR"


def test_schema_manager_infers_types(sample_records: list[dict]) -> None:
    manager = SchemaManager()
    columns = manager._infer_columns(sample_records)
    assert columns["population"] == "Int64"
    assert columns["cca2"] == "String"


def test_schema_manager_schema_hash_is_stable() -> None:
    columns = {"a": "String", "b": "Int64"}
    assert SchemaManager.schema_hash(columns) == SchemaManager.schema_hash(columns)


def test_transform_records_adds_metadata(sample_records: list[dict]) -> None:
    context = PipelineContext.create(
        dag_id="test_dag",
        source_name="rest_countries",
        entity_name="countries",
        schema_version="v1",
        run_id="run-123",
    )
    rows = transform_records(sample_records, context)
    assert len(rows) == 2
    assert rows[0]["_run_id"] == "run-123"
    assert rows[0]["_extraction_key"] == "BR"
    assert "payload" in rows[0]
    assert rows[0]["name_common"] == "Brazil"


def test_record_hash_is_deterministic(sample_records: list[dict]) -> None:
    first = record_hash(sample_records[0])
    second = record_hash(sample_records[0])
    assert first == second


def test_extraction_key_fallback_uses_hash() -> None:
    key = extraction_key({"foo": "bar"})
    assert len(key) == 16


def test_validate_load_batch_requires_metadata(sample_records: list[dict]) -> None:
    context = PipelineContext.create(
        dag_id="test_dag",
        source_name="rest_countries",
        entity_name="countries",
        schema_version="v1",
    )
    rows = transform_records(sample_records, context)
    result = validate_load_batch(rows)
    assert result.has_valid
    assert not result.errors
