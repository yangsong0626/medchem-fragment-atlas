from __future__ import annotations

from fastapi import APIRouter, Response

from app.services.image_service import smiles_to_svg

router = APIRouter(tags=["render"])


@router.get("/render/fragment.svg")
def render_fragment(smiles: str):
    return Response(content=smiles_to_svg(smiles), media_type="image/svg+xml")
