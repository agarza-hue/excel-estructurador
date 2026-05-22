from fastapi import APIRouter

from app.services.schema_store import BusinessSchema, load_schema, save_schema

router = APIRouter(prefix="/api/schema", tags=["schema"])


@router.get("")
async def get_schema() -> BusinessSchema:
    return load_schema()


@router.put("")
async def update_schema(schema: BusinessSchema) -> BusinessSchema:
    current = load_schema()
    schema.version = current.version + 1
    return save_schema(schema)
