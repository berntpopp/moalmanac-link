"""Service tests over the real bundled snapshot: acceptance cases, aliases, honesty, defects."""

from __future__ import annotations

from typing import Any

import pytest

from moalmanac_link.exceptions import InvalidInputError, NotFoundError
from moalmanac_link.service import MoaService


async def _search(svc: MoaService, **kw: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "gene": None,
        "biomarker": None,
        "disease": None,
        "therapy": None,
        "agency": None,
        "biomarker_type": None,
        "limit": 100,
        "offset": 0,
        "response_mode": "compact",
    }
    return await svc.search_approvals(**{**args, **kw})


def _therapies(out: dict[str, Any]) -> set[str]:
    return {t for row in out["approvals"] for t in row["therapies"]}


async def test_kras_g12c_nsclc_returns_sotorasib_and_adagrasib(moa_service: MoaService) -> None:
    out = await _search(moa_service, gene="KRAS", biomarker="G12C", disease="NSCLC")
    assert {"Sotorasib", "Adagrasib"} <= _therapies(out)
    assert out["total"] == len(out["approvals"]) and out["truncated"] is False
    for row in out["approvals"]:
        assert row["agency"] in {"fda", "ema", "hc", "hse", "hpra"}
        assert row["label"]["version_date"] and row["label"]["document_id"]
        assert row["status"] in {"Approved", "Accelerated"}
    assert out["data_version"] == "v.2026-11-05"


async def test_braf_v600e_melanoma_returns_approvals(moa_service: MoaService) -> None:
    out = await _search(moa_service, biomarker="BRAF V600E", disease="melanoma")
    assert out["total"] > 0
    assert {"Dabrafenib", "Vemurafenib"} <= _therapies(out)
    assert {"fda", "ema"} <= {row["agency"] for row in out["approvals"]}


async def test_her2_alias_expands_to_erbb2_both_ways(moa_service: MoaService) -> None:
    erbb2 = await _search(moa_service, gene="ERBB2", disease="breast")
    names = {b for row in erbb2["approvals"] for b in row["biomarkers"]}
    assert "HER2-positive" in names and "ERBB2 amplification" in names
    # A HER2-negative criterion is the absence of the product, not an ERBB2 approval.
    assert not any(row["biomarkers"] == ["HER2-negative"] for row in erbb2["approvals"])
    her2 = await _search(moa_service, gene="her2", disease="breast")
    assert her2["total"] == erbb2["total"] and her2["resolved_from"] == "her2"
    assert her2["query"]["gene"] == "ERBB2"


@pytest.mark.parametrize("form", ["KRAS", "kras", "HGNC:6407", "ENSG00000133703", "NCBIGene:3845"])
async def test_gene_forms_resolve_to_the_symbol(moa_service: MoaService, form: str) -> None:
    out = await _search(moa_service, gene=form)
    assert out["query"]["gene"] == "KRAS" and out["total"] > 0


async def test_unknown_filter_values_are_not_found_naming_the_field(
    moa_service: MoaService,
) -> None:
    for field in ("gene", "biomarker", "disease", "therapy"):
        with pytest.raises(NotFoundError) as err:
            await _search(moa_service, **{field: "zzqx"})
        assert err.value.extra["field"] == field
        message = err.value.message.lower()
        assert "no moalmanac approval found" in message and "not approved" not in message
    with pytest.raises(InvalidInputError):
        await _search(moa_service, gene="BRAF V600E")


async def test_empty_result_says_no_moalmanac_approval_found(moa_service: MoaService) -> None:
    # Known coverage lag: FDA sotorasib + panitumumab for KRAS G12C CRC (Jan 2025) is absent
    # from this release. The answer must say "no MOAlmanac approval found", never "not approved".
    out = await _search(moa_service, therapy="sotorasib", disease="colorectal")
    assert out["total"] == 0 and out["approvals"] == []
    assert out["message"].startswith("No MOAlmanac approval found")
    assert "not approved" not in out["message"].lower()


async def test_known_defect_pemigatinib_is_bound_to_elacestrant_upstream(
    moa_service: MoaService,
) -> None:
    # Upstream defect (documented, not fixed): EMA/HSE pemigatinib cholangiocarcinoma
    # statements point at elacestrant. The label document exposes the contradiction.
    out = await _search(moa_service, therapy="elacestrant", disease="cholangiocarcinoma")
    assert {r["indication_id"] for r in out["approvals"]} == {
        "ind:ema:pemazyre:0",
        "ind:hse:00889:a",
    }
    for row in out["approvals"]:
        assert row["therapies"] == ["Elacestrant"]
        assert "pemigatinib" in (row["label"]["generic"] or row["label"]["name"]).lower()


