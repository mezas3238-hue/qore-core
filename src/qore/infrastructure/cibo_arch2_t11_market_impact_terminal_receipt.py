"""Terminal receipt contract for Architect-2 T11 market-impact evidence.

Consumes only the frozen DEMO market-impact report.  It does not rerun the
experiment, alter coefficients, or soften fold gates.  A fully valid report
must end in exactly one terminal recommendation:
- COMPLETED_AND_PROVEN when the frozen market-impact model validates 4/4;
- FALSIFIED_AND_CLOSED when the frozen hypothesis fails at least one fold.

This receipt is Architect-2 evidence only.  It never mutates the canonical
ledger and grants no productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from qore.infrastructure.cibo_arch2_t11_post_containment_cycle_v3 import (
    CYCLE_ID,
    T11_POST_CONTAINMENT_CYCLE_V3,
)
from qore.infrastructure.cibo_arch2_t11_v3_retry_claim import (
    T11_V3_TECHNICAL_RETRY_CLAIM,
)
from qore.infrastructure.cibo_arch2_t11_experiment_plan import (
    T11_MARKET_IMPACT_EXPERIMENT_PLAN,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    REQUIRED_SYMBOLS,
    T11_NONLINEAR_INPUT_FREEZE,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

COMPLETED = "COMPLETED_AND_PROVEN"
FALSIFIED = "FALSIFIED_AND_CLOSED"

V3_CANONICAL_RUN_ID = 36948511045
V3_CANONICAL_RUN_ATTEMPT = 1
V3_CANONICAL_HEAD_SHA = "7b9f6e6c6b4cf385f6df0c87d217b47e6cd12069"


@dataclass(frozen=True, slots=True)
class T11MarketImpactTerminalReceipt:
    report_sha256: str
    protocol_sha256: str
    experiment_plan_sha256: str
    execution_cycle_id: str
    canonical_run_id: int
    canonical_run_attempt: int
    canonical_head_sha: str
    symbol_count: int
    episode_count: int
    child_entry_count: int
    four_of_four_by_symbol: tuple[tuple[str, bool], ...]
    market_impact_model_ready: bool
    terminal_recommendation: str
    broker_mutation_performed: bool
    all_created_positions_closed: bool
    phase22_v2_consumed: bool
    canonical_ledger_modified: bool
    productive_authority: bool

    def __post_init__(self) -> None:
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
                    f"T11 terminal receipt {name} invalid"
                )
        if self.execution_cycle_id != CYCLE_ID:
            raise CiboCapitalManagementError(
                "T11 terminal receipt V3 cycle lineage drift"
            )
        if (
            self.canonical_run_id != V3_CANONICAL_RUN_ID
            or self.canonical_run_attempt != V3_CANONICAL_RUN_ATTEMPT
            or self.canonical_head_sha != V3_CANONICAL_HEAD_SHA
        ):
            raise CiboCapitalManagementError(
                "T11 terminal receipt canonical execution lineage drift"
            )
        if self.protocol_sha256 != T11_NONLINEAR_INPUT_FREEZE.fingerprint():
            raise CiboCapitalManagementError(
                "T11 terminal receipt protocol lineage drift"
            )
        if self.experiment_plan_sha256 != T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint():
            raise CiboCapitalManagementError(
                "T11 terminal receipt experiment-plan lineage drift"
            )
        if self.symbol_count != len(REQUIRED_SYMBOLS):
            raise CiboCapitalManagementError(
                "T11 terminal receipt symbol count drift"
            )
        if self.episode_count != 144 or self.child_entry_count != 216:
            raise CiboCapitalManagementError(
                "T11 terminal receipt frozen population drift"
            )
        names = tuple(name for name, _ in self.four_of_four_by_symbol)
        if names != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "T11 terminal receipt exact symbol ordering required"
            )
        expected_ready = all(passed for _, passed in self.four_of_four_by_symbol)
        if self.market_impact_model_ready != expected_ready:
            raise CiboCapitalManagementError(
                "T11 terminal receipt readiness drift"
            )
        expected_terminal = COMPLETED if expected_ready else FALSIFIED
        if self.terminal_recommendation != expected_terminal:
            raise CiboCapitalManagementError(
                "T11 terminal receipt disposition drift"
            )
        if not self.broker_mutation_performed or not self.all_created_positions_closed:
            raise CiboCapitalManagementError(
                "T11 terminal receipt requires contained real DEMO execution"
            )
        if (
            self.phase22_v2_consumed
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 terminal receipt exceeded Architect-2 authority"
            )


def build_t11_market_impact_terminal_receipt(
    report: dict[str, Any],
) -> T11MarketImpactTerminalReceipt:
    if report.get("schema") != "qore.cibo.arch2.t11.market-impact-demo.v2":
        raise CiboCapitalManagementError(
            "T11 terminal receipt report schema mismatch"
        )
    for key, expected in (
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
    ):
        if report.get(key) != expected:
            raise CiboCapitalManagementError(
                f"T11 terminal receipt report governance drift: {key}"
            )
    if report.get("episode_count") != 144 or report.get("child_entry_count") != 216:
        raise CiboCapitalManagementError(
            "T11 terminal receipt report population drift"
        )
    if report.get("experiment_plan_sha256") != (
        T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint()
    ):
        raise CiboCapitalManagementError(
            "T11 terminal receipt report experiment-plan lineage drift"
        )
    if not T11_POST_CONTAINMENT_CYCLE_V3.ready_for_versioned_execution:
        raise CiboCapitalManagementError(
            "T11 terminal receipt V3 base cycle not ready"
        )
    if not T11_V3_TECHNICAL_RETRY_CLAIM.one_retry_allowed:
        raise CiboCapitalManagementError(
            "T11 terminal receipt V3 retry lineage not authorized"
        )
    if (
        str(report.get("run_id", "")) != str(V3_CANONICAL_RUN_ID)
        or str(report.get("run_attempt", "")) != str(V3_CANONICAL_RUN_ATTEMPT)
        or report.get("git_sha") != V3_CANONICAL_HEAD_SHA
    ):
        raise CiboCapitalManagementError(
            "T11 terminal receipt report canonical-run lineage drift"
        )

    evaluation = report.get("evaluation")
    if not isinstance(evaluation, dict):
        raise CiboCapitalManagementError(
            "T11 terminal receipt evaluation missing"
        )
    raw_symbols = evaluation.get("symbols")
    if not isinstance(raw_symbols, list):
        raise CiboCapitalManagementError(
            "T11 terminal receipt symbol evaluation missing"
        )
    rows: list[tuple[str, bool]] = []
    for item in raw_symbols:
        if not isinstance(item, dict):
            raise CiboCapitalManagementError(
                "T11 terminal receipt symbol row invalid"
            )
        symbol = item.get("qore_symbol")
        passed = item.get("four_of_four_validated")
        if not isinstance(symbol, str) or type(passed) is not bool:
            raise CiboCapitalManagementError(
                "T11 terminal receipt symbol result invalid"
            )
        rows.append((symbol, passed))
    ordered = tuple(rows)
    if tuple(name for name, _ in ordered) != REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError(
            "T11 terminal receipt symbol surface drift"
        )

    model_ready = evaluation.get("market_impact_model_ready")
    if type(model_ready) is not bool:
        raise CiboCapitalManagementError(
            "T11 terminal receipt model readiness missing"
        )
    expected_ready = all(passed for _, passed in ordered)
    if model_ready != expected_ready:
        raise CiboCapitalManagementError(
            "T11 terminal receipt model/symbol result drift"
        )

    canonical = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return T11MarketImpactTerminalReceipt(
        report_sha256=digest,
        protocol_sha256=T11_NONLINEAR_INPUT_FREEZE.fingerprint(),
        experiment_plan_sha256=T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint(),
        execution_cycle_id=CYCLE_ID,
        canonical_run_id=V3_CANONICAL_RUN_ID,
        canonical_run_attempt=V3_CANONICAL_RUN_ATTEMPT,
        canonical_head_sha=V3_CANONICAL_HEAD_SHA,
        symbol_count=len(ordered),
        episode_count=144,
        child_entry_count=216,
        four_of_four_by_symbol=ordered,
        market_impact_model_ready=model_ready,
        terminal_recommendation=COMPLETED if model_ready else FALSIFIED,
        broker_mutation_performed=True,
        all_created_positions_closed=True,
        phase22_v2_consumed=False,
        canonical_ledger_modified=False,
        productive_authority=False,
    )
