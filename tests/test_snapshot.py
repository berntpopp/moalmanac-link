"""Schema guard: a moalmanac-db schema change or an altered snapshot fails loudly."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
from typing import Any

import pytest

from moalmanac_link import snapshot

ROOT = pathlib.Path(__file__).parents[1]
_spec = importlib.util.spec_from_file_location("build_snapshot", ROOT / "scripts/build_snapshot.py")
assert _spec and _spec.loader
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def _minimal_tables() -> dict[str, Any]:
    """One row per table carrying exactly the required fields."""
    return {
        name: (dict.fromkeys(fields) if name == "about" else [dict.fromkeys(fields)])
        for name, fields in build.REQUIRED.items()
    }


def test_build_schema_guard_accepts_the_required_shape() -> None:
    build.check_schema(_minimal_tables())


@pytest.mark.parametrize(
    ("table", "field"), [("statements", "indication_id"), ("about", "release")]
)
def test_build_schema_guard_names_the_missing_field(table: str, field: str) -> None:
    tables = _minimal_tables()
    row = tables[table] if table == "about" else tables[table][0]
    del row[field]
    with pytest.raises(build.SchemaError, match=f"{table}.*missing {field}"):
        build.check_schema(tables)


def test_build_schema_guard_names_a_missing_table() -> None:
    tables = _minimal_tables()
    del tables["propositions"]
    with pytest.raises(build.SchemaError, match="propositions: table missing"):
        build.check_schema(tables)


def test_loaded_snapshot_passes_and_matches_provenance() -> None:
    data = snapshot.load()
    prov = snapshot.provenance()
    assert prov["data_version"] == build.TAG and prov["source_commit"] == build.COMMIT
    assert prov["counts"]["approvals"] == len(data["approvals"])
    assert prov["license"].startswith("CC-BY-4.0")


def test_runtime_guard_rejects_a_row_missing_a_field() -> None:
    data = copy.deepcopy(snapshot.load())
    del data["approvals"][0]["label"]["version_date"]
    with pytest.raises(snapshot.SnapshotError, match="version_date"):
        snapshot.check(data)


def test_runtime_guard_rejects_an_altered_file(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "moalmanac_snapshot.json").write_text(json.dumps({"schema_version": 1}))
    (tmp_path / "moalmanac_provenance.json").write_text(
        (snapshot.DATA / "moalmanac_provenance.json").read_text()
    )
    monkeypatch.setattr(snapshot, "DATA", tmp_path)
    snapshot.provenance.cache_clear()
    snapshot.load.cache_clear()
    try:
        with pytest.raises(snapshot.SnapshotError, match="sha256"):
            snapshot.load()
    finally:
        snapshot.provenance.cache_clear()
        snapshot.load.cache_clear()
