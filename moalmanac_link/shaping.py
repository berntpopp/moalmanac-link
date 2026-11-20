"""Pure shapers: pagination, untrusted-text fencing and response_mode projection."""

from __future__ import annotations

from typing import Any

from moalmanac_link.mcp.untrusted_content import fence_untrusted_text

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

#: Fleet response_mode canon (Response-Envelope Standard v1 §3); compact is the default.
RESPONSE_MODES = ("minimal", "compact", "standard", "full")


def fence(raw: Any, record_id: str) -> dict[str, Any] | None:
    """Fence one upstream prose value (``None``/empty stays ``None``)."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    return fence_untrusted_text(raw, source="moalmanac", record_id=record_id).model_dump(
        mode="json"
    )


def page_block(*, total: int, returned: int, limit: int, offset: int) -> dict[str, Any]:
    """Uniform pagination block; ``total`` is the exact derived count."""
    truncated = offset + returned < total
    return {
        "total": total,
        "returned": returned,
        "limit": limit,
        "offset": offset,
        "truncated": truncated,
        "next_offset": offset + returned if truncated else None,
    }
