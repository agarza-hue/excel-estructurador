"""Request bodies for the JSON endpoints. The file is uploaded once via
/upload/analyze (returns an upload_id); later steps reference that id instead of
re-uploading the workbook."""
from pydantic import BaseModel, Field


class MappingRequest(BaseModel):
    upload_id: str
    # { sheet_name: { excel_col: schema_field | "__ignore__" } }
    mapping: dict[str, dict[str, str]]
    header_rows: dict[str, int] = Field(default_factory=dict)


class ImportRequest(MappingRequest):
    period: str | None = None


class RecordCreate(BaseModel):
    data: dict
    period: str | None = None
