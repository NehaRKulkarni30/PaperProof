import json
import secrets
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Claim, Reference, Report, ReviewDecision, User
from app.pipeline.ingest import (
    IngestError,
    ScannedPDFError,
    extract_pages_from_bytes,
    extract_pages_from_text,
    sanitize_filename,
)
from app.pipeline.runner import run_verification_pipeline
from app.sample_data import SAMPLE_DOCUMENT_TEXT, SAMPLE_FILENAME
from app.schemas import (
    ClaimOut,
    ReferenceOut,
    ReportDetailOut,
    ReportStatusOut,
    ReportSummaryItem,
    ReviewDecisionOut,
    ReviewDecisionRequest,
    ShareToggleRequest,
)

router = APIRouter(prefix="/api", tags=["reports"])
settings = get_settings()

# Simple in-memory per-user rate limiter for /api/verify (10 requests / minute)
_rate_buckets: Dict[str, List[float]] = defaultdict(list)


def _check_rate_limit(user_id: str, limit: int = 12, window_sec: int = 60):
    now = time.time()
    bucket = [t for t in _rate_buckets[user_id] if now - t < window_sec]
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification requests in a short period. Please wait a moment and try again.",
        )
    bucket.append(now)
    _rate_buckets[user_id] = bucket


def _safe_json(val: Optional[str], default: Any):
    if not val:
        return default
    try:
        return json.loads(val)
    except Exception:
        return default


def serialize_reference(ref: Reference) -> ReferenceOut:
    return ReferenceOut(
        id=ref.id,
        marker=ref.marker,
        raw_text=ref.raw_text,
        parsed=_safe_json(ref.parsed_json, {}),
        resolved=_safe_json(ref.resolved_json, {}),
        found=ref.found,
        match_score=ref.match_score,
    )


def serialize_report_detail(report: Report, db: Session) -> ReportDetailOut:
    ref_map = {r.id: serialize_reference(r) for r in report.references}
    user_cache: Dict[str, str] = {}

    def _get_user_name(uid: Optional[str]) -> str:
        if not uid:
            return "Reviewer"
        if uid not in user_cache:
            u = db.query(User).filter(User.id == uid).first()
            user_cache[uid] = u.name if u else "Reviewer"
        return user_cache[uid]

    claims_out: List[ClaimOut] = []
    all_decisions: List[ReviewDecisionOut] = []

    for c in sorted(report.claims, key=lambda x: x.idx):
        decs = []
        for d in c.decisions:
            d_out = ReviewDecisionOut(
                id=d.id,
                claim_id=c.id,
                claim_idx=c.idx,
                user_id=d.user_id,
                user_name=_get_user_name(d.user_id),
                decision=d.decision,
                note=d.note or "",
                created_at=d.created_at,
            )
            decs.append(d_out)
            all_decisions.append(d_out)

        claims_out.append(
            ClaimOut(
                id=c.id,
                idx=c.idx,
                text=c.text,
                page=c.page,
                markers=_safe_json(c.markers, []),
                reference_id=c.reference_id,
                reference=ref_map.get(c.reference_id) if c.reference_id else None,
                verdict=c.verdict,
                reason=c.reason,
                evidence_quote=c.evidence_quote,
                evidence_passage=c.evidence_passage,
                evidence_location=_safe_json(c.evidence_location, {"section": "Body", "page": 1}),
                confidence=c.confidence,
                confidence_note=c.confidence_note,
                flags=_safe_json(c.flags_json, []),
                source_links=_safe_json(c.source_links_json, {}),
                latest_decision=decs[0] if decs else None,
                decisions=decs,
            )
        )

    all_decisions.sort(key=lambda d: d.created_at, reverse=True)
    uploader = report.user.name if report.user else _get_user_name(report.user_id)

    return ReportDetailOut(
        id=report.id,
        short_id=report.id[:8].upper(),
        filename=report.filename,
        uploaded_by=uploader,
        status=report.status,
        stage=report.stage,
        progress=report.progress,
        status_message=report.status_message,
        mode=report.mode,
        summary=_safe_json(report.summary_json, {}),
        is_public=report.is_public,
        share_token=report.share_token,
        error_message=report.error_message,
        created_at=report.created_at,
        references=list(ref_map.values()),
        claims=claims_out,
        review_history=all_decisions,
    )


