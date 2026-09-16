"""Durable fail-closed kill switches for the FundedNext production runtime."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.infrastructure.fundednext_live_guard import CERTIFIED_LIVE_DIRECTIONS
from qore.infrastructure.fundednext_mt5 import Mt5ExecutionBlockedError
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.fundednext.live-safety.v1"


class FundedNextLiveSafetyError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class FundedNextLiveSafetyState:
    account_enabled: bool
    gateway_enabled: bool
    disabled_traders: tuple[str, ...]
    disabled_markets: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.account_enabled) is not bool or type(self.gateway_enabled) is not bool:
            raise FundedNextLiveSafetyError("live safety switches must be bool")
        if tuple(sorted(set(self.disabled_traders))) != self.disabled_traders:
            raise FundedNextLiveSafetyError("disabled traders must be sorted unique")
        if tuple(sorted(set(self.disabled_markets))) != self.disabled_markets:
            raise FundedNextLiveSafetyError("disabled markets must be sorted unique")
        if any(symbol not in CERTIFIED_LIVE_DIRECTIONS for symbol in self.disabled_markets):
            raise FundedNextLiveSafetyError("disabled market outside live universe")


class JsonFileLiveOperationalSafetyBoundary:
    """Reload safety state for every new order; missing/unreadable state blocks."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def assert_new_order_allowed(self, submission: ExecutionSubmission) -> None:
        state = load_live_safety_state(self._path)
        intent = submission.authorized_intent.intent
        trader = intent.metadata.attributes.get("trader-id")
        symbol = intent.instrument.value
        if not state.account_enabled:
            raise Mt5ExecutionBlockedError("account-kill-switch-disabled")
        if not state.gateway_enabled:
            raise Mt5ExecutionBlockedError("gateway-kill-switch-disabled")
        if isinstance(trader, str) and trader in state.disabled_traders:
            raise Mt5ExecutionBlockedError("trader-kill-switch-disabled")
        if symbol in state.disabled_markets:
            raise Mt5ExecutionBlockedError("market-kill-switch-disabled")


def load_live_safety_state(path: Path) -> FundedNextLiveSafetyState:
    if not path.is_file():
        raise FundedNextLiveSafetyError("live-safety-state-missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise FundedNextLiveSafetyError("live-safety-state-unreadable") from error
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise FundedNextLiveSafetyError("live-safety-state-schema-mismatch")
    account_enabled = payload.get("account_enabled")
    gateway_enabled = payload.get("gateway_enabled")
    if type(account_enabled) is not bool or type(gateway_enabled) is not bool:
        raise FundedNextLiveSafetyError("live-safety booleans invalid")
    disabled_traders = _tuple_of_text(payload.get("disabled_traders"), "disabled_traders")
    disabled_markets = _tuple_of_text(payload.get("disabled_markets"), "disabled_markets")
    return FundedNextLiveSafetyState(
        account_enabled=account_enabled,
        gateway_enabled=gateway_enabled,
        disabled_traders=tuple(sorted(disabled_traders)),
        disabled_markets=tuple(sorted(disabled_markets)),
    )


def initialize_live_safety_state(path: Path) -> None:
    if path.exists():
        load_live_safety_state(path)
        return
    store_live_safety_state(
        path,
        FundedNextLiveSafetyState(
            account_enabled=True,
            gateway_enabled=True,
            disabled_traders=(),
            disabled_markets=(),
        ),
    )


def store_live_safety_state(path: Path, state: FundedNextLiveSafetyState) -> None:
    if not isinstance(state, FundedNextLiveSafetyState):
        raise FundedNextLiveSafetyError("canonical live safety state required")
    payload = {
        "schema": _SCHEMA,
        "account_enabled": state.account_enabled,
        "gateway_enabled": state.gateway_enabled,
        "disabled_traders": list(state.disabled_traders),
        "disabled_markets": list(state.disabled_markets),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
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


def _tuple_of_text(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise FundedNextLiveSafetyError(f"{name} must be string array")
    return tuple(value)
