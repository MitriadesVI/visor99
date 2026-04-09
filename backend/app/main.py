from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.routers import candidate_new, competitive_new, datasets_new, filters_new, municipal_new


app = FastAPI(title="Visor 99 API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets_new.router)
app.include_router(filters_new.router)
app.include_router(candidate_new.router)
app.include_router(competitive_new.router)
app.include_router(municipal_new.router)


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
