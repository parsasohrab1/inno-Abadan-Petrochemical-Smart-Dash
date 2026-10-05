"""JWT authentication + role-based access control (RBAC) — NFR-11, NFR-12."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from services.common.config import get_settings
from services.common.domain.enums import Role

_settings = get_settings()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# access hierarchy — each role also has the access of lower roles
ROLE_RANK: dict[str, int] = {
    Role.VIEWER: 0,
    Role.OPERATOR: 1,
    Role.MAINTENANCE: 2,
    Role.ENGINEER: 3,
    Role.MANAGER: 4,
    Role.ADMIN: 5,
}


class TokenData(BaseModel):
    sub: str
    role: str
    full_name: str | None = None


def hash_password(raw: str) -> str:
    return _pwd.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return _pwd.verify(raw, hashed)


def create_access_token(sub: str, role: str, full_name: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "full_name": full_name,
        "iat": now,
        "exp": now + timedelta(minutes=_settings.access_token_ttl_min),
    }
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_alg)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, _settings.jwt_secret, algorithms=[_settings.jwt_alg])
        return TokenData(sub=payload["sub"], role=payload["role"], full_name=payload.get("full_name"))
    except (JWTError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc


async def current_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> TokenData:
    if not token:
        # in development, allow viewer access without a token (disable in production)
        if _settings.environment == "development":
            return TokenData(sub="dev", role=Role.MANAGER, full_name="Developer")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return decode_token(token)


def require_role(minimum: Role):
    async def _guard(user: Annotated[TokenData, Depends(current_user)]) -> TokenData:
        if ROLE_RANK.get(user.role, -1) < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient access")
        return user

    return _guard
