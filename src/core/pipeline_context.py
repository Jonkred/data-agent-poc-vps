"""Contexto de execução compartilhado entre tasks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PipelineContext:
    run_id: str
    dag_id: str
    source_name: str
    entity_name: str
    schema_version: str
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        dag_id: str,
        source_name: str,
        entity_name: str,
        schema_version: str,
        run_id: str | None = None,
    ) -> PipelineContext:
        return cls(
            run_id=run_id or str(uuid.uuid4()),
            dag_id=dag_id,
            source_name=source_name,
            entity_name=entity_name,
            schema_version=schema_version,
        )

    def bind(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "dag_id": self.dag_id,
            "source_name": self.source_name,
            "entity_name": self.entity_name,
            "schema_version": self.schema_version,
        }
