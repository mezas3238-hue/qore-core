from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    Phase22PredecisionCandidate,
)
from qore.infrastructure.trader_lab.cibo_three_holdout_admission import (
    cibo_admission_accepts,
    normalize_cibo_admission_rules,
)


def _candidate(
    *,
    trader_id: str = "VT31_NAS100",
    side: str = "long",
    hour: int = 14,
    weekday_day: int = 6,
    context: tuple[tuple[str, str], ...] = (
        ("ctx_session", "new-york"),
        ("reg_h1_body_alignment", "with"),
    ),
) -> Phase22PredecisionCandidate:
    # Bypass the replay-plan constructor only to isolate the admission adapter;
    # canonical replay-plan invariants are independently tested elsewhere.
    candidate = object.__new__(Phase22PredecisionCandidate)
    signal_at = datetime(2022, 1, weekday_day, hour, tzinfo=UTC)
    opportunity = SimpleNamespace(
        decision_context=context,
        side=side,
    )
    projection = SimpleNamespace(
        candidate=SimpleNamespace(
            capital_input=SimpleNamespace(opportunity=opportunity)
        )
    )
    object.__setattr__(candidate, "trader_id", trader_id)
    object.__setattr__(candidate, "signal_at", signal_at)
    object.__setattr__(candidate, "projection", projection)
    return candidate


def test_no_rules_preserve_candidate() -> None:
    assert cibo_admission_accepts(_candidate(), None) is True


def test_clock_and_context_atoms_are_and_semantics() -> None:
    candidate = _candidate(weekday_day=3, hour=14)
    rules = {
        "VT31_NAS100": (
            ("weekday", "0"),
            ("hour_bucket", "14"),
            ("ctx_session", "new-york"),
        )
    }
    assert cibo_admission_accepts(candidate, rules) is True


def test_context_mismatch_rejects_without_changing_trader() -> None:
    candidate = _candidate()
    rules = {
        "VT31_NAS100": (
            ("reg_h1_body_alignment", "opposed"),
        )
    }
    assert cibo_admission_accepts(candidate, rules) is False


@pytest.mark.parametrize(
    "field",
    (
        "qore_symbol",
        "ctx_symbol",
        "trader_id",
        "realized_pnl",
        "exit_reason",
        "future_outcome",
    ),
)
def test_outcome_symbol_and_lineage_fields_are_forbidden(field: str) -> None:
    with pytest.raises(CiboCapitalManagementError):
        normalize_cibo_admission_rules(
            {"VT31_NAS100": ((field, "anything"),)}
        )


def test_unknown_trader_lineage_is_forbidden() -> None:
    with pytest.raises(CiboCapitalManagementError):
        normalize_cibo_admission_rules(
            {"UNKNOWN_TRADER": (("weekday", "0"),)}
        )
