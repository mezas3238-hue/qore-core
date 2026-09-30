"""V47-S2D Development-only simple causal admission policy lab.

Policy choice reads outcomes from Development only. Validation/Reserved are
transport diagnostics after the Development policy is frozen in-memory.
Fresh Holdout is never touched.

Frozen in PR #623 comment 5902089060.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_gross_economics_v47_s2b as s2b,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s2 as s2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_winner_preservation_adjudicator_v47 as preservation,
)

IDENTITY = "QORE_CAPITALIZER_V47_S2D_SIMPLE_CAUSAL_ADMISSION_POLICY_LAB"
PREDECLARATION_COMMENT_ID = 5902089060
TARGET_R_BANDS = ("<2R", "[2,4)R", "[4,8)R", "[8,16)R", ">=16R")


@dataclass(frozen=True, slots=True)
class FrozenPair:
    trade: s2b.S2BGrossTrade
    source: s2.S2AdmittedFillRow

    @property
    def trade_id(self) -> str:
        return f"{self.trade.period}|{self.trade.symbol}|{self.trade.entry_at}"


@dataclass(frozen=True, slots=True)
class Policy:
    policy_id: str
    feature: str
    mode: str
    values: tuple[str, ...]
    baseline: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("S2D policy id required")
        if self.baseline:
            if self.policy_id != "KEEP_ALL":
                raise ValueError("S2D baseline id drift")
            return
        if self.mode not in {"INCLUDE", "EXCLUDE"}:
            raise ValueError("S2D policy mode unsupported")
        if not self.feature or not self.values:
            raise ValueError("S2D non-baseline policy requires feature/values")


@dataclass(frozen=True, slots=True)
class PolicyPeriodReport:
    period: str
    trades: int
    metrics: s2b.S2BMetrics
    winner_preservation: preservation.WinnerPreservationReport


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    policy: Policy
    development: PolicyPeriodReport
    development_eligible: bool
    development_eligibility_reasons: tuple[str, ...]


def _trade_id(row: s2b.S2BGrossTrade) -> str:
    return f"{row.period}|{row.symbol}|{row.entry_at}"


def _target_r_band(value: Decimal) -> str:
    if value < Decimal("2"):
        return "<2R"
    if value < Decimal("4"):
        return "[2,4)R"
    if value < Decimal("8"):
        return "[4,8)R"
    if value < Decimal("16"):
        return "[8,16)R"
    return ">=16R"


def _feature(pair: FrozenPair, name: str) -> str:
    if name == "entry_mode":
        return pair.source.entry_mode
    if name == "side":
        return pair.trade.side
    if name == "session":
        return pair.trade.session
    if name == "weekday":
        at = datetime.fromisoformat(pair.trade.entry_at).astimezone(s1.NEW_YORK)
        return at.strftime("%A").upper()
    if name == "target_provenance":
        return pair.source.target_provenance
    if name == "target_r_band":
        return _target_r_band(Decimal(pair.trade.target_r))
    raise ValueError(f"S2D unsupported feature: {name}")


def _keep(policy: Policy, pair: FrozenPair) -> bool:
    if policy.baseline:
        return True
    value = _feature(pair, policy.feature)
    member = value in policy.values
    return member if policy.mode == "INCLUDE" else not member


def _load_pairs(
    s2a_root: Path,
    s2b_root: Path,
) -> tuple[FrozenPair, ...]:
    source_rows: list[s2.S2AdmittedFillRow] = []
    for path in sorted(s2a_root.rglob("capitalizer-s2a-*-max3.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                source_rows.append(s2.S2AdmittedFillRow(**json.loads(line)))

    trade_rows: list[s2b.S2BGrossTrade] = []
    for path in sorted(s2b_root.rglob("capitalizer-s2b-chronology.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                trade_rows.append(s2b.S2BGrossTrade(**json.loads(line)))

    if len(source_rows) != 91 or len(trade_rows) != 91:
        raise ValueError("S2D requires exact 91-row S2A/S2B population")

    source_map = {
        (row.period, row.symbol, row.entry_at): row
        for row in source_rows
    }
    if len(source_map) != 91:
        raise ValueError("S2D source key collision")

    pairs: list[FrozenPair] = []
    for trade in trade_rows:
        key = (trade.period, trade.symbol, trade.entry_at)
        source = source_map.get(key)
        if source is None:
            raise ValueError("S2D source/economics join mismatch")
        pairs.append(FrozenPair(trade=trade, source=source))
    return tuple(pairs)


def _candidate_policies(
    development: tuple[FrozenPair, ...],
) -> tuple[Policy, ...]:
    policies: list[Policy] = [
        Policy(
            policy_id="KEEP_ALL",
            feature="",
            mode="",
            values=(),
            baseline=True,
        )
    ]
    for feature in (
        "entry_mode",
        "side",
        "session",
        "weekday",
        "target_provenance",
    ):
        values = sorted({_feature(pair, feature) for pair in development})
        for value in values:
            policies.append(
                Policy(
                    policy_id=f"{feature}:INCLUDE:{value}",
                    feature=feature,
                    mode="INCLUDE",
                    values=(value,),
                )
            )
            policies.append(
                Policy(
                    policy_id=f"{feature}:EXCLUDE:{value}",
                    feature=feature,
                    mode="EXCLUDE",
                    values=(value,),
                )
            )

    for start in range(len(TARGET_R_BANDS)):
        for end in range(start, len(TARGET_R_BANDS)):
            values = TARGET_R_BANDS[start : end + 1]
            policies.append(
                Policy(
                    policy_id=(
                        "target_r_band:INCLUDE_CONTIGUOUS:"
                        + "|".join(values)
                    ),
                    feature="target_r_band",
                    mode="INCLUDE",
                    values=values,
                )
            )
    return tuple(policies)


def _preservation(
    baseline: tuple[FrozenPair, ...],
    selected: tuple[FrozenPair, ...],
) -> preservation.WinnerPreservationReport:
    baseline_rows = tuple(
        preservation.PreservationTrade(
            trade_id=pair.trade_id,
            realized_r=Decimal(pair.trade.realized_gross_r),
        )
        for pair in baseline
    )
    selected_ids = frozenset(pair.trade_id for pair in selected)
    return preservation.adjudicate_winner_preservation(
        baseline_rows,
        selected_ids,
    )


def _period_report(
    *,
    period: str,
    baseline: tuple[FrozenPair, ...],
    selected: tuple[FrozenPair, ...],
) -> PolicyPeriodReport:
    return PolicyPeriodReport(
        period=period,
        trades=len(selected),
        metrics=s2b.metrics(tuple(pair.trade for pair in selected)),
        winner_preservation=_preservation(baseline, selected),
    )


def _development_eligibility(
    report: PolicyPeriodReport,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    metrics = report.metrics
    preservation_report = report.winner_preservation
    if report.trades <= 0:
        reasons.append("ZERO_SELECTED_TRADES")
    if not preservation_report.passed:
        reasons.append("WINNER_PRESERVATION_FAILED")

    pf = (
        None
        if metrics.profit_factor is None
        else Decimal(metrics.profit_factor)
    )
    payoff = (
        None
        if metrics.payoff_ratio is None
        else Decimal(metrics.payoff_ratio)
    )
    if pf is None or pf < Decimal("1.50"):
        reasons.append("PF_LT_1_50")
    if Decimal(metrics.expectancy_r) < Decimal("0.15"):
        reasons.append("EXPECTANCY_LT_0_15R")
    if payoff is None or payoff < Decimal("1.50"):
        reasons.append("PAYOFF_LT_1_50")
    if Decimal(metrics.max_drawdown_r) > Decimal("6"):
        reasons.append("DD_GT_6R")
    return not reasons, tuple(reasons)


def _evaluate_development(
    policy: Policy,
    development: tuple[FrozenPair, ...],
) -> PolicyEvaluation:
    selected = tuple(pair for pair in development if _keep(policy, pair))
    report = _period_report(
        period="development",
        baseline=development,
        selected=selected,
    )
    eligible, reasons = _development_eligibility(report)
    if policy.baseline:
        eligible = False
        reasons = tuple((*reasons, "BASELINE_NOT_SELECTABLE"))
    return PolicyEvaluation(
        policy=policy,
        development=report,
        development_eligible=eligible,
        development_eligibility_reasons=reasons,
    )


def _rank_key(
    row: PolicyEvaluation,
) -> tuple[Decimal, Decimal, int, Decimal, Decimal, str]:
    preservation_report = row.development.winner_preservation
    winner_r = preservation_report.winner_r_preservation
    winner_count = preservation_report.winner_count_preservation
    pf = row.development.metrics.profit_factor
    # Lower tuple is better; policy_id supplies the final ascending tie-break.
    return (
        -(Decimal("-1") if winner_r is None else winner_r),
        -(Decimal("-1") if winner_count is None else winner_count),
        -row.development.trades,
        -Decimal(row.development.metrics.total_r),
        -(Decimal("-1") if pf is None else Decimal(pf)),
        row.policy.policy_id,
    )


def _serialize_period(report: PolicyPeriodReport) -> dict[str, object]:
    return {
        "period": report.period,
        "trades": report.trades,
        "metrics": asdict(report.metrics),
        "winner_preservation": asdict(report.winner_preservation),
    }


def build_lab(
    s2a_root: Path,
    s2b_root: Path,
    output: Path,
) -> dict[str, object]:
    pairs = _load_pairs(s2a_root, s2b_root)
    by_period = {
        period: tuple(pair for pair in pairs if pair.trade.period == period)
        for period in ("reserved", "validation", "development")
    }
    development = by_period["development"]
    policies = _candidate_policies(development)
    evaluations = tuple(
        _evaluate_development(policy, development)
        for policy in policies
    )
    eligible = tuple(
        row for row in evaluations if row.development_eligible
    )
    winner = min(eligible, key=_rank_key) if eligible else None

    if winner is None:
        decision = "SIMPLE_CAUSAL_POLICY_FAMILY_FALSIFIED"
        selected_policy: Policy | None = None
        transport: dict[str, object] = {}
    else:
        decision = "DEVELOPMENT_POLICY_FROZEN_FOR_CONSUMED_TRANSPORT"
        selected_policy = winner.policy
        transport = {}
        for period in ("validation", "reserved"):
            baseline = by_period[period]
            selected = tuple(
                pair for pair in baseline if _keep(selected_policy, pair)
            )
            transport[period] = _serialize_period(
                _period_report(
                    period=period,
                    baseline=baseline,
                    selected=selected,
                )
            )

    evaluated_rows = []
    for row in evaluations:
        evaluated_rows.append(
            {
                "policy": asdict(row.policy),
                "development": _serialize_period(row.development),
                "development_eligible": row.development_eligible,
                "development_eligibility_reasons": list(
                    row.development_eligibility_reasons
                ),
            }
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_s2a_run_id": 36642644284,
        "source_s2b_run_id": 36651366703,
        "development_policy_count": len(policies),
        "eligible_nonbaseline_policy_count": len(eligible),
        "decision": decision,
        "selected_policy": (
            None if selected_policy is None else asdict(selected_policy)
        ),
        "development_selection": (
            None
            if winner is None
            else _serialize_period(winner.development)
        ),
        "transport": transport,
        "all_development_evaluations": evaluated_rows,
        "validation_used_for_policy_selection": False,
        "reserved_used_for_policy_selection": False,
        "fresh_holdout_opened": False,
        "rule_promoted_to_final_trader": False,
        "trader_certified": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v47-s2d-simple-policy-lab.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True, default=str))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("s2a_root", type=Path)
    parser.add_argument("s2b_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_lab(args.s2a_root, args.s2b_root, args.output)


if __name__ == "__main__":
    main()
