"""Read-only delayed M5 collector for CE2I T08 factor evidence.

The collector intentionally runs after the M5 bar that opened at the requested
boundary has closed. It reads that finalized bar for every frozen T08 market,
including NAS100, and returns exact boundary opens. It has no sizing, Risk,
execution, or broker mutation authority and is designed to run outside the
2-second execution-critical path.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    FROZEN_T08_MARKET_SYMBOLS,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_store import (
    DurableT08FactorEvidenceError,
    T08FinalizedBoundaryOpen,
)
from qore.infrastructure.ctrader_demo_compat import (
    normalise_legacy_server_epoch,
)

M5_BAR_DURATION = timedelta(minutes=5)
DEFAULT_LOOKBACK_BARS = 16


def collect_finalized_t08_m5_boundary_opens(
    api: Any,
    *,
    provider_symbols: Mapping[str, str],
    boundary_at: datetime,
    observed_at: datetime,
    lookback_bars: int = DEFAULT_LOOKBACK_BARS,
) -> tuple[T08FinalizedBoundaryOpen, ...]:
    """Read the exact finalized M5 bar opened at boundary for all T08 markets."""

    _aware(boundary_at, "T08 M5 collector boundary_at")
    _aware(observed_at, "T08 M5 collector observed_at")
    if observed_at < boundary_at + M5_BAR_DURATION:
        raise DurableT08FactorEvidenceError(
            "T08 M5 collector must wait until boundary bar is finalized"
        )
    if (
        not isinstance(lookback_bars, int)
        or isinstance(lookback_bars, bool)
        or lookback_bars < 2
        or lookback_bars > 64
    ):
        raise DurableT08FactorEvidenceError(
            "T08 M5 collector lookback must be int in [2, 64]"
        )
    if tuple(sorted(provider_symbols)) != FROZEN_T08_MARKET_SYMBOLS:
        raise DurableT08FactorEvidenceError(
            "T08 M5 collector provider map must cover exact frozen universe"
        )
    if not hasattr(api, "TIMEFRAME_M5"):
        raise DurableT08FactorEvidenceError(
            "T08 M5 collector API missing TIMEFRAME_M5"
        )

    observations: list[T08FinalizedBoundaryOpen] = []
    for qore_symbol in FROZEN_T08_MARKET_SYMBOLS:
        provider_symbol = provider_symbols[qore_symbol]
        if not isinstance(provider_symbol, str) or not provider_symbol:
            raise DurableT08FactorEvidenceError(
                "T08 M5 collector provider symbol is required"
            )
        rows = api.copy_rates_from_pos(
            provider_symbol,
            api.TIMEFRAME_M5,
            0,
            lookback_bars,
        )
        if rows is None:
            raise DurableT08FactorEvidenceError(
                f"T08 M5 collector rows unavailable:{qore_symbol}"
            )
        match = None
        for row in rows:
            try:
                opened_at = normalise_legacy_server_epoch(int(row["time"]))
            except (KeyError, TypeError, ValueError) as error:
                raise DurableT08FactorEvidenceError(
                    f"T08 M5 collector invalid row:{qore_symbol}"
                ) from error
            if opened_at == boundary_at:
                match = row
                break
        if match is None:
            raise DurableT08FactorEvidenceError(
                f"T08 M5 finalized boundary bar missing:{qore_symbol}"
            )

        try:
            open_price = Decimal(str(match["open"]))
            high = Decimal(str(match["high"]))
            low = Decimal(str(match["low"]))
            close = Decimal(str(match["close"]))
        except (KeyError, ValueError, TypeError) as error:
            raise DurableT08FactorEvidenceError(
                f"T08 M5 collector OHLC invalid:{qore_symbol}"
            ) from error
        for name, value in (
            ("open", open_price),
            ("high", high),
            ("low", low),
            ("close", close),
        ):
            if not value.is_finite() or value <= 0:
                raise DurableT08FactorEvidenceError(
                    f"T08 M5 collector {name} invalid:{qore_symbol}"
                )
        if high < max(open_price, close) or low > min(open_price, close):
            raise DurableT08FactorEvidenceError(
                f"T08 M5 collector OHLC geometry invalid:{qore_symbol}"
            )

        evidence = {
            "qore_symbol": qore_symbol,
            "provider_symbol": provider_symbol,
            "boundary_at": boundary_at.isoformat(),
            "bar_closed_at": (boundary_at + M5_BAR_DURATION).isoformat(),
            "open": str(open_price),
            "high": str(high),
            "low": str(low),
            "close": str(close),
            "observed_at": observed_at.isoformat(),
        }
        observations.append(
            T08FinalizedBoundaryOpen(
                qore_symbol=qore_symbol,
                boundary_at=boundary_at,
                open_price=open_price,
                observed_at=observed_at,
                evidence_ref="sha256:" + _sha256_json(evidence),
                finalized=True,
            )
        )
    return tuple(observations)


def _sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DurableT08FactorEvidenceError(
            f"{name} must be timezone-aware"
        )
