"""Conector para APIs públicas de dados."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.core.config import PublicApiConfig
from src.core.logging_utils import get_logger


class PublicApiError(RuntimeError):
    pass


def fetch_public_countries(
    config: PublicApiConfig | None = None,
) -> list[dict[str, Any]]:
    cfg = config or PublicApiConfig.from_env()
    log = get_logger(__name__)
    log.info(
        "fetch_start",
        extra={"url": cfg.url, "timeout": cfg.timeout},
    )

    request = Request(
        url=cfg.url,
        headers={"Accept": "application/json", "User-Agent": "poc-data-agent/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=cfg.timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise PublicApiError(
            f"API HTTP {exc.code}: {error_body[:500]}"
        ) from exc
    except URLError as exc:
        raise PublicApiError(
            f"Falha ao consultar API pública: {exc.reason}"
        ) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise PublicApiError("Resposta da API não é JSON válido") from exc

    if not isinstance(payload, list):
        raise PublicApiError(
            f"Formato inesperado: esperado list, recebido {type(payload).__name__}"
        )

    limited = payload[: cfg.max_records]
    log.info(
        "fetch_success",
        extra={
            "records_total": len(payload),
            "records_returned": len(limited),
            "truncated": len(payload) > len(limited),
        },
    )
    return limited
