"""Causal mark-to-market observation for open CIBO positions.

Research-only.  Uses only the latest fully closed market bar at or before the
observation time.  It never consumes the current unfinished bar, future bars,
trade outcome, stop/target result, or broker mutation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar


@dataclass(frozen=True, slots=True)
class CiboPositionMarkRequest:
    signal_fingerprint: str
    qore_symbol: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "position mark request identity required"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "position mark observed_at must be timezone-aware"
            )


@dataclass(frozen=True, slots=True)
class CiboPositionMarkEvidence:
    signal_fingerprint: str
    qore_symbol: str
    observed_at: datetime
    source_bar_opened_at: datetime
    source_bar_closed_at: datetime
    mark_price: Decimal
    evidence_sha256: str
    outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "position mark evidence identity required"
            )
        for name in (
            "observed_at",
            "source_bar_opened_at",
            "source_bar_closed_at",
        ):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"position mark {name} must be timezone-aware"
                )
        if self.source_bar_closed_at > self.observed_at:
            raise CiboCapitalManagementError(
                "position mark cannot consume future/unclosed bar"
            )
        if (
            not isinstance(self.mark_price, Decimal)
            or not self.mark_price.is_finite()
        ):
            raise CiboCapitalManagementError(
                "position mark price must be finite Decimal"
            )
        if (
            not self.evidence_sha256.startswith("sha256:")
            or len(self.evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "position mark evidence digest invalid"
            )
        if self.outcome_used or self.productive_authority:
            raise CiboCapitalManagementError(
                "position mark evidence cannot use outcomes or authority"
            )


def observe_position_mark(
    request: CiboPositionMarkRequest,
    bars: Sequence[Bar],
) -> CiboPositionMarkEvidence | None:
    """Return the latest causally closed mark or None if unavailable."""

    if not isinstance(request, CiboPositionMarkRequest):
        raise CiboCapitalManagementError(
            "position mark observer requires canonical request"
        )
    eligible = tuple(
        bar
        for bar in bars
        if bar.closed_at <= request.observed_at
    )
    if not eligible:
        return None
    bar = max(
        eligible,
        key=lambda item: (item.closed_at, item.opened_at),
    )
    payload = {
        "signal_fingerprint": request.signal_fingerprint,
        "qore_symbol": request.qore_symbol,
        "observed_at": request.observed_at.isoformat(),
        "source_bar_opened_at": bar.opened_at.isoformat(),
        "source_bar_closed_at": bar.closed_at.isoformat(),
        "mark_price": format(bar.close, "f"),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return CiboPositionMarkEvidence(
        signal_fingerprint=request.signal_fingerprint,
        qore_symbol=request.qore_symbol,
        observed_at=request.observed_at,
        source_bar_opened_at=bar.opened_at,
        source_bar_closed_at=bar.closed_at,
        mark_price=bar.close,
        evidence_sha256="sha256:" + hashlib.sha256(raw.encode()).hexdigest(),
        outcome_used=False,
        productive_authority=False,
    )
