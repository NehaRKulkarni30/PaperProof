"""Root entrypoint for Vercel FastAPI runtime (exports app from app.main)."""

from app.main import app

__all__ = ["app"]
