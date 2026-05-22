"""Runtime configuration. Everything lives under DATA_DIR so the whole app is
a single self-hosted folder — no external DB server, matching the spec."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="XE_", env_file=".env", extra="ignore")

    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    max_upload_mb: int = 50
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db" / "warehouse.duckdb"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def schema_path(self) -> Path:
        return self.data_dir / "schema.json"

    def ensure_dirs(self) -> None:
        for p in (self.db_path.parent, self.raw_dir, self.uploads_dir):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
