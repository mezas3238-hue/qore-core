from datetime import UTC, datetime
from types import SimpleNamespace

from scripts.cibo_phase22_v3_vt31_fresh_runner import (
    FROZEN_SOURCE_GIT_SHA,
    _frozen_market_evidence_tuple,
)


def test_vt31_recovery_adapter_restores_exact_six_field_abi() -> None:
    checked = datetime(2015, 10, 19, tzinfo=UTC)
    source = SimpleNamespace(
        series=("BAR_SENTINEL",),
        fingerprint="f" * 64,
        last_closed_at=checked,
        collector_git_sha="a" * 40,
        provider_symbol="USTEC",
    )

    adapted = _frozen_market_evidence_tuple(source)

    assert len(adapted) == 6
    assert adapted[0] == ("BAR_SENTINEL",)
    assert adapted[1] == "PHASE22_V3_HISTORICAL_ACCOUNT_NOT_CLAIMED"
    assert adapted[2] == "f" * 64
    assert adapted[3] == checked
    assert adapted[4] == "a" * 40
    assert adapted[5] == "USTEC"


def test_vt31_recovery_keeps_frozen_methodology_commit() -> None:
    assert FROZEN_SOURCE_GIT_SHA == (
        "cac38ed14f20e066536910145027426fd23f5939"
    )