async def test_known_defect_her2_and_erbb2_are_separate_biomarkers(
    moa_service: MoaService,
) -> None:
    out = await moa_service.list_biomarkers("ERBB2", None, 100, 0)
    names = {b["name"] for b in out["biomarkers"]}
    assert {"HER2-positive", "ERBB2 amplification"} <= names


async def test_total_is_honest_under_paging(moa_service: MoaService) -> None:
    page = await _search(moa_service, gene="BRAF", limit=2)
    assert page["returned"] == 2 and page["total"] > 2 and page["truncated"] is True
    nxt = await _search(moa_service, gene="BRAF", limit=2, offset=page["next_offset"])
    assert nxt["total"] == page["total"]
    assert nxt["approvals"][0]["statement_id"] != page["approvals"][0]["statement_id"]


async def test_agency_filter_and_response_modes(moa_service: MoaService) -> None:
    ema = await _search(moa_service, gene="KRAS", agency="ema")
    assert ema["total"] > 0 and {r["agency"] for r in ema["approvals"]} == {"ema"}
    minimal = await _search(moa_service, gene="KRAS", agency="ema", response_mode="minimal")
    row = minimal["approvals"][0]
    assert {"statement_id", "indication_id", "agency", "therapies", "label"} <= set(row)
    assert "genes" not in row
    full = await _search(moa_service, gene="KRAS", agency="ema", response_mode="full")
    assert full["approvals"][0]["indication"]["kind"] == "untrusted_text"


async def test_get_indication_fences_text_and_lists_history(moa_service: MoaService) -> None:
    out = await moa_service.get_indication("ind:fda:lumakras:0")
    ind = out["indication"]
    assert ind["description"]["kind"] == "untrusted_text"
    assert ind["documents"][0]["regulatory_id"] == "NDA214665"
    assert any(c["date"] == "2021-05-28" for c in ind["contributions"])
    assert [r["therapies"] for r in out["approvals"]] == [["Sotorasib"]]
    with pytest.raises(NotFoundError) as err:
        await moa_service.get_indication("ind:fda:nope:0")
    assert err.value.extra["field"] == "indication_id"


async def test_list_biomarkers_by_type(moa_service: MoaService) -> None:
    out = await moa_service.list_biomarkers(None, "Gene fusion", 100, 0)
    assert out["total"] > 0 and {b["type"] for b in out["biomarkers"]} == {"Gene fusion"}
    assert all(b["approvals"] >= 0 for b in out["biomarkers"])


async def test_short_tokens_match_whole_words_not_substrings(moa_service: MoaService) -> None:
    # "ER" must not hit "HER2-positive" or "ERBB2"; a residue still prefixes (V600 -> V600E).
    er = await _search(moa_service, biomarker="ER positive", limit=100)
    assert all(any(b.startswith("ER ") for b in r["biomarkers"]) for r in er["approvals"])
    with pytest.raises(NotFoundError):
        await _search(moa_service, biomarker="AR")
    v600 = await _search(moa_service, biomarker="BRAF V600", disease="melanoma")
    assert {"BRAF p.V600E", "BRAF p.V600K"} <= {
        b for r in v600["approvals"] for b in r["biomarkers"]
    }


async def test_every_listed_biomarker_count_is_retrievable(moa_service: MoaService) -> None:
    # Issue #4: "KIT p.D816V" listed 2 approvals, but both require its *absence* (imatinib in
    # systemic mastocytosis): the count must be what search_approvals returns for that name,
    # and the absence rows must be reachable as "NOT <name>".
    # ...and the biomarker's own genes and type narrow nothing away, for name and "NOT name".
    for b in moa_service.data["biomarkers"]:
        scopes = [{}, {"biomarker_type": b["type"]}, *({"gene": g} for g in b["genes"])]
        for kw in scopes:
            found = (await _search(moa_service, biomarker=b["name"], limit=1, **kw))["total"]
            absent = await _search(moa_service, biomarker=f"NOT {b['name']}", limit=1, **kw)
            got = (found, absent["total"])
            assert got == (b["approvals"], b["approvals_when_absent"]), (b["name"], kw)
    kit = await _search(moa_service, biomarker="NOT KIT p.D816V")
    assert kit["total"] == 2 and _therapies(kit) == {"Imatinib"}
