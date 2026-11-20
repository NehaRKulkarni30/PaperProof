import secrets

from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import AuthResponse, GoogleAuthRequest, LoginRequest, SignupRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _user_to_out(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please log in instead.",
        )

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=_user_to_out(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user.id, remember_me=payload.remember_me)
    return AuthResponse(access_token=token, user=_user_to_out(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return _user_to_out(current_user)


@router.post("/demo", response_model=AuthResponse)
def demo_login(db: Session = Depends(get_db)):
    """One-click demo reviewer login (no credentials required)."""
    demo_email = "demo@paperproof.app"
    user = db.query(User).filter(User.email == demo_email).first()
    if not user:
        user = User(
            name="Demo Reviewer",
            email=demo_email,
            password_hash=hash_password(secrets.token_urlsafe(24)),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user.id, remember_me=True)
    return AuthResponse(access_token=token, user=_user_to_out(user))


@router.post("/google", response_model=AuthResponse)
async def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google Sign-In is not configured on this server (GOOGLE_CLIENT_ID not set). Please use email and password.",
        )
    if not payload.credential:
        raise HTTPException(status_code=400, detail="Missing Google ID token credential.")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": payload.credential},
            timeout=10.0,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google credential.")

    info = resp.json()
    if info.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=401, detail="Google token audience mismatch.")
    if str(info.get("email_verified", "")).lower() != "true":
        raise HTTPException(status_code=401, detail="Google account email is not verified.")

    email = (info.get("email") or "").strip().lower()
    google_id = info.get("sub")
    name = info.get("name") or email.split("@")[0]

    user = db.query(User).filter((User.google_id == google_id) | (User.email == email)).first()
    if not user:
        user = User(name=name, email=email, google_id=google_id, password_hash=None)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.google_id:
        user.google_id = google_id
        db.commit()

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=_user_to_out(user))
