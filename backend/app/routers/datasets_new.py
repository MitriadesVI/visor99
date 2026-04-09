from __future__ import annotations

from fastapi import APIRouter

from backend.app.services.json_reader import read_json

router = APIRouter(prefix="/api", tags=["datasets"])


@router.get("/datasets")
def list_datasets() -> list[dict]:
    return read_json("datasets.json")
