"""Failure-fingerprint recurrence audit for the frozen Capitalizer 2Y 1R set.

This lab consumes the fully source-bound V2 cognitive evidence ledger and builds
outcome-free fingerprint candidates from categorical facts that existed by entry.
It then asks a separate diagnostic question: when a later candidate arrived, had
an earlier losing trade with the same fingerprint already CLOSED?

The current trade's outcome never participates in fingerprint construction or
repeat detection. Prior closed outcomes are admissible memory because they were
known at the later decision timestamp.

No fingerprint is promoted to runtime enforcement here. Resolution semantics for
an "unresolved" failure state remain an explicit open contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_FAILURE_FINGERPRINT_AUDIT_2Y_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"

_ALLOWED_OBSERVATION_PREFIXES = (
    "LIQUIDITY_SOURCE:",
    "LIQUIDITY_KIND:",
    "ENTRY_MODE:",
    "M1_OB_FVG_OVERLAP:",
    "RECOVERY_SOURCE:",
    "WAIT5_ARMED:",
    "ORIGINAL_TERMINAL_REASON:",
    "PROTECTED_AT_MSS_STOP_VALID:",
    "REARM_STOP_VALID:",
)


@dataclass(frozen=True, slots=True)
class FailureFingerprintAuditRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    provenance: str
    structural_fingerprint: str
    contextual_fingerprint: str
    structural_tokens: tuple[str, ...]
    contextual_tokens: tuple[str, ...]
    prior_closed_loss_same_structural_all_history: int
    prior_closed_loss_same_structural_same_day: int
    prior_closed_loss_same_structural_same_session_day: int
    prior_closed_loss_same_contextual_all_history: int
    prior_closed_loss_same_contextual_same_day: int
    prior_closed_loss_same_contextual_same_session_day: int
    current_exit_reason: str
    current_realized_gross_r: str
    current_outcome_used_to_build_fingerprint: bool = False
    current_outcome_used_to_detect_repeat: bool = False


def _binding_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["symbol"]),
        str(row["session"]),
        str(row["operating_date"]),
        str(row["h1_open"]),
        str(row["entry_at"]),
    )


def _load_binding(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("failure fingerprint audit requires one V2 binding artifact")

    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected V2 binding identity")
    coverage = report.get("binding_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("V2 binding report missing coverage")
    if int(coverage.get("source_microstructure", -1)) != int(
        report.get("control_trades", -2)
    ):
        raise ValueError("failure fingerprint audit requires fully bound source evidence")
    if int(coverage.get("evidence_provenance_complete", -1)) != int(
        report.get("control_trades", -2)
    ):
        raise ValueError("failure fingerprint audit requires complete provenance")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("failure fingerprint audit rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("V2 binding row must be object")
            if raw.get("source_microstructure_bound") is not True:
                raise ValueError("every V2 row must be source-bound")
            rows.append(raw)
    if len(rows) != int(report["control_trades"]):
        raise ValueError("V2 binding population mismatch")
    return report, tuple(rows)


def _hash(tokens: tuple[str, ...]) -> str:
    payload = json.dumps(tokens, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _fingerprint_tokens(
    row: dict[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    observations = tuple(
        str(token)
        for token in row.get("microstructure_observations", ())
        if isinstance(token, str)
        and token.startswith(_ALLOWED_OBSERVATION_PREFIXES)
    )
    structural = tuple(
        sorted(
            {
                f"SYMBOL:{row['symbol']}",
                f"SESSION:{row['session']}",
                f"SIDE:{row['side']}",
                f"PROVENANCE:{row['provenance']}",
                f"SOURCE_FAMILY:{row.get('source_microstructure_family')}",
                *observations,
            }
        )
    )

    shared = ">".join(str(item) for item in row.get("baseline_shared_factors", ()))
    same = ">".join(
        str(item) for item in row.get("baseline_same_direction_factors", ())
    )
    opposing = ">".join(
        str(item) for item in row.get("baseline_opposing_direction_factors", ())
    )
    completed = ">".join(
        str(item) for item in row.get("completed_prior_sessions", ())
    )
    contextual = tuple(
        sorted(
            {
                *structural,
                f"ACTIVE_SHARED_FACTORS:{shared or 'NONE'}",
                f"ACTIVE_SAME_DIRECTION_FACTORS:{same or 'NONE'}",
                f"ACTIVE_OPPOSING_DIRECTION_FACTORS:{opposing or 'NONE'}",
                f"PRIOR_SAME_SESSION_SELECTED:{row.get('prior_same_session_selected')}",
                f"COMPLETED_PRIOR_SESSIONS:{completed or 'NONE'}",
            }
        )
    )
    return structural, contextual


def _metrics(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    return {
        "trades": len(rows),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(str(row["exit_reason"]) == "STOP" for row in rows),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
    }


def build_report(
    binding_root: Path,
    target_root: Path,
) -> tuple[dict[str, Any], tuple[FailureFingerprintAuditRow, ...]]:
    binding_report, binding_rows = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    if len(control) != len(binding_rows):
        raise ValueError("failure fingerprint control/binding population mismatch")

    binding_by_key = {_binding_key(row): row for row in binding_rows}
    control_by_key = {_binding_key(row): row for row in control}
    if binding_by_key.keys() != control_by_key.keys():
        raise ValueError("failure fingerprint control/binding identities differ")

    fingerprints: dict[
        tuple[str, str, str, str, str],
        tuple[tuple[str, ...], tuple[str, ...], str, str],
    ] = {}
    for key, row in binding_by_key.items():
        structural, contextual = _fingerprint_tokens(row)
        if not structural or not contextual:
            raise ValueError("failure fingerprint requires non-empty causal tokens")
        fingerprints[key] = (
            structural,
            contextual,
            _hash(structural),
            _hash(contextual),
        )

    ordered = tuple(
        sorted(
            control,
            key=lambda row: (
                binding_v1._aware(row["entry_at"], field_name="entry_at"),
                str(row["symbol"]),
            ),
        )
    )
    result: list[FailureFingerprintAuditRow] = []

    for current in ordered:
        key = _binding_key(current)
        structural, contextual, structural_hash, contextual_hash = fingerprints[key]
        entry_at = binding_v1._aware(current["entry_at"], field_name="entry_at")

        prior_losses = tuple(
            row
            for row in ordered
            if binding_v1._aware(row["exit_at"], field_name="exit_at") <= entry_at
            and binding_v1._aware(row["entry_at"], field_name="entry_at") < entry_at
            and Decimal(str(row["realized_gross_r"])) < 0
        )

        def same_prior(
            prior: dict[str, Any],
            *,
            contextual_mode: bool,
            same_day: bool,
            same_session_day: bool,
        ) -> bool:
            prior_key = _binding_key(prior)
            prior_hash = fingerprints[prior_key][3 if contextual_mode else 2]
            wanted = contextual_hash if contextual_mode else structural_hash
            if prior_hash != wanted:
                return False
            if same_day and str(prior["operating_date"]) != str(
                current["operating_date"]
            ):
                return False
            if same_session_day and (
                str(prior["operating_date"]) != str(current["operating_date"])
                or str(prior["session"]) != str(current["session"])
            ):
                return False
            return True

        structural_all = sum(
            same_prior(
                prior,
                contextual_mode=False,
                same_day=False,
                same_session_day=False,
            )
            for prior in prior_losses
        )
        structural_day = sum(
            same_prior(
                prior,
                contextual_mode=False,
                same_day=True,
                same_session_day=False,
            )
            for prior in prior_losses
        )
        structural_session = sum(
            same_prior(
                prior,
                contextual_mode=False,
                same_day=False,
                same_session_day=True,
            )
            for prior in prior_losses
        )
        contextual_all = sum(
            same_prior(
                prior,
                contextual_mode=True,
                same_day=False,
                same_session_day=False,
            )
            for prior in prior_losses
        )
        contextual_day = sum(
            same_prior(
                prior,
                contextual_mode=True,
                same_day=True,
                same_session_day=False,
            )
            for prior in prior_losses
        )
        contextual_session = sum(
            same_prior(
                prior,
                contextual_mode=True,
                same_day=False,
                same_session_day=True,
            )
            for prior in prior_losses
        )

        result.append(
            FailureFingerprintAuditRow(
                symbol=str(current["symbol"]),
                session=str(current["session"]),
                operating_date=str(current["operating_date"]),
                side=str(current["side"]),
                entry_at=str(current["entry_at"]),
                exit_at=str(current["exit_at"]),
                provenance=str(current["provenance"]),
                structural_fingerprint=structural_hash,
                contextual_fingerprint=contextual_hash,
                structural_tokens=structural,
                contextual_tokens=contextual,
                prior_closed_loss_same_structural_all_history=structural_all,
                prior_closed_loss_same_structural_same_day=structural_day,
                prior_closed_loss_same_structural_same_session_day=structural_session,
                prior_closed_loss_same_contextual_all_history=contextual_all,
                prior_closed_loss_same_contextual_same_day=contextual_day,
                prior_closed_loss_same_contextual_same_session_day=contextual_session,
                current_exit_reason=str(current["exit_reason"]),
                current_realized_gross_r=str(current["realized_gross_r"]),
            )
        )

    rows = tuple(result)
    def cohort(
        *,
        field: str,
        repeated: bool,
    ) -> tuple[dict[str, Any], ...]:
        selected: list[dict[str, Any]] = []
        for current in ordered:
            audit = next(
                row
                for row in rows
                if row.symbol == str(current["symbol"])
                and row.session == str(current["session"])
                and row.operating_date == str(current["operating_date"])
                and row.entry_at == str(current["entry_at"])
            )
            value = int(getattr(audit, field))
            if (value > 0) is repeated:
                selected.append(current)
        return tuple(selected)

    recurrence = {
        "structural_all_history": sum(
            row.prior_closed_loss_same_structural_all_history > 0 for row in rows
        ),
        "structural_same_day": sum(
            row.prior_closed_loss_same_structural_same_day > 0 for row in rows
        ),
        "structural_same_session_day": sum(
            row.prior_closed_loss_same_structural_same_session_day > 0
            for row in rows
        ),
        "contextual_all_history": sum(
            row.prior_closed_loss_same_contextual_all_history > 0 for row in rows
        ),
        "contextual_same_day": sum(
            row.prior_closed_loss_same_contextual_same_day > 0 for row in rows
        ),
        "contextual_same_session_day": sum(
            row.prior_closed_loss_same_contextual_same_session_day > 0
            for row in rows
        ),
    }

    report = {
        "identity": IDENTITY,
        "source_binding_run_id": SOURCE_BINDING_RUN_ID,
        "source_binding_sha": SOURCE_BINDING_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "control_trades": len(control),
        "fingerprint_candidate_coverage": len(rows),
        "unique_structural_fingerprints": len(
            {row.structural_fingerprint for row in rows}
        ),
        "unique_contextual_fingerprints": len(
            {row.contextual_fingerprint for row in rows}
        ),
        "recurrence_after_prior_closed_loss": recurrence,
        "structural_same_day_repeat_metrics": _metrics(
            cohort(
                field="prior_closed_loss_same_structural_same_day",
                repeated=True,
            )
        ),
        "structural_same_day_nonrepeat_metrics": _metrics(
            cohort(
                field="prior_closed_loss_same_structural_same_day",
                repeated=False,
            )
        ),
        "contextual_same_day_repeat_metrics": _metrics(
            cohort(
                field="prior_closed_loss_same_contextual_same_day",
                repeated=True,
            )
        ),
        "contextual_same_day_nonrepeat_metrics": _metrics(
            cohort(
                field="prior_closed_loss_same_contextual_same_day",
                repeated=False,
            )
        ),
        "allowed_categorical_observation_prefixes": _ALLOWED_OBSERVATION_PREFIXES,
        "timestamps_excluded_from_fingerprint": True,
        "numeric_market_thresholds_added": False,
        "current_outcome_used_to_build_fingerprint": False,
        "current_outcome_used_to_detect_repeat": False,
        "prior_closed_outcomes_used_as_causal_memory": True,
        "current_outcome_used_for_post_audit_metrics": True,
        "runtime_failure_fingerprint_selected": False,
        "loss_memory_resolution_bound": False,
        "unresolved_failure_enforcement_allowed": False,
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
        "binding_v2_control_reproduced": len(control)
        == int(binding_report["control_trades"]),
        "next_phase": "FALSIFY_FINGERPRINT_GRANULARITY_AND_DEFINE_RESOLUTION_SEMANTICS",
    }
    return report, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[FailureFingerprintAuditRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-failure-fingerprint-audit-2y-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-failure-fingerprint-audit-2y-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binding_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, rows = build_report(args.binding_root, args.target_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
