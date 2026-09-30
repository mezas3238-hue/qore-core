"""Cognitive evidence-binding audit V2 for the frozen Capitalizer 2Y 1R set.

V1 proved that 840/948 frozen trades can be joined to the causal arbitration
microstructure ledger, while baseline portfolio exposure, session/day journey,
and slot state can be reconstructed for all 948 trades.

V2 does not mutate V1. It consumes the frozen V1 artifact and binds the two
remaining source families from their original outcome-free research artifacts:
- PROTECTED_SWING_GEOMETRY_RESCUE
- WAIT_REJECTED_PARALLEL_REARM

No strategy, cognition, entry, stop, target, MAX3, or runtime rule is changed.
Every source timestamp must be at or before the frozen entry timestamp.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as v1,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_EVIDENCE_BINDING_AUDIT_2Y_V2"
SOURCE_BINDING_V1_RUN_ID = 36065178049
SOURCE_BINDING_V1_SHA = "a36f2401b395ae1c80d9307b197e01e01343c5be"
SOURCE_STOP_ATLAS_RUN_ID = 35863455539
SOURCE_STOP_ATLAS_SHA = "d55b380fe9be21cee59023c2d6ed4cb3ebc84052"
SOURCE_REARM_RUN_ID = 35934425045
SOURCE_REARM_SHA = "3fca2555ca6161817809f58c07c9606d8f187cbe"

PROTECTED = "PROTECTED_SWING_GEOMETRY_RESCUE"
REARM = "WAIT_REJECTED_PARALLEL_REARM"
ARBITRATION = "CAUSAL_ARBITRATION_BASE"


def _binding_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["symbol"]),
        str(row["session"]),
        str(row["operating_date"]),
        str(row["h1_open"]),
        str(row["entry_at"]),
    )


def _recovery_key(
    *,
    symbol: object,
    operating_date: object,
    side: object,
    entry_at: object,
) -> tuple[str, str, str, str]:
    return (
        str(symbol),
        str(operating_date),
        str(side),
        str(entry_at),
    )


def _load_v1(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v1.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v1-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("V2 requires exactly one frozen V1 binding artifact")

    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("V1 binding report must be a JSON object")
    if report.get("identity") != v1.IDENTITY:
        raise ValueError("unexpected V1 binding identity")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("V2 cannot consume V1 with future-evidence violations")
    if bool(report.get("missing_evidence_fabricated", True)):
        raise ValueError("V2 cannot consume fabricated V1 evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("V1 binding row must be a JSON object")
            rows.append(raw)
    if len(rows) != int(report.get("control_trades", -1)):
        raise ValueError("V1 binding row count mismatch")
    return report, tuple(rows)


def _load_protected(root: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-"
            "stop-invalid-geometry-atlas-2y-v1-rows.jsonl"
        )
    )
    if not paths:
        raise ValueError("V2 found no protected-swing source ledgers")

    result: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("protected source row must be object")
                if raw.get("protected_at_mss_stop_valid") is not True:
                    continue
                key = _recovery_key(
                    symbol=raw.get("symbol"),
                    operating_date=raw.get("operating_date"),
                    side=raw.get("side"),
                    entry_at=raw.get("final_fill_at"),
                )
                if key in result:
                    raise ValueError("protected source identity must be unique")
                result[key] = raw
    return result


def _load_rearm(root: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait-rejected-"
            "parallel-rearm-atlas-2y-v1-rows.jsonl"
        )
    )
    if not paths:
        raise ValueError("V2 found no parallel-rearm source ledgers")

    result: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("rearm source row must be object")
                if raw.get("terminal_stage") != "REARM_EXECUTABLE":
                    continue
                if raw.get("stop_valid") is not True:
                    continue
                fill = raw.get("new_fill_at")
                if not isinstance(fill, str):
                    raise ValueError("executable rearm requires new_fill_at")
                key = _recovery_key(
                    symbol=raw.get("symbol"),
                    operating_date=raw.get("operating_date"),
                    side=raw.get("side"),
                    entry_at=fill,
                )
                if key in result:
                    raise ValueError("rearm source identity must be unique")
                result[key] = raw
    return result


def _timestamps_causal(
    values: tuple[object, ...],
    *,
    entry_at: datetime,
) -> bool:
    for raw in values:
        if raw is None:
            continue
        observed = v1._aware(raw, field_name="source_timestamp")
        if observed > entry_at:
            return False
    return True


def _protected_binding(
    source: dict[str, Any] | None,
    *,
    entry_at: datetime,
) -> tuple[bool, bool, tuple[str, ...]]:
    if source is None:
        return False, False, ()
    if str(source.get("final_fill_at")) != entry_at.isoformat():
        return True, False, ()

    protected_at = source.get("protected_at_mss_confirmed_at")
    causal = _timestamps_causal(
        (
            source.get("source_first_mss_at"),
            source.get("displacement_opened_at"),
            protected_at,
            source.get("final_fill_at"),
        ),
        entry_at=entry_at,
    )
    if not causal:
        return True, False, ()

    observations = (
        "RECOVERY_SOURCE:PROTECTED_SWING_GEOMETRY_RESCUE",
        f"SOURCE_FIRST_MSS_AT:{source.get('source_first_mss_at')}",
        f"DISPLACEMENT_OPENED_AT:{source.get('displacement_opened_at')}",
        f"ENTRY_MODE:{source.get('final_entry_mode')}",
        "M1_OB_FVG_OVERLAP:"
        + ("TRUE" if bool(source.get("ob_fvg_overlap")) else "FALSE"),
        "WAIT5_ARMED:" + ("TRUE" if bool(source.get("wait5_armed")) else "FALSE"),
        f"PROTECTED_AT_MSS_CONFIRMED_AT:{protected_at}",
        "PROTECTED_AT_MSS_STOP_VALID:TRUE",
    )
    return True, True, observations


def _rearm_binding(
    source: dict[str, Any] | None,
    *,
    entry_at: datetime,
) -> tuple[bool, bool, tuple[str, ...]]:
    if source is None:
        return False, False, ()
    if str(source.get("new_fill_at")) != entry_at.isoformat():
        return True, False, ()

    required = (
        source.get("original_mss_at"),
        source.get("rearm_eligible_at"),
        source.get("new_raid_at"),
        source.get("new_closeback_at"),
        source.get("new_mss_at"),
        source.get("new_fvg_at"),
        source.get("new_fill_at"),
    )
    if any(value is None for value in required):
        return True, False, ()
    causal = _timestamps_causal(required, entry_at=entry_at)
    if not causal:
        return True, False, ()

    observations = (
        "RECOVERY_SOURCE:WAIT_REJECTED_PARALLEL_REARM",
        f"ORIGINAL_TERMINAL_REASON:{source.get('original_terminal_reason')}",
        f"ORIGINAL_MSS_AT:{source.get('original_mss_at')}",
        f"REARM_ELIGIBLE_AT:{source.get('rearm_eligible_at')}",
        f"NEW_RAID_AT:{source.get('new_raid_at')}",
        f"NEW_CLOSEBACK_AT:{source.get('new_closeback_at')}",
        f"NEW_MSS_AT:{source.get('new_mss_at')}",
        f"NEW_FVG_AT:{source.get('new_fvg_at')}",
        f"NEW_FILL_AT:{source.get('new_fill_at')}",
        "REARM_STOP_VALID:TRUE",
    )
    return True, True, observations


def _enrich_rows(
    v1_rows: tuple[dict[str, Any], ...],
    control: tuple[dict[str, Any], ...],
    protected: dict[tuple[str, str, str, str], dict[str, Any]],
    rearm: dict[tuple[str, str, str, str], dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    control_by_key = {_binding_key(row): row for row in control}
    if len(control_by_key) != len(control):
        raise ValueError("control identity is not unique")

    result: list[dict[str, Any]] = []
    for row in v1_rows:
        key = _binding_key(row)
        control_row = control_by_key.get(key)
        if control_row is None:
            raise ValueError("V1 binding row missing frozen control counterpart")
        provenance = str(control_row["provenance"])
        entry_at = v1._aware(control_row["entry_at"], field_name="entry_at")

        source_match = bool(row.get("source_microstructure_match_found"))
        source_bound = bool(row.get("source_microstructure_bound"))
        causal = bool(row.get("source_timestamps_causal"))
        observations = tuple(str(item) for item in row.get("microstructure_observations", ()))
        family = ARBITRATION if source_bound else None

        recovery_key = _recovery_key(
            symbol=control_row["symbol"],
            operating_date=control_row["operating_date"],
            side=control_row["side"],
            entry_at=control_row["entry_at"],
        )

        if provenance == PROTECTED and not source_bound:
            match, causal, observations = _protected_binding(
                protected.get(recovery_key),
                entry_at=entry_at,
            )
            source_match = match
            source_bound = match and causal
            family = PROTECTED if source_bound else None
        elif provenance == REARM and not source_bound:
            match, causal, observations = _rearm_binding(
                rearm.get(recovery_key),
                entry_at=entry_at,
            )
            source_match = match
            source_bound = match and causal
            family = REARM if source_bound else None

        enriched = dict(row)
        enriched.update(
            {
                "source_microstructure_match_found": source_match,
                "source_microstructure_bound": source_bound,
                "source_timestamps_causal": causal,
                "evidence_provenance_complete": source_bound and causal,
                "microstructure_observations": list(observations),
                "source_microstructure_family": family,
                "full_master_cognitive_frame_ready": False,
                "current_outcome_visible_to_binding": False,
            }
        )
        result.append(enriched)

    return tuple(result)


def build_report(
    v1_root: Path,
    target_root: Path,
    protected_root: Path,
    rearm_root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    v1_report, v1_rows = _load_v1(v1_root)
    control = v1._load_control(target_root)
    if len(control) != len(v1_rows):
        raise ValueError("V2 control/V1 population mismatch")

    protected = _load_protected(protected_root)
    rearm = _load_rearm(rearm_root)
    rows = _enrich_rows(v1_rows, control, protected, rearm)

    source_family = Counter(
        str(row["source_microstructure_family"])
        for row in rows
        if row.get("source_microstructure_bound")
    )
    provenance = Counter(str(row["provenance"]) for row in control)

    stop_keys = {
        v1._control_key(row)
        for row in control
        if str(row["exit_reason"]) == "STOP"
    }
    row_by_key = {_binding_key(row): row for row in rows}
    bound_stops = sum(
        bool(row_by_key[key].get("source_microstructure_bound"))
        for key in stop_keys
    )

    future_violations = sum(
        bool(row.get("source_microstructure_match_found"))
        and not bool(row.get("source_timestamps_causal"))
        for row in rows
    )
    source_bound = sum(bool(row.get("source_microstructure_bound")) for row in rows)
    evidence_bound = sum(bool(row.get("evidence_provenance_complete")) for row in rows)

    report = {
        "identity": IDENTITY,
        "source_binding_v1_run_id": SOURCE_BINDING_V1_RUN_ID,
        "source_binding_v1_sha": SOURCE_BINDING_V1_SHA,
        "source_stop_atlas_run_id": SOURCE_STOP_ATLAS_RUN_ID,
        "source_stop_atlas_sha": SOURCE_STOP_ATLAS_SHA,
        "source_rearm_run_id": SOURCE_REARM_RUN_ID,
        "source_rearm_sha": SOURCE_REARM_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "control_trades": len(control),
        "control_stops": len(stop_keys),
        "source_provenance_counts": dict(sorted(provenance.items())),
        "source_microstructure_family_counts": dict(sorted(source_family.items())),
        "binding_coverage": {
            "source_microstructure": source_bound,
            "evidence_provenance_complete": evidence_bound,
            "baseline_portfolio_exposure": sum(
                bool(row.get("baseline_portfolio_exposure_bound")) for row in rows
            ),
            "day_session_journey": sum(
                bool(row.get("day_session_journey_bound")) for row in rows
            ),
            "baseline_slot_state": sum(
                bool(row.get("baseline_slot_state_bound")) for row in rows
            ),
            "failure_state_fingerprint": 0,
            "destination_intelligence": 0,
            "regime_intelligence": 0,
            "execution_quality": 0,
            "perception_integrity": 0,
            "full_opportunity_competition": 0,
            "full_master_cognitive_frame_ready": 0,
        },
        "delta_vs_v1": {
            "source_microstructure": source_bound
            - int(v1_report["binding_coverage"]["source_microstructure"]),
            "evidence_provenance_complete": evidence_bound
            - int(v1_report["binding_coverage"]["evidence_provenance_complete"]),
        },
        "stop_label_coverage": {
            "stops": len(stop_keys),
            "source_microstructure_bound": bound_stops,
            "source_microstructure_unbound": len(stop_keys) - bound_stops,
        },
        "future_evidence_violations": future_violations,
        "current_trade_outcome_used_for_binding": False,
        "prior_closed_outcomes_used_for_day_journey": True,
        "control_outcome_labels_used_for_post_binding_audit": True,
        "baseline_path_reconstruction_only": True,
        "counterfactual_cognitive_path_recomputed": False,
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
        "remaining_blocking_layers": (
            "FAILURE_STATE_FINGERPRINT",
            "DESTINATION_INTELLIGENCE",
            "REGIME_INTELLIGENCE",
            "EXECUTION_QUALITY",
            "PERCEPTION_INTEGRITY",
            "FULL_OPPORTUNITY_COMPETITION",
        ),
        "next_phase": "BIND_REMAINING_COGNITIVE_LAYERS_BEFORE_ENFORCEMENT",
    }
    return report, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[dict[str, Any], ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-evidence-binding-audit-2y-v2.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("v1_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("protected_root", type=Path)
    parser.add_argument("rearm_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, rows = build_report(
        args.v1_root,
        args.target_root,
        args.protected_root,
        args.rearm_root,
    )
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
