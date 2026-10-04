"""Chronology and leakage firewall for Shared Lab predecision evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab import TemporalDatumReceipt


class TemporalFailure(StrEnum):
    MISSING_TIMESTAMP = "MISSING_TIMESTAMP"
    NEGATIVE_OFFSET = "NEGATIVE_OFFSET"
    FUTURE_TIMESTAMP = "FUTURE_TIMESTAMP"
    OUT_OF_ORDER_SEQUENCE = "OUT_OF_ORDER_SEQUENCE"
    DUPLICATE_TIMESTAMP = "DUPLICATE_TIMESTAMP"
    TIMEZONE_MISMATCH = "TIMEZONE_MISMATCH"
    CLOCK_DRIFT = "CLOCK_DRIFT"
    SESSION_ROLLOVER = "SESSION_ROLLOVER"


@dataclass(frozen=True, slots=True)
class TemporalProbeReceipt:
    datum_id: str
    base: TemporalDatumReceipt | None
    failures: tuple[TemporalFailure, ...]
    detected_future_leakage: bool

    @property
    def passed(self) -> bool:
        return self.base is not None and self.base.leakage_free and not self.failures


def assess_temporal(*, datum_id: str, observed_at_ns: int | None, available_at_ns: int | None, decision_at_ns: int | None, consumed_at_ns: int | None, max_clock_drift_ns: int | None = None) -> TemporalProbeReceipt:
    values = (observed_at_ns, available_at_ns, decision_at_ns, consumed_at_ns)
    if any(value is None for value in values):
        return TemporalProbeReceipt(datum_id, None, (TemporalFailure.MISSING_TIMESTAMP,), False)
    assert observed_at_ns is not None
    assert available_at_ns is not None
    assert decision_at_ns is not None
    assert consumed_at_ns is not None
    base = TemporalDatumReceipt(datum_id, observed_at_ns, available_at_ns, decision_at_ns, consumed_at_ns)
    failures: list[TemporalFailure] = []
    if available_at_ns < observed_at_ns or consumed_at_ns < decision_at_ns:
        failures.append(TemporalFailure.NEGATIVE_OFFSET)
    future = available_at_ns > decision_at_ns or observed_at_ns > decision_at_ns
    if future:
        failures.append(TemporalFailure.FUTURE_TIMESTAMP)
    if max_clock_drift_ns is not None and abs(available_at_ns - observed_at_ns) > max_clock_drift_ns:
        failures.append(TemporalFailure.CLOCK_DRIFT)
    return TemporalProbeReceipt(datum_id, base, tuple(dict.fromkeys(failures)), future)


def assess_sequence(timestamps_ns: tuple[int, ...]) -> tuple[TemporalFailure, ...]:
    failures: list[TemporalFailure] = []
    if len(set(timestamps_ns)) != len(timestamps_ns):
        failures.append(TemporalFailure.DUPLICATE_TIMESTAMP)
    if any(b < a for a, b in zip(timestamps_ns, timestamps_ns[1:])):
        failures.append(TemporalFailure.OUT_OF_ORDER_SEQUENCE)
    return tuple(failures)
