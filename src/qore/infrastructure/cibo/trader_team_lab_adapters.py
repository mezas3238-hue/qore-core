"""Adapters from canonical market snapshots to the CIBO shadow boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from qore.infrastructure.cibo.trader_team_lab import (
    CiboMarketState,
    TraderTeamLabError,
    TraderTeamLabValidationError,
)
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.traders.contracts import (
    DemoTradingMethodologyIdentity,
    DemoTradingOutput,
    DemoTradingTraderIdentity,
)
from qore.infrastructure.traders.instrument_binding import (
    DemoTradingEvaluatorBoundary,
    build_instrument_bound_demo_trading_input,
    evaluate_instrument_bound_demo_trader,
    market_snapshot_evidence_ref,
)
from qore.kernel.result import Failure, Result, Success

_EXECUTION_SECONDS = {
    "vt-01": 300,
    "vt-08": 300,
    "vt-09": 900,
    "vt-17": 300,
    "vt-31": 300,
}


class CiboMarketSnapshotPort(Protocol):
    """Read-only resolver for snapshots already named by a frozen market state."""

    def load(
        self, market_state: CiboMarketState
    ) -> Result[tuple[OhlcSnapshot, ...], TraderTeamLabError]: ...


@dataclass(frozen=True, slots=True)
class FirstCohortShadowEvaluatorAdapter:
    """Run one existing cohort evaluator behind the generic isolated Lab seam."""

    trader_identity: DemoTradingTraderIdentity
    methodology_identity: DemoTradingMethodologyIdentity
    evaluator: DemoTradingEvaluatorBoundary
    snapshots: CiboMarketSnapshotPort

    def __post_init__(self) -> None:
        self.trader_identity.__post_init__()
        self.methodology_identity.__post_init__()
        if self.trader_identity.trader_code.value not in _EXECUTION_SECONDS:
            raise TraderTeamLabValidationError("adapter Trader is outside first cohort")

    def evaluate(
        self, market_state: CiboMarketState
    ) -> Result[DemoTradingOutput, TraderTeamLabError]:
        try:
            self.__post_init__()
            market_state.__post_init__()
            loaded = self.snapshots.load(market_state)
            if isinstance(loaded, Failure):
                return loaded
            snapshots = loaded.value
            if (
                type(snapshots) is not tuple
                or not snapshots
                or any(type(item) is not OhlcSnapshot for item in snapshots)
            ):
                raise TraderTeamLabValidationError("snapshot adapter returned invalid evidence")
            allowed_refs = {item.value for item in market_state.provenance}
            for snapshot in snapshots:
                snapshot.__post_init__()
                if snapshot.instrument != market_state.instrument:
                    raise TraderTeamLabValidationError("snapshot instrument mismatch")
                if snapshot.closed_at > market_state.information_cutoff:
                    raise TraderTeamLabValidationError("future snapshot leakage")
                if market_snapshot_evidence_ref(snapshot).value not in allowed_refs:
                    raise TraderTeamLabValidationError(
                        "snapshot is not named by frozen market-state provenance"
                    )
            code = self.trader_identity.trader_code.value
            execution = tuple(
                item for item in snapshots if item.timeframe.seconds == _EXECUTION_SECONDS[code]
            )
            context = (
                tuple(item for item in snapshots if item.timeframe.seconds == 14_400)
                if code == "vt-08"
                else ()
            )
            bound = build_instrument_bound_demo_trading_input(
                execution_evidence=execution,
                context_evidence=context,
                as_of=market_state.information_cutoff,
            )
            evaluated = evaluate_instrument_bound_demo_trader(self.evaluator, bound)
            if isinstance(evaluated, Failure):
                return Failure(TraderTeamLabValidationError(str(evaluated.error)))
            output = evaluated.value.trader_output
            if (
                output.trader_code != self.trader_identity.trader_code
                or output.version != self.trader_identity.version
                or output.config_fingerprint != self.trader_identity.config_fingerprint
                or output.methodology_id != self.methodology_identity.methodology_id
                or output.methodology_version != self.methodology_identity.version
                or output.methodology_fingerprint != self.methodology_identity.fingerprint
            ):
                raise TraderTeamLabValidationError(
                    "existing evaluator output does not match adapter identity"
                )
            return Success(output)
        except TraderTeamLabError as error:
            return Failure(error)


__all__ = ["CiboMarketSnapshotPort", "FirstCohortShadowEvaluatorAdapter"]
