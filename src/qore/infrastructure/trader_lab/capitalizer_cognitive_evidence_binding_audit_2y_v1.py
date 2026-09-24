"""Decision-time cognitive evidence-binding audit for Capitalizer 2Y.

This lab does not change strategy admission, entry, stop, target, MAX3, cognition,
or runtime. It answers a narrower prerequisite question: for each frozen 1R
control trade, which cognitive facts can be reconstructed from evidence that
already existed at or before the entry timestamp?

The audit deliberately distinguishes:
- source/microstructure evidence that can be joined to the causal arbitration ledger;
- baseline-path portfolio exposure and day/session journey state that can be
  reconstructed chronologically;
- cognitive layers that remain unbound because no admissible evidence artifact
  has been supplied.

Current-trade outcomes are never used to decide whether a cognitive field is bound.
Previously closed trade outcomes may contribute to day-journey state because they
were already known at the later candidate's decision time.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerExposurePosition,
    CapitalizerSide,
    factor_exposures,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_EVIDENCE_BINDING_AUDIT_2Y_V1"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"
SOURCE_ARBITRATION_RUN_ID = 35929691710
SOURCE_ARBITRATION_SHA = "93fcd53cca8b56ab9a3de596881435a5573b65ac"
EXPECTED_TARGET_R = Decimal("1.00")

_CAUSAL_TIMESTAMP_FIELDS = (
    "h1_sweep_at",
    "m5_closeback_at",
    "m3_mss_at",
    "m1_ob_opened_at",
    "m1_fvg_confirmed_at",
)

_REQUIRED_CONTROL_FIELDS = (
    "symbol",
    "session",
    "operating_date",
    "side",
    "h1_open",
    "h1_deadline",
    "entry_at",
    "exit_at",
    "target_r",
    "realized_gross_r",
    "exit_reason",
    "provenance",
)

_REQUIRED_ARBITRATION_FIELDS = (
    "symbol",
    "session",
    "operating_date",
    "side",
    "h1_open",
    "entry_at",
    "liquidity_source",
    "liquidity_kind",
    "h1_sweep_at",
    "m5_closeback_at",
    "m3_mss_at",
    "m1_ob_opened_at",
    "m1_fvg_confirmed_at",
    "m1_ob_fvg_overlap",
    "entry_mode",
)


@dataclass(frozen=True, slots=True)
class CognitiveEvidenceBindingRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    entry_at: str
    provenance: str
    source_microstructure_bound: bool
    source_timestamps_causal: bool
    evidence_provenance_complete: bool
    microstructure_observations: tuple[str, ...]
    baseline_portfolio_exposure_bound: bool
    baseline_active_positions: int
    baseline_shared_factors: tuple[str, ...]
    baseline_same_direction_factors: tuple[str, ...]
    baseline_opposing_direction_factors: tuple[str, ...]
    day_session_journey_bound: bool
    prior_closed_trades_today: int
    prior_realized_r_today: str
    completed_prior_sessions: tuple[str, ...]
    prior_same_session_selected: int
    session_slots_remaining_before: int
    baseline_slot_state_bound: bool
    failure_state_fingerprint_bound: bool
    destination_intelligence_bound: bool
    regime_intelligence_bound: bool
    execution_quality_bound: bool
    perception_integrity_bound: bool
    full_opportunity_competition_bound: bool
    current_outcome_visible_to_binding: bool
    full_master_cognitive_frame_ready: bool


def _aware(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


def _required(row: dict[str, Any], fields: tuple[str, ...], *, label: str) -> None:
    missing = tuple(field for field in fields if field not in row)
    if missing:
        raise ValueError(f"{label} missing required fields: {missing}")


def _control_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["symbol"]),
        str(row["session"]),
        str(row["operating_date"]),
        str(row["h1_open"]),
        str(row["entry_at"]),
    )


def _load_control(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob("capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl")
    )
    if len(paths) != 1:
        raise ValueError(f"binding audit requires one frozen 1R ledger, got {len(paths)}")

    rows: list[dict[str, Any]] = []
    keys: set[tuple[str, str, str, str, str]] = set()
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("control trade row must be a JSON object")
            _required(raw, _REQUIRED_CONTROL_FIELDS, label="control trade")
            if Decimal(str(raw["target_r"])) != EXPECTED_TARGET_R:
                raise ValueError("binding audit received non-1R control trade")
            if str(raw["symbol"]) != str(raw["symbol"]).upper():
                raise ValueError("control symbol must be uppercase")
            CapitalizerSession(str(raw["session"]))
            CapitalizerSide(str(raw["side"]))
            entry = _aware(raw["entry_at"], field_name="entry_at")
            exit_at = _aware(raw["exit_at"], field_name="exit_at")
            if exit_at < entry:
                raise ValueError("control trade exit cannot precede entry")
            key = _control_key(raw)
            if key in keys:
                raise ValueError("control trade identity must be unique")
            keys.add(key)
            rows.append(raw)

    return tuple(
        sorted(
            rows,
            key=lambda row: (_aware(row["entry_at"], field_name="entry_at"), str(row["symbol"])),
        )
    )


def _load_arbitration(root: Path) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-"
            "no-rearm-closeback-arbitration-2y-v1-trades.jsonl"
        )
    )
    if not paths:
        raise ValueError("binding audit found no arbitration trade ledgers")

    result: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("arbitration trade row must be a JSON object")
                _required(raw, _REQUIRED_ARBITRATION_FIELDS, label="arbitration trade")
                key = _control_key(raw)
                if key in result:
                    raise ValueError("arbitration trade identity must be unique")
                result[key] = raw
    return result


def _causal_microstructure(
    arbitration: dict[str, Any] | None,
    *,
    entry_at: datetime,
) -> tuple[bool, bool, tuple[str, ...]]:
    if arbitration is None:
        return False, False, ()

    causal = True
    for field in _CAUSAL_TIMESTAMP_FIELDS:
        observed = _aware(arbitration[field], field_name=field)
        if observed > entry_at:
            causal = False

    if not causal:
        return False, False, ()

    observations = (
        f"LIQUIDITY_SOURCE:{arbitration['liquidity_source']}",
        f"LIQUIDITY_KIND:{arbitration['liquidity_kind']}",
        f"ENTRY_MODE:{arbitration['entry_mode']}",
        "M1_OB_FVG_OVERLAP:"
        + ("TRUE" if bool(arbitration["m1_ob_fvg_overlap"]) else "FALSE"),
        f"H1_SWEEP_AT:{arbitration['h1_sweep_at']}",
        f"M5_CLOSEBACK_AT:{arbitration['m5_closeback_at']}",
        f"M3_MSS_AT:{arbitration['m3_mss_at']}",
        f"M1_FVG_CONFIRMED_AT:{arbitration['m1_fvg_confirmed_at']}",
    )
    return True, True, observations


def _unit_position(row: dict[str, Any]) -> CapitalizerExposurePosition:
    return CapitalizerExposurePosition(
        symbol=str(row["symbol"]),
        side=CapitalizerSide(str(row["side"])),
        risk_r=Decimal("1"),
    )


def _factor_relation(
    candidate: dict[str, Any],
    active: tuple[dict[str, Any], ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    if not active:
        return (), (), ()

    candidate_factors = {
        item.factor: item for item in factor_exposures((_unit_position(candidate),))
    }
    active_factors = {
        item.factor: item
        for item in factor_exposures(tuple(_unit_position(row) for row in active))
    }

    shared: list[str] = []
    same: list[str] = []
    opposing: list[str] = []
    for factor, candidate_exposure in candidate_factors.items():
        active_exposure = active_factors.get(factor)
        if active_exposure is None or active_exposure.gross_r == 0:
            continue
        shared.append(factor)
        if active_exposure.net_r == 0:
            continue
        if active_exposure.net_r * candidate_exposure.net_r > 0:
            same.append(factor)
        else:
            opposing.append(factor)
    return tuple(sorted(shared)), tuple(sorted(same)), tuple(sorted(opposing))


def _completed_prior_sessions(session: str) -> tuple[str, ...]:
    current = CapitalizerSession(session)
    if current is CapitalizerSession.ASIA:
        return ()
    if current is CapitalizerSession.LONDON:
        return (CapitalizerSession.ASIA.value,)
    return (CapitalizerSession.ASIA.value, CapitalizerSession.LONDON.value)


def _build_rows(
    control: tuple[dict[str, Any], ...],
    arbitration: dict[tuple[str, str, str, str, str], dict[str, Any]],
) -> tuple[CognitiveEvidenceBindingRow, ...]:
    result: list[CognitiveEvidenceBindingRow] = []

    for current in control:
        entry_at = _aware(current["entry_at"], field_name="entry_at")
        operating_date = str(current["operating_date"])
        session = str(current["session"])

        prior_entered = tuple(
            row
            for row in control
            if str(row["operating_date"]) == operating_date
            and _aware(row["entry_at"], field_name="entry_at") < entry_at
        )
        active = tuple(
            row
            for row in prior_entered
            if _aware(row["exit_at"], field_name="exit_at") > entry_at
        )
        closed = tuple(
            row
            for row in prior_entered
            if _aware(row["exit_at"], field_name="exit_at") <= entry_at
        )
        prior_same_session = sum(
            str(row["session"]) == session for row in prior_entered
        )
        slots_remaining = max(
            0,
            MAX_EXECUTIONS_PER_SESSION - prior_same_session,
        )

        shared, same, opposing = _factor_relation(current, active)
        source = arbitration.get(_control_key(current))
        source_bound, timestamps_causal, observations = _causal_microstructure(
            source,
            entry_at=entry_at,
        )

        prior_realized = sum(
            (Decimal(str(row["realized_gross_r"])) for row in closed),
            Decimal("0"),
        )

        full_ready = all(
            (
                source_bound,
                timestamps_causal,
                False,  # failure-state fingerprint
                False,  # destination intelligence
                False,  # regime intelligence
                False,  # execution-quality evidence
                False,  # perception-integrity evidence
                False,  # full opportunity competition
            )
        )

        result.append(
            CognitiveEvidenceBindingRow(
                symbol=str(current["symbol"]),
                session=session,
                operating_date=operating_date,
                side=str(current["side"]),
                h1_open=str(current["h1_open"]),
                entry_at=str(current["entry_at"]),
                provenance=str(current["provenance"]),
                source_microstructure_bound=source_bound,
                source_timestamps_causal=timestamps_causal,
                evidence_provenance_complete=source_bound and timestamps_causal,
                microstructure_observations=observations,
                baseline_portfolio_exposure_bound=True,
                baseline_active_positions=len(active),
                baseline_shared_factors=shared,
                baseline_same_direction_factors=same,
                baseline_opposing_direction_factors=opposing,
                day_session_journey_bound=True,
                prior_closed_trades_today=len(closed),
                prior_realized_r_today=str(prior_realized),
                completed_prior_sessions=_completed_prior_sessions(session),
                prior_same_session_selected=prior_same_session,
                session_slots_remaining_before=slots_remaining,
                baseline_slot_state_bound=True,
                failure_state_fingerprint_bound=False,
                destination_intelligence_bound=False,
                regime_intelligence_bound=False,
                execution_quality_bound=False,
                perception_integrity_bound=False,
                full_opportunity_competition_bound=False,
                current_outcome_visible_to_binding=False,
                full_master_cognitive_frame_ready=full_ready,
            )
        )

    return tuple(result)


def build_report(
    target_root: Path,
    arbitration_root: Path,
) -> tuple[dict[str, Any], tuple[CognitiveEvidenceBindingRow, ...]]:
    control = _load_control(target_root)
    arbitration = _load_arbitration(arbitration_root)
    rows = _build_rows(control, arbitration)

    provenance = Counter(str(row["provenance"]) for row in control)
    micro_by_provenance: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.source_microstructure_bound:
            micro_by_provenance[row.provenance] += 1

    stop_keys = {
        _control_key(row)
        for row in control
        if str(row["exit_reason"]) == "STOP"
    }
    row_by_key = {
        (
            row.symbol,
            row.session,
            row.operating_date,
            row.h1_open,
            row.entry_at,
        ): row
        for row in rows
    }
    bound_stops = sum(
        bool(row_by_key[key].source_microstructure_bound)
        for key in stop_keys
    )
    future_violations = sum(
        row.source_microstructure_bound and not row.source_timestamps_causal
        for row in rows
    )
    minimum_context = sum(
        row.source_microstructure_bound
        and row.baseline_portfolio_exposure_bound
        and row.day_session_journey_bound
        for row in rows
    )

    report = {
        "identity": IDENTITY,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "source_arbitration_run_id": SOURCE_ARBITRATION_RUN_ID,
        "source_arbitration_sha": SOURCE_ARBITRATION_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "control_trades": len(control),
        "control_stops": len(stop_keys),
        "source_provenance_counts": dict(sorted(provenance.items())),
        "binding_coverage": {
            "source_microstructure": sum(
                row.source_microstructure_bound for row in rows
            ),
            "evidence_provenance_complete": sum(
                row.evidence_provenance_complete for row in rows
            ),
            "baseline_portfolio_exposure": sum(
                row.baseline_portfolio_exposure_bound for row in rows
            ),
            "day_session_journey": sum(
                row.day_session_journey_bound for row in rows
            ),
            "baseline_slot_state": sum(
                row.baseline_slot_state_bound for row in rows
            ),
            "failure_state_fingerprint": sum(
                row.failure_state_fingerprint_bound for row in rows
            ),
            "destination_intelligence": sum(
                row.destination_intelligence_bound for row in rows
            ),
            "regime_intelligence": sum(
                row.regime_intelligence_bound for row in rows
            ),
            "execution_quality": sum(
                row.execution_quality_bound for row in rows
            ),
            "perception_integrity": sum(
                row.perception_integrity_bound for row in rows
            ),
            "full_opportunity_competition": sum(
                row.full_opportunity_competition_bound for row in rows
            ),
            "full_master_cognitive_frame_ready": sum(
                row.full_master_cognitive_frame_ready for row in rows
            ),
        },
        "microstructure_bound_by_provenance": dict(
            sorted(micro_by_provenance.items())
        ),
        "stop_label_coverage": {
            "stops": len(stop_keys),
            "source_microstructure_bound": bound_stops,
            "source_microstructure_unbound": len(stop_keys) - bound_stops,
        },
        "minimum_causal_context_bound_trades": minimum_context,
        "future_evidence_violations": future_violations,
        "current_trade_outcome_used_for_binding": False,
        "prior_closed_outcomes_used_for_day_journey": True,
        "control_outcome_labels_used_for_post_binding_audit": True,
        "baseline_path_reconstruction_only": True,
        "counterfactual_cognitive_path_recomputed": False,
        "unit_r_factor_exposure_proxy": True,
        "missing_evidence_fabricated": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "blocking_layers": (
            "FAILURE_STATE_FINGERPRINT",
            "DESTINATION_INTELLIGENCE",
            "REGIME_INTELLIGENCE",
            "EXECUTION_QUALITY",
            "PERCEPTION_INTEGRITY",
            "FULL_OPPORTUNITY_COMPETITION",
        ),
        "next_phase": "BIND_MISSING_CAUSAL_LAYERS_BEFORE_COGNITIVE_ENFORCEMENT",
    }
    return report, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[CognitiveEvidenceBindingRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-evidence-binding-audit-2y-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-evidence-binding-audit-2y-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target_root", type=Path)
    parser.add_argument("arbitration_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, rows = build_report(args.target_root, args.arbitration_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
