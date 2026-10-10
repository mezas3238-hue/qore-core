"""P0 method-first quarantine of A2's ninth CISD forensic ledger.

A2 stores genuinely FUTURE MFE/MAE (+15/+30/+60) beside an AS-OF
sensor signal. The cognitive admission path MUST NEVER see those labels.
This adapter validates the original V49 ID, regime-free causal timestamps,
route classification, and projects an explicit WHITELIST only. It does not
connect to any Master Frame or change trading authority before methodology
adjudication and Candle3 A/B.

Source observations cannot be retroactively classified by how well the
later excursion performed. No implied opposite-direction test is possible.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

IDENTITY = "QORE_SCALPER_A1_CISD_METHODOLOGY_OUTCOME_BLIND_BOUNDARY_V1"

CLASSES = frozenset((
    "MATCHED", "SENSOR_EARLIER_THAN_V49",
    "SAME_TIME_DIFFERENT_FAMILY", "SENSOR_NOT_DETECTED",
    "SENSOR_LATER_THAN_V49",
))
FAMILIES = frozenset(("FVG_RETRACE_CISD", "LIQUIDITY_SWEEP_CISD"))

# Restrict the input envelope explicitly: adding any new B-field fails
# until the field is reviewed for hindsight or post hoc P&L. Future
# excursion objects are required in raw A2 but NEVER read or forwarded.
A2_FIELDS = frozenset((
    "source_opportunity_id", "symbol", "session", "operating_date",
    "original_family", "sensor_family", "original_entry_at",
    "sensor_first_cisd_at", "direction", "h1_basis", "m15_confirmed_at",
    "classification", "sensor_minus_original_minutes",
    "sensor_event_not_necessarily_valid_under_v49_window",
    "original_excur", "sensor_excur", "input_was_a_paper_order",
    "outcome_used_to_admit_trade",
))
EX_POST_FIELDS = frozenset(("original_excur", "sensor_excur"))


def _aware(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() is None:
        raise ValueError("CISD witness timestamp must be timezone-aware")
    return stamp


@dataclass(frozen=True, slots=True)
class A1CISDPredecisionMethodWitness:
    source_opportunity_id: str
    symbol: str
    original_family: str
    sensor_family: str | None
    original_decision_at: str
    first_sensor_cisd_at: str | None
    m15_confirmed_at: str
    original_direction: str
    classification: str
    sensor_is_causal_predecision: bool = True
    opposite_direction_assessed: bool = False
    author_eligible_methodology_adjudicated: bool = False
    contains_future_excursions: bool = False
    enters_master_frame_before_author_review: bool = False
    changes_trade_admission: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            not self.source_opportunity_id
            or self.original_family not in FAMILIES
            or self.classification not in CLASSES
            or self.original_direction not in ("BULLISH", "BEARISH")
        ):
            raise ValueError("invalid original source-method contract")
        decision, thesis = _aware(self.original_decision_at), _aware(
            self.m15_confirmed_at
        )
        if thesis >= decision:
            raise ValueError("M15 setup must precede original M1 entry")
        sensor = (
            _aware(self.first_sensor_cisd_at)
            if self.first_sensor_cisd_at is not None else None
        )
        if sensor is not None and not thesis <= sensor <= decision:
            raise ValueError("sensor cannot use future or pre-thesis candles")
        if self.classification == "MATCHED" and (
            sensor != decision or self.sensor_family != self.original_family
        ):
            raise ValueError("MATCHED contradiction")
        if self.classification == "SENSOR_EARLIER_THAN_V49" and not (
            sensor is not None and sensor < decision
        ):
            raise ValueError("early CISD requires earlier closed candle")
        if self.classification == "SAME_TIME_DIFFERENT_FAMILY" and not (
            sensor == decision and self.sensor_family in FAMILIES
            and self.sensor_family != self.original_family
        ):
            raise ValueError("same-bar route difference invalid")
        if self.classification == "SENSOR_NOT_DETECTED" and (
            sensor is not None or self.sensor_family is not None
        ):
            raise ValueError("missing signal cannot have a sensor time/family")
        if self.classification == "SENSOR_LATER_THAN_V49":
            raise ValueError("sensor horizon after source is not observable as-of")
        if self.sensor_family is not None and self.sensor_family not in FAMILIES:
            raise ValueError("unexpected route family")
        if any((
            not self.sensor_is_causal_predecision,
            self.opposite_direction_assessed,
            self.author_eligible_methodology_adjudicated,
            self.contains_future_excursions,
            self.enters_master_frame_before_author_review,
            self.changes_trade_admission,
            self.live_authorized,
        )):
            raise ValueError("unadjudicated A2 forensic witness has no trade authority")


def sanitize_a2_forensic(
    *,
    original: V49Opportunity,
    raw: Mapping[str, Any],
) -> A1CISDPredecisionMethodWitness:
    """Validate raw A2 original identity, then project an outcome-free subset."""
    if set(raw) != A2_FIELDS:
        raise ValueError("A2 forensic schema changed: strict input review required")
    if not isinstance(raw["original_excur"], list) or not isinstance(
        raw["sensor_excur"], list
    ):
        raise ValueError("expected isolated future labels (never forward them)")
    if raw["input_was_a_paper_order"] is not False or (
        raw["outcome_used_to_admit_trade"] is not False
    ):
        raise ValueError("B forensic cannot contain a paper-order admission")
    sid = source_opportunity_id(original)
    if (
        raw["source_opportunity_id"] != sid
        or raw["symbol"] != original.symbol
        or raw["session"] != original.session
        or raw["operating_date"] != original.operating_date
        or raw["original_family"] != original.m1_trigger_family
        or raw["original_entry_at"] != original.m1_trigger_confirmed_at
        or raw["direction"] != original.h1_state_direction
        or raw["h1_basis"] != original.h1_state_basis
        or raw["m15_confirmed_at"] != original.m15_setup_confirmed_at
    ):
        raise ValueError("A2 row does not identify SAME frozen V49 source")
    sensor_at = raw["sensor_first_cisd_at"]
    family = raw["sensor_family"]
    original_at = _aware(original.m1_trigger_confirmed_at)
    first = _aware(sensor_at) if isinstance(sensor_at, str) else None
    if sensor_at is not None and not isinstance(sensor_at, str):
        raise ValueError("sensor time must be string or null")
    if first is not None and first > original_at:
        raise ValueError("A2 sensor after source is future evidence")
    expected_kind = (
        "SENSOR_NOT_DETECTED" if first is None or family is None
        else "SENSOR_EARLIER_THAN_V49" if first < original_at
        else "SAME_TIME_DIFFERENT_FAMILY"
        if family != original.m1_trigger_family else "MATCHED"
    )
    if raw["classification"] != expected_kind:
        raise ValueError("A2 route classification inconsistent with causal source")
    delta = (
        str((first - original_at).total_seconds() / 60)
        if first is not None else None
    )
    if raw["sensor_minus_original_minutes"] != delta:
        raise ValueError("A2 source-sensor delta contradicts original time")
    if raw["sensor_event_not_necessarily_valid_under_v49_window"] is not (
        expected_kind != "MATCHED"
    ):
        raise ValueError("A2 unknown source-window risk must remain visible")
    return A1CISDPredecisionMethodWitness(
        source_opportunity_id=sid,
        symbol=original.symbol,
        original_family=original.m1_trigger_family,
        sensor_family=family,
        original_decision_at=original.m1_trigger_confirmed_at,
        first_sensor_cisd_at=sensor_at,
        m15_confirmed_at=original.m15_setup_confirmed_at,
        original_direction=original.h1_state_direction,
        classification=expected_kind,
    )


def audit_nine_market_a2_quarantine(
    *, originals_root: Path, forensic_root: Path, output: Path,
) -> dict[str, object]:
    originals_paths = sorted(originals_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    forensic_paths = sorted(forensic_root.rglob("scalper-cisd-381-rows.jsonl"))
    if len(originals_paths) != 9 or len(forensic_paths) != 9:
        raise ValueError("exactly nine original and nine forensic books required")
    originals: dict[str, V49Opportunity] = {}
    for path in originals_paths:
        rows = tuple(
            V49Opportunity(**json.loads(line))
            for line in path.read_text().splitlines() if line.strip()
        )
        if not rows or len({row.symbol for row in rows}) != 1:
            raise ValueError("V49 original market book empty or mixed")
        for row in rows:
            sid = source_opportunity_id(row)
            if sid in originals:
                raise ValueError("original source repeated")
            originals[sid] = row
    if len(originals) != 2876:
        raise ValueError("V49 source population changed")
    reviewed: set[str] = set()
    counts: Counter[str] = Counter()
    markets: set[str] = set()
    output.mkdir(parents=True, exist_ok=True)
    with (output / "scalper-a1-outcome-blind-cisd-witnesses.jsonl").open("w") as f:
        for path in forensic_paths:
            seen_market: str | None = None
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                raw = json.loads(line)
                sid = raw["source_opportunity_id"]
                if sid in reviewed or sid not in originals:
                    raise ValueError("missing/duplicated A2 source ID")
                reviewed.add(sid)
                witness = sanitize_a2_forensic(original=originals[sid], raw=raw)
                if seen_market is None:
                    seen_market = witness.symbol
                elif seen_market != witness.symbol:
                    raise ValueError("forensic market artifact mixes symbols")
                counts[witness.classification] += 1
                counts["FAMILY:" + witness.original_family + "->" +
                       (witness.sensor_family or "NONE")] += 1
                f.write(json.dumps(asdict(witness), sort_keys=True)+"\n")
            if seen_market is None or seen_market in markets:
                raise ValueError("empty/duplicated A2 market artifact")
            markets.add(seen_market)
    if len(reviewed) != 2876 or len(markets) != 9:
        raise ValueError("A2 forensic/source population not fully reconciled")
    if (
        counts["MATCHED"] != 2495
        or counts["SENSOR_EARLIER_THAN_V49"] != 247
        or counts["SAME_TIME_DIFFERENT_FAMILY"] != 134
        or counts["SENSOR_NOT_DETECTED"] != 0
        or counts["SENSOR_LATER_THAN_V49"] != 0
    ):
        raise ValueError("ninth causal source taxonomy changed unexpectedly")
    result: dict[str, object] = {
        "identity": IDENTITY,
        "nine_markets": len(markets),
        "original_opportunities": len(originals),
        "source_ids_reconciled": len(reviewed),
        "counts": dict(sorted(counts.items())),
        "post_entry_mfe_mae_excluded_from_output": True,
        "h1_opposite_direction_not_instrumented": True,
        "source_window_and_route_author_fidelity_unresolved": True,
        "candle3_december_january_ab_unresolved": True,
        "safe_cognitive_admission_unlocked": False,
        "full_nine_market_master_frame_executed": False,
        "trades_changed": 0, "new_entry_vetoes": 0,
        "profit_factor": None, "drawdown_r": None,
        "author_certified": False, "live_authorized": False,
    }
    (output / "scalper-a1-cisd-method-boundary-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n"
    )
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_v49", type=Path)
    p.add_argument("a2_forensic", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    print(json.dumps(audit_nine_market_a2_quarantine(
        originals_root=args.original_v49,
        forensic_root=args.a2_forensic,
        output=args.output,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
