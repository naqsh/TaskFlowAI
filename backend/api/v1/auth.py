"""Authentication API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User
from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from backend.exceptions import RateLimitError
from backend.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.security.rate_limit import InMemoryRateLimiter, get_client_ip
from backend.services.auth_service import AuthService
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

_login_rate_limiter: InMemoryRateLimiter | None = None


def _get_login_rate_limiter(settings: Settings) -> InMemoryRateLimiter:
    global _login_rate_limiter
    if _login_rate_limiter is None:
        _login_rate_limiter = InMemoryRateLimiter(
            max_requests=settings.auth_login_rate_limit,
            window_seconds=settings.auth_login_rate_window_seconds,
        )
    return _login_rate_limiter


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    """Provide an AuthService bound to the request session."""
    return AuthService(session, settings)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Register a new user account."""
    _profile, tokens = await auth_service.register(payload)
    return auth_service.token_response(tokens)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Authenticate with email and password."""
    client_ip = get_client_ip(
        forwarded_for=request.headers.get("X-Forwarded-For"),
        client_host=request.client.host if request.client else None,
    )
    limiter = _get_login_rate_limiter(settings)
    if not limiter.is_allowed(client_ip):
        raise RateLimitError("Too many login attempts. Try again later.")

    _profile, tokens = await auth_service.login(payload)
    return auth_service.token_response(tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Exchange a refresh token for a new token pair."""
    tokens = await auth_service.refresh(payload.refresh_token)
    return auth_service.token_response(tokens)


@router.post("/logout", status_code=204)
async def logout(
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """Invalidate the provided refresh token."""
    await auth_service.logout(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Return the authenticated user's profile."""
    return await auth_service.get_profile(current_user)
