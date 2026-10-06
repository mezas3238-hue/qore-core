"""Release execution readiness sensor for Full Economic Twin positions.

Research-only. Distinguishes economic release desirability from actual
settlement executability. A Portfolio shadow RELEASE cannot become an executable
proposal until causal mark-to-market state is present.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)


@dataclass(frozen=True, slots=True)
class CiboPositionReleaseReadinessReport:
    twin_id: str
    open_position_count: int
    continuation_identified_count: int
    price_geometry_identified_count: int
    mark_to_market_identified_count: int
    executable_release_count: int
    executable_release_rate: Decimal
    primary_blocker: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id or not self.primary_blocker:
            raise CiboCapitalManagementError(
                "release readiness identity/blocker required"
            )
        for name in (
            "open_position_count",
            "continuation_identified_count",
            "price_geometry_identified_count",
            "mark_to_market_identified_count",
            "executable_release_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"release readiness {name} invalid"
                )
        if (
            self.executable_release_rate < 0
            or self.executable_release_rate > 1
        ):
            raise CiboCapitalManagementError(
                "release readiness rate outside [0,1]"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "release readiness sensor cannot acquire authority"
            )


def _ratio(num: int, den: int) -> Decimal:
    if den <= 0:
        return Decimal(1)
    return Decimal(num) / Decimal(den)


def measure_position_release_readiness(
    twin: CiboObservedEconomicTwin,
) -> CiboPositionReleaseReadinessReport:
    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "release readiness requires canonical Full Economic Twin"
        )

    positions = twin.positions
    total = len(positions)
    continuation = sum(
        item.continuation_value_identified
        for item in positions
    )
    geometry = sum(
        item.entry_price is not None
        and item.structural_stop is not None
        and item.technical_target is not None
        for item in positions
    )
    marks = sum(
        item.mark_to_market_identified
        for item in positions
    )
    executable = sum(
        item.releasable
        and item.continuation_value_identified
        and item.mark_to_market_identified
        for item in positions
    )

    if total == 0:
        blocker = "NO_OPEN_POSITIONS"
    elif continuation < total:
        blocker = "CONTINUATION_VALUE_UNIDENTIFIED"
    elif geometry < total:
        blocker = "PRICE_GEOMETRY_UNIDENTIFIED"
    elif marks < total:
        blocker = "MARK_TO_MARKET_UNIDENTIFIED"
    elif executable < total:
        blocker = "PARTIAL_RELEASE_EXECUTABILITY"
    else:
        blocker = "NONE"

    return CiboPositionReleaseReadinessReport(
        twin_id=twin.twin_id,
        open_position_count=total,
        continuation_identified_count=continuation,
        price_geometry_identified_count=geometry,
        mark_to_market_identified_count=marks,
        executable_release_count=executable,
        executable_release_rate=_ratio(executable, total),
        primary_blocker=blocker,
        productive_authority=False,
    )
