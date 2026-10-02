"""Outcome-blind terminal receipt contract for the T11 V3 provider experiment.

Frozen before consuming the V3 terminal artifact.  The contract accepts only
the exact post-containment V3 execution lineage and derives the terminal
recommendation mechanically from the six frozen symbol validations.

Architect 2 does not mutate the canonical CIBO ledger and grants no productive
authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from qore.infrastructure.cibo_arch2_t11_experiment_plan import (
    T11_MARKET_IMPACT_EXPERIMENT_PLAN,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
    REQUIRED_SYMBOLS,
    T11_NONLINEAR_INPUT_FREEZE,
)
from qore.infrastructure.cibo_arch2_t11_post_containment_cycle_v3 import (
    CYCLE_ID,
)
from qore.infrastructure.cibo_arch2_t11_v3_retry_claim import (
    FAILED_RUN_ID,
    RETRY_TOKEN,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

V3_CANONICAL_RUN_ID = 36948511045
V3_CANONICAL_RUN_ATTEMPT = 1
V3_CANONICAL_HEAD_SHA = "7b9f6e6c6b4cf385f6df0c87d217b47e6cd12069"
V3_CANCELLED_DUPLICATE_RUN_ID = 36948554909

COMPLETED = "COMPLETED_AND_PROVEN"
FALSIFIED = "FALSIFIED_AND_CLOSED"


@dataclass(frozen=True, slots=True)
class T11V3TerminalReceipt:
    cycle_id: str
    report_sha256: str
    protocol_sha256: str
    experiment_plan_sha256: str
    canonical_run_id: int
    canonical_run_attempt: int
    canonical_head_sha: str
    precursor_failed_run_id: int
    retry_token: str
    cancelled_duplicate_run_id: int
    symbol_count: int
    episode_count: int
    child_entry_count: int
    four_of_four_by_symbol: tuple[tuple[str, bool], ...]
    market_impact_model_ready: bool
    terminal_recommendation: str
    broker_mutation_performed: bool
    all_created_positions_closed: bool
    holdout_outcomes_used: bool
    phase22_v2_consumed: bool
    canonical_ledger_modified: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.cycle_id != CYCLE_ID:
            raise CiboCapitalManagementError("T11 V3 receipt cycle drift")
        for value, name in (
            (self.report_sha256, "report_sha256"),
            (self.protocol_sha256, "protocol_sha256"),
            (self.experiment_plan_sha256, "experiment_plan_sha256"),
        ):
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCapitalManagementError(
                    f"T11 V3 receipt {name} invalid"
                )
        if self.protocol_sha256 != T11_NONLINEAR_INPUT_FREEZE.fingerprint():
            raise CiboCapitalManagementError("T11 V3 protocol lineage drift")
        if self.experiment_plan_sha256 != T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint():
            raise CiboCapitalManagementError("T11 V3 experiment-plan lineage drift")
        if (
            self.canonical_run_id != V3_CANONICAL_RUN_ID
            or self.canonical_run_attempt != V3_CANONICAL_RUN_ATTEMPT
            or self.canonical_head_sha != V3_CANONICAL_HEAD_SHA
        ):
            raise CiboCapitalManagementError("T11 V3 canonical run drift")
        if (
            self.precursor_failed_run_id != FAILED_RUN_ID
            or self.retry_token != RETRY_TOKEN
            or self.cancelled_duplicate_run_id != V3_CANCELLED_DUPLICATE_RUN_ID
        ):
            raise CiboCapitalManagementError("T11 V3 retry lineage drift")
        if self.symbol_count != len(REQUIRED_SYMBOLS):
            raise CiboCapitalManagementError("T11 V3 symbol count drift")
        if self.episode_count != 144 or self.child_entry_count != 216:
            raise CiboCapitalManagementError("T11 V3 frozen population drift")
        names = tuple(name for name, _ in self.four_of_four_by_symbol)
        if names != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError("T11 V3 symbol ordering drift")
        expected_ready = all(passed for _, passed in self.four_of_four_by_symbol)
        if self.market_impact_model_ready != expected_ready:
            raise CiboCapitalManagementError("T11 V3 readiness drift")
        expected_terminal = COMPLETED if expected_ready else FALSIFIED
        if self.terminal_recommendation != expected_terminal:
            raise CiboCapitalManagementError("T11 V3 disposition drift")
        if not self.broker_mutation_performed or not self.all_created_positions_closed:
            raise CiboCapitalManagementError(
                "T11 V3 terminal receipt requires contained DEMO execution"
            )
        if (
            self.holdout_outcomes_used
            or self.phase22_v2_consumed
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 V3 terminal receipt exceeded Architect-2 authority"
            )


def build_t11_v3_terminal_receipt(
    report: dict[str, Any],
) -> T11V3TerminalReceipt:
    if report.get("schema") != "qore.cibo.arch2.t11.market-impact-demo.v2":
        raise CiboCapitalManagementError("T11 V3 report schema mismatch")

    expected_fields: tuple[tuple[str, object], ...] = (
        ("provider_key", "ctrader-demo"),
        ("environment", "demo"),
        ("deposit_asset", "USD"),
        ("metric", "ADVERSE_REALIZED_ALL_IN_SETTLEMENT_COST_USD"),
        ("minimum_volume_child_orders_only", True),
        ("two_x_children_open_before_close", True),
        ("balanced_long_short_pairs", True),
        ("alternating_level_order", True),
        ("all_created_positions_closed", True),
        ("broker_mutation_performed", True),
        ("holdout_outcomes_used", False),
        ("phase22_v2_consumed", False),
        ("fundednext_touched", False),
        ("vps_touched", False),
        ("live_authorized", False),
        ("real_capital_authorized", False),
        ("canonical_ledger_modified", False),
        ("productive_authority", False),
    )
    for key, expected in expected_fields:
        if report.get(key) != expected:
            raise CiboCapitalManagementError(
                f"T11 V3 report governance drift: {key}"
            )

    if report.get("protocol_frozen_at") != FROZEN_AT.isoformat():
        raise CiboCapitalManagementError("T11 V3 protocol freeze drift")
    if report.get("experiment_plan_sha256") != T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint():
        raise CiboCapitalManagementError("T11 V3 plan fingerprint drift")
    if report.get("episode_count") != 144 or report.get("child_entry_count") != 216:
        raise CiboCapitalManagementError("T11 V3 population drift")
    if (
        str(report.get("run_id", "")) != str(V3_CANONICAL_RUN_ID)
        or str(report.get("run_attempt", "")) != str(V3_CANONICAL_RUN_ATTEMPT)
        or report.get("git_sha") != V3_CANONICAL_HEAD_SHA
    ):
        raise CiboCapitalManagementError("T11 V3 report run lineage drift")

    evaluation = report.get("evaluation")
    if not isinstance(evaluation, dict):
        raise CiboCapitalManagementError("T11 V3 evaluation missing")
    raw_symbols = evaluation.get("symbols")
    if not isinstance(raw_symbols, list):
        raise CiboCapitalManagementError("T11 V3 symbol evaluation missing")

    rows: list[tuple[str, bool]] = []
    for item in raw_symbols:
        if not isinstance(item, dict):
            raise CiboCapitalManagementError("T11 V3 symbol row invalid")
        symbol = item.get("qore_symbol")
        passed = item.get("four_of_four_validated")
        if not isinstance(symbol, str) or type(passed) is not bool:
            raise CiboCapitalManagementError("T11 V3 symbol result invalid")
        rows.append((symbol, passed))
    ordered = tuple(rows)
    if tuple(name for name, _ in ordered) != REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError("T11 V3 symbol surface drift")

    ready = evaluation.get("market_impact_model_ready")
    if type(ready) is not bool:
        raise CiboCapitalManagementError("T11 V3 readiness missing")
    expected_ready = all(passed for _, passed in ordered)
    if ready != expected_ready:
        raise CiboCapitalManagementError("T11 V3 evaluation inconsistency")

    expected_status = (
        "MARKET_IMPACT_MODEL_READY"
        if ready
        else "MARKET_IMPACT_MODEL_FALSIFIED_OR_NOT_READY"
    )
    if report.get("status") != expected_status:
        raise CiboCapitalManagementError("T11 V3 report status drift")

    canonical = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    report_digest = "sha256:" + hashlib.sha256(canonical).hexdigest()

    return T11V3TerminalReceipt(
        cycle_id=CYCLE_ID,
        report_sha256=report_digest,
        protocol_sha256=T11_NONLINEAR_INPUT_FREEZE.fingerprint(),
        experiment_plan_sha256=T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint(),
        canonical_run_id=V3_CANONICAL_RUN_ID,
        canonical_run_attempt=V3_CANONICAL_RUN_ATTEMPT,
        canonical_head_sha=V3_CANONICAL_HEAD_SHA,
        precursor_failed_run_id=FAILED_RUN_ID,
        retry_token=RETRY_TOKEN,
        cancelled_duplicate_run_id=V3_CANCELLED_DUPLICATE_RUN_ID,
        symbol_count=len(ordered),
        episode_count=144,
        child_entry_count=216,
        four_of_four_by_symbol=ordered,
        market_impact_model_ready=ready,
        terminal_recommendation=COMPLETED if ready else FALSIFIED,
        broker_mutation_performed=True,
        all_created_positions_closed=True,
        holdout_outcomes_used=False,
        phase22_v2_consumed=False,
        canonical_ledger_modified=False,
        productive_authority=False,
    )
