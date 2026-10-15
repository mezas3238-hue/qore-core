"""VT31 source-cognitive Trader Lab shared-source Ultra Fast runner invariants."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import vt31_method_cog_lab_batch_ultrafast_20261015 as batch


def test_canonical_sha256_full_casebook_order_independent():
    left = {"cases": [{"day": "2025-01-15", "state": "WAIT"}], "count": 483}
    right = {"count": 483, "cases": [{"state": "WAIT", "day": "2025-01-15"}]}
    assert batch.canonical_sha256(left) == batch.canonical_sha256(right)
    assert batch.canonical_sha256(left) != batch.canonical_sha256(
        {"count": 483, "cases": [{"day": "2025-01-15", "state": "READY"}]}
    )


def test_canonical_json_rejects_nonfinite_unstable_values():
    with pytest.raises(ValueError, match="Out of range float"):
        batch.canonical_sha256({"case": float("nan")})


def test_source_reuse_requires_identical_preloaded_reference(monkeypatch):
    frozen = {"observed_days_total": 775, "source_classifications": [{"a": 1}]}
    groups = {"2025-07-01": {}}
    monkeypatch.setattr(batch, "_GROUPS", groups)
    monkeypatch.setattr(batch, "_CENSUS", frozen)
    duplicate = batch.frozen_census_copy(groups)
    assert duplicate == frozen and duplicate is not frozen
    duplicate["source_classifications"][0]["a"] = 2
    assert frozen["source_classifications"][0]["a"] == 1
    with pytest.raises(ValueError, match="UNAUTHENTICATED"):
        batch.frozen_census_copy(dict(groups))


def test_worker_rejects_missing_source(monkeypatch):
    monkeypatch.setattr(batch, "_GROUPS", None)
    monkeypatch.setattr(batch, "_CENSUS", None)
    with pytest.raises(ValueError, match="PRELOAD"):
        batch._fork_gate("M3_WAIT_V2")


def test_gate_list_exact_and_nothing_related_to_economics():
    assert set(batch.SOURCES) == {
        "M3_WAIT_V2", "M4_FAMILY", "M5_CAUSATIVE_SWING",
        "M4_M5_AUTHOR_COMPONENTS",
    }
    assert all(path.startswith("scripts.vt31_") for path, _, _ in batch.SOURCES.values())
    with pytest.raises(ValueError, match="UNKNOWN_COGNITIVE_GATE"):
        batch._call("ECONOMIC_PF_OR_SIZING", {}, reuse_census=False)


def test_override_original_census_only_inside_cognitive_witness(monkeypatch):
    group = {"fixed": object()}
    frozen = {"observed_days_total": 775}
    original_census = lambda requested: {"original": requested}
    module = SimpleNamespace()
    module.run_census = original_census
    def audit_483(source):
        got = module.run_census(source)
        assert got == frozen
        got["observed_days_total"] = 1
        return {"cases_frozen": 483, "trader_certified": False}
    module.audit_483 = audit_483
    monkeypatch.setattr(batch, "_GROUPS", group)
    monkeypatch.setattr(batch, "_CENSUS", frozen)
    monkeypatch.setattr(batch.importlib, "import_module", lambda name: module)
    returned = batch._call("M5_CAUSATIVE_SWING", group, reuse_census=True)
    assert returned["cases_frozen"] == 483
    assert frozen["observed_days_total"] == 775
    assert module.run_census is original_census


def test_cannot_claim_483_with_false_certification(monkeypatch):
    mod = SimpleNamespace(
        run_census=lambda _: {},
        audit_483=lambda _: {"cases_frozen": 483, "trader_certified": True},
    )
    monkeypatch.setattr(batch.importlib, "import_module", lambda name: mod)
    with pytest.raises(AssertionError, match="FALSE_CERTIFIED"):
        batch._call("M5_CAUSATIVE_SWING", {}, reuse_census=False)


def test_worker_count_is_bounded_before_source_touched(tmp_path):
    with pytest.raises(ValueError, match="BOUNDED_FORK"):
        batch.run_replay_batch(
            tmp_path/"missing-market.json", parity=False, workers=8,
        )
