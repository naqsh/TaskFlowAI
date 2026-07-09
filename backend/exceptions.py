"""Application exception hierarchy with structured error responses."""

from typing import Any


class AppException(Exception):
    """Base application exception with HTTP status and structured payload."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class NotFoundError(AppException):
    status_code = 404
    error_code = "not_found"


class ValidationError(AppException):
    status_code = 422
    error_code = "validation_error"


class UnauthorizedError(AppException):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppException):
    status_code = 403
    error_code = "forbidden"


class ConflictError(AppException):
    status_code = 409
    error_code = "conflict"


class RateLimitError(AppException):
    status_code = 429
    error_code = "rate_limit_exceeded"


class UnsupportedMediaTypeError(AppException):
    status_code = 415
    error_code = "unsupported_media_type"


class PayloadTooLargeError(AppException):
    status_code = 413
    error_code = "payload_too_large"


class ConsentRequiredError(AppException):
    status_code = 403
    error_code = "consent_required"


class ServiceUnavailableError(AppException):
    status_code = 503
    error_code = "service_unavailable"
