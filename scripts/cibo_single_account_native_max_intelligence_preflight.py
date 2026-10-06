#!/usr/bin/env python3
"""Preflight the single-account population against native MAX CIBO intelligence.

No external AI/provider is called. Each archived opportunity is reconstructed,
its sovereign CF01-CF19 consultation is executed, and the native-only MAX engine
is asked to consume the complete semantic surface.

The script is intentionally fail-observing rather than fail-fast: it reports
every Trader whose historical transport still carries fractional perception.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_native_maximum_intelligence import (
    run_native_maximum_intelligence,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    validate_single_account_manifest_sha256,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    consult_cibo_economic_faculties,
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _dt(value: object) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError("preflight timestamp must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            "preflight timestamp must be timezone-aware"
        )
    return result


def _boolish(value: object, name: str) -> bool:
    if type(value) is bool:
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no", ""}:
            return False
    if value is None:
        return False
    raise CiboCapitalManagementError(
        f"preflight {name} must be bool-compatible"
    )


def _opportunity(row: dict[str, Any]) -> TraderOpportunityEnvelope:
    payload = row["trader_opportunity"]
    context = tuple(
        (str(item[0]), str(item[1]))
        for item in payload.get("decision_context", ())
    )
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage(str(row["trader_id"])),
        signal_fingerprint=str(row["signal_fingerprint"]),
        qore_symbol=str(row["qore_symbol"]),
        provider_symbol=str(
            payload.get("provider_symbol") or row["qore_symbol"]
        ),
        side=str(payload["side"]),
        entry_type=str(payload.get("entry_type", "market")),
        intended_entry=_d(payload["intended_entry"]),
        stop_loss=_d(payload["stop_loss"]),
        take_profit=_d(payload["take_profit"]),
        stop_loss_per_volume=_d(payload["stop_loss_per_volume"]),
        margin_per_volume=_d(payload["margin_per_volume"]),
        volume_step=_d(payload["volume_step"]),
        minimum_volume=_d(payload["minimum_volume"]),
        maximum_volume=_d(payload["maximum_volume"]),
        minimum_execution_steps=int(
            payload.get("minimum_execution_steps", 1)
        ),
        decision_context=context,
    )


def _regime(
    row: dict[str, Any],
    *,
    opportunity_count: int,
) -> CiboCapitalRegimeState:
    if (
        not isinstance(opportunity_count, int)
        or isinstance(opportunity_count, bool)
        or opportunity_count <= 0
    ):
        raise CiboCapitalManagementError(
            "preflight opportunity_count must be positive int"
        )
    ce2i = row.get("ce2i_predecision_evidence")
    receipts = ce2i.get("runtime_receipts") if isinstance(ce2i, dict) else None
    candidates = [
        item
        for item in (receipts or ())
        if isinstance(item, dict)
        and item.get("engine_name") == "select_ce2i_tools_for_regime"
    ]
    if len(candidates) != 1:
        raise CiboCapitalManagementError(
            "preflight requires exact CE2I regime receipt"
        )
    payload = candidates[0]["input_payload"]
    declared_count = payload.get("opportunity_count")
    if declared_count is not None:
        try:
            int(str(declared_count))
        except (TypeError, ValueError) as error:
            raise CiboCapitalManagementError(
                "preflight CE2I opportunity_count is invalid"
            ) from error
        # Archived CE2I receipts were emitted once per Trader opportunity and
        # may therefore say opportunity_count=1.  The manifest groups the true
        # simultaneous decision surface causally; that observed epoch size
        # supersedes the stale transport count without changing market regime
        # semantics or consulting outcomes.
    return CiboCapitalRegimeState(
        liquidity=LiquidityState(str(payload["liquidity"])),
        volatility=VolatilityState(str(payload["volatility"])),
        correlation=CorrelationState(str(payload["correlation"])),
        provider_condition=ProviderCondition(
            str(payload["provider_condition"])
        ),
        risk_utilization=_d(payload["risk_utilization"]),
        margin_utilization=_d(payload["margin_utilization"]),
        drawdown_utilization=_d(payload["drawdown_utilization"]),
        opportunity_count=opportunity_count,
        position_path_adverse=_boolish(
            payload.get("position_path_adverse", False),
            "position_path_adverse",
        ),
        evidence_stale=_boolish(
            payload.get("evidence_stale", False),
            "evidence_stale",
        ),
    )


def _group_rows_by_epoch(
    rows: list[dict[str, Any]],
) -> tuple[tuple[dict[str, Any], ...], ...]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        epoch_id = row.get("decision_epoch_id")
        if not isinstance(epoch_id, str) or not epoch_id:
            raise CiboCapitalManagementError(
                "native MAX preflight requires decision_epoch_id"
            )
        grouped[epoch_id].append(row)

    epochs: list[tuple[dict[str, Any], ...]] = []
    for epoch_id, epoch_rows in grouped.items():
        decision_times = {
            str(item.get("market_decision_at")) for item in epoch_rows
        }
        if len(decision_times) != 1:
            raise CiboCapitalManagementError(
                "native MAX preflight epoch decision-time drift"
            )
        signals = tuple(
            str(item.get("signal_fingerprint")) for item in epoch_rows
        )
        if len(signals) != len(set(signals)):
            raise CiboCapitalManagementError(
                "native MAX preflight duplicate signal in epoch"
            )
        ordered = tuple(
            sorted(
                epoch_rows,
                key=lambda item: (
                    str(item["trader_id"]),
                    str(item["qore_symbol"]),
                    str(item["signal_fingerprint"]),
                ),
            )
        )
        epochs.append(ordered)

    return tuple(
        sorted(
            epochs,
            key=lambda epoch: (
                _dt(epoch[0]["market_decision_at"]),
                str(epoch[0]["decision_epoch_id"]),
            ),
        )
    )


def run(
    manifest: dict[str, Any],
    *,
    progress_every: int = 0,
) -> dict[str, Any]:
    if (
        not isinstance(progress_every, int)
        or isinstance(progress_every, bool)
        or progress_every < 0
    ):
        raise CiboCapitalManagementError(
            "native MAX preflight progress_every must be non-negative int"
        )
    source_manifest_sha256 = validate_single_account_manifest_sha256(manifest)
    rows = manifest.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise CiboCapitalManagementError(
            "native MAX preflight requires manifest opportunities"
        )

    passed = Counter()
    blocked = Counter()
    failure_reasons: Counter[str] = Counter()
    context_counts: dict[str, set[int]] = defaultdict(set)
    formal_blocked: Counter[str] = Counter()
    examples: list[dict[str, str]] = []

    processed = 0

    def emit_progress() -> None:
        if progress_every and (
            processed % progress_every == 0 or processed == len(rows)
        ):
            print(
                json.dumps(
                    {
                        "progress": processed,
                        "decision_count": len(rows),
                        "native_max_pass_count": sum(passed.values()),
                        "native_max_blocked_count": sum(blocked.values()),
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )

    for epoch_rows in _group_rows_by_epoch(rows):
        opportunities = tuple(_opportunity(row) for row in epoch_rows)
        for row, opportunity in zip(
            epoch_rows,
            opportunities,
            strict=True,
        ):
            trader = str(row["trader_id"])
            context_counts[trader].add(len(opportunity.decision_context))

        try:
            regime_states = tuple(
                _regime(row, opportunity_count=len(opportunities))
                for row in epoch_rows
            )
            regime_state = regime_states[0]
            if any(item != regime_state for item in regime_states[1:]):
                raise CiboCapitalManagementError(
                    "native MAX preflight mixed regime evidence inside epoch"
                )
            consultation = consult_cibo_economic_faculties(
                decision_at=_dt(epoch_rows[0]["market_decision_at"]),
                opportunities=opportunities,
                regime_state=regime_state,
            )
        except Exception as error:
            message = str(error)
            for row in epoch_rows:
                trader = str(row["trader_id"])
                blocked[trader] += 1
                failure_reasons[message] += 1
                if len(examples) < 30:
                    examples.append(
                        {
                            "trader_id": trader,
                            "signal_fingerprint": str(
                                row["signal_fingerprint"]
                            ),
                            "error": message,
                        }
                    )
                processed += 1
                emit_progress()
            continue

        for row, opportunity in zip(
            epoch_rows,
            opportunities,
            strict=True,
        ):
            trader = str(row["trader_id"])
            try:
                result = run_native_maximum_intelligence(
                    consultation=consultation,
                    opportunities=opportunities,
                    target=opportunity,
                    regime_state=regime_state,
                )
                if (
                    not result.native_only
                    or result.external_ai_call_count != 0
                    or result.external_reasoning_provider_used
                ):
                    raise CiboCapitalManagementError(
                        "native MAX preflight external AI dependency drift"
                    )
                passed[trader] += 1
                for code in result.blocked_function_codes:
                    formal_blocked[code] += 1
            except Exception as error:
                blocked[trader] += 1
                message = str(error)
                failure_reasons[message] += 1
                if len(examples) < 30:
                    examples.append(
                        {
                            "trader_id": trader,
                            "signal_fingerprint": str(
                                row["signal_fingerprint"]
                            ),
                            "error": message,
                        }
                    )
            processed += 1
            emit_progress()

    expected = len(rows)
    native_pass = sum(passed.values())
    native_blocked = sum(blocked.values())
    return {
        "schema": "qore.cibo.native-max-intelligence-preflight.v1",
        "source_manifest_sha256": source_manifest_sha256,
        "decision_count": expected,
        "native_max_pass_count": native_pass,
        "native_max_blocked_count": native_blocked,
        "external_ai_call_count": 0,
        "external_reasoning_provider_used": False,
        "maximum_intelligence_ready": native_pass == expected,
        "per_trader_pass": dict(sorted(passed.items())),
        "per_trader_blocked": dict(sorted(blocked.items())),
        "per_trader_context_key_counts": {
            trader: sorted(values)
            for trader, values in sorted(context_counts.items())
        },
        "formal_authority_blocked_function_counts": dict(
            sorted(formal_blocked.items())
        ),
        "failure_reasons": dict(failure_reasons.most_common()),
        "failure_examples": examples,
        "governance": {
            "native_cibo_only": True,
            "external_ai": False,
            "outcome_aware_tuning": False,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Emit progress JSON to stderr every N decisions; 0 disables it.",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    summary = run(manifest, progress_every=args.progress_every)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision_count": summary["decision_count"],
                "native_max_pass_count": summary[
                    "native_max_pass_count"
                ],
                "native_max_blocked_count": summary[
                    "native_max_blocked_count"
                ],
                "maximum_intelligence_ready": summary[
                    "maximum_intelligence_ready"
                ],
                "external_ai_call_count": 0,
                "per_trader_pass": summary["per_trader_pass"],
                "per_trader_blocked": summary["per_trader_blocked"],
                "per_trader_context_key_counts": summary[
                    "per_trader_context_key_counts"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if summary["maximum_intelligence_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
