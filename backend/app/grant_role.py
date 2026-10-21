"""Operator-only bootstrap. Requires database access; never available through HTTP."""

import argparse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import engine
from app.models import User, Role, UserRole, AuditLog

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("role", choices=["content_editor", "admin", "super_admin"])
    args = parser.parse_args()
    with Session(engine()) as db:
        user = db.scalar(select(User).where(User.email == args.email.lower()))
        if not user:
            raise SystemExit(
                "Register the account first. No default privileged accounts are created."
            )
        role = db.scalar(select(Role).where(Role.name == args.role))
        if role is None:
            role = Role(name=args.role)
            db.add(role)
            db.flush()
        if not db.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id, UserRole.role_id == role.id
            )
        ):
            db.add(UserRole(user_id=user.id, role_id=role.id))
            db.add(
                AuditLog(
                    actor_id=user.id,
                    action="operator_grant_" + args.role,
                    resource_id=user.id,
                )
            )
        db.commit()
    print("Role granted. Sign in again to update the app role view.")
