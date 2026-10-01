"""Collect post-declaration cTrader DEMO T16 market-structure evidence.

This probe is read-only. It consumes only M1 trendbars whose close is after the
pre-registered T16 declaration. It measures return/correlation/basis structure
without fabricating historical spread, slippage or execution-cost evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t16_hedge_candidate import (
    T16HedgeReturnObservation,
    assess_t16_hedge_candidate,
)
from qore.infrastructure.cibo_ce2i_t16_preregistered_hedge_universe import (
    PREREGISTERED_T16_HEDGE_CANDIDATES,
    T16_ACCOUNT_FINGERPRINT_SHA256,
    T16_PROVIDER_CATALOG_SHA256,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    collect_ctrader_demo_account_capability,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_M1_NATIVE_PERIOD = 1
_ONE_MINUTE = timedelta(minutes=1)


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
        timeout_seconds=10.0,
    )
    if isinstance(result, Failure):
        raise CiboCapitalManagementError(str(result.error))
    return result.value


def _closed_m1_closes(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    declared_at: datetime,
    observed_at: datetime,
) -> dict[int, int]:
    start = declared_at.replace(second=0, microsecond=0) + _ONE_MINUTE
    response = _request(
        client,
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(start.timestamp() * 1000),
            "period": _M1_NATIVE_PERIOD,
            "symbolId": symbol_id,
            "toTimestamp": int(observed_at.timestamp() * 1000),
        },
        f"qore-cibo-t16-m1-{symbol_id}",
    )
    bars = getattr(response, "trendbar", None)
    if bars is None:
        raise CiboCapitalManagementError(
            "T16 cTrader trendbar response missing bars"
        )

    closes: dict[int, int] = {}
    for item in bars:
        low = getattr(item, "low", None)
        delta_close = getattr(item, "deltaClose", None)
        minute = getattr(item, "utcTimestampInMinutes", None)
        if (
            type(low) is not int
            or low <= 0
            or type(delta_close) is not int
            or delta_close < 0
            or type(minute) is not int
            or minute <= 0
        ):
            raise CiboCapitalManagementError(
                "T16 cTrader trendbar payload invalid"
            )
        bar_open = datetime.fromtimestamp(minute * 60, tz=UTC)
        bar_close = bar_open + _ONE_MINUTE
        if bar_close <= declared_at or bar_close > observed_at:
            continue
        closes[minute] = low + delta_close
    return closes


def _digest(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _observations(
    *,
    declaration: Any,
    target_closes: dict[int, int],
    hedge_closes: dict[int, int],
    known_at: datetime,
) -> tuple[T16HedgeReturnObservation, ...]:
    common = tuple(sorted(set(target_closes) & set(hedge_closes)))
    rows: list[T16HedgeReturnObservation] = []
    for previous, current in zip(common, common[1:], strict=False):
        if current != previous + 1:
            continue
        start_market_at = datetime.fromtimestamp(
            (previous + 1) * 60,
            tz=UTC,
        )
        end_market_at = datetime.fromtimestamp(
            (current + 1) * 60,
            tz=UTC,
        )
        if start_market_at < declaration.declared_at:
            continue
        target_previous = Decimal(target_closes[previous])
        hedge_previous = Decimal(hedge_closes[previous])
        target_current = Decimal(target_closes[current])
        hedge_current = Decimal(hedge_closes[current])
        evidence = {
            "declaration_id": declaration.declaration_id,
            "previous_minute": previous,
            "current_minute": current,
            "target_previous_close_relative": target_closes[previous],
            "target_current_close_relative": target_closes[current],
            "hedge_previous_close_relative": hedge_closes[previous],
            "hedge_current_close_relative": hedge_closes[current],
            "provider_catalog_sha256": T16_PROVIDER_CATALOG_SHA256,
        }
        rows.append(
            T16HedgeReturnObservation(
                provider_key=declaration.provider_key,
                target_symbol=declaration.target_symbol,
                hedge_symbol=declaration.hedge_symbol,
                start_market_at=start_market_at,
                end_market_at=end_market_at,
                known_at=known_at,
                target_return=(
                    target_current - target_previous
                ) / target_previous,
                hedge_return=(
                    hedge_current - hedge_previous
                ) / hedge_previous,
                hedge_cost_bps=None,
                execution_supported=None,
                source_evidence_sha256=_digest(evidence),
            )
        )
    return tuple(rows)


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def build_report() -> dict[str, object]:
    observed_at = datetime.now(UTC)
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        capability = collect_ctrader_demo_account_capability(
            client,
            observed_at=observed_at,
        )
        account_fingerprint = hashlib.sha256(
            capability.account_ref.encode("utf-8")
        ).hexdigest()
        if account_fingerprint != T16_ACCOUNT_FINGERPRINT_SHA256:
            raise CiboCapitalManagementError(
                "T16 account fingerprint drift"
            )
        if capability.catalog_sha256 != T16_PROVIDER_CATALOG_SHA256:
            raise CiboCapitalManagementError(
                "T16 provider catalog changed after preregistration"
            )
        by_name = {
            item.symbol_name: item
            for item in capability.symbols
            if item.enabled
        }
        required = {"USTEC", "US30", "US500"}
        if not required.issubset(by_name):
            raise CiboCapitalManagementError(
                "T16 preregistered provider symbols are no longer enabled"
            )

        closes = {
            name: _closed_m1_closes(
                client,
                symbol_id=by_name[name].symbol_id,
                declared_at=min(
                    item.declaration.declared_at
                    for item in PREREGISTERED_T16_HEDGE_CANDIDATES
                ),
                observed_at=observed_at,
            )
            for name in sorted(required)
        }

        pairs: list[dict[str, object]] = []
        for candidate in PREREGISTERED_T16_HEDGE_CANDIDATES:
            declaration = candidate.declaration
            rows = _observations(
                declaration=declaration,
                target_closes=closes[candidate.target_provider_symbol],
                hedge_closes=closes[candidate.hedge_provider_symbol],
                known_at=observed_at,
            )
            audit = assess_t16_hedge_candidate(
                declaration=declaration,
                observations=rows,
                decision_at=observed_at,
            )
            pairs.append(
                {
                    "declaration_id": declaration.declaration_id,
                    "target_symbol": declaration.target_symbol,
                    "target_provider_symbol": candidate.target_provider_symbol,
                    "hedge_symbol": declaration.hedge_symbol,
                    "sample_count": len(rows),
                    "first_market_at": (
                        rows[0].start_market_at.isoformat()
                        if rows
                        else None
                    ),
                    "last_market_at": (
                        rows[-1].end_market_at.isoformat()
                        if rows
                        else None
                    ),
                    "observation_set_sha256": _digest(
                        [_canonical(asdict(row)) for row in rows]
                    ),
                    "audit": _canonical(asdict(audit)),
                }
            )
    finally:
        client.close()

    return {
        "schema": "qore.cibo.t16.post_declaration_market_structure.v1",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "observed_at": observed_at.isoformat(),
        "account_fingerprint_sha256": T16_ACCOUNT_FINGERPRINT_SHA256,
        "provider_catalog_sha256": T16_PROVIDER_CATALOG_SHA256,
        "pair_count": len(pairs),
        "pairs": pairs,
        "hedge_cost_history_claimed": False,
        "execution_cost_history_claimed": False,
        "holdout_outcomes_used": False,
        "holdout_market_data_read": False,
        "broker_mutation_performed": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
