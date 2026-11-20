"""Process-wide dependency-injection registry for the MOAlmanac service.

The running server registers a concrete :class:`MoaService` at startup; tests inject
one over the bundled snapshot. An unregistered service is an ``internal`` error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from moalmanac_link.exceptions import InternalError

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from moalmanac_link.service import MoaService

_service: MoaService | None = None


def get_moa_service() -> MoaService:
    """Return the registered :class:`MoaService` or raise ``InternalError``."""
    if _service is None:
        raise InternalError(
            "MOAlmanac service is not initialised; the server must register it at startup.",
            recovery_action="switch_tool",
        )
    return _service


def set_moa_service(service: MoaService | None) -> None:
    """Register (or clear) the process-wide service. Used by the server and tests."""
    global _service
    _service = service