@router.post("/verify", status_code=status.HTTP_202_ACCEPTED)
async def verify_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(default=None),
    text: Optional[str] = Form(default=None),
    filename: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_rate_limit(current_user.id)

    # Support both multipart/form-data AND application/json
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        body = await request.json()
        text = body.get("text")
        filename = body.get("filename") or "Pasted_Manuscript.txt"

    pages: List[Dict[str, Any]] = []
    clean_name = "Pasted_Manuscript.txt"

    try:
        if file is not None and file.filename:
            clean_name = sanitize_filename(file.filename)
            raw_bytes = await file.read()
            if len(raw_bytes) > settings.max_upload_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File exceeds the 15 MB size limit.",
                )
            if len(raw_bytes) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            # Extract pages in memory; raw uploaded bytes are never persisted to disk
            pages = extract_pages_from_bytes(raw_bytes, clean_name)
        elif text and text.strip():
            clean_name = sanitize_filename(filename or "Pasted_Manuscript.txt")
            pages = extract_pages_from_text(text)
        else:
            raise HTTPException(
                status_code=400,
                detail="Please upload a PDF/DOCX/TXT file or paste manuscript text to verify.",
            )
    except ScannedPDFError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    report = Report(
        user_id=current_user.id,
        filename=clean_name,
        status="processing",
        stage="upload",
        progress=5,
        status_message="Document ingested. Starting verification pipeline…",
        mode="gemini",
        summary_json="{}",
        source_pages_json=json.dumps(pages, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(run_verification_pipeline, report.id, pages, False)
    return {
        "id": report.id,
        "short_id": report.id[:8].upper(),
        "filename": report.filename,
        "status": report.status,
    }


@router.post("/sample", status_code=status.HTTP_202_ACCEPTED)
async def run_sample_document(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_rate_limit(current_user.id)
    pages = extract_pages_from_text(SAMPLE_DOCUMENT_TEXT)
    report = Report(
        user_id=current_user.id,
        filename=SAMPLE_FILENAME,
        status="processing",
        stage="upload",
        progress=5,
        status_message="Sample Transformer & BERT manuscript loaded. Starting pipeline…",
        mode="gemini",
        summary_json="{}",
        is_sample=True,
        source_pages_json=json.dumps(pages, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(run_verification_pipeline, report.id, pages, True)
    return {
        "id": report.id,
        "short_id": report.id[:8].upper(),
        "filename": report.filename,
        "status": report.status,
    }


@router.get("/reports", response_model=List[ReportSummaryItem])
def list_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reports = (
        db.query(Report)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    out = []
    for r in reports:
        summary = _safe_json(r.summary_json, {})
        vc = summary.get("verdict_counts") or {}
        out.append(
            ReportSummaryItem(
                id=r.id,
                short_id=r.id[:8].upper(),
                filename=r.filename,
                status=r.status,
                stage=r.stage,
                progress=r.progress,
                mode=r.mode,
                claim_count=summary.get("total_claims", len(r.claims)),
                reference_count=summary.get("total_references", len(r.references)),
                verdict_counts=vc,
                is_public=r.is_public,
                share_token=r.share_token,
                created_at=r.created_at,
            )
        )
    return out


@router.get("/reports/{report_id}/status", response_model=ReportStatusOut)
def get_report_status(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    partial_claims = [
        {
            "idx": c.idx,
            "text": c.text[:140] + ("…" if len(c.text) > 140 else ""),
            "verdict": c.verdict,
            "markers": _safe_json(c.markers, []),
        }
        for c in sorted(report.claims, key=lambda x: x.idx)[:10]
    ]

    return ReportStatusOut(
        id=report.id,
        filename=report.filename,
        status=report.status,
        stage=report.stage,
        progress=report.progress,
        status_message=report.status_message,
        mode=report.mode,
        error_message=report.error_message,
        claims_found=len(report.claims),
        references_found=len(report.references),
        partial_claims=partial_claims,
    )


@router.get("/reports/{report_id}", response_model=ReportDetailOut)
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return serialize_report_detail(report, db)


@router.delete("/reports/{report_id}")
def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    db.delete(report)
    db.commit()
    return {"deleted": True, "id": report_id}


@router.post("/reports/{report_id}/rerun", status_code=status.HTTP_202_ACCEPTED)
def rerun_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_rate_limit(current_user.id)
    old = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not old:
        raise HTTPException(status_code=404, detail="Report not found.")
    pages = _safe_json(old.source_pages_json, [])
    if not pages:
        raise HTTPException(status_code=400, detail="Source text is no longer available to re-run.")

    new_report = Report(
        user_id=current_user.id,
        filename=old.filename,
        status="processing",
        stage="upload",
        progress=5,
        status_message="Re-running verification pipeline…",
        mode="gemini",
        summary_json="{}",
        is_sample=old.is_sample,
        source_pages_json=old.source_pages_json,
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    background_tasks.add_task(run_verification_pipeline, new_report.id, pages, old.is_sample)
    return {"id": new_report.id, "short_id": new_report.id[:8].upper(), "status": "processing"}


@router.patch("/reports/{report_id}/claims/{claim_id}/review", response_model=ReviewDecisionOut)
def review_claim(
    report_id: str,
    claim_id: str,
    payload: ReviewDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    claim = db.query(Claim).filter(Claim.id == claim_id, Claim.report_id == report.id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")

    decision = ReviewDecision(
        claim_id=claim.id,
        user_id=current_user.id,
        decision=payload.decision,
        note=(payload.note or "").strip(),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    return ReviewDecisionOut(
        id=decision.id,
        claim_id=claim.id,
        claim_idx=claim.idx,
        user_id=current_user.id,
        user_name=current_user.name,
        decision=decision.decision,
        note=decision.note,
        created_at=decision.created_at,
    )


@router.post("/reports/{report_id}/share")
def toggle_share_link(
    report_id: str,
    payload: ShareToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    report.is_public = bool(payload.is_public)
    if report.is_public and not report.share_token:
        report.share_token = secrets.token_urlsafe(18)
    db.commit()
    db.refresh(report)

    return {
        "is_public": report.is_public,
        "share_token": report.share_token if report.is_public else None,
        "share_path": f"/shared/{report.share_token}" if (report.is_public and report.share_token) else None,
    }


@router.get("/reports/{report_id}/export.json")
def export_report_json(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    detail = serialize_report_detail(report, db)
    data = json.loads(detail.model_dump_json())
    data["disclaimer"] = (
        "A citation is not proof by itself. This is an automated evidence check, "
        "not a final academic judgment. Review every finding."
    )
    safe_stem = report.filename.rsplit(".", 1)[0]
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="PaperProof_{safe_stem}_{detail.short_id}.json"'
        },
    )
