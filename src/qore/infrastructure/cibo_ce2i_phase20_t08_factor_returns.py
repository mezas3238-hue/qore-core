"""Causal T08 factor-return reconstruction from complete market snapshots.

This module deliberately rejects candidate-conditioned quote sets. T08 correlation
research must observe the complete frozen symbol universe independently of whether
any Trader emitted an opportunity. USD is the account numeraire; cross-FX factor
returns are reconstructed algebraically from synchronized provider marks.

The output is research evidence only. It does not map structural stop risk into
factor risk, certify a correlation state, or authorize portfolio-netting credit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

FROZEN_T08_MARKET_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)
FROZEN_T08_FACTOR_IDS = (
    "AUD",
    "EUR",
    "GBP",
    "JPY",
    "USD",
    "US_TECH_EQUITY_BETA",
    "XAU",
)


class T08MarketCollectionBasis(StrEnum):
    FULL_FROZEN_UNIVERSE = "FULL_FROZEN_UNIVERSE"
    CANDIDATE_ONLY = "CANDIDATE_ONLY"


@dataclass(frozen=True, slots=True)
class T08MarketMark:
    qore_symbol: str
    bid: Decimal
    ask: Decimal
    observed_at: datetime
    evidence_ref: str

    def __post_init__(self) -> None:
        symbol = self.qore_symbol.strip().upper()
        if symbol not in FROZEN_T08_MARKET_SYMBOLS:
            raise CiboCapitalManagementError(
                "T08 market mark symbol outside frozen factor universe"
            )
        if symbol != self.qore_symbol:
            raise CiboCapitalManagementError(
                "T08 market mark symbol must be canonical uppercase"
            )
        for name in ("bid", "ask"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"T08 market mark {name} must be positive finite Decimal"
                )
        if self.ask < self.bid:
            raise CiboCapitalManagementError(
                "T08 market mark ask cannot be below bid"
            )
        _aware(self.observed_at, "T08 market mark observed_at")
        if not self.evidence_ref:
            raise CiboCapitalManagementError(
                "T08 market mark evidence_ref is required"
            )

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal(2)


@dataclass(frozen=True, slots=True)
class T08FactorMarketSnapshot:
    snapshot_id: str
    provider_key: str
    observed_at: datetime
    collection_basis: T08MarketCollectionBasis
    marks: tuple[T08MarketMark, ...]

    def __post_init__(self) -> None:
        if not self.snapshot_id or not self.provider_key:
            raise CiboCapitalManagementError(
                "T08 factor snapshot identity/provider are required"
            )
        _aware(self.observed_at, "T08 factor snapshot observed_at")
        if type(self.collection_basis) is not T08MarketCollectionBasis:
            raise CiboCapitalManagementError(
                "T08 factor snapshot collection basis must be canonical"
            )
        if not self.marks:
            raise CiboCapitalManagementError(
                "T08 factor snapshot requires market marks"
            )
        symbols = tuple(item.qore_symbol for item in self.marks)
        if len(symbols) != len(set(symbols)):
            raise CiboCapitalManagementError(
                "T08 factor snapshot symbols must be unique"
            )
        for mark in self.marks:
            if mark.observed_at != self.observed_at:
                raise CiboCapitalManagementError(
                    "T08 factor snapshot marks must share one causal timestamp"
                )
        if (
            self.collection_basis
            is T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE
            and tuple(sorted(symbols)) != FROZEN_T08_MARKET_SYMBOLS
        ):
            raise CiboCapitalManagementError(
                "T08 full-universe snapshot must contain every frozen symbol"
            )

    @property
    def complete_frozen_universe(self) -> bool:
        return (
            self.collection_basis
            is T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE
            and tuple(sorted(item.qore_symbol for item in self.marks))
            == FROZEN_T08_MARKET_SYMBOLS
        )


@dataclass(frozen=True, slots=True)
class T08FactorReturn:
    factor_id: str
    gross_change: Decimal
    fractional_return: Decimal

    def __post_init__(self) -> None:
        if self.factor_id not in FROZEN_T08_FACTOR_IDS:
            raise CiboCapitalManagementError(
                "T08 factor return uses unknown frozen factor"
            )
        for name in ("gross_change", "fractional_return"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"T08 factor return {name} must be finite Decimal"
                )
        if self.gross_change <= 0:
            raise CiboCapitalManagementError(
                "T08 factor gross change must be positive"
            )
        if self.fractional_return != self.gross_change - Decimal(1):
            raise CiboCapitalManagementError(
                "T08 factor fractional return must match gross change"
            )


@dataclass(frozen=True, slots=True)
class T08FactorReturnObservation:
    provider_key: str
    start_snapshot_id: str
    end_snapshot_id: str
    start_at: datetime
    end_at: datetime
    factor_returns: tuple[T08FactorReturn, ...]
    source_evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not self.provider_key
            or not self.start_snapshot_id
            or not self.end_snapshot_id
        ):
            raise CiboCapitalManagementError(
                "T08 factor-return observation identity/provider required"
            )
        _aware(self.start_at, "T08 factor return start_at")
        _aware(self.end_at, "T08 factor return end_at")
        if self.end_at <= self.start_at:
            raise CiboCapitalManagementError(
                "T08 factor-return interval must move forward in time"
            )
        factor_ids = tuple(item.factor_id for item in self.factor_returns)
        if factor_ids != FROZEN_T08_FACTOR_IDS:
            raise CiboCapitalManagementError(
                "T08 factor-return observation must contain canonical factors"
            )
        if len(self.source_evidence_refs) != len(
            set(self.source_evidence_refs)
        ):
            raise CiboCapitalManagementError(
                "T08 factor-return source evidence refs must be unique"
            )
        if not self.source_evidence_refs:
            raise CiboCapitalManagementError(
                "T08 factor-return source evidence is required"
            )

    def return_for(self, factor_id: str) -> Decimal:
        for item in self.factor_returns:
            if item.factor_id == factor_id:
                return item.fractional_return
        raise CiboCapitalManagementError(
            "T08 factor return requested for unknown factor"
        )


def reconstruct_t08_factor_returns(
    *,
    start: T08FactorMarketSnapshot,
    end: T08FactorMarketSnapshot,
) -> T08FactorReturnObservation:
    """Reconstruct account-numeraire factor returns without candidate selection."""

    if not isinstance(start, T08FactorMarketSnapshot) or not isinstance(
        end,
        T08FactorMarketSnapshot,
    ):
        raise CiboCapitalManagementError(
            "T08 factor-return reconstruction requires canonical snapshots"
        )
    if not start.complete_frozen_universe or not end.complete_frozen_universe:
        raise CiboCapitalManagementError(
            "T08 factor returns reject candidate-conditioned/incomplete snapshots"
        )
    if start.provider_key != end.provider_key:
        raise CiboCapitalManagementError(
            "T08 factor-return snapshots must use one provider"
        )
    if end.observed_at <= start.observed_at:
        raise CiboCapitalManagementError(
            "T08 factor-return snapshots must advance in time"
        )

    start_mid = {item.qore_symbol: item.mid for item in start.marks}
    end_mid = {item.qore_symbol: item.mid for item in end.marks}

    def pair_gross(symbol: str) -> Decimal:
        return end_mid[symbol] / start_mid[symbol]

    gbp = pair_gross("GBPUSD")
    eur = pair_gross("EURUSD")
    jpy = gbp / pair_gross("GBPJPY")
    aud = pair_gross("AUDJPY") * jpy
    usd = Decimal(1)
    tech = pair_gross("NAS100")
    xau = pair_gross("XAUUSD")
    gross_by_factor = {
        "AUD": aud,
        "EUR": eur,
        "GBP": gbp,
        "JPY": jpy,
        "USD": usd,
        "US_TECH_EQUITY_BETA": tech,
        "XAU": xau,
    }

    refs = tuple(
        dict.fromkeys(
            item.evidence_ref
            for snapshot in (start, end)
            for item in snapshot.marks
        )
    )
    return T08FactorReturnObservation(
        provider_key=start.provider_key,
        start_snapshot_id=start.snapshot_id,
        end_snapshot_id=end.snapshot_id,
        start_at=start.observed_at,
        end_at=end.observed_at,
        factor_returns=tuple(
            T08FactorReturn(
                factor_id=factor_id,
                gross_change=gross_by_factor[factor_id],
                fractional_return=(
                    gross_by_factor[factor_id] - Decimal(1)
                ),
            )
            for factor_id in FROZEN_T08_FACTOR_IDS
        ),
        source_evidence_refs=refs,
    )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")
