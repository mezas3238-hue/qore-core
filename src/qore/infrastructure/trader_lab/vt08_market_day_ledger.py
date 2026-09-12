"""Revision 3.2 VT-08 market-day diagnostic ledger.

This layer enriches the generic one-trade-per-New-York-date authority with
source-model diagnostics. It never chooses which qualified setup wins.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from qore.infrastructure.trader_lab.trader_daily_cardinality import MarketDayLedger
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import (
    VT08LtfProfile,
    VT08MarketFamily,
    VT08TimingProfile,
    anchor_hours,
)
from qore.kernel.errors import InfrastructureError


class VT08MarketDayLedgerError(InfrastructureError):
    __slots__ = ()


class VT08MarketDayLedgerValidationError(VT08MarketDayLedgerError):
    __slots__ = ()


def _unique(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise VT08MarketDayLedgerValidationError(f"{field_name} must be tuple")
    if any(type(item) is not str or not item.strip() for item in values):
        raise VT08MarketDayLedgerValidationError(f"{field_name} contains invalid id")
    if len(set(values)) != len(values):
        raise VT08MarketDayLedgerValidationError(f"{field_name} contains duplicates")
    return values


@dataclass(frozen=True, slots=True)
class VT08MarketDayLedger:
    cardinality: MarketDayLedger
    market_family: VT08MarketFamily
    timing_profile: VT08TimingProfile
    ltf_profile: VT08LtfProfile
    c2_candidate_ids: tuple[str, ...] = ()
    c3_candidate_ids: tuple[str, ...] = ()
    protected_swing_candidate_ids: tuple[str, ...] = ()
    entry_family_candidate_ids: tuple[str, ...] = ()
    stop_family_candidate_ids: tuple[str, ...] = ()
    target_family_candidate_ids: tuple[str, ...] = ()
    source_provenance: tuple[str, ...] = ()
    time_exit_trade_id: str | None = None

    def __post_init__(self) -> None:
        if type(self.cardinality) is not MarketDayLedger:
            raise VT08MarketDayLedgerValidationError("cardinality must be exact ledger")
        if type(self.market_family) is not VT08MarketFamily:
            raise VT08MarketDayLedgerValidationError("market_family must be exact")
        if type(self.timing_profile) is not VT08TimingProfile:
            raise VT08MarketDayLedgerValidationError("timing_profile must be exact")
        if type(self.ltf_profile) is not VT08LtfProfile:
            raise VT08MarketDayLedgerValidationError("ltf_profile must be exact")
        expected = anchor_hours(self.market_family, self.timing_profile)
        if self.cardinality.authorized_windows != expected:
            raise VT08MarketDayLedgerValidationError(
                "cardinality windows do not match VT-08 timing profile"
            )
        for field_name, values in (
            ("c2_candidate_ids", self.c2_candidate_ids),
            ("c3_candidate_ids", self.c3_candidate_ids),
            ("protected_swing_candidate_ids", self.protected_swing_candidate_ids),
            ("entry_family_candidate_ids", self.entry_family_candidate_ids),
            ("stop_family_candidate_ids", self.stop_family_candidate_ids),
            ("target_family_candidate_ids", self.target_family_candidate_ids),
            ("source_provenance", self.source_provenance),
        ):
            _unique(values, field_name=field_name)
        if self.time_exit_trade_id is not None:
            if type(self.time_exit_trade_id) is not str or not self.time_exit_trade_id.strip():
                raise VT08MarketDayLedgerValidationError("time_exit_trade_id is invalid")
            if self.cardinality.terminal_trade_id != self.time_exit_trade_id:
                raise VT08MarketDayLedgerValidationError(
                    "time exit must identify the terminal trade in cardinality ledger"
                )

    def add_scenario_candidate(
        self,
        *,
        candidate_id: str,
        scenario: Literal["c2", "c3"],
    ) -> "VT08MarketDayLedger":
        cardinality = self.cardinality.add_candidate(candidate_id)
        if scenario == "c2":
            if candidate_id in self.c2_candidate_ids:
                raise VT08MarketDayLedgerValidationError("duplicate C2 candidate")
            return replace(
                self,
                cardinality=cardinality,
                c2_candidate_ids=(*self.c2_candidate_ids, candidate_id),
            )
        if scenario == "c3":
            if candidate_id in self.c3_candidate_ids:
                raise VT08MarketDayLedgerValidationError("duplicate C3 candidate")
            return replace(
                self,
                cardinality=cardinality,
                c3_candidate_ids=(*self.c3_candidate_ids, candidate_id),
            )
        raise VT08MarketDayLedgerValidationError("scenario must be c2 or c3")

    def add_diagnostic(
        self,
        *,
        diagnostic_id: str,
        category: Literal["protected-swing", "entry", "stop", "target"],
    ) -> "VT08MarketDayLedger":
        if type(diagnostic_id) is not str or not diagnostic_id.strip():
            raise VT08MarketDayLedgerValidationError("diagnostic_id is invalid")
        if category == "protected-swing":
            if diagnostic_id in self.protected_swing_candidate_ids:
                raise VT08MarketDayLedgerValidationError("duplicate diagnostic identity")
            return replace(
                self,
                protected_swing_candidate_ids=(
                    *self.protected_swing_candidate_ids,
                    diagnostic_id,
                ),
            )
        if category == "entry":
            if diagnostic_id in self.entry_family_candidate_ids:
                raise VT08MarketDayLedgerValidationError("duplicate diagnostic identity")
            return replace(
                self,
                entry_family_candidate_ids=(*self.entry_family_candidate_ids, diagnostic_id),
            )
        if category == "stop":
            if diagnostic_id in self.stop_family_candidate_ids:
                raise VT08MarketDayLedgerValidationError("duplicate diagnostic identity")
            return replace(
                self,
                stop_family_candidate_ids=(*self.stop_family_candidate_ids, diagnostic_id),
            )
        if category == "target":
            if diagnostic_id in self.target_family_candidate_ids:
                raise VT08MarketDayLedgerValidationError("duplicate diagnostic identity")
            return replace(
                self,
                target_family_candidate_ids=(
                    *self.target_family_candidate_ids,
                    diagnostic_id,
                ),
            )
        raise VT08MarketDayLedgerValidationError("unsupported diagnostic category")

    def record_time_exit(self, terminal_trade_id: str) -> "VT08MarketDayLedger":
        if self.cardinality.terminal_trade_id != terminal_trade_id:
            raise VT08MarketDayLedgerValidationError(
                "time exit must match the already terminal cardinality trade"
            )
        if self.time_exit_trade_id is not None:
            raise VT08MarketDayLedgerValidationError("time exit already recorded")
        return replace(self, time_exit_trade_id=terminal_trade_id)

    def payload(self) -> dict[str, object]:
        base = self.cardinality.payload()
        base.update(
            {
                "market_family": self.market_family.value,
                "timing_profile": self.timing_profile.value,
                "ltf_profile": self.ltf_profile.value,
                "authorized_anchor_hours": list(self.cardinality.authorized_windows),
                "observed_anchor_hours": list(self.cardinality.observed_windows),
                "window_count": len(self.cardinality.observed_windows),
                "c2_candidate_count": len(self.c2_candidate_ids),
                "c3_candidate_count": len(self.c3_candidate_ids),
                "protected_swing_candidates": len(self.protected_swing_candidate_ids),
                "entry_family_candidates": len(self.entry_family_candidate_ids),
                "stop_family_candidates": len(self.stop_family_candidate_ids),
                "target_family_candidates": len(self.target_family_candidate_ids),
                "time_exit_count": int(self.time_exit_trade_id is not None),
                "source_provenance": list(self.source_provenance),
            }
        )
        return base
