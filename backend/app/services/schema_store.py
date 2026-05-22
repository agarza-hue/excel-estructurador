"""The configurable business schema (Pantalla 5 · Configuración).

Persisted as a single JSON file under data/. Defines the target fields that
Excel columns map onto and that the capture form renders.
"""
import json
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import settings

FieldType = Literal["text", "number", "currency", "date", "boolean", "select"]


class SchemaField(BaseModel):
    name: str = Field(..., description="machine key, used as the JSON data key")
    label: str
    type: FieldType = "text"
    required: bool = False
    options: list[str] = Field(default_factory=list)  # for type == "select"


class BusinessSchema(BaseModel):
    fields: list[SchemaField]
    version: int = 1


DEFAULT_SCHEMA = BusinessSchema(
    fields=[
        SchemaField(name="fecha", label="Fecha", type="date", required=True),
        SchemaField(name="descripcion", label="Descripción", type="text", required=True),
        SchemaField(name="categoria", label="Categoría", type="text"),
        SchemaField(name="cantidad", label="Cantidad", type="number"),
        SchemaField(name="monto", label="Monto", type="currency"),
    ]
)


def load_schema() -> BusinessSchema:
    if not settings.schema_path.exists():
        save_schema(DEFAULT_SCHEMA)
        return DEFAULT_SCHEMA
    raw = json.loads(settings.schema_path.read_text(encoding="utf-8"))
    return BusinessSchema(**raw)


def save_schema(schema: BusinessSchema) -> BusinessSchema:
    settings.ensure_dirs()
    settings.schema_path.write_text(
        schema.model_dump_json(indent=2), encoding="utf-8"
    )
    return schema
