#!/usr/bin/env python3
"""Build a full-period causal walk-forward expectation manifest.

Every signal is observed in shadow after its own exit time, whether or not CIBO
would have deployed capital. Before each decision epoch, only already-finished
signals are allowed into the expectation history. The attached historical
outcome is never decoded before its exit timestamp.

This is research-only manifest construction. It does not change Traders, Risk,
sizing, leverage, compound or provider economics.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
    validate_single_account_manifest_sha256,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    CiboManifestShadowOutcomeObservation,
    manifest_row_to_shadow_outcome_observation,
)
from qore.infrastructure.cibo_walk_forward_expectation import (
    build_walk_forward_expectation,
    walk_forward_minimum_observations,
)
from qore.infrastructure.cibo_walk_forward_forecast_confidence import (
    assess_walk_forward_forecast_confidence,
    walk_forward_mature_observation_count,
)


def _dt(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(f"{name} must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"{name} must be timezone-aware"
        )
    return result


def _d(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            f"{name} must be Decimal-compatible"
        ) from error
    if not result.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite")
    return result


def _outcome_exit_at(row: dict[str, Any]) -> datetime:
    outcome = row.get("settlement_outcome_research_only")
    if not isinstance(outcome, dict):
        raise CiboCapitalManagementError(
            "walk-forward source outcome must be mapping"
        )
    if (
        outcome.get("not_available_to_predecision") is not True
        or outcome.get("used_for_decision") is not False
    ):
        raise CiboCapitalManagementError(
            "walk-forward source outcome governance invalid"
        )
    return _dt(outcome.get("exit_at"), "outcome exit_at")


def _minimum_stop_risk_usd(row: dict[str, Any]) -> Decimal:
    opportunity = row.get("trader_opportunity")
    if not isinstance(opportunity, dict):
        raise CiboCapitalManagementError(
            "walk-forward trader opportunity must be mapping"
        )
    steps = opportunity.get("minimum_execution_steps", 1)
    if (
        not isinstance(steps, int)
        or isinstance(steps, bool)
        or steps < 1
    ):
        raise CiboCapitalManagementError(
            "walk-forward minimum execution steps invalid"
        )
    with localcontext() as context:
        context.prec = 100
        result = (
            _d(
                opportunity.get("stop_loss_per_volume"),
                "stop_loss_per_volume",
            )
            * _d(opportunity.get("minimum_volume"), "minimum_volume")
            * Decimal(steps)
        )
    if result <= 0:
        raise CiboCapitalManagementError(
            "walk-forward minimum stop risk must be positive"
        )
    return result


def _expectation_payload(snapshot) -> dict[str, object]:
    expectation = snapshot.expectation
    confidence = assess_walk_forward_forecast_confidence(
        observation_count=snapshot.observation_count,
        expected_structural_r=snapshot.expected_structural_r,
        chronological_block_means_r=snapshot.chronological_block_means_r,
    )
    return {
        "evidence_id": expectation.evidence_id,
        "evidence_available_at": snapshot.evidence_available_at.isoformat(),
        "as_of": expectation.as_of.isoformat(),
        "basis": expectation.basis.value,
        "expected_net_value_usd": format(
            expectation.expected_net_value_usd,
            "f",
        ),
        "expected_capital_minutes": format(
            expectation.expected_capital_minutes,
            "f",
        ),
        "walk_forward_observation_count": snapshot.observation_count,
        "walk_forward_history_sha256": snapshot.history_sha256,
        "walk_forward_cold_start": snapshot.cold_start,
        "walk_forward_expected_structural_r": (
            None
            if snapshot.expected_structural_r is None
            else format(snapshot.expected_structural_r, "f")
        ),
        "walk_forward_block_means_r": [
            format(value, "f")
            for value in snapshot.chronological_block_means_r
        ],
        "walk_forward_maturity": confidence.maturity.value,
        "walk_forward_mature_for_capital_consideration": (
            confidence.mature_for_capital_consideration
        ),
        "walk_forward_positive_block_count": confidence.positive_block_count,
        "walk_forward_nonpositive_block_count": confidence.nonpositive_block_count,
        "walk_forward_block_dispersion_r": format(
            confidence.block_dispersion_r,
            "f",
        ),
        "walk_forward_median_absolute_deviation_r": format(
            confidence.median_absolute_deviation_r,
            "f",
        ),
        "walk_forward_maturity_fraction": format(
            confidence.maturity_fraction,
            "f",
        ),
        "future_market_used": False,
        "outcome_used": False,
        "pnl_used": False,
        "post_entry_path_used": False,
        "sizing_authority": False,
        "risk_authority": False,
        "order_authority": False,
        "execution_authority": False,
    }


def build_walk_forward_manifest(
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_sha = validate_single_account_manifest_sha256(manifest)
    source_rows = manifest.get("opportunities")
    if not isinstance(source_rows, list) or not source_rows:
        raise CiboCapitalManagementError(
            "walk-forward manifest requires source opportunities"
        )

    rows = [
        json.loads(json.dumps(row))
        for row in source_rows
        if isinstance(row, dict)
    ]
    if len(rows) != len(source_rows):
        raise CiboCapitalManagementError(
            "walk-forward source opportunity row invalid"
        )
    rows.sort(
        key=lambda row: (
            str(row["market_decision_at"]),
            str(row["decision_epoch_id"]),
            str(row["signal_fingerprint"]),
        )
    )

    grouped: dict[tuple[datetime, str], list[dict[str, Any]]] = defaultdict(
        list
    )
    for row in rows:
        decision_at = _dt(
            row.get("market_decision_at"),
            "market_decision_at",
        )
        epoch_id = str(row.get("decision_epoch_id", ""))
        if not epoch_id:
            raise CiboCapitalManagementError(
                "walk-forward decision_epoch_id required"
            )
        grouped[(decision_at, epoch_id)].append(row)

    completed: list[CiboManifestShadowOutcomeObservation] = []
    pending: list[tuple[datetime, dict[str, Any]]] = []
    basis_counts: Counter[str] = Counter()
    forecast_counts: Counter[str] = Counter()
    cold_start_counts: Counter[str] = Counter()
    first_forecast_at: dict[str, str] = {}
    transformed: list[dict[str, Any]] = []
    max_observation_count: Counter[str] = Counter()
    decoded_before_exit_count = 0

    for (decision_at, _epoch_id), epoch_rows in sorted(
        grouped.items(),
        key=lambda item: item[0],
    ):
        due = [
            item for item in pending if item[0] <= decision_at
        ]
        pending = [
            item for item in pending if item[0] > decision_at
        ]
        for exit_at, source_row in sorted(
            due,
            key=lambda item: (
                item[0],
                str(item[1]["signal_fingerprint"]),
            ),
        ):
            if exit_at > decision_at:
                decoded_before_exit_count += 1
                raise CiboCapitalManagementError(
                    "walk-forward attempted to decode future outcome"
                )
            observation = manifest_row_to_shadow_outcome_observation(
                source_row
            )
            if observation.exit_at > decision_at:
                decoded_before_exit_count += 1
                raise CiboCapitalManagementError(
                    "walk-forward shadow observation unavailable"
                )
            completed.append(observation)

        history_surface = tuple(completed)
        for row in sorted(
            epoch_rows,
            key=lambda item: (
                str(item["trader_id"]),
                str(item["qore_symbol"]),
                str(item["signal_fingerprint"]),
            ),
        ):
            trader = TraderLineage(str(row["trader_id"]))
            snapshot = build_walk_forward_expectation(
                trader_id=trader,
                decision_at=decision_at,
                stop_risk_usd=_minimum_stop_risk_usd(row),
                completed_observations=history_surface,
            )
            row["expectation"] = _expectation_payload(snapshot)
            basis_counts[snapshot.expectation.basis.value] += 1
            max_observation_count[trader.value] = max(
                max_observation_count[trader.value],
                snapshot.observation_count,
            )
            if snapshot.cold_start:
                cold_start_counts[trader.value] += 1
            else:
                forecast_counts[trader.value] += 1
                first_forecast_at.setdefault(
                    trader.value,
                    decision_at.isoformat(),
                )
            transformed.append(row)

        # Only after the entire simultaneous epoch has been forecast may its
        # outcomes enter the shadow pending queue.
        for row in epoch_rows:
            exit_at = _outcome_exit_at(row)
            if exit_at < decision_at:
                raise CiboCapitalManagementError(
                    "walk-forward source outcome predates decision"
                )
            pending.append((exit_at, row))

    expected_count = len(rows)
    if len(transformed) != expected_count:
        raise CiboCapitalManagementError(
            "walk-forward transformed decision count drift"
        )

    result = json.loads(json.dumps(manifest))
    result["schema"] = (
        "qore.cibo.single-account-walk-forward-expectation.v1"
    )
    result["opportunities"] = transformed
    result["walk_forward_expectation"] = {
        "schema": "qore.cibo.walk-forward-expectation-manifest.v1",
        "source_manifest_sha256": source_sha,
        "minimum_observations": walk_forward_minimum_observations(),
        "mature_observation_count": walk_forward_mature_observation_count(),
        "signal_outcomes_observed_in_shadow": True,
        "outcome_decoded_only_after_exit": True,
        "future_outcome_used": False,
        "capital_pnl_used_for_forecast": False,
        "provider_specific_model": False,
        "market_specific_model": False,
        "platform_specific_model": False,
        "cold_start_decision_count": sum(cold_start_counts.values()),
        "forecast_decision_count": sum(forecast_counts.values()),
        "basis_counts": dict(sorted(basis_counts.items())),
        "per_trader_cold_start": dict(sorted(cold_start_counts.items())),
        "per_trader_forecast": dict(sorted(forecast_counts.items())),
        "per_trader_first_forecast_at": dict(
            sorted(first_forecast_at.items())
        ),
        "per_trader_max_observation_count": dict(
            sorted(max_observation_count.items())
        ),
        "decoded_before_exit_count": decoded_before_exit_count,
        "research_only": True,
        "certification_claimed": False,
    }
    governance = dict(result.get("governance", {}))
    governance["walk_forward_expectation_required"] = True
    governance["future_expectation_evidence_allowed"] = False
    result["governance"] = governance
    resealed = reseal_single_account_manifest(result)

    receipt = {
        **result["walk_forward_expectation"],
        "manifest_sha256": resealed["manifest_sha256"],
        "opportunity_decision_count": expected_count,
        "decision_epoch_count": result["decision_epoch_count"],
        "first_market_decision_at": result["first_market_decision_at"],
        "last_market_decision_at": result["last_market_decision_at"],
    }
    return resealed, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    source = json.loads(args.manifest.read_text(encoding="utf-8"))
    result, receipt = build_walk_forward_manifest(source)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
