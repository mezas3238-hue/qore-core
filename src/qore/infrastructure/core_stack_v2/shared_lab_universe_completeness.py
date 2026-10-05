"""Cross-asset universe completeness receipts for Shared Lab Data Reality."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UniverseCoverageReceipt:
    expected_instruments: tuple[str, ...]
    received_instruments: tuple[str, ...]
    missing_instruments: tuple[str, ...]
    unexpected_instruments: tuple[str, ...]
    coverage_ratio: float
    min_coverage_ratio: float

    @property
    def passed(self) -> bool:
        return (
            self.coverage_ratio >= self.min_coverage_ratio
            and not self.unexpected_instruments
        )


def assess_universe_coverage(
    expected_instruments: tuple[str, ...],
    received_instruments: tuple[str, ...],
    *,
    min_coverage_ratio: float = 1.0,
) -> UniverseCoverageReceipt:
    if not expected_instruments:
        raise ValueError("expected universe cannot be empty")
    if len(set(expected_instruments)) != len(expected_instruments):
        raise ValueError("expected universe must be unique")
    if not 0 <= min_coverage_ratio <= 1:
        raise ValueError("min_coverage_ratio must be in [0,1]")

    expected = set(expected_instruments)
    received = set(received_instruments)
    missing = tuple(sorted(expected - received))
    unexpected = tuple(sorted(received - expected))
    covered = len(expected & received)
    ratio = covered / len(expected)
    return UniverseCoverageReceipt(
        expected_instruments=tuple(sorted(expected)),
        received_instruments=tuple(sorted(received)),
        missing_instruments=missing,
        unexpected_instruments=unexpected,
        coverage_ratio=ratio,
        min_coverage_ratio=min_coverage_ratio,
    )
