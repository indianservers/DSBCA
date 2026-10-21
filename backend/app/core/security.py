import hashlib
import secrets
import time
import os
import ipaddress
from datetime import timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.core.config import settings
from app.core.database import db_session
from app.models import User, AuthSession, Role, UserRole, RateLimit, now

hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(value, hashed):
    try:
        return hasher.verify(hashed, value)
    except VerificationError:
        return False


def roles(db, user_id):
    return list(
        db.scalars(
            select(Role.name)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
    )


def current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(db_session)
):
    if not token:
        raise HTTPException(401, "Sign in required")
    try:
        payload = jwt.decode(
            token.credentials,
            settings().jwt_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "sid", "type"]},
        )
        if payload["type"] != "access":
            raise ValueError()
        session = db.get(AuthSession, payload["sid"])
        user = db.get(User, payload["sub"])
        if (
            not user
            or user.status != "active"
            or not session
            or session.revoked
            or session.user_id != user.id
            or expired(session.expires_at)
        ):
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Invalid or expired session")


def editor(user=Depends(current_user), db=Depends(db_session)):
    if not set(roles(db, user.id)) & {"content_editor", "admin", "super_admin"}:
        raise HTTPException(403, "Content role required")
    return user


def optional_user(
    token: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(db_session)
):
    return current_user(token, db) if token else None


def administrator(user=Depends(current_user), db=Depends(db_session)):
    if not set(roles(db, user.id)) & {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator role required")
    return user


def issue(db, user, session=None):
    raw = secrets.token_urlsafe(48)
    if session is None:
        session = AuthSession(user_id=user.id)
        db.add(session)
    session.refresh_hash = digest(raw)
    session.expires_at = now() + timedelta(days=settings().refresh_token_expire_days)
    db.flush()
    access = jwt.encode(
        {
            "sub": user.id,
            "sid": session.id,
            "type": "access",
            "exp": now() + timedelta(minutes=settings().access_token_expire_minutes),
        },
        settings().jwt_secret_key,
        algorithm="HS256",
    )
    return {"access_token": access, "refresh_token": raw, "token_type": "bearer"}


def expired(dt):
    return dt.replace(tzinfo=timezone.utc) <= now()


def sensitive(request: Request, db=Depends(db_session)):
    # Database-backed bucket survives serverless process replacement. Never trust a client-supplied forwarding header.
    address = request.client.host if request.client else "unknown"
    if os.environ.get("VERCEL") == "1":
        # Vercel overwrites x-forwarded-for at its ingress. Never trust it on a directly hosted server.
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        try:
            address = str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    key = digest(address + request.url.path)
    window = int(time.time()) // 60
    if db.bind.dialect.name == "postgresql":
        stmt = pg_insert(RateLimit).values(key=key, window=window, count=1)
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={
                "window": window,
                "count": __import__("sqlalchemy").case(
                    (RateLimit.window == window, RateLimit.count + 1), else_=1
                ),
            },
        )
        db.execute(stmt)
        db.flush()
        count = db.get(RateLimit, key, populate_existing=True).count
    else:
        row = db.get(RateLimit, key)
        if row is None:
            row = RateLimit(key=key, window=window, count=1)
            db.add(row)
        elif row.window != window:
            row.window, row.count = window, 1
        else:
            row.count += 1
        count = row.count
    db.commit()  # Failed credentials must still consume quota.
    if count > 15:
        raise HTTPException(429, "Too many requests. Try again in a minute.")
