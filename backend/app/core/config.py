from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name: str = "medchem-fragment-atlas"
    data_dir: Path = Field(default=Path(__file__).resolve().parents[3] / "data")
    duckdb_path: Path | None = None
    api_page_size_limit: int = 200

    @property
    def derived_dir(self) -> Path:
        return self.data_dir / "derived"

    @property
    def database_path(self) -> Path:
        return self.duckdb_path or self.derived_dir / "fragment_atlas.duckdb"


@lru_cache
def get_settings() -> Settings:
    return Settings()
