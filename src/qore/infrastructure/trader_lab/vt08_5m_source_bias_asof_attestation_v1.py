"""Auditable source-day/bias provenance for five-market VT08 research.

Reconstructs the two ACTUAL complete source days and their M15 constituents.
No synthetic as-of, no PnL, and no authority to bypass Cognitive B readiness.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    resolve_bias,
    source_day_from_m15,
)

SCHEMA: Final = "qore.vt08.5m.source_bias_provenance.v1"
SOURCE_SHA: Final = "b2d33e1b4829d8b4afc76983decca8a99131403c"
_NY = ZoneInfo("America/New_York")


def _sha_bars(bars: tuple[Vt08B01Bar, ...]) -> str:
    payload = tuple(
        (
            bar.opened_at.astimezone(UTC).isoformat(),
            bar.closed_at.astimezone(UTC).isoformat(),
            str(bar.open),
            str(bar.high),
            str(bar.low),
            str(bar.close),
        )
        for bar in bars
    )
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceDayProof:
    """Reconstructed 17:00 NY→17:00 NY day with authenticated closed M15s."""

    day: Vt08B01Bar
    m15_count: int
    m15_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "opened_at": self.day.opened_at.astimezone(UTC).isoformat(),
            "closed_at": self.day.closed_at.astimezone(UTC).isoformat(),
            "m15_count": self.m15_count,
            "m15_sha256": self.m15_sha256,
            "open": str(self.day.open),
            "high": str(self.day.high),
            "low": str(self.day.low),
            "close": str(self.day.close),
        }


@dataclass(frozen=True, slots=True)
class BiasAsOfAttestation:
    decision_at: datetime
    current_day: SourceDayProof
    previous_day: SourceDayProof
    bias: DemoTradingSetupSide | None

    def __post_init__(self) -> None:
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise ValueError("decision_at must be timezone aware")
        if not (
            self.previous_day.day.closed_at <= self.current_day.day.opened_at
            and self.current_day.day.closed_at <= self.decision_at
        ):
            raise ValueError("bias uses future/overlapping source day")

    def payload(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "decision_at": self.decision_at.astimezone(UTC).isoformat(),
            "bias_feature_cutoff": self.current_day.day.closed_at.astimezone(
                UTC
            ).isoformat(),
            "source_day_current": self.current_day.payload(),
            "source_day_previous": self.previous_day.payload(),
            "bias_side": self.bias.value if self.bias is not None else "UNRESOLVED",
            "bias_rule": "VT08_B01_R3_8_RESOLVE_BIAS_QORE_CONTAINMENT",
            "source_days_end": "17:00_AMERICA_NEW_YORK_QORE",
            "research_only": True,
            "broker_authority": False,
        }


def _day_proof(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    end_date: date,
    as_of: datetime,
) -> SourceDayProof | None:
    complete = source_day_from_m15(bars_by_open, end_date=end_date)
    if complete is None or complete.closed_at > as_of:
        return None
    cursor = complete.opened_at.astimezone(UTC)
    end = complete.closed_at.astimezone(UTC)
    originals: list[Vt08B01Bar] = []
    while cursor < end:
        row = bars_by_open.get(cursor)
        if row is None or row.closed_at.astimezone(UTC) != cursor + timedelta(
            minutes=15
        ):
            return None
        originals.append(row)
        cursor = row.closed_at.astimezone(UTC)
    if cursor != end:
        return None
    if not originals or originals[0].open != complete.open:
        raise AssertionError("source-day OHLC mismatch")
    if (
        originals[-1].close != complete.close
        or min(x.low for x in originals) != complete.low
        or max(x.high for x in originals) != complete.high
    ):
        raise AssertionError("source-day high/low/close mismatch")
    return SourceDayProof(
        day=complete,
        m15_count=len(originals),
        m15_sha256=_sha_bars(tuple(originals)),
    )


def attest_bias(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    decision_at: datetime,
) -> BiasAsOfAttestation | None:
    """Select same historical day window as frozen B01 without changing it."""
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise ValueError("decision_at requires timezone")
    local = decision_at.astimezone(_NY)
    end_date = local.date() - timedelta(days=1)
    proofs: list[SourceDayProof] = []
    for offset in range(10):
        proof = _day_proof(
            bars_by_open,
            end_date=end_date - timedelta(days=offset),
            as_of=decision_at.astimezone(UTC),
        )
        if proof:
            proofs.append(proof)
        if len(proofs) == 2:
            break
    if len(proofs) != 2:
        return None
    return BiasAsOfAttestation(
        decision_at=decision_at,
        current_day=proofs[0],
        previous_day=proofs[1],
        bias=resolve_bias(
            previous_day=proofs[1].day,
            current_day=proofs[0].day,
        ),
    )


def audit_market(path: Path) -> dict[str, object]:
    fp, symbol, checked, sha, m15 = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS or sha != SOURCE_SHA:
        raise ValueError("invalid consumed research evidence")
    indexed = {bar.opened_at: bar for bar in m15}
    ledger: list[dict[str, object]] = []
    reasons: Counter[str] = Counter()
    for bar in m15:
        local = bar.opened_at.astimezone(_NY)
        if local.hour not in ANCHORS_NY or local.minute or local.second:
            continue
        proof = attest_bias(indexed, decision_at=bar.opened_at)
        reason = (
            "BIAS_PROVENANCE_MISSING"
            if proof is None
            else "BIAS_UNRESOLVED"
            if proof.bias is None
            else "BIAS_PROVENANCE_ATTESTED"
        )
        reasons[reason] += 1
        ledger.append({
            "anchor_at": bar.opened_at.astimezone(UTC).isoformat(),
            "ny_date": local.date().isoformat(),
            "anchor_ny_hour": local.hour,
            "status": reason,
            "provenance": proof.payload() if proof else None,
        })
    if sum(reasons.values()) != len(ledger):
        raise AssertionError("anchor/provenance ledger mismatch")
    return {
        "schema": SCHEMA,
        "symbol": symbol,
        "source_sha": sha,
        "consumed_checked_at": checked.isoformat(),
        "account_fingerprint": fp,
        "observed_owner_anchors": len(ledger),
        "reasons": dict(sorted(reasons.items())),
        "ledger": ledger,
        "research_only": True,
        "cognitive_readiness_signed": False,
        "eligible_to_trade": False,
    }
