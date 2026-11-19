import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Report
from app.pipeline.llm import gemini_client
from app.routers import auth_router, reports_router, shared_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Prevent noisy HTTP/body logging of user documents
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx2").setLevel(logging.WARNING)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Mark any reports orphaned mid-run from a prior restart as failed so users can click Re-run
    db = SessionLocal()
    try:
        stale = db.query(Report).filter(Report.status == "processing").all()
        for r in stale:
            r.status = "failed"
            r.error_message = "Verification was interrupted by a server restart. Click Re-run to verify again."
            r.status_message = "Interrupted by server restart — click Re-run."
        if stale:
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title="PaperProof API",
    description="CiteVerify – Scientific Claim and Citation Verification System (INNOVEDGE Hackathon 2026)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(reports_router.router)
app.include_router(shared_router.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "PaperProof",
        "gemini_configured": gemini_client.is_configured,
        "gemini_model": gemini_client._model_name if gemini_client.is_configured else None,
        "google_oauth_configured": bool(settings.google_client_id),
    }
