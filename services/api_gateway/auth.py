"""مسیرهای احراز هویت — ورود، ساخت کاربر اولیه، 2FA (اختیاری)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from services.common.db import get_session
from services.common.domain.enums import Role
from services.common.domain.models import User
from services.common.security import (
    TokenData,
    create_access_token,
    current_user,
    hash_password,
    require_role,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_session)]

_DEFAULT_USERS = [
    ("admin", "مدیر سیستم", "admin123", Role.ADMIN),
    ("manager", "مدیر ارشد", "manager123", Role.MANAGER),
    ("engineer", "مهندس بهره‌برداری", "engineer123", Role.ENGINEER),
    ("operator", "اپراتور کنترل‌خانه", "operator123", Role.OPERATOR),
    ("viewer", "بازدیدکننده", "viewer123", Role.VIEWER),
]


def ensure_seed_users(session: Session) -> None:
    if session.exec(select(User)).first():
        return
    for username, full_name, pw, role in _DEFAULT_USERS:
        session.add(User(username=username, full_name=full_name,
                         hashed_password=hash_password(pw), role=role))
    session.commit()


@router.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> dict:
    user = db.exec(select(User).where(User.username == form.username)).first()
    if not user or not verify_password(form.password, user.hashed_password) or not user.is_active:
        raise HTTPException(401, "نام کاربری یا گذرواژه نادرست است")
    token = create_access_token(user.username, user.role, user.full_name)
    return {"access_token": token, "token_type": "bearer", "role": user.role,
            "full_name": user.full_name}


@router.get("/me")
def me(user: Annotated[TokenData, Depends(current_user)]) -> TokenData:
    return user


@router.get("/users")
def list_users(
    db: DbSession, _: Annotated[TokenData, Depends(require_role(Role.ADMIN))]
) -> list[dict]:
    return [
        {"username": u.username, "full_name": u.full_name, "role": u.role, "active": u.is_active}
        for u in db.exec(select(User)).all()
    ]
