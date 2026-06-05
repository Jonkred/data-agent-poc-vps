from unittest.mock import MagicMock, patch

import pytest

from src.core.config import ClickHouseConfig
from src.warehouse.clickhouse_client import ClickHouseClient, ClickHouseError
from src.warehouse.loader import BronzeLoader
from src.warehouse.schema_manager import SchemaManager


def _mock_client() -> MagicMock:
    client = MagicMock()
    client.config = ClickHouseConfig(
        host="localhost",
        port=8123,
        database="poc_dw",
        user="poc_user",
        password="",
        connect_timeout=10.0,
        read_timeout=120.0,
    )
    return client


def test_schema_manager_creates_table_when_missing() -> None:
    client = _mock_client()
    client.table_exists.return_value = False
    client.describe_table.return_value = {}

    manager = SchemaManager(client)
    schema = manager.ensure_table(
        "bronze_rest_countries",
        [{"cca2": "BR", "population": 10, "name": {"common": "Brazil"}}],
    )

    client.execute.assert_called_once()
    assert "_run_id" in schema
    assert "cca2" in schema


def test_schema_manager_adds_missing_columns() -> None:
    client = _mock_client()
    client.table_exists.return_value = True
    client.describe_table.return_value = {
        "_run_id": "String",
        "cca2": "String",
    }

    manager = SchemaManager(client)
    manager.ensure_table(
        "bronze_rest_countries",
        [{"cca2": "BR", "population": 10}],
    )

    assert client.execute.call_count >= 1
    alter_sql = client.execute.call_args[0][0]
    assert "ADD COLUMN IF NOT EXISTS population" in alter_sql


def test_loader_verify_raises_when_count_mismatch() -> None:
    client = MagicMock(spec=ClickHouseClient)
    client.query_one.return_value = "0"
    loader = BronzeLoader(client=client, schema_manager=SchemaManager(client))

    from src.core.config import PipelineConfig
    from src.core.pipeline_context import PipelineContext

    context = PipelineContext.create(
        dag_id="dag",
        source_name="src",
        entity_name="ent",
        schema_version="v1",
        run_id="run-1",
    )
    config = PipelineConfig(
        source_name="src",
        entity_name="ent",
        target_table="bronze_rest_countries",
        schema_version="v1",
    )

    with pytest.raises(RuntimeError, match="Verificação falhou"):
        loader.verify_load(
            context=context,
            pipeline_config=config,
            expected_min=5,
        )


def test_clickhouse_client_raises_on_error_body() -> None:
    client = ClickHouseClient()
    mock_response = MagicMock()
    mock_response.read.return_value = b"Code: 60. DB::Exception: missing table"
    mock_response.__enter__.return_value = mock_response

    with patch(
        "src.warehouse.clickhouse_client.urlopen",
        return_value=mock_response,
    ):
        with pytest.raises(ClickHouseError, match="Code: 60"):
            client.execute("SELECT 1")
