"""Cliente HTTP para ClickHouse (sem dependências extras)."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.core.config import ClickHouseConfig
from src.core.logging_utils import get_logger


class ClickHouseError(RuntimeError):
    pass


class ClickHouseClient:
    def __init__(self, config: ClickHouseConfig | None = None) -> None:
        self.config = config or ClickHouseConfig.from_env()
        self.log = get_logger(__name__)

    def _request(
        self,
        sql: str,
        *,
        data: bytes | None = None,
        params: dict[str, str] | None = None,
    ) -> str:
        query_params = {
            "database": self.config.database,
            "user": self.config.user,
            "password": self.config.password,
        }
        if params:
            query_params.update(params)
        url = f"{self.config.base_url}/?{urlencode(query_params)}"
        request = Request(
            url=url,
            data=data,
            method="POST" if data is not None else "GET",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        try:
            with urlopen(
                request,
                timeout=(
                    self.config.connect_timeout
                    if data is None
                    else self.config.read_timeout
                ),
            ) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            self.log.error(
                "clickhouse_http_error",
                extra={
                    "status": exc.code,
                    "sql_preview": sql[:200],
                    "error": error_body,
                },
            )
            raise ClickHouseError(
                f"ClickHouse HTTP {exc.code}: {error_body}"
            ) from exc
        except URLError as exc:
            self.log.error(
                "clickhouse_connection_error",
                extra={"sql_preview": sql[:200], "error": str(exc.reason)},
            )
            raise ClickHouseError(
                f"Falha de conexão com ClickHouse: {exc.reason}"
            ) from exc

        if body.startswith("Code:"):
            raise ClickHouseError(body.strip())
        return body

    def execute(self, sql: str) -> str:
        return self._request(sql)

    def query_rows(self, sql: str) -> list[list[str]]:
        result = self.execute(f"{sql.strip()} FORMAT TabSeparated")
        if not result.strip():
            return []
        return [line.split("\t") for line in result.strip().splitlines()]

    def query_one(self, sql: str) -> str | None:
        rows = self.query_rows(sql)
        if not rows:
            return None
        return rows[0][0]

    def describe_table(self, table: str) -> dict[str, str]:
        rows = self.query_rows(f"DESCRIBE TABLE {table}")
        return {row[0]: row[1] for row in rows}

    def table_exists(self, table: str) -> bool:
        value = self.query_one(
            f"EXISTS TABLE {self.config.database}.{table}"
        )
        return value == "1"

    def insert_json_each_row(
        self,
        table: str,
        rows: list[dict[str, Any]],
    ) -> int:
        if not rows:
            return 0
        payload = "\n".join(
            json.dumps(row, ensure_ascii=False, default=str) for row in rows
        ).encode("utf-8")
        sql = f"INSERT INTO {table} FORMAT JSONEachRow"
        self._request(sql, data=payload)
        return len(rows)
