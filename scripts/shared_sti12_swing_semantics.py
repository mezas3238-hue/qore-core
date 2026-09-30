#!/usr/bin/env python3
"""Seal STI-12 research-only Swing support semantics for all declared families."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_swing_trader_support import (
    SharedSwingHorizon,
    SharedSwingTraderFamily,
    build_research_swing_support_profile,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedIntelligenceClass,
)

IDENTITY = "QORE_SHARED_STI12_SWING_RESEARCH_SEMANTICS_001"


def main() -> None:
    frozen_at = datetime(2026, 9, 30, 18, 15, tzinfo=UTC)
    classes = tuple(sorted(SharedIntelligenceClass, key=lambda item: item.value))
    horizons = tuple(sorted(SharedSwingHorizon, key=lambda item: item.value))
    market_map = {
        SharedSwingTraderFamily.GLOBAL_MACRO_SWING: (
            "EURUSD",
            "USDJPY",
            "XAUUSD",
        ),
        SharedSwingTraderFamily.COMMODITY_SWING: (
            "XAUUSD",
            "XTIUSD",
        ),
        SharedSwingTraderFamily.CROSS_ASSET_SWING: (
            "NAS100",
            "SP500",
            "US30",
        ),
        SharedSwingTraderFamily.REGIME_TRANSITION_SWING: (
            "EURUSD",
            "NAS100",
            "XAUUSD",
        ),
    }

    profiles = []
    for family in SharedSwingTraderFamily:
        profile = build_research_swing_support_profile(
            profile_id=f"sti12:{family.value.lower()}",
            trader_family=family,
            version="001",
            frozen_at=frozen_at,
            markets=tuple(sorted(market_map[family])),
            horizons=horizons,
            intelligence_classes=classes,
            source_evidence_refs=(
                "gap-audit:QORE_SHARED_TRADER_INTELLIGENCE_GAP_AUDIT_001",
                "owner-directive:SHARED_COGNITIVE_OS_005",
            ),
        )
        capability = profile.as_routing_capability()
        profiles.append(
            {
                "family": family.value,
                "fingerprint": profile.fingerprint(),
                "markets": profile.markets,
                "horizons": tuple(item.value for item in profile.horizons),
                "intelligence_classes": tuple(
                    item.value for item in profile.intelligence_classes
                ),
                "runtime_trader_exists": profile.runtime_trader_exists,
                "trader_certified": profile.trader_certified,
                "all_authority_false": all(
                    not value
                    for value in (
                        profile.setup_authority,
                        profile.direction_authority,
                        profile.entry_authority,
                        profile.stop_target_authority,
                        profile.position_management_authority,
                        profile.execution_authority,
                        profile.sizing_authority,
                    )
                ),
                "routing_capability_read_only": (
                    not capability.methodology_visible_to_shared
                    and not capability.shared_methodology_mutation_authority
                ),
            }
        )

    all_families = {item["family"] for item in profiles} == {
        item.value for item in SharedSwingTraderFamily
    }
    all_horizons = all(
        set(item["horizons"]) == {h.value for h in SharedSwingHorizon}
        for item in profiles
    )
    passed = (
        all_families
        and all_horizons
        and all(item["all_authority_false"] for item in profiles)
        and all(item["routing_capability_read_only"] for item in profiles)
        and all(not item["runtime_trader_exists"] for item in profiles)
        and all(not item["trader_certified"] for item in profiles)
    )

    payload = {
        "identity": IDENTITY,
        "status": (
            "STI12_SWING_RESEARCH_SEMANTICS_COMPLETED_AND_PROVEN"
            if passed
            else "STI12_SWING_RESEARCH_SEMANTICS_FAIL"
        ),
        "profiles": profiles,
        "all_four_families_present": all_families,
        "h1_h4_d1_w1_interface_present": all_horizons,
        "runtime_swing_trader_created": False,
        "swing_trader_certified": False,
        "predictive_value_claimed": False,
        "economic_value_claimed": False,
        "protected_certification_holdout_opened": False,
        "sti12_completed_and_proven": passed,
    }
    Path("result").mkdir(exist_ok=True)
    Path("result/sti12-swing-semantics.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
