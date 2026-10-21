import secrets
from datetime import timedelta
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from app.models import (
    User,
    UserProfile,
    Role,
    UserRole,
    AuthSession,
    PasswordResetToken,
    now,
)
from app.schemas import (
    Registration,
    Credentials,
    Refresh,
    ResetRequest,
    Reset,
    TokenPair,
    UserResponse,
)
from app.core.database import db_session
from app.core.config import settings
from app.core.security import (
    hasher,
    verify_password,
    sensitive,
    issue,
    digest,
    expired,
    current_user,
    roles,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
DUMMY_PASSWORD_HASH = hasher.hash(secrets.token_urlsafe(32))


@router.post(
    "/register",
    response_model=TokenPair,
    dependencies=[Depends(sensitive)],
    status_code=201,
)
def register(data: Registration, db=Depends(db_session)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, password_hash=hasher.hash(data.password))
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, name=data.name))
    role = db.scalar(select(Role).where(Role.name == "user"))
    if role is None:
        role = Role(name="user")
        db.add(role)
        db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    return issue(db, user)


@router.post("/login", response_model=TokenPair, dependencies=[Depends(sensitive)])
def login(data: Credentials, db=Depends(db_session)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    password_ok = verify_password(
        data.password, user.password_hash if user else DUMMY_PASSWORD_HASH
    )
    if not user or not password_ok or user.status != "active":
        raise HTTPException(401, "Invalid credentials or inactive account")
    return issue(db, user)


@router.post("/refresh", response_model=TokenPair, dependencies=[Depends(sensitive)])
def refresh(data: Refresh, db=Depends(db_session)):
    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.refresh_hash == digest(data.refresh_token))
        .with_for_update()
    )
    if not session or session.revoked or expired(session.expires_at):
        raise HTTPException(401, "Refresh token expired or revoked")
    user = db.get(User, session.user_id)
    if user.status != "active":
        raise HTTPException(401, "Inactive account")
    # Revoke the old session, also invalidating its access tokens.
    session.revoked = True
    return issue(db, user)


@router.post("/logout")
def logout(data: Refresh, user=Depends(current_user), db=Depends(db_session)):
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_hash == digest(data.refresh_token),
            AuthSession.user_id == user.id,
        )
    )
    if session:
        session.revoked = True
    return {"message": "Signed out"}


@router.get("/me", response_model=UserResponse)
def me(user=Depends(current_user), db=Depends(db_session)):
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    return {
        "id": user.id,
        "email": user.email,
        "name": profile.name if profile else "",
        "status": user.status,
        "roles": roles(db, user.id),
    }


@router.post("/request-password-reset", dependencies=[Depends(sensitive)])
def request_reset(data: ResetRequest, db=Depends(db_session)):
    cfg = settings()
    if not cfg.reset_delivery_url or not cfg.reset_delivery_token:
        raise HTTPException(503, "Password-reset delivery is not configured")
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user:
        raw = secrets.token_urlsafe(48)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=digest(raw),
                expires_at=now() + timedelta(minutes=20),
            )
        )
        # Token is only sent to an explicitly configured trusted delivery adapter, never returned to the requester.
        with httpx.Client(timeout=8) as client:
            response = client.post(
                cfg.reset_delivery_url,
                headers={"Authorization": "Bearer " + cfg.reset_delivery_token},
                json={"email": user.email, "reset_token": raw},
            )
            if response.is_error:
                raise HTTPException(503, "Reset delivery is temporarily unavailable")
    return {"message": "If the account exists, a reset link will be sent"}


@router.post("/reset-password", dependencies=[Depends(sensitive)])
def reset_password(data: Reset, db=Depends(db_session)):
    token = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == digest(data.token))
        .with_for_update()
    )
    if not token or token.used or expired(token.expires_at):
        raise HTTPException(400, "Reset token invalid or expired")
    db.get(User, token.user_id).password_hash = hasher.hash(data.password)
    token.used = True
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == token.user_id)
        .values(revoked=True)
    )
    return {"message": "Password updated; sign in again"}


@router.get("/oauth/{provider}")
def oauth(provider: str):
    if provider not in {"google", "microsoft"}:
        raise HTTPException(404)
    raise HTTPException(503, "OAuth provider is not configured")
