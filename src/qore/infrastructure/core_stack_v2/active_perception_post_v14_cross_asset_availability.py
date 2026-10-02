"""Source-only governance for post-V14 cross-asset sensor availability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

POST_V14_CROSS_ASSET_AUDIT_IDENTITY: Final = (
    "QORE_SHARED_WP05_POST_V14_CROSS_ASSET_SENSOR_AVAILABILITY_001"
)


@dataclass(frozen=True, slots=True)
class CrossAssetSensorCandidate:
    semantic_role: str
    provider_symbol: str
    provider_symbol_id: int

    def __post_init__(self) -> None:
        if not self.semantic_role:
            raise ValueError("semantic_role must be non-empty")
        if not self.provider_symbol:
            raise ValueError("provider_symbol must be non-empty")
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise ValueError("provider_symbol_id must be a positive int")


FROZEN_CROSS_ASSET_CANDIDATES: Final = (
    CrossAssetSensorCandidate(
        semantic_role="EQUITY_BREADTH_PROXY",
        provider_symbol="US2000",
        provider_symbol_id=10012,
    ),
    CrossAssetSensorCandidate(
        semantic_role="DEFENSIVE_ASSET_PROXY",
        provider_symbol="XAUUSD",
        provider_symbol_id=41,
    ),
    CrossAssetSensorCandidate(
        semantic_role="CYCLICAL_COMMODITY_PROXY",
        provider_symbol="XTIUSD",
        provider_symbol_id=10019,
    ),
)


def validate_candidates_against_catalog(
    catalog_rows: list[dict[str, object]],
) -> None:
    """Fail closed unless the frozen semantic candidates exist exactly."""

    by_name = {
        row.get("provider_symbol"): row.get("provider_symbol_id")
        for row in catalog_rows
    }
    for candidate in FROZEN_CROSS_ASSET_CANDIDATES:
        if by_name.get(candidate.provider_symbol) != candidate.provider_symbol_id:
            raise ValueError(
                f"provider catalog drift for {candidate.provider_symbol}"
            )
