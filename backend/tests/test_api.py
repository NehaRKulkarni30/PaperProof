"""Integration tests for PaperProof FastAPI endpoints (auth, reports, reviews, sharing, export)."""

import os
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base, get_db
from app.main import app
from app.models import Claim, Reference, Report


@pytest.fixture()
def client_and_db():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def _override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client, TestSessionLocal
    app.dependency_overrides.clear()
    test_engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


def _signup(client: TestClient, name: str, email: str, password: str = "StrongPass123!") -> str:
    resp = client.post("/api/auth/signup", json={"name": name, "email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def test_health_endpoint(client_and_db):
    client, _ = client_and_db
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "PaperProof"


def test_auth_signup_login_me_and_protected_routes(client_and_db):
    client, _ = client_and_db

    # Protected route rejects anonymous access
    assert client.get("/api/reports").status_code == 401

    token = _signup(client, "Alice Researcher", "alice@university.edu")
    headers = {"Authorization": f"Bearer {token}"}

    # Duplicate email returns 409
    dup = client.post(
        "/api/auth/signup",
        json={"name": "Alice", "email": "alice@university.edu", "password": "StrongPass123!"},
    )
    assert dup.status_code == 409

    # Login succeeds with valid password and fails with wrong password
    ok_login = client.post(
        "/api/auth/login",
        json={"email": "alice@university.edu", "password": "StrongPass123!"},
    )
    assert ok_login.status_code == 200

    bad_login = client.post(
        "/api/auth/login",
        json={"email": "alice@university.edu", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # /api/auth/me returns profile
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "alice@university.edu"


def test_demo_login_works_idempotently(client_and_db):
    client, _ = client_and_db
    r1 = client.post("/api/auth/demo")
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["user"]["email"] == "demo@paperproof.app"
    assert body1["access_token"]

    # Calling demo login again reuses the same demo user cleanly
    r2 = client.post("/api/auth/demo")
    assert r2.status_code == 200
    assert r2.json()["user"]["id"] == body1["user"]["id"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body1['access_token']}"})
    assert me.status_code == 200
    assert me.json()["name"] == "Demo Reviewer"


def test_verify_input_validation(client_and_db):
    client, _ = client_and_db
    token = _signup(client, "Bob", "bob@university.edu")
    headers = {"Authorization": f"Bearer {token}"}

    # Empty JSON body -> 400
    r_empty = client.post("/api/verify", json={"text": ""}, headers=headers)
    assert r_empty.status_code == 400

    # Unsupported file extension -> 400
    r_bad_ext = client.post(
        "/api/verify",
        files={"file": ("malware.exe", b"binary content here", "application/octet-stream")},
        headers=headers,
    )
    assert r_bad_ext.status_code == 400


def test_report_review_share_export_and_user_isolation(client_and_db):
    client, TestSessionLocal = client_and_db
    alice_token = _signup(client, "Alice", "alice2@university.edu")
    bob_token = _signup(client, "Bob", "bob2@university.edu")
    alice_hdr = {"Authorization": f"Bearer {alice_token}"}
    bob_hdr = {"Authorization": f"Bearer {bob_token}"}

    alice_id = client.get("/api/auth/me", headers=alice_hdr).json()["id"]

    # Seed a completed report owned by Alice directly in the isolated test DB
    db = TestSessionLocal()
    report = Report(
        user_id=alice_id,
        filename="Benchmark_Paper.pdf",
        status="completed",
        stage="report",
        progress=100,
        status_message="Verification complete.",
        mode="gemini",
        summary_json='{"total_claims": 1, "total_references": 1, "verdict_counts": {"supported": 1}}',
        source_pages_json='[{"page": 1, "text": "The Transformer relies on attention [1]."}]',
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    ref = Reference(
        report_id=report.id,
        marker="[1]",
        raw_text="[1] Vaswani et al. (2017). Attention Is All You Need.",
        parsed_json='{"title": "Attention Is All You Need", "year": 2017}',
        resolved_json='{"title": "Attention Is All You Need", "year": 2017}',
        found=True,
        match_score=100.0,
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)

    claim = Claim(
        report_id=report.id,
        idx=1,
        text="The Transformer relies solely on attention mechanisms [1].",
        page=1,
        markers='["[1]"]',
        reference_id=ref.id,
        verdict="supported",
        reason="Explicitly substantiated by the cited abstract.",
        evidence_quote="based solely on attention mechanisms",
        confidence=94,
        confidence_note="Checked against full text.",
        flags_json="[]",
        source_links_json='{"found_via": "arXiv id"}',
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    report_id, claim_id = report.id, claim.id
    db.close()

    # Bob cannot view, review, share, or delete Alice's private report
    assert client.get(f"/api/reports/{report_id}", headers=bob_hdr).status_code == 404
    assert client.delete(f"/api/reports/{report_id}", headers=bob_hdr).status_code == 404

    # Alice can submit a human review decision
    rev = client.patch(
        f"/api/reports/{report_id}/claims/{claim_id}/review",
        json={"decision": "accepted", "note": "Verified verbatim quote against Vaswani 2017."},
        headers=alice_hdr,
    )
    assert rev.status_code == 200
    assert rev.json()["decision"] == "accepted"

    # Alice can export JSON with ethical disclaimer
    exp = client.get(f"/api/reports/{report_id}/export.json", headers=alice_hdr)
    assert exp.status_code == 200
    assert "not a final academic judgment" in exp.json()["disclaimer"]
    assert len(exp.json()["review_history"]) == 1

    # Alice toggles public share link on -> anonymous read works -> toggle off -> 404
    sh_on = client.post(f"/api/reports/{report_id}/share", json={"is_public": True}, headers=alice_hdr)
    assert sh_on.status_code == 200
    share_token = sh_on.json()["share_token"]
    assert share_token

    pub = client.get(f"/api/shared/{share_token}")
    assert pub.status_code == 200
    assert pub.json()["filename"] == "Benchmark_Paper.pdf"

    sh_off = client.post(f"/api/reports/{report_id}/share", json={"is_public": False}, headers=alice_hdr)
    assert sh_off.status_code == 200
    assert client.get(f"/api/shared/{share_token}").status_code == 404
