"""Read-only fresh-OOS collector/evaluator for Architect-2 T16.

Collects closed M1 bars from cTrader DEMO for NAS100, US30 and US500 strictly
after the frozen T16 utility protocol. It opens no orders or positions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.cibo_arch2_t16_demo_execution_receipt import (
    T16_DEMO_EXECUTION_RECEIPT,
)
from qore.infrastructure.cibo_arch2_t16_fresh_oos_utility import (
    FROZEN_AT,
    MINIMUM_OOS_OBSERVATIONS,
    T16UtilityObservation,
    evaluate_t16_fresh_oos_utility,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    collect_ctrader_demo_account_capability,
)
from qore.infrastructure.ctrader_demo_free_sink import credentials_from_environment
from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.kernel.result import Failure

_PERIOD_M1 = 1
_PRICE_SCALE = Decimal("100000")
_REQUIRED = ("NAS100", "US30", "US500")


def _request(
    client: SpotwareCTraderOpenApiClient,
    name: str,
    fields: dict[str, object],
    message_id: str,
) -> object:
    result = client.request(
        name,
        fields,
        client_msg_id=message_id,
        timeout_seconds=15.0,
    )
    if isinstance(result, Failure):
        raise CiboCapitalManagementError(
            f"T16 fresh-OOS request failed: {name}: {result.error}"
        )
    return result.value


def _closed_m1_prices(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[tuple[datetime, Decimal], ...]:
    if opened_at.tzinfo is None or closed_at.tzinfo is None:
        raise CiboCapitalManagementError("T16 M1 interval must be timezone-aware")
    response = _request(
        client,
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": _PERIOD_M1,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000),
        },
        f"t16-oos-m1:{symbol_id}:{int(closed_at.timestamp())}",
    )
    rows: list[tuple[datetime, Decimal]] = []
    for bar in tuple(getattr(response, "trendbar", ())):
        low = getattr(bar, "low", None)
        delta_close = getattr(bar, "deltaClose", None)
        minute = getattr(bar, "utcTimestampInMinutes", None)
        if (
            type(low) is not int
            or low <= 0
            or type(delta_close) is not int
            or delta_close < 0
            or type(minute) is not int
            or minute < 0
        ):
            raise CiboCapitalManagementError("T16 M1 trendbar payload invalid")
        market_at = datetime.fromtimestamp(minute * 60, tz=UTC)
        close = Decimal(low + delta_close) / _PRICE_SCALE
        if close <= 0:
            raise CiboCapitalManagementError("T16 M1 close must be positive")
        if market_at <= FROZEN_AT:
            continue
        if market_at + timedelta(minutes=1) > closed_at:
            continue
        rows.append((market_at, close))
    ordered = tuple(sorted(rows, key=lambda item: item[0]))
    if len({item[0] for item in ordered}) != len(ordered):
        raise CiboCapitalManagementError("T16 M1 duplicate timestamps")
    return ordered


def _aligned_returns(
    target: tuple[tuple[datetime, Decimal], ...],
    hedge: tuple[tuple[datetime, Decimal], ...],
) -> tuple[T16UtilityObservation, ...]:
    target_map = dict(target)
    hedge_map = dict(hedge)
    shared = tuple(sorted(set(target_map) & set(hedge_map)))
    observations: list[T16UtilityObservation] = []
    for previous, current in zip(shared, shared[1:], strict=False):
        if current - previous != timedelta(minutes=1):
            continue
        target_previous = target_map[previous]
        hedge_previous = hedge_map[previous]
        observations.append(
            T16UtilityObservation(
                market_at=current,
                target_return=(target_map[current] / target_previous) - Decimal(1),
                hedge_return=(hedge_map[current] / hedge_previous) - Decimal(1),
            )
        )
    return tuple(observations)


def _sha256_rows(rows: tuple[tuple[datetime, Decimal], ...]) -> str:
    raw = json.dumps(
        [[at.isoformat(), format(price, "f")] for at, price in rows],
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def run() -> dict[str, object]:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    closed_at = now - timedelta(minutes=1)
    if closed_at <= FROZEN_AT:
        raise CiboCapitalManagementError("T16 fresh-OOS interval not yet available")
    opened_at = FROZEN_AT.replace(second=0, microsecond=0)

    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CiboCapitalManagementError(
                f"T16 fresh-OOS authentication failed: {connected.error}"
            )
        capability = collect_ctrader_demo_account_capability(client)
        receipt = T16_DEMO_EXECUTION_RECEIPT
        account_fingerprint = hashlib.sha256(
            capability.account_ref.encode("utf-8")
        ).hexdigest()
        if account_fingerprint != receipt.account_fingerprint_sha256:
            raise CiboCapitalManagementError("T16 fresh-OOS account drift")
        if capability.catalog_sha256 != receipt.provider_catalog_sha256:
            raise CiboCapitalManagementError("T16 fresh-OOS provider catalog drift")

        by_name = {
            item.symbol_name: item
            for item in capability.symbols
            if item.enabled
        }
        if not set(_REQUIRED).issubset(by_name):
            raise CiboCapitalManagementError("T16 fresh-OOS symbols unavailable")

        bars = {
            symbol: _closed_m1_prices(
                client,
                symbol_id=by_name[symbol].symbol_id,
                opened_at=opened_at,
                closed_at=closed_at,
            )
            for symbol in _REQUIRED
        }
        costs = dict(receipt.max_round_trip_cost_bps)
        results: dict[str, object] = {}
        for hedge in ("US30", "US500"):
            observations = _aligned_returns(bars["NAS100"], bars[hedge])
            if len(observations) < MINIMUM_OOS_OBSERVATIONS:
                raise CiboCapitalManagementError(
                    f"T16 {hedge} fresh-OOS observations insufficient: "
                    f"{len(observations)}/{MINIMUM_OOS_OBSERVATIONS}"
                )
            evaluated = evaluate_t16_fresh_oos_utility(
                hedge_symbol=hedge,
                observations=observations,
                conservative_round_trip_cost_bps=costs[hedge],
            )
            results[hedge] = {
                "observation_count": evaluated.observation_count,
                "hedge_beta": format(evaluated.hedge_beta, "f"),
                "four_of_four_pass": evaluated.four_of_four_pass,
                "net_economic_benefit_proven": (
                    evaluated.net_economic_benefit_proven
                ),
                "fresh_oos_utility_proven": evaluated.fresh_oos_utility_proven,
                "t16_candidate_pass": evaluated.t16_candidate_pass,
                "fold_results": [
                    {
                        "fold_index": row.fold_index,
                        "observations": row.observations,
                        "control_downside_semideviation": format(
                            row.control_downside_semideviation, "f"
                        ),
                        "hedged_downside_semideviation": format(
                            row.hedged_downside_semideviation, "f"
                        ),
                        "conservative_round_trip_cost_fraction": format(
                            row.conservative_round_trip_cost_fraction, "f"
                        ),
                        "net_protection_fraction": format(
                            row.net_protection_fraction, "f"
                        ),
                        "pass_gate": row.pass_gate,
                    }
                    for row in evaluated.fold_results
                ],
            }

        candidate_passes = [
            symbol
            for symbol, result in results.items()
            if bool(result["t16_candidate_pass"])
        ]
        return {
            "schema": "qore.cibo.arch2.t16.fresh-oos-m1.v1",
            "status": "EVALUATED",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "frozen_at": FROZEN_AT.isoformat(),
            "opened_at": opened_at.isoformat(),
            "closed_at": closed_at.isoformat(),
            "required_symbols": list(_REQUIRED),
            "bar_counts": {symbol: len(rows) for symbol, rows in bars.items()},
            "bar_sha256": {
                symbol: _sha256_rows(rows) for symbol, rows in bars.items()
            },
            "results": results,
            "candidate_passes": candidate_passes,
            "terminal_recommendation": (
                "COMPLETED_AND_PROVEN"
                if candidate_passes
                else "FALSIFIED_AND_CLOSED"
            ),
            "orders_created": 0,
            "positions_created": 0,
            "broker_mutation_performed": False,
            "holdout_outcomes_used": False,
            "phase22_v2_consumed": False,
            "fundednext_touched": False,
            "vps_touched": False,
            "productive_authority": False,
            "git_sha": os.environ.get("GITHUB_SHA", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        }
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "candidate_passes": report["candidate_passes"],
                "terminal_recommendation": report["terminal_recommendation"],
                "bar_counts": report["bar_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
