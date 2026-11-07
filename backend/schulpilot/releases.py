import json
from pathlib import Path

from fastapi import APIRouter, Request

from .config import settings

router = APIRouter(tags=["Android-Download"])


def download_url(request: Request, sha256: str) -> str:
    """Select only an explicitly trusted origin; keep old installers working."""
    candidate = f"{request.url.scheme}://{request.headers.get('host', '')}"
    origin = candidate if settings.accepts_web_origin(candidate) else settings.public_url
    filename = settings.android_download_filename if origin == settings.public_url else "schulpilot-android.apk"
    if filename not in ("schulpilot-android.apk", "schuleschlau-android.apk"):
        raise ValueError("Invalid Android download filename")
    return origin + "/downloads/" + filename + "?v=" + sha256[:16]


@router.get("/app-release")
def android_release(request: Request):
    manifest = Path(__file__).resolve().parents[2] / "android-release.json"
    if not manifest.is_file():
        return {"available": False}
    data = json.loads(manifest.read_text())
    return {"available": True, **data, "download_url": download_url(request, data["sha256"])}
