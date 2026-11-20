"""Agent-UX fixes (docs/benchmarks): generic disease words, suggestions, exact vocabulary
names, the all-rows summary and per-row known upstream defects."""

from __future__ import annotations

import pytest

from moalmanac_link.exceptions import InvalidInputError, NotFoundError
from moalmanac_link.service import MoaService
from tests.test_service import _search


async def test_generic_disease_words_do_not_narrow(moa_service: MoaService) -> None:
    # "Invasive Breast Carcinoma" has no word "cancer"; "ovarian cancer" must not shrink to
    # the one disease whose name happens to say "Cancer".
    for organ in ("breast", "ovarian", "colorectal"):
        plain = await _search(moa_service, disease=organ)
        assert (await _search(moa_service, disease=f"{organ} cancer"))["total"] == plain["total"]
    assert (await _search(moa_service, disease="breast carcinoma"))["total"] > 0


async def test_unknown_disease_suggests_vocabulary(moa_service: MoaService) -> None:
    with pytest.raises(NotFoundError) as err:
        await _search(moa_service, gene="KRAS", disease="lung adenocarcinoma")
    assert "Non-Small Cell Lung Cancer" in err.value.extra["suggestions"]
    step = err.value.extra["next_commands"][0]
    assert step["arguments"]["gene"] == "KRAS"
    assert step["arguments"]["disease"] in err.value.extra["suggestions"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [("ALK fusion", "v::ALK"), ("BRCA", "BRCA1 pathogenic variants"), ("NTRK", "v::NTRK1")],
)
async def test_unknown_biomarker_suggests_vocabulary(
    moa_service: MoaService, query: str, expected: str
) -> None:
    with pytest.raises(NotFoundError) as err:
        await _search(moa_service, biomarker=query)
    assert expected in err.value.extra["suggestions"]


async def test_exact_vocabulary_name_matches_only_that_biomarker(moa_service: MoaService) -> None:
    out = await _search(moa_service, biomarker="EGFR activating variants")
    assert out["total"] > 0
    assert all("EGFR activating variants" in row["biomarkers"] for row in out["approvals"])


async def test_therapy_matches_the_label_name(moa_service: MoaService) -> None:
    out = await _search(moa_service, therapy="pemigatinib")
    assert "ind:hse:00889:a" in {row["indication_id"] for row in out["approvals"]}


async def test_summary_counts_every_matched_row(moa_service: MoaService) -> None:
    out = await _search(moa_service, biomarker="BRAF V600E", disease="melanoma", limit=1)
    summary = out["summary"]
    assert summary["agencies"] == {"fda": 11, "ema": 10, "hc": 8, "hse": 6}
    assert "Dabrafenib + Trametinib" in summary["therapies"]
    assert summary["biomarkers"] == {"BRAF p.V600E": 35}


async def test_known_defects_flag_affected_rows(moa_service: MoaService) -> None:
    out = await _search(moa_service, therapy="pemigatinib")
    flagged = {r["indication_id"] for r in out["approvals"] if r.get("known_defects")}
    assert flagged == {"ind:ema:pemazyre:0", "ind:hse:00889:a"}
    ind = await moa_service.get_indication("ind:fda:lumakras:0")
    assert any("accelerated" in note for note in ind["known_defects"])


async def test_bare_product_name_suggests_indication_ids(moa_service: MoaService) -> None:
    with pytest.raises(InvalidInputError) as err:
        await moa_service.get_indication("lumakras")
    ids = {c["arguments"].get("indication_id") for c in err.value.extra["next_commands"]}
    assert "ind:fda:lumakras:0" in ids


async def test_unknown_value_keeps_the_absence_caveat(moa_service: MoaService) -> None:
    with pytest.raises(NotFoundError) as err:
        await _search(moa_service, gene="KRAS", biomarker="G12D")
    assert "not evidence that no approval exists" in err.value.message
