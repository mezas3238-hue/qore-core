"""Persistent QORE Risk capitalization mission for the FundedNext 2K -> 5K path.

The mission is economic context only. It never creates a signal, widens a stop,
changes a trader methodology, or bypasses provider/QORE Risk authority.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.risk.capitalization-mission.v1"
MISSION_ID = "FUNDEDNEXT_2K_TO_5K_CAPITALIZATION"
TARGET_ACCOUNT_SIZE_USD = Decimal("5000")
POST_WITHDRAWAL_RESERVE_FRACTION = Decimal("0.03")


class CapitalizationMissionError(InfrastructureError):
    __slots__ = ()


class CapitalizationMissionState(StrEnum):
    CAPITALIZE = "CAPITALIZE"
    BANK = "BANK"
    DEFEND = "DEFEND"
    TARGET_REACHED = "TARGET_REACHED"
    PAYOUT_READY = "PAYOUT_READY"
    MISSION_COMPLETE = "MISSION_COMPLETE"


def _money_ceil(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CapitalizationMissionError("money value must be finite Decimal")
    return value.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


def _nonnegative(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise CapitalizationMissionError(f"{name} must be non-negative finite Decimal")


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise CapitalizationMissionError(f"{name} must be positive finite Decimal")


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CapitalizationMissionError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CapitalizationMissionConfig:
    mission_id: str
    account_identity_fingerprint: str
    start_balance: Decimal
    target_account_size: Decimal
    purchase_cash_required: Decimal
    reward_split_fraction: Decimal
    post_withdrawal_reserve: Decimal

    def __post_init__(self) -> None:
        if self.mission_id != MISSION_ID:
            raise CapitalizationMissionError("unexpected capitalization mission id")
        if len(self.account_identity_fingerprint) != 64:
            raise CapitalizationMissionError("mission account fingerprint must be SHA-256")
        for name, value in (
            ("start_balance", self.start_balance),
            ("target_account_size", self.target_account_size),
            ("purchase_cash_required", self.purchase_cash_required),
            ("post_withdrawal_reserve", self.post_withdrawal_reserve),
        ):
            _positive(value, name)
        if (
            not isinstance(self.reward_split_fraction, Decimal)
            or not self.reward_split_fraction.is_finite()
            or self.reward_split_fraction <= 0
            or self.reward_split_fraction > 1
        ):
            raise CapitalizationMissionError(
                "reward_split_fraction must be Decimal in (0, 1]"
            )
        if self.target_account_size != TARGET_ACCOUNT_SIZE_USD:
            raise CapitalizationMissionError("mission target account must remain 5K")

    @property
    def gross_reward_required(self) -> Decimal:
        return _money_ceil(self.purchase_cash_required / self.reward_split_fraction)

    @property
    def minimum_trading_profit_target(self) -> Decimal:
        return self.gross_reward_required + self.post_withdrawal_reserve

    @property
    def mission_balance_target(self) -> Decimal:
        return self.start_balance + self.minimum_trading_profit_target

    @property
    def bank_balance_threshold(self) -> Decimal:
        return self.start_balance + self.gross_reward_required

    @property
    def fingerprint(self) -> str:
        material = {
            "mission_id": self.mission_id,
            "account_identity_fingerprint": self.account_identity_fingerprint,
            "start_balance": str(self.start_balance),
            "target_account_size": str(self.target_account_size),
            "purchase_cash_required": str(self.purchase_cash_required),
            "reward_split_fraction": str(self.reward_split_fraction),
            "post_withdrawal_reserve": str(self.post_withdrawal_reserve),
        }
        return sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class CapitalizationMissionSnapshot:
    mission_id: str
    account_identity_fingerprint: str
    config_fingerprint: str
    state: CapitalizationMissionState
    current_closed_balance: Decimal
    current_equity: Decimal
    realized_profit: Decimal
    target_remaining: Decimal
    purchase_cash_required: Decimal
    gross_reward_required: Decimal
    post_withdrawal_reserve: Decimal
    bank_balance_threshold: Decimal
    mission_balance_target: Decimal
    highest_closed_balance_seen: Decimal
    bank_latched: bool
    target_reached_latched: bool
    payout_ready_latched: bool
    mission_complete: bool
    new_risk_allowed_by_mission: bool
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.mission_id != MISSION_ID:
            raise CapitalizationMissionError("mission snapshot id mismatch")
        if len(self.account_identity_fingerprint) != 64:
            raise CapitalizationMissionError("mission snapshot account fingerprint invalid")
        if len(self.config_fingerprint) != 64:
            raise CapitalizationMissionError("mission snapshot config fingerprint invalid")
        if type(self.state) is not CapitalizationMissionState:
            raise CapitalizationMissionError("mission snapshot state invalid")
        for name, value in (
            ("current_closed_balance", self.current_closed_balance),
            ("current_equity", self.current_equity),
            ("purchase_cash_required", self.purchase_cash_required),
            ("gross_reward_required", self.gross_reward_required),
            ("post_withdrawal_reserve", self.post_withdrawal_reserve),
            ("bank_balance_threshold", self.bank_balance_threshold),
            ("mission_balance_target", self.mission_balance_target),
            ("highest_closed_balance_seen", self.highest_closed_balance_seen),
        ):
            _positive(value, name)
        _nonnegative(self.target_remaining, "target_remaining")
        if not isinstance(self.realized_profit, Decimal) or not self.realized_profit.is_finite():
            raise CapitalizationMissionError("realized_profit must be finite Decimal")
        _aware(self.updated_at, "updated_at")
        for name, flag in (
            ("bank_latched", self.bank_latched),
            ("target_reached_latched", self.target_reached_latched),
            ("payout_ready_latched", self.payout_ready_latched),
            ("mission_complete", self.mission_complete),
            ("new_risk_allowed_by_mission", self.new_risk_allowed_by_mission),
        ):
            if type(flag) is not bool:
                raise CapitalizationMissionError(f"{name} must be bool")
        if self.target_reached_latched and not self.bank_latched:
            raise CapitalizationMissionError("target reached requires BANK to be latched")
        if self.payout_ready_latched and not self.target_reached_latched:
            raise CapitalizationMissionError("payout ready requires target reached")
        if self.mission_complete and not self.payout_ready_latched:
            raise CapitalizationMissionError("mission complete requires payout ready")
        if self.state in {
            CapitalizationMissionState.TARGET_REACHED,
            CapitalizationMissionState.PAYOUT_READY,
            CapitalizationMissionState.MISSION_COMPLETE,
        } and self.new_risk_allowed_by_mission:
            raise CapitalizationMissionError(
                "capitalization mission cannot authorize new risk after target"
            )


def evaluate_capitalization_mission(
    *,
    config: CapitalizationMissionConfig,
    closed_balance: Decimal,
    equity: Decimal,
    now: datetime,
    previous: CapitalizationMissionSnapshot | None,
    defend: bool,
    payout_eligible: bool,
    mission_complete: bool = False,
) -> CapitalizationMissionSnapshot:
    """Update mission cognition from realized account economics.

    The state is path-aware: BANK and TARGET_REACHED latch once achieved. A
    provider/QORE risk rejection can overlay DEFEND without clearing those latches.
    """

    if not isinstance(config, CapitalizationMissionConfig):
        raise CapitalizationMissionError("canonical mission config required")
    _positive(closed_balance, "closed_balance")
    _positive(equity, "equity")
    _aware(now, "now")
    if type(defend) is not bool or type(payout_eligible) is not bool:
        raise CapitalizationMissionError("mission flags must be bool")
    if type(mission_complete) is not bool:
        raise CapitalizationMissionError("mission_complete must be bool")

    highest = closed_balance
    bank_latched = closed_balance >= config.bank_balance_threshold
    target_latched = closed_balance >= config.mission_balance_target
    payout_latched = target_latched and payout_eligible

    if previous is not None:
        if previous.mission_id != config.mission_id:
            raise CapitalizationMissionError("prior mission id mismatch")
        if previous.account_identity_fingerprint != config.account_identity_fingerprint:
            raise CapitalizationMissionError("prior mission account mismatch")
        highest = max(highest, previous.highest_closed_balance_seen)
        if previous.config_fingerprint == config.fingerprint:
            bank_latched = bank_latched or previous.bank_latched
            target_latched = target_latched or previous.target_reached_latched
            payout_latched = payout_latched or previous.payout_ready_latched
        mission_complete = mission_complete or previous.mission_complete

    if mission_complete:
        state = CapitalizationMissionState.MISSION_COMPLETE
    elif payout_latched:
        state = CapitalizationMissionState.PAYOUT_READY
    elif target_latched:
        state = CapitalizationMissionState.TARGET_REACHED
    elif defend:
        state = CapitalizationMissionState.DEFEND
    elif bank_latched:
        state = CapitalizationMissionState.BANK
    else:
        state = CapitalizationMissionState.CAPITALIZE

    realized_profit = closed_balance - config.start_balance
    target_remaining = max(
        Decimal(0),
        config.mission_balance_target - closed_balance,
    )
    new_risk_allowed = state not in {
        CapitalizationMissionState.TARGET_REACHED,
        CapitalizationMissionState.PAYOUT_READY,
        CapitalizationMissionState.MISSION_COMPLETE,
    }
    return CapitalizationMissionSnapshot(
        mission_id=config.mission_id,
        account_identity_fingerprint=config.account_identity_fingerprint,
        config_fingerprint=config.fingerprint,
        state=state,
        current_closed_balance=closed_balance,
        current_equity=equity,
        realized_profit=realized_profit,
        target_remaining=target_remaining,
        purchase_cash_required=config.purchase_cash_required,
        gross_reward_required=config.gross_reward_required,
        post_withdrawal_reserve=config.post_withdrawal_reserve,
        bank_balance_threshold=config.bank_balance_threshold,
        mission_balance_target=config.mission_balance_target,
        highest_closed_balance_seen=highest,
        bank_latched=bank_latched,
        target_reached_latched=target_latched,
        payout_ready_latched=payout_latched,
        mission_complete=mission_complete,
        new_risk_allowed_by_mission=new_risk_allowed,
        updated_at=now,
    )


def _json_bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if type(value) is not bool:
        raise CapitalizationMissionError(f"{key} must be bool")
    return value


class DurableCapitalizationMissionStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> CapitalizationMissionSnapshot | None:
        if not self._path.exists():
            return None
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
                raise CapitalizationMissionError("capitalization mission schema mismatch")
            return CapitalizationMissionSnapshot(
                mission_id=str(payload["mission_id"]),
                account_identity_fingerprint=str(
                    payload["account_identity_fingerprint"]
                ),
                config_fingerprint=str(payload["config_fingerprint"]),
                state=CapitalizationMissionState(str(payload["state"])),
                current_closed_balance=Decimal(str(payload["current_closed_balance"])),
                current_equity=Decimal(str(payload["current_equity"])),
                realized_profit=Decimal(str(payload["realized_profit"])),
                target_remaining=Decimal(str(payload["target_remaining"])),
                purchase_cash_required=Decimal(str(payload["purchase_cash_required"])),
                gross_reward_required=Decimal(str(payload["gross_reward_required"])),
                post_withdrawal_reserve=Decimal(
                    str(payload["post_withdrawal_reserve"])
                ),
                bank_balance_threshold=Decimal(str(payload["bank_balance_threshold"])),
                mission_balance_target=Decimal(str(payload["mission_balance_target"])),
                highest_closed_balance_seen=Decimal(
                    str(payload["highest_closed_balance_seen"])
                ),
                bank_latched=_json_bool(payload, "bank_latched"),
                target_reached_latched=_json_bool(
                    payload, "target_reached_latched"
                ),
                payout_ready_latched=_json_bool(payload, "payout_ready_latched"),
                mission_complete=_json_bool(payload, "mission_complete"),
                new_risk_allowed_by_mission=_json_bool(
                    payload, "new_risk_allowed_by_mission"
                ),
                updated_at=datetime.fromisoformat(str(payload["updated_at"])),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise CapitalizationMissionError(
                "capitalization mission state unreadable"
            ) from error

    def store(self, snapshot: CapitalizationMissionSnapshot) -> None:
        if not isinstance(snapshot, CapitalizationMissionSnapshot):
            raise CapitalizationMissionError("canonical capitalization snapshot required")
        payload = {
            "schema": _SCHEMA,
            "mission_id": snapshot.mission_id,
            "account_identity_fingerprint": snapshot.account_identity_fingerprint,
            "config_fingerprint": snapshot.config_fingerprint,
            "state": snapshot.state.value,
            "current_closed_balance": str(snapshot.current_closed_balance),
            "current_equity": str(snapshot.current_equity),
            "realized_profit": str(snapshot.realized_profit),
            "target_remaining": str(snapshot.target_remaining),
            "purchase_cash_required": str(snapshot.purchase_cash_required),
            "gross_reward_required": str(snapshot.gross_reward_required),
            "post_withdrawal_reserve": str(snapshot.post_withdrawal_reserve),
            "bank_balance_threshold": str(snapshot.bank_balance_threshold),
            "mission_balance_target": str(snapshot.mission_balance_target),
            "highest_closed_balance_seen": str(snapshot.highest_closed_balance_seen),
            "bank_latched": snapshot.bank_latched,
            "target_reached_latched": snapshot.target_reached_latched,
            "payout_ready_latched": snapshot.payout_ready_latched,
            "mission_complete": snapshot.mission_complete,
            "new_risk_allowed_by_mission": snapshot.new_risk_allowed_by_mission,
            "updated_at": snapshot.updated_at.astimezone(UTC).isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            suffix=".tmp",
            dir=self._path.parent,
        )
        temp = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self._path)
        except OSError as error:
            raise CapitalizationMissionError(
                "capitalization mission atomic write failed"
            ) from error
        finally:
            if temp.exists():
                temp.unlink()


def build_5k_mission_config(
    *,
    account_identity_fingerprint: str,
    start_balance: Decimal,
    purchase_cash_required: Decimal,
    reward_split_fraction: Decimal,
) -> CapitalizationMissionConfig:
    return CapitalizationMissionConfig(
        mission_id=MISSION_ID,
        account_identity_fingerprint=account_identity_fingerprint,
        start_balance=start_balance,
        target_account_size=TARGET_ACCOUNT_SIZE_USD,
        purchase_cash_required=purchase_cash_required,
        reward_split_fraction=reward_split_fraction,
        post_withdrawal_reserve=(
            start_balance * POST_WITHDRAWAL_RESERVE_FRACTION
        ),
    )
