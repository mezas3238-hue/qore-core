from __future__ import annotations

import pytest

from qore.infrastructure.ctrader_demo_live_anomaly_supervisor import (
    AnomalyClass,
    classify_anomaly,
    run_with_bounded_repair,
)


def test_classifies_feed_clock_as_repairable() -> None:
    error = RuntimeError("VT31 journey tick is from the future")
    assert classify_anomaly(error) is AnomalyClass.FEED_OR_CLOCK


def test_retries_once_and_emits_repair_success() -> None:
    calls = {"operation": 0, "recover": 0}
    events: list[dict[str, object]] = []

    def operation() -> str:
        calls["operation"] += 1
        if calls["operation"] == 1:
            raise RuntimeError("market snapshot unavailable")
        return "ok"

    def recover() -> None:
        calls["recover"] += 1

    result = run_with_bounded_repair(
        trader="VT31_NAS100",
        operation=operation,
        recover=recover,
        emit=events.append,
    )

    assert result == "ok"
    assert calls == {"operation": 2, "recover": 1}
    assert [event["event"] for event in events] == [
        "CTRADER_DEMO_ANOMALY_DETECTED",
        "CTRADER_DEMO_ANOMALY_REPAIR_ATTEMPT",
        "CTRADER_DEMO_ANOMALY_AUTO_REPAIRED",
    ]


def test_strategy_invariant_is_never_auto_repaired() -> None:
    events: list[dict[str, object]] = []
    recovered = False

    def operation() -> None:
        raise RuntimeError("VT31 live target-plan binding drift")

    def recover() -> None:
        nonlocal recovered
        recovered = True

    with pytest.raises(RuntimeError, match="binding drift"):
        run_with_bounded_repair(
            trader="VT31_NAS100",
            operation=operation,
            recover=recover,
            emit=events.append,
        )

    assert recovered is False
    assert events[-1]["event"] == "CTRADER_DEMO_ANOMALY_ESCALATED"
