from fastapi import APIRouter, Depends, UploadFile, File
from app.models.user import User
from app.core.security import get_current_user
from app.services.yolo_service import detect_wildlife

router = APIRouter()


# ── POST /api/detect ──────────────────────────────────────────────────────────
# Matches Flutter's ApiService.detectSpecies(), which posts an image here
# directly (no report is created — this is a "preview" detection, e.g. for
# showing the user a live guess before they submit the full report).
# NOTE: route is "" (not "/") combined with the /api/detect prefix in
# main.py, so the final path is exactly /api/detect with no trailing
# slash — avoids FastAPI's redirect-on-trailing-slash behavior, which
# would otherwise drop the multipart body on some HTTP clients.
@router.post("")
async def detect_species(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    image_bytes = await image.read()
    result = detect_wildlife(image_bytes)
    return result
