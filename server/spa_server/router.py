import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["Frontend SPA"])

DIST_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "client", "dist")
)
os.makedirs(DIST_DIR, exist_ok=True)

# Known static file extensions — never serve index.html for these
STATIC_EXTENSIONS = {
    ".js",
    ".css",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".map",
    ".json",
    ".webp",
}


def _serve_file_or_404(full_path: str):
    """Serve a static file from dist, or raise 404 if it's a static asset that doesn't exist."""
    file_path = os.path.join(DIST_DIR, full_path)
    _, ext = os.path.splitext(full_path)

    # If the file physically exists, serve it
    if full_path and os.path.isfile(file_path):
        return FileResponse(file_path)

    # If this looks like a static asset but doesn't exist, return 404 (NOT index.html)
    if ext.lower() in STATIC_EXTENSIONS:
        raise HTTPException(
            status_code=404, detail=f"Static file not found: {full_path}"
        )

    # For all other paths (page navigation), serve index.html for React Router
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")

    raise HTTPException(
        status_code=404, detail="Frontend build not found. Run npm run build."
    )


@router.get("/")
async def serve_frontend_root():
    return _serve_file_or_404("")


@router.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    return _serve_file_or_404(full_path)
