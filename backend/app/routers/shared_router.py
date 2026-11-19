from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Report
from app.routers.reports_router import serialize_report_detail
from app.schemas import ReportDetailOut

router = APIRouter(prefix="/api/shared", tags=["shared"])


@router.get("/{token}", response_model=ReportDetailOut)
def get_shared_report(token: str, db: Session = Depends(get_db)):
    report = (
        db.query(Report)
        .filter(Report.share_token == token, Report.is_public.is_(True))
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Shared report not found or no longer public.")
    return serialize_report_detail(report, db)
