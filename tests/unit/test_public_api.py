import json
from unittest.mock import MagicMock, patch

import pytest

from src.connectors.public_api import PublicApiError, fetch_public_countries
from src.core.config import PublicApiConfig


def test_fetch_public_countries_success() -> None:
    payload = [{"cca2": "BR", "population": 1}]
    config = PublicApiConfig(
        url="https://example.test/all",
        timeout=5.0,
        max_records=10,
        batch_size=5,
    )

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("src.connectors.public_api.urlopen", return_value=mock_response):
        records = fetch_public_countries(config)

    assert records == payload


def test_fetch_public_countries_invalid_json() -> None:
    config = PublicApiConfig(
        url="https://example.test/all",
        timeout=5.0,
        max_records=10,
        batch_size=5,
    )
    mock_response = MagicMock()
    mock_response.read.return_value = b"not-json"
    mock_response.__enter__.return_value = mock_response

    with patch("src.connectors.public_api.urlopen", return_value=mock_response):
        with pytest.raises(PublicApiError, match="JSON"):
            fetch_public_countries(config)


def test_fetch_public_countries_respects_max_records() -> None:
    payload = [{"cca2": f"C{i}"} for i in range(20)]
    config = PublicApiConfig(
        url="https://example.test/all",
        timeout=5.0,
        max_records=5,
        batch_size=5,
    )
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("src.connectors.public_api.urlopen", return_value=mock_response):
        records = fetch_public_countries(config)

    assert len(records) == 5
