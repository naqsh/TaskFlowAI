"""Authentication service — registration, login, JWT, refresh rotation."""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import RefreshToken, User, Workspace, WorkspaceMember, WorkspaceRole
from backend.exceptions import ConflictError, UnauthorizedError
from backend.repositories.refresh_token_repository import RefreshTokenRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.services.audit_service import AuditService
from backend.settings import Settings


@dataclass(frozen=True)
class TokenPair:
    """Issued access and refresh tokens."""

    access_token: str
    refresh_token: str
    expires_in: int


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    salt = bcrypt.gensalt()
    hashed: bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def hash_refresh_token(token: str) -> str:
    """Return a SHA-256 hex digest of a refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token."""
    return secrets.token_urlsafe(48)


def _slugify_email(email: str) -> str:
    local = email.split("@", maxsplit=1)[0].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", local).strip("-")
    return slug or "workspace"


class AuthService:
    """Handles user authentication lifecycle."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._audit = AuditService()

    def _create_access_token(
        self,
        *,
        user_id: UUID,
        email: str,
        workspace_id: UUID | None,
    ) -> tuple[str, int]:
        expires_minutes = self._settings.jwt_access_token_expire_minutes
        expires_delta = timedelta(minutes=expires_minutes)
        expires_at = datetime.now(UTC) + expires_delta
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "exp": expires_at,
        }
        if workspace_id is not None:
            payload["workspace_id"] = str(workspace_id)
        token: str = jwt.encode(payload, self._settings.jwt_secret_key, algorithm="HS256")
        return token, int(expires_delta.total_seconds())

    async def _issue_token_pair(
        self,
        user: User,
        *,
        workspace_id: UUID | None,
    ) -> TokenPair:
        access_token, expires_in = self._create_access_token(
            user_id=user.id,
            email=user.email,
            workspace_id=workspace_id,
        )
        refresh_token = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(
            days=self._settings.jwt_refresh_token_expire_days
        )
        record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
        )
        await self._refresh_tokens.add(record)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    async def _primary_workspace_id(self, user_id: UUID) -> UUID | None:
        stmt = (
            select(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.created_at)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        member = result.scalar_one_or_none()
        return member.workspace_id if member else None

    async def register(self, payload: RegisterRequest) -> tuple[UserResponse, TokenPair]:
        """Register a new user with a default workspace."""
        email = payload.email.lower()
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError("Email already registered")

        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name.strip(),
        )
        await self._users.add(user)

        base_slug = _slugify_email(email)
        workspace = Workspace(
            name=f"{payload.full_name.strip()}'s Workspace",
            slug=f"{base_slug}-{uuid4().hex[:8]}",
        )
        self._session.add(workspace)
        await self._session.flush()

        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.ADMIN,
        )
        self._session.add(membership)
        await self._session.flush()

        tokens = await self._issue_token_pair(user, workspace_id=workspace.id)
        profile = UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            workspace_id=workspace.id,
        )

        await self._audit.log_event(
            actor_id=user.id,
            action="user.register",
            resource_type="user",
            resource_id=user.id,
            metadata={
                "workspace_id": str(workspace.id),
            },
            workspace_id=workspace.id,
        )
        return profile, tokens

    async def login(self, payload: LoginRequest) -> tuple[UserResponse, TokenPair]:
        """Authenticate a user and issue tokens."""
        user = await self._users.get_by_email(payload.email.lower())
        if user is None or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")

        workspace_id = await self._primary_workspace_id(user.id)
        tokens = await self._issue_token_pair(user, workspace_id=workspace_id)
        profile = UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            workspace_id=workspace_id,
        )

        await self._audit.log_event(
            actor_id=user.id,
            action="user.login",
            resource_type="user",
            resource_id=user.id,
            metadata={
                "workspace_id": str(workspace_id) if workspace_id is not None else None,
            },
            workspace_id=workspace_id,
        )
        return profile, tokens

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Rotate refresh token and issue a new access/refresh pair."""
        token_hash = hash_refresh_token(refresh_token)
        record = await self._refresh_tokens.get_by_hash(token_hash)
        now = datetime.now(UTC)

        if record is None:
            raise UnauthorizedError("Invalid refresh token")
        if record.revoked_at is not None:
            await self._refresh_tokens.revoke_all_for_user(record.user_id)
            raise UnauthorizedError("Refresh token reuse detected")
        if record.expires_at <= now:
            raise UnauthorizedError("Refresh token expired")

        user = await self._users.get_active_by_id(record.user_id)
        if user is None:
            raise UnauthorizedError("User not found or inactive")

        workspace_id = await self._primary_workspace_id(user.id)
        new_tokens = await self._issue_token_pair(user, workspace_id=workspace_id)
        new_record = await self._refresh_tokens.get_by_hash(
            hash_refresh_token(new_tokens.refresh_token)
        )
        replaced_by_id = new_record.id if new_record is not None else None
        await self._refresh_tokens.revoke(record, replaced_by_id=replaced_by_id)
        return new_tokens

    async def logout(self, refresh_token: str) -> None:
        """Revoke a refresh token on logout."""
        token_hash = hash_refresh_token(refresh_token)
        record = await self._refresh_tokens.get_by_hash(token_hash)
        if record is not None and record.revoked_at is None:
            await self._refresh_tokens.revoke(record)

    async def get_profile(self, user: User) -> UserResponse:
        """Build a user profile response."""
        workspace_id = await self._primary_workspace_id(user.id)
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            workspace_id=workspace_id,
        )

    def token_response(self, tokens: TokenPair) -> TokenResponse:
        """Convert an internal token pair to an API response."""
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        )

    def create_expired_access_token(self, user_id: UUID, email: str) -> str:
        """Create an expired access token (testing helper)."""
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        }
        return jwt.encode(payload, self._settings.jwt_secret_key, algorithm="HS256")  # type: ignore[no-any-return]
