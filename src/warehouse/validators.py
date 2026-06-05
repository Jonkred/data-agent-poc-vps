"""Validação de dados em cada etapa do pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    valid_records: list[dict[str, Any]] = field(default_factory=list)
    invalid_records: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.valid_records and not self.invalid_records

    @property
    def has_valid(self) -> bool:
        return bool(self.valid_records)


def validate_api_response(payload: Any) -> ValidationResult:
    result = ValidationResult()
    if payload is None:
        result.errors.append("Resposta da API é nula")
        return result
    if not isinstance(payload, list):
        result.errors.append(
            f"Resposta da API deve ser lista, recebido: {type(payload).__name__}"
        )
        return result
    if len(payload) == 0:
        result.errors.append("Resposta da API está vazia")
        return result
    return result


def validate_country_records(records: list[dict[str, Any]]) -> ValidationResult:
    result = ValidationResult()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            result.invalid_records.append(
                {"index": index, "record": record, "reason": "not_a_dict"}
            )
            result.errors.append(f"Registro {index} não é um objeto JSON")
            continue

        cca2 = record.get("cca2")
        if not cca2 or not isinstance(cca2, str) or len(cca2) != 2:
            result.invalid_records.append(
                {
                    "index": index,
                    "record": record,
                    "reason": "invalid_cca2",
                }
            )
            result.errors.append(
                f"Registro {index} possui cca2 inválido: {cca2!r}"
            )
            continue

        population = record.get("population")
        if population is not None and not isinstance(population, (int, float)):
            result.invalid_records.append(
                {
                    "index": index,
                    "record": record,
                    "reason": "invalid_population",
                }
            )
            result.errors.append(
                f"Registro {index} possui population inválida: {population!r}"
            )
            continue

        result.valid_records.append(record)
    return result


def validate_load_batch(rows: list[dict[str, Any]]) -> ValidationResult:
    result = ValidationResult()
    required = {"_run_id", "_record_hash", "_extraction_key", "payload"}
    for index, row in enumerate(rows):
        missing = required - set(row.keys())
        if missing:
            result.invalid_records.append(row)
            result.errors.append(
                f"Linha {index} sem colunas obrigatórias: {sorted(missing)}"
            )
            continue
        result.valid_records.append(row)
    return result
