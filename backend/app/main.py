from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import APP_SETTINGS
from backend.app.routers import candidate, competitive, datasets, filters, municipal
from backend.app.services.dataset_loader import DatasetStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = DatasetStore()
    store.resolve(APP_SETTINGS.default_dataset_path)  # verify default exists
    app.state.dataset_store = store
    yield


app = FastAPI(title="Visor 99 API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(filters.router)
app.include_router(candidate.router)
app.include_router(competitive.router)
app.include_router(municipal.router)


@app.get("/api/health")
def api_healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _frontend_dist.is_dir():
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))
