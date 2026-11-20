"""Custom exceptions for moalmanac-link.

Each subclass carries a stable ``error_code`` from the fleet's 6-code wire taxonomy.
The data plane (``snapshot``, ``service``) raises these; the MCP plane
(``mcp/envelope.py::run_mcp_tool``) catches each and converts it into a
**returned** structured error (it reads ``error_code``, ``retryable``,
``recovery_action`` and the ``extra`` dict). Errors are never raised to the
client.
"""

from __future__ import annotations


class MoaError(Exception):
    """Base exception for all moalmanac-link data/client/service errors."""

    error_code = "internal"

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        recovery_action: str | None = None,
        **extra: object,
    ) -> None:
        """Store a human-readable message plus structured envelope hints.

        Args:
            message: Human-readable error message.
            retryable: Whether the caller may retry the same call.
            recovery_action: Optional machine hint (e.g. ``"switch_tool"``).
            **extra: Arbitrary structured fields surfaced on the error envelope
                (stored on ``self.extra``); e.g. ``field``, ``hint``, ``candidates``.
        """
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.recovery_action = recovery_action
        self.extra: dict[str, object] = dict(extra)


class InvalidInputError(MoaError):
    """A tool/service argument failed validation before any lookup ran."""

    error_code = "invalid_input"


class NotFoundError(MoaError):
    """A lookup returned nothing for an otherwise valid identifier."""

    error_code = "not_found"


class AmbiguousQueryError(MoaError):
    """A query matched several records and cannot be resolved unambiguously."""

    error_code = "ambiguous_query"

    def __init__(
        self,
        message: str,
        *,
        candidates: list[object],
        retryable: bool = False,
        recovery_action: str | None = None,
        **extra: object,
    ) -> None:
        """Store the ambiguous candidates so the envelope can surface them."""
        super().__init__(
            message,
            retryable=retryable,
            recovery_action=recovery_action,
            candidates=candidates,
            **extra,
        )
        self.candidates = candidates


class RateLimitedError(MoaError):
    """A call was refused by a rate limit (kept for the fleet's 6-code taxonomy)."""

    error_code = "rate_limited"


class UpstreamUnavailableError(MoaError):
    """A dependency is temporarily unavailable (kept for the fleet's 6-code taxonomy)."""

    error_code = "upstream_unavailable"


class InternalError(MoaError):
    """An unexpected internal error (the catch-all default code)."""

    error_code = "internal"
