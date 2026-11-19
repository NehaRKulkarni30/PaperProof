import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("ReviewDecision", back_populates="user")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=new_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(32), default="processing", nullable=False)  # processing | completed | failed
    stage = Column(String(64), default="upload", nullable=False)  # upload | extract | retrieve | compare | report
    progress = Column(Integer, default=0, nullable=False)
    status_message = Column(String(512), default="Initializing verification pipeline...", nullable=False)
    mode = Column(String(32), default="gemini", nullable=False)  # gemini | heuristic
    summary_json = Column(Text, default="{}", nullable=False)
    share_token = Column(String(64), unique=True, index=True, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    is_sample = Column(Boolean, default=False, nullable=False)
    source_pages_json = Column(Text, nullable=True)  # Stored structured pages for re-run (original uploaded file deleted)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="reports")
    references = relationship("Reference", back_populates="report", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="report", cascade="all, delete-orphan", order_by="Claim.idx")


class Reference(Base):
    __tablename__ = "references"

    id = Column(String(36), primary_key=True, default=new_uuid)
    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    marker = Column(String(64), nullable=False)
    raw_text = Column(Text, nullable=False)
    parsed_json = Column(Text, default="{}", nullable=False)
    resolved_json = Column(Text, default="{}", nullable=False)
    found = Column(Boolean, default=False, nullable=False)
    match_score = Column(Float, default=0.0, nullable=False)

    report = relationship("Report", back_populates="references")
    claims = relationship("Claim", back_populates="reference")


class Claim(Base):
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=new_uuid)
    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    idx = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    page = Column(Integer, default=1, nullable=False)
    markers = Column(Text, default="[]", nullable=False)  # JSON list of citation markers
    reference_id = Column(String(36), ForeignKey("references.id", ondelete="SET NULL"), nullable=True)
    verdict = Column(String(48), default="unsupported", nullable=False)
    reason = Column(Text, default="", nullable=False)
    evidence_quote = Column(Text, nullable=True)
    evidence_passage = Column(Text, nullable=True)
    evidence_location = Column(Text, default="{}", nullable=False)  # JSON {section, page}
    confidence = Column(Integer, default=0, nullable=False)
    confidence_note = Column(Text, default="", nullable=False)
    flags_json = Column(Text, default="[]", nullable=False)
    source_links_json = Column(Text, default="{}", nullable=False)

    report = relationship("Report", back_populates="claims")
    reference = relationship("Reference", back_populates="claims")
    decisions = relationship(
        "ReviewDecision",
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="ReviewDecision.created_at.desc()",
    )


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(String(36), primary_key=True, default=new_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision = Column(String(32), nullable=False)  # accepted | rejected | needs_review
    note = Column(Text, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    claim = relationship("Claim", back_populates="decisions")
    user = relationship("User", back_populates="decisions")


class PaperCache(Base):
    __tablename__ = "paper_cache"

    key = Column(String(512), primary_key=True)
    json = Column(Text, nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=utcnow)
