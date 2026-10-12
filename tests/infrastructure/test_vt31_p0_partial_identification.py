"""Pure arithmetic gates for VT31 P0 paired uncertainty (synthetic fixtures)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/vt31_p0_partial_identification_from_ledger.py"
SPEC = importlib.util.spec_from_file_location("vt31_p0_partial_bounds", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(
    a: str, b: str, *, a_hit: bool = False, b_hit: bool = False,
) -> dict[str, object]:
    return {
        "A_class": a, "B_class": b,
        "A_original_clean_CE_quote_side_reachable_1p60": a_hit,
        "B_original_clean_CE_quote_side_reachable_1p60": b_hit,
    }


def test_matched_known_b_only_contact_has_exact_plus_one() -> None:
    s = MODULE._summary([row("INVALIDATED", "VALID_CE", b_hit=True)])
    assert s["paired_lower_diff"] == s["paired_upper_diff"] == 1
    assert s["B_only_known"] == 1


def test_matched_known_a_only_contact_has_exact_minus_one() -> None:
    s = MODULE._summary([row("VALID_CE", "INVALIDATED", a_hit=True)])
    assert s["paired_lower_diff"] == s["paired_upper_diff"] == -1
    assert s["A_only_known"] == 1


def test_matching_both_known_contacts_does_not_invent_advantage() -> None:
    s = MODULE._summary([row("VALID_CE", "VALID_CE", a_hit=True, b_hit=True)])
    assert s["paired_lower_diff"] == s["paired_upper_diff"] == 0
    assert s["both_known"] == 1


def test_b_known_a_indeterminate_is_zero_to_plus_one() -> None:
    s = MODULE._summary([row("INDETERMINATE", "VALID_CE", b_hit=True)])
    assert s["paired_lower_diff"] == 0
    assert s["paired_upper_diff"] == 1


def test_a_known_b_indeterminate_is_minus_one_to_zero() -> None:
    s = MODULE._summary([row("VALID_CE", "INDETERMINATE", a_hit=True)])
    assert s["paired_lower_diff"] == -1
    assert s["paired_upper_diff"] == 0


def test_both_unknown_is_minus_one_to_plus_one() -> None:
    s = MODULE._summary([row("INDETERMINATE", "INDETERMINATE")])
    assert (s["paired_lower_diff"], s["paired_upper_diff"]) == (-1, 1)
    assert s["both_unknown"] == 1


def test_valid_ce_without_spread_side_evidence_does_not_count() -> None:
    s = MODULE._summary([row("VALID_CE", "VALID_CE")])
    assert s["A_known"] == s["B_known"] == 0
    assert s["A_max"] == s["B_max"] == 0


def test_canonical_example_with_missingness_can_reverse_observed_sign() -> None:
    rows = [
        row("INVALIDATED", "VALID_CE", b_hit=True),
        row("INDETERMINATE", "INVALIDATED"),
        row("INDETERMINATE", "INDETERMINATE"),
    ]
    s = MODULE._summary(rows)
    assert s["known_diff"] == 1
    assert s["paired_lower_diff"] == -1
    assert s["paired_upper_diff"] == 2
    assert s["preregistered_5pp_guaranteed_over_missingness"] is False


@pytest.mark.parametrize("bad", [
    row("INDETERMINATE", "VALID_CE", a_hit=True),
    row("INVALIDATED", "VALID_CE", a_hit=True),
    row("VALID_CE", "INDETERMINATE", b_hit=True),
    row("VALID_CE", "INVALIDATED", b_hit=True),
    row("made_up", "VALID_CE"),
])
def test_clean_ce_cannot_coexist_with_nonvalid_source_class(bad: dict) -> None:
    with pytest.raises(ValueError):
        MODULE._summary([bad])


def test_truthy_numeric_one_is_not_accepted_as_boolean() -> None:
    r = row("VALID_CE", "VALID_CE")
    r["B_original_clean_CE_quote_side_reachable_1p60"] = 1
    with pytest.raises(ValueError, match="nonboolean"):
        MODULE._summary([r])


def test_missing_record_rejected() -> None:
    with pytest.raises(ValueError, match="missing source"):
        MODULE._summary([])


def test_incorrect_source_or_fabricated_broker_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="not the original"):
        MODULE.analyze({"base": "old VT31 R2", "market_M1": 1059784})
    with pytest.raises(ValueError, match="split or altered"):
        MODULE.analyze({
            "base": "VT31_NAS100_OWNER_3Y_BASE_001",
            "market_M1": 1059784,
            "registered_trader_count": 2,
        })
