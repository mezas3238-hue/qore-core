"""Read-only T03 multi-leg FX margin-efficiency screen."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.cibo_arch2_t03_multileg_math import (
    PairTerms,
    candidate,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
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

_PRICE_SCALE = Decimal("100000")
_CURRENCIES = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")
_TARGETS = ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD")
_EXPECTED_ACCOUNT_FINGERPRINT = (
    "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
)


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
        raise CiboCapitalManagementError(
            f"T03 multi-leg provider request failed: {name}: {result.error}"
        )
    return result.value


def _positive_int(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise CiboCapitalManagementError(
            f"T03 multi-leg {name} must be positive int"
        )
    return value


def _spot_midpoints(
    client: SpotwareCTraderOpenApiClient,
    symbol_ids: tuple[int, ...],
) -> dict[int, Decimal]:
    subscribed = client.request(
        "ProtoOASubscribeSpotsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": list(symbol_ids),
            "subscribeToSpotTimestamp": True,
        },
        client_msg_id="qore-cibo-arch2-t03-spots",
        timeout_seconds=10.0,
    )
    if isinstance(subscribed, Failure) and "ALREADY_SUBSCRIBED" not in str(
        subscribed.error
    ):
        raise CiboCapitalManagementError(str(subscribed.error))
    wanted = set(symbol_ids)
    partial: dict[int, tuple[int | None, int | None]] = {}
    deadline = datetime.now(UTC).timestamp() + 12.0
    while True:
        if set(partial) == wanted and all(
            bid is not None and ask is not None
            for bid, ask in partial.values()
        ):
            break
        remaining = deadline - datetime.now(UTC).timestamp()
        if remaining <= 0:
            raise CiboCapitalManagementError(
                "T03 multi-leg spot collection timed out"
            )
        event = client.wait_for_event(
            "ProtoOASpotEvent",
            timeout_seconds=min(1.0, remaining),
        )
        if isinstance(event, Failure):
            continue
        item = event.value
        symbol_id = getattr(item, "symbolId", None)
        if symbol_id not in wanted:
            continue
        previous = partial.get(int(symbol_id), (None, None))
        raw_bid = getattr(item, "bid", None)
        raw_ask = getattr(item, "ask", None)
        bid = raw_bid if type(raw_bid) is int and raw_bid > 0 else previous[0]
        ask = raw_ask if type(raw_ask) is int and raw_ask > 0 else previous[1]
        partial[int(symbol_id)] = (bid, ask)
    result: dict[int, Decimal] = {}
    for symbol_id, (bid_raw, ask_raw) in partial.items():
        if bid_raw is None or ask_raw is None or ask_raw < bid_raw:
            raise CiboCapitalManagementError(
                "T03 multi-leg provider spot invalid"
            )
        bid_price = Decimal(bid_raw) / _PRICE_SCALE
        ask_price = Decimal(ask_raw) / _PRICE_SCALE
        result[symbol_id] = (bid_price + ask_price) / Decimal(2)
    return result


def _collect_terms(
    client: SpotwareCTraderOpenApiClient,
    pair_symbols: dict[str, int],
) -> dict[str, PairTerms]:
    ids = tuple(sorted(set(pair_symbols.values())))
    details_response = _request(
        client,
        "ProtoOASymbolByIdReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": list(ids),
        },
        "qore-cibo-arch2-t03-details",
    )
    details = {
        int(item.symbolId): item
        for item in tuple(getattr(details_response, "symbol", ()))
    }
    mids = _spot_midpoints(client, ids)
    result: dict[str, PairTerms] = {}
    for symbol, symbol_id in sorted(pair_symbols.items()):
        detail = details.get(symbol_id)
        if detail is None:
            raise CiboCapitalManagementError(
                f"T03 multi-leg detail missing: {symbol}"
            )
        lot_size = _positive_int(
            getattr(detail, "lotSize", None),
            f"{symbol}.lotSize",
        )
        margin_response = _request(
            client,
            "ProtoOAExpectedMarginReq",
            {
                "ctidTraderAccountId": client.account_id,
                "symbolId": symbol_id,
                "volume": [lot_size],
            },
            f"qore-cibo-arch2-t03-margin-{symbol.lower()}",
        )
        money_digits = getattr(margin_response, "moneyDigits", None)
        if type(money_digits) is not int or money_digits < 0:
            raise CiboCapitalManagementError(
                f"T03 multi-leg margin digits invalid: {symbol}"
            )
        rows = tuple(getattr(margin_response, "margin", ()))
        if len(rows) != 1:
            raise CiboCapitalManagementError(
                f"T03 multi-leg margin quote missing: {symbol}"
            )
        row = rows[0]
        scale = Decimal(1).scaleb(-money_digits)
        buy = Decimal(
            _positive_int(
                getattr(row, "buyMargin", None),
                f"{symbol}.buyMargin",
            )
        ) * scale
        sell = Decimal(
            _positive_int(
                getattr(row, "sellMargin", None),
                f"{symbol}.sellMargin",
            )
        ) * scale
        result[symbol] = PairTerms(
            symbol=symbol,
            base=symbol[:3],
            quote=symbol[3:],
            midpoint=mids[symbol_id],
            lot_size_cents=lot_size,
            buy_margin_per_native_cent=buy / Decimal(lot_size),
            sell_margin_per_native_cent=sell / Decimal(lot_size),
        )
    return result


def build_report() -> dict[str, object]:
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        capability = collect_ctrader_demo_account_capability(client)
        account_fingerprint = hashlib.sha256(
            capability.account_ref.encode("utf-8")
        ).hexdigest()
        if account_fingerprint != _EXPECTED_ACCOUNT_FINGERPRINT:
            raise CiboCapitalManagementError(
                "T03 multi-leg account fingerprint drift"
            )
        pair_symbols: dict[str, int] = {}
        for item in capability.symbols:
            name = item.symbol_name
            if (
                item.enabled
                and len(name) == 6
                and name[:3] in _CURRENCIES
                and name[3:] in _CURRENCIES
                and name[:3] != name[3:]
            ):
                pair_symbols[name] = item.symbol_id
        missing = [name for name in _TARGETS if name not in pair_symbols]
        if missing:
            raise CiboCapitalManagementError(
                "T03 multi-leg target unavailable: " + ",".join(missing)
            )
        terms = _collect_terms(client, pair_symbols)
        target_reports: list[dict[str, object]] = []
        global_lower = False
        for target_name in _TARGETS:
            target = terms[target_name]
            candidates: list[dict[str, object]] = []
            for pivot in _CURRENCIES:
                if pivot in {target.base, target.quote}:
                    continue
                long_row = candidate(
                    target=target,
                    pivot=pivot,
                    pairs=terms,
                    target_side="BUY",
                )
                short_row = candidate(
                    target=target,
                    pivot=pivot,
                    pairs=terms,
                    target_side="SELL",
                )
                if long_row is None or short_row is None:
                    continue
                robust_lower = (
                    bool(long_row["continuous_lower_margin"])
                    and bool(short_row["continuous_lower_margin"])
                )
                global_lower = global_lower or robust_lower
                candidates.append(
                    {
                        "pivot": pivot,
                        "long": long_row,
                        "short": short_row,
                        "continuous_lower_margin_both_sides": robust_lower,
                    }
                )
            target_reports.append(
                {
                    "target": target_name,
                    "candidate_count": len(candidates),
                    "candidates": candidates,
                    "continuous_lower_margin_candidate_identified": any(
                        bool(item["continuous_lower_margin_both_sides"])
                        for item in candidates
                    ),
                }
            )
        return {
            "schema": "qore.cibo.arch2.t03.multileg-margin-screen.v1",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_fingerprint_sha256": account_fingerprint,
            "catalog_sha256": capability.catalog_sha256,
            "catalog_symbol_count": len(capability.symbols),
            "enabled_fx_pair_count": len(pair_symbols),
            "targets": target_reports,
            "any_continuous_lower_margin_candidate_identified": global_lower,
            "continuous_screen_only": True,
            "discrete_volume_equivalence_proven": False,
            "execution_economics_proven": False,
            "fresh_oos_utility_proven": False,
            "holdout_outcomes_used": False,
            "broker_mutation_performed": False,
            "productive_authority": False,
        }
    finally:
        client.close()


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
    print(
        json.dumps(
            {
                "enabled_fx_pair_count": report["enabled_fx_pair_count"],
                "any_continuous_lower_margin_candidate_identified": report[
                    "any_continuous_lower_margin_candidate_identified"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
