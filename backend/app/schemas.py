from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


# --- Auth Schemas ---
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Verification & Report Schemas ---
class VerifyTextRequest(BaseModel):
    text: str = Field(..., min_length=20)
    filename: Optional[str] = "Pasted manuscript.txt"


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(accepted|rejected|needs_review)$")
    note: Optional[str] = ""


class ShareToggleRequest(BaseModel):
    is_public: bool = True


class ReviewDecisionOut(BaseModel):
    id: str
    claim_id: str
    claim_idx: Optional[int] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    decision: str
    note: str
    created_at: datetime


class ReferenceOut(BaseModel):
    id: str
    marker: str
    raw_text: str
    parsed: Dict[str, Any]
    resolved: Dict[str, Any]
    found: bool
    match_score: float


class ClaimOut(BaseModel):
    id: str
    idx: int
    text: str
    page: int
    markers: List[str]
    reference_id: Optional[str] = None
    reference: Optional[ReferenceOut] = None
    verdict: str
    reason: str
    evidence_quote: Optional[str] = None
    evidence_passage: Optional[str] = None
    evidence_location: Dict[str, Any]
    confidence: int
    confidence_note: str
    flags: List[str]
    source_links: Dict[str, Any]
    latest_decision: Optional[ReviewDecisionOut] = None
    decisions: List[ReviewDecisionOut] = []


class ReportStatusOut(BaseModel):
    id: str
    filename: str
    status: str
    stage: str
    progress: int
    status_message: str
    mode: str
    error_message: Optional[str] = None
    claims_found: int = 0
    references_found: int = 0
    partial_claims: List[Dict[str, Any]] = []


class ReportSummaryItem(BaseModel):
    id: str
    short_id: str
    filename: str
    status: str
    stage: str
    progress: int
    mode: str
    claim_count: int
    reference_count: int
    verdict_counts: Dict[str, int]
    is_public: bool
    share_token: Optional[str] = None
    created_at: datetime


class ReportDetailOut(BaseModel):
    id: str
    short_id: str
    filename: str
    uploaded_by: str
    status: str
    stage: str
    progress: int
    status_message: str
    mode: str
    summary: Dict[str, Any]
    is_public: bool
    share_token: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    references: List[ReferenceOut]
    claims: List[ClaimOut]
    review_history: List[ReviewDecisionOut]
