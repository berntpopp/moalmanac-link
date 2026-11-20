"""The bundled MOAlmanac release snapshot: load once, verify, and fail loudly if it is wrong.

Built by ``scripts/build_snapshot.py`` from a pinned moalmanac-db release (CC BY 4.0); nothing
is fetched at runtime. The loader checks the file's sha256 against its provenance record and
that every row carries the fields the service reads, so a stale or hand-edited snapshot stops
the server at startup instead of answering with silently missing fields.
"""

from __future__ import annotations

import hashlib
import json
from functools import cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data"
SCHEMA_VERSION = 1
APPROVAL_FIELDS = frozenset(
    {
        "statement_id", "indication_id", "agency", "status", "first_agency_date",
        "biomarkers", "biomarker_types", "genes", "disease", "therapies", "therapy_operator",
        "predicate", "strength", "direction", "label",
    }
)  # fmt: skip
LABEL_FIELDS = frozenset(
    {"document_id", "name", "brand", "generic", "version_date", "regulatory_id"}
)


class SnapshotError(RuntimeError):
    """The bundled snapshot is missing, altered, or not the schema this code reads."""


@cache
def provenance() -> dict[str, Any]:
    """Release tag, commit, DOI, licence, attribution and sha256s of the snapshot."""
    return dict(json.loads((DATA / "moalmanac_provenance.json").read_text()))


def data_version() -> str:
    """The upstream release's own version string (``v.YYYY-MM-DD``)."""
    return str(provenance()["data_version"])


def check(snapshot: dict[str, Any]) -> None:
    """Schema guard over a loaded snapshot; raises :class:`SnapshotError` on any gap."""
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise SnapshotError(f"snapshot schema_version is not {SCHEMA_VERSION}")
    for key in ("approvals", "indications", "biomarkers", "genes", "agencies"):
        if not snapshot.get(key):
            raise SnapshotError(f"snapshot has no {key!r}")
    for row in snapshot["approvals"]:
        missing = (APPROVAL_FIELDS - set(row)) or (LABEL_FIELDS - set(row["label"]))
        if missing:
            raise SnapshotError(f"approval {row.get('statement_id')}: missing {sorted(missing)}")


@cache
def load() -> dict[str, Any]:
    """The verified snapshot (cached for the life of the process)."""
    blob = (DATA / provenance()["derived_file"]).read_bytes()
    if hashlib.sha256(blob).hexdigest() != provenance()["derived_sha256"]:
        raise SnapshotError("snapshot sha256 does not match moalmanac_provenance.json")
    snapshot: dict[str, Any] = json.loads(blob)
    check(snapshot)
    return snapshot
