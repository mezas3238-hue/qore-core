from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2ce_wait_cohort_alignment as r2ce,
)
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction,
)


@dataclass(frozen=True)
class _HistoryRow:
    key: str
    action: CrtPureReasoningAction


def _decide(_model: object, row: _HistoryRow) -> SimpleNamespace:
    return SimpleNamespace(action=row.action)


def test_preregistration_no_position_size_or_market_transfer() -> None:
    assert r2ce.ARMS == ("CONTROL_ALL", "WAIT_ALIGNED_DIAGNOSTIC")
    assert set(r2ce.REFERENCE) == {"AUDUSD", "USDJPY"}
    assert r2ce.MIN_DENSITY_PER_YEAR == 170.0


def test_training_wait_population_excludes_execute_abstain_and_terminal() -> None:
    rows = (
        _HistoryRow("execute", CrtPureReasoningAction.EXECUTE),
        _HistoryRow("abstain", CrtPureReasoningAction.ABSTAIN),
        _HistoryRow("wait_valid", CrtPureReasoningAction.WAIT),
        _HistoryRow("wait_terminal", CrtPureReasoningAction.WAIT),
    )
    delayed = {
        "execute": SimpleNamespace(delayed_trade=object()),
        "abstain": SimpleNamespace(delayed_trade=object()),
        "wait_valid": SimpleNamespace(delayed_trade=object()),
        "wait_terminal": SimpleNamespace(delayed_trade=None),
    }
    selected, counts = r2ce._wait_training_cohort(
        rows, object(), _decide, delayed, lambda row: row.key
    )
    assert len(selected) == 1
    assert selected[0] is delayed["wait_valid"]
    assert counts["EXECUTE"] == 1
    assert counts["ABSTAIN"] == 1
    assert counts["WAIT"] == 2
    assert counts["WAIT_TERMINAL"] == 1
    assert counts["WAIT_DELAYED_VIABLE"] == 1


def test_unknown_initial_action_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unexpected initial cognitive action"):
        r2ce._initial_action(
            lambda _model, _row: SimpleNamespace(action="HOLD"),
            object(),
            object(),
        )


def test_frozen_published_reproduction_is_a_hard_gate() -> None:
    aud = r2ce._reference_check(
        "AUDUSD",
        {"trades": 1067, "profit_factor": 1.07424084, "total_r": 28.1440},
    )
    assert aud["matches_frozen_publication"] is True
    failed = r2ce._reference_check(
        "USDJPY",
        {"trades": 511, "profit_factor": 0.96, "total_r": -7.96},
    )
    assert failed["matches_frozen_publication"] is False


def test_unsupported_market_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported market"):
        r2ce.run_market("EURUSD")
