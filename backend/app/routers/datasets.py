from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.models.schemas import DatasetItem
from backend.app.routers.common import get_dataset_store


router = APIRouter(prefix="/api", tags=["datasets"])


@router.get("/datasets", response_model=list[DatasetItem])
def list_datasets(request: Request) -> list[DatasetItem]:
    store = get_dataset_store(request)
    return [
        DatasetItem(
            name=spec.path.name,
            path=spec.display_name,
            format=spec.file_format,
            row_count=spec.row_count,
        )
        for spec in store.list_specs()
    ]
