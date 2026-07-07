"""Authentication and authorization dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User
from backend.dependencies.database import get_db
from backend.exceptions import UnauthorizedError
from backend.repositories.user_repository import UserRepository
from backend.settings import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def decode_access_token(token: str, settings: Settings) -> dict[str, str]:
    """Decode and validate an access JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc

    token_type = payload.get("type")
    if token_type != "access":
        raise UnauthorizedError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Invalid token subject")

    email = payload.get("email")
    if not isinstance(email, str):
        raise UnauthorizedError("Invalid token claims")

    return {
        "sub": sub,
        "email": email,
        "workspace_id": payload.get("workspace_id"),
    }


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Resolve the authenticated user from a bearer access token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing authentication credentials")

    claims = decode_access_token(credentials.credentials, settings)
    user_id = UUID(claims["sub"])
    user_repo = UserRepository(session)
    user = await user_repo.get_active_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User not found or inactive")
    return user


async def get_optional_workspace_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UUID | None:
    """Extract workspace_id claim from JWT without loading the user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        claims = decode_access_token(credentials.credentials, settings)
    except UnauthorizedError:
        return None
    workspace_id = claims.get("workspace_id")
    if workspace_id is None:
        return None
    return UUID(workspace_id)
