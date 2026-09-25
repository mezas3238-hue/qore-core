"""Bounded real-time anomaly supervision for cTrader DEMO.

The supervisor may retry/recover technical transport, feed-clock and broker
projection anomalies. It never changes trader methodology, signal validity,
target selection, sizing economics or risk intent.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class AnomalyClass(StrEnum):
    FEED_OR_CLOCK = "FEED_OR_CLOCK"
    BROKER_PROJECTION = "BROKER_PROJECTION"
    EXECUTION_REJECTION = "EXECUTION_REJECTION"
    STRATEGY_INVARIANT = "STRATEGY_INVARIANT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RepairTelemetry:
    trader: str
    anomaly_class: AnomalyClass
    original_error: str
    repair_attempted: bool
    repaired: bool
    retry_error: str | None = None

    def as_event(self) -> dict[str, object]:
        return {
            "event": (
                "CTRADER_DEMO_ANOMALY_AUTO_REPAIRED"
                if self.repaired
                else "CTRADER_DEMO_ANOMALY_REPAIR_FAILED"
                if self.repair_attempted
                else "CTRADER_DEMO_ANOMALY_ESCALATED"
            ),
            "trader": self.trader,
            "anomaly_class": self.anomaly_class.value,
            "original_error": self.original_error,
            "repair_attempted": self.repair_attempted,
            "repaired": self.repaired,
            "retry_error": self.retry_error,
        }


def classify_anomaly(error: Exception) -> AnomalyClass:
    text = f"{type(error).__name__}:{error}".lower()
    if any(
        token in text
        for token in (
            "stale",
            "future",
            "tick",
            "feed",
            "timeout",
            "connection",
            "snapshot unavailable",
            "market-data",
        )
    ):
        return AnomalyClass.FEED_OR_CLOCK
    if any(
        token in text
        for token in (
            "state drift",
            "position snapshot",
            "position reconciliation",
            "projection",
            "pending provider",
            "magic resolved",
            "position missing",
        )
    ):
        return AnomalyClass.BROKER_PROJECTION
    if any(
        token in text
        for token in (
            "order_check rejected",
            "order_send",
            "rejected",
            "retcode",
        )
    ):
        return AnomalyClass.EXECUTION_REJECTION
    if any(
        token in text
        for token in (
            "binding drift",
            "target-plan",
            "invalid",
            "cannot be expressed",
        )
    ):
        return AnomalyClass.STRATEGY_INVARIANT
    return AnomalyClass.UNKNOWN


def is_auto_repairable(anomaly_class: AnomalyClass) -> bool:
    return anomaly_class in {
        AnomalyClass.FEED_OR_CLOCK,
        AnomalyClass.BROKER_PROJECTION,
    }


def run_with_bounded_repair[T](
    *,
    trader: str,
    operation: Callable[[], T],
    recover: Callable[[], None],
    emit: Callable[[dict[str, object]], None],
) -> T:
    """Run one trader operation and retry once after technical recovery."""

    try:
        return operation()
    except Exception as error:
        anomaly_class = classify_anomaly(error)
        emit(
            {
                "event": "CTRADER_DEMO_ANOMALY_DETECTED",
                "trader": trader,
                "anomaly_class": anomaly_class.value,
                "reason": type(error).__name__,
                "message": str(error),
            }
        )
        if not is_auto_repairable(anomaly_class):
            emit(
                RepairTelemetry(
                    trader=trader,
                    anomaly_class=anomaly_class,
                    original_error=f"{type(error).__name__}:{error}",
                    repair_attempted=False,
                    repaired=False,
                ).as_event()
            )
            raise
        emit(
            {
                "event": "CTRADER_DEMO_ANOMALY_REPAIR_ATTEMPT",
                "trader": trader,
                "anomaly_class": anomaly_class.value,
            }
        )
        recover()
        try:
            value = operation()
        except Exception as retry_error:
            emit(
                RepairTelemetry(
                    trader=trader,
                    anomaly_class=anomaly_class,
                    original_error=f"{type(error).__name__}:{error}",
                    repair_attempted=True,
                    repaired=False,
                    retry_error=f"{type(retry_error).__name__}:{retry_error}",
                ).as_event()
            )
            raise
        emit(
            RepairTelemetry(
                trader=trader,
                anomaly_class=anomaly_class,
                original_error=f"{type(error).__name__}:{error}",
                repair_attempted=True,
                repaired=True,
            ).as_event()
        )
        return value
