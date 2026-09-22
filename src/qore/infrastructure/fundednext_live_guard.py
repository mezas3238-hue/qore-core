"""Fail-closed operational guards for the FundedNext VT-08 live runtime.

These guards do not create trading authority or change the certified VT-08
methodology.  They restrict the live path to a causal subset of the certified
portfolio and ensure that broker-executable risk cannot exceed sovereign Risk.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.kernel.errors import InfrastructureError

_NY = ZoneInfo("America/New_York")
_SCHEMA = "qore.fundednext.live-capital-checkpoint.v1"

CERTIFIED_LIVE_DIRECTIONS: dict[str, frozenset[str]] = {
    "AUDJPY": frozenset({"short"}),
    "GBPUSD": frozenset({"short"}),
    "GBPJPY": frozenset({"long", "short"}),
    "EURUSD": frozenset({"long", "short"}),
    "XAUUSD": frozenset({"long", "short"}),
    "NAS100": frozenset({"long", "short"}),
}
LIVE_ENTRY_ANCHORS_NY = (1, 5, 9)
MAX_LIVE_ENTRY_DRIFT_TICKS = Decimal("1")
FOREX_OPEN_COMMISSION_PER_LOT_USD = Decimal("7")
INACTIVITY_WARNING_DAYS = 25
INACTIVITY_BLOCK_DAYS = 30


class FundedNextLiveGuardError(InfrastructureError):
    __slots__ = ()


class InactivityState(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


def assert_certified_direction(symbol: str, side: str) -> None:
    allowed = CERTIFIED_LIVE_DIRECTIONS.get(symbol)
    if allowed is None or side not in allowed:
        raise FundedNextLiveGuardError("direction-outside-certified-live-portfolio")


def causal_daily_candidate_allowed(
    *,
    candidate_anchor_hours: tuple[int, ...],
    current_anchor_hour: int,
) -> bool:
    """Permit the current causal VT-08 Forex anchor at 01/05/09 New York.

    Only information observable at the current anchor is considered.  Prior same-day
    candidates do not suppress a later authorized anchor; CIBO and sovereign Risk keep
    their existing authority over each candidate that reaches the live pipeline.
    """

    normalized = tuple(sorted(candidate_anchor_hours))
    return (
        current_anchor_hour in LIVE_ENTRY_ANCHORS_NY
        and current_anchor_hour in normalized
    )


def market_stop_risk_usd(
    *,
    executable_entry: Decimal,
    stop_loss: Decimal,
    tick_size: Decimal,
    tick_value: Decimal,
    volume: Decimal,
    opening_commission_per_lot: Decimal = FOREX_OPEN_COMMISSION_PER_LOT_USD,
) -> Decimal:
    for name, value in (
        ("executable_entry", executable_entry),
        ("stop_loss", stop_loss),
        ("tick_size", tick_size),
        ("tick_value", tick_value),
        ("volume", volume),
    ):
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            raise FundedNextLiveGuardError(f"{name} must be positive finite Decimal")
    if opening_commission_per_lot < 0:
        raise FundedNextLiveGuardError("opening commission cannot be negative")
    price_risk = abs(executable_entry - stop_loss) / tick_size * tick_value * volume
    return price_risk + opening_commission_per_lot * volume


def entry_drift_ticks(
    *,
    intended_entry: Decimal,
    executable_entry: Decimal,
    tick_size: Decimal,
) -> Decimal:
    if tick_size <= 0:
        raise FundedNextLiveGuardError("tick_size must be positive")
    return abs(executable_entry - intended_entry) / tick_size


def assert_certified_entry_drift(
    *,
    intended_entry: Decimal,
    executable_entry: Decimal,
    tick_size: Decimal,
) -> None:
    if entry_drift_ticks(
        intended_entry=intended_entry,
        executable_entry=executable_entry,
        tick_size=tick_size,
    ) > MAX_LIVE_ENTRY_DRIFT_TICKS:
        raise FundedNextLiveGuardError("live-entry-drift-exceeds-certified-containment")


def h4_containment_exit_at(signal_at: datetime) -> datetime:
    _aware(signal_at, "signal_at")
    local = signal_at.astimezone(_NY)
    if local.minute != 0 or local.second != 0 or local.microsecond != 0:
        raise FundedNextLiveGuardError("signal_at must be exact H4 anchor")
    return (local + timedelta(hours=4)).astimezone(UTC)


def inactivity_state(*, last_activity_at: datetime, now: datetime) -> InactivityState:
    _aware(last_activity_at, "last_activity_at")
    _aware(now, "now")
    if now < last_activity_at:
        raise FundedNextLiveGuardError("inactivity clock moved backwards")
    age = now - last_activity_at
    if age >= timedelta(days=INACTIVITY_BLOCK_DAYS):
        return InactivityState.BLOCKED
    if age >= timedelta(days=INACTIVITY_WARNING_DAYS):
        return InactivityState.WARNING
    return InactivityState.OK


@dataclass(frozen=True, slots=True)
class FundedNextLiveCapitalCheckpoint:
    git_sha: str
    account_identity_fingerprint: str
    highest_closed_balance: Decimal
    active_mll: Decimal
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if len(self.git_sha) != 40:
            raise FundedNextLiveGuardError("capital checkpoint requires full Git SHA")
        if len(self.account_identity_fingerprint) != 64:
            raise FundedNextLiveGuardError("capital checkpoint account fingerprint invalid")
        for name, value in (
            ("highest_closed_balance", self.highest_closed_balance),
            ("active_mll", self.active_mll),
        ):
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise FundedNextLiveGuardError(f"{name} must be positive finite Decimal")
        _aware(self.created_at, "created_at")
        _aware(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise FundedNextLiveGuardError("capital checkpoint time moved backwards")

    def advance(
        self,
        *,
        highest_closed_balance: Decimal,
        active_mll: Decimal,
        updated_at: datetime,
    ) -> FundedNextLiveCapitalCheckpoint:
        _aware(updated_at, "updated_at")
        if highest_closed_balance < self.highest_closed_balance:
            raise FundedNextLiveGuardError("highest closed balance cannot move downward")
        if active_mll < self.active_mll:
            raise FundedNextLiveGuardError("active MLL cannot move downward")
        return replace(
            self,
            highest_closed_balance=highest_closed_balance,
            active_mll=active_mll,
            updated_at=updated_at,
        )


class DurableFundedNextLiveCapitalStore:
    """Two-copy atomic store; both copies missing after closeout fails closed."""

    def __init__(self, primary: Path, backup: Path) -> None:
        if primary == backup:
            raise FundedNextLiveGuardError("capital checkpoint copies must differ")
        self._primary = primary
        self._backup = backup

    def load_required(self) -> FundedNextLiveCapitalCheckpoint:
        primary = self._load(self._primary)
        backup = self._load(self._backup)
        if primary is None and backup is None:
            raise FundedNextLiveGuardError("durable-capital-checkpoint-missing")
        if primary is None:
            assert backup is not None
            self.store(backup)
            return backup
        if backup is None:
            self.store(primary)
            return primary
        if primary != backup:
            raise FundedNextLiveGuardError("durable-capital-checkpoint-copies-diverged")
        return primary

    def initialize_once(self, checkpoint: FundedNextLiveCapitalCheckpoint) -> None:
        if self._primary.exists() or self._backup.exists():
            raise FundedNextLiveGuardError("capital checkpoint already initialized")
        self.store(checkpoint)

    def store(self, checkpoint: FundedNextLiveCapitalCheckpoint) -> None:
        if not isinstance(checkpoint, FundedNextLiveCapitalCheckpoint):
            raise FundedNextLiveGuardError("canonical capital checkpoint required")
        payload = {
            "schema": _SCHEMA,
            "git_sha": checkpoint.git_sha,
            "account_identity_fingerprint": checkpoint.account_identity_fingerprint,
            "highest_closed_balance": str(checkpoint.highest_closed_balance),
            "active_mll": str(checkpoint.active_mll),
            "created_at": checkpoint.created_at.astimezone(UTC).isoformat(),
            "updated_at": checkpoint.updated_at.astimezone(UTC).isoformat(),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        self._atomic_write(self._primary, encoded)
        self._atomic_write(self._backup, encoded)

    @staticmethod
    def _load(path: Path) -> FundedNextLiveCapitalCheckpoint | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
                raise FundedNextLiveGuardError("capital checkpoint schema mismatch")
            return FundedNextLiveCapitalCheckpoint(
                git_sha=str(payload["git_sha"]),
                account_identity_fingerprint=str(payload["account_identity_fingerprint"]),
                highest_closed_balance=Decimal(str(payload["highest_closed_balance"])),
                active_mll=Decimal(str(payload["active_mll"])),
                created_at=datetime.fromisoformat(str(payload["created_at"])),
                updated_at=datetime.fromisoformat(str(payload["updated_at"])),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise FundedNextLiveGuardError("capital checkpoint unreadable") from error

    @staticmethod
    def _atomic_write(path: Path, encoded: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise FundedNextLiveGuardError(f"{name} must be timezone-aware")
