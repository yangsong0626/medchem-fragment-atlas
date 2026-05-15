from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import fragments, molecules, search
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="MedChem Fragment Atlas",
    description="Searchable BRICS fragment dictionary built from ChEMBL molecules.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fragments.router, prefix="/api")
app.include_router(molecules.router, prefix="/api")
app.include_router(search.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "database": str(settings.database_path)}
