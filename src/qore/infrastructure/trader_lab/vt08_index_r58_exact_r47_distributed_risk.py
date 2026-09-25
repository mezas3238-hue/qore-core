"""VT08 Index R58 — exact-R47-lineage distributed causal risk candidate.

R58 preserves the distributed causal risk overlay researched in R55, but fixes
its lineage. The base is reconstructed exactly as the frozen R47 candidate:
R34 allocator -> R47 transport demotions. R42/R43 static priors are not
inherited. Only then is the frozen distributed-risk overlay applied.

All windows are consumed development evidence. No LIVE authority is granted.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r34_hybrid_formation_poi_health as r34,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r43_sp500_long_stability_prior as r43,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r48_candidate_freeze as r48,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as overlay,
)

SCHEMA = "qore.trader_lab.vt08_index_r58_exact_r47_distributed_risk.v1"
IDENTITY = "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
CANDIDATE_ID = IDENTITY

OVERLAY_RULE_SOURCE_ID = overlay.CANDIDATE_ID
OVERLAY_RULE_SOURCE_FINGERPRINT = overlay.RULE_FINGERPRINT
RULES = overlay.RULES


def _fingerprint_payload() -> dict[str, object]:
    return {
        "candidate_id": CANDIDATE_ID,
        "base_candidate_id": r48.CANDIDATE_ID,
        "base_rule_fingerprint": r48.CANDIDATE_RULE_FINGERPRINT,
        "base_allocator": r34.IDENTITY,
        "r42_r43_static_priors_inherited": False,
        "overlay_rule_source_id": OVERLAY_RULE_SOURCE_ID,
        "overlay_rule_source_fingerprint": OVERLAY_RULE_SOURCE_FINGERPRINT,
        "rules": RULES,
        "lineage": ["R34", "R47", "R58_DISTRIBUTED_OVERLAY"],
    }


RULE_FINGERPRINT = sha256(
    json.dumps(
        _fingerprint_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()


def _exact_r47(
    stream: Any,
    *,
    bars_by_symbol: Any,
) -> tuple[Any, dict[str, Any]]:
    _base_row, baseline = r34._row(
        stream,
        overlay=r43.BASE_POI_OVERLAY,
    )
    assigned, diagnostics = r47._apply_transport_rules(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    return assigned, diagnostics


def _verify_r47_exact(
    assigned: Any,
    diagnostics: dict[str, Any],
    *,
    expected: dict[str, object],
    years: int,
    bars_by_symbol: Any,
    opened_by_symbol: Any,
) -> None:
    metrics = r47._window_metrics(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        years=years,
    )
    if len(assigned) != int(str(expected["sample"])):
        raise ValueError("R58 R47 base sample drift")
    if str(metrics["secondary"]["profit_factor"]) != str(
        expected["secondary_pf"]
    ):
        raise ValueError("R58 R47 base secondary PF drift")
    if str(metrics["secondary"]["total_r"]) != str(
        expected["secondary_total_r"]
    ):
        raise ValueError("R58 R47 base secondary total drift")
    expected_mean = (
        "0.01202823024648536964968234842"
        if years == 5
        else "0.008629572189718310319257016108"
    )
    if str(diagnostics["mean_effective_weight"]) != expected_mean:
        raise ValueError("R58 R47 base allocator lineage drift")


def _window(
    *,
    stream: Any,
    bars_by_symbol: Any,
    opened_by_symbol: Any,
    years: int,
    expected_r47: dict[str, object],
) -> dict[str, object]:
    base, base_diagnostics = _exact_r47(
        stream,
        bars_by_symbol=bars_by_symbol,
    )
    _verify_r47_exact(
        base,
        base_diagnostics,
        expected=expected_r47,
        years=years,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
    )
    candidate, diagnostics = overlay._apply_candidate(
        base,
        bars_by_symbol=bars_by_symbol,
    )
    economic = r47._window_metrics(
        candidate,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        years=years,
    )
    concentration = overlay._concentration(candidate)
    extra = {
        str(stress): overlay._stress_metrics(candidate, stress=stress)
        for stress in overlay.EXTRA_STRESSES
    }
    extra_pass = all(
        Decimal(str(metrics["total_r"])) > 0
        and Decimal(str(metrics["profit_factor"] or "0"))
        >= overlay.EXTRA_STRESS_PF_MIN
        for metrics in extra.values()
    )
    return {
        "sample": len(candidate),
        "base_r47_diagnostics": base_diagnostics,
        "economic": economic,
        "r58_diagnostics": diagnostics,
        "concentration": concentration,
        "extra_stress": extra,
        "extra_stress_pass": extra_pass,
        "window_pass": (
            bool(economic["economic_pass"])
            and bool(concentration["leave_top_3_positive"])
            and extra_pass
        ),
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    if not r48.dependency_contract_matches():
        raise ValueError("R58 frozen R47 dependency drift")
    if overlay.RULE_FINGERPRINT != OVERLAY_RULE_SOURCE_FINGERPRINT:
        raise ValueError("R58 distributed overlay source drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    five = _window(
        stream=five_stream,
        bars_by_symbol=five_bars,
        opened_by_symbol=five_opened,
        years=5,
        expected_r47=r48.FIVE_YEAR,
    )
    two = _window(
        stream=two_stream,
        bars_by_symbol=two_bars,
        opened_by_symbol=two_opened,
        years=2,
        expected_r47=r48.RECENT_TWO_YEAR,
    )
    development_pass = bool(five["window_pass"]) and bool(two["window_pass"])
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "lineage": {
            "base_candidate_id": r48.CANDIDATE_ID,
            "base_rule_fingerprint": r48.CANDIDATE_RULE_FINGERPRINT,
            "base_allocator": r34.IDENTITY,
            "r42_r43_static_priors_inherited": False,
            "overlay_rule_source_id": OVERLAY_RULE_SOURCE_ID,
            "overlay_rule_source_fingerprint": OVERLAY_RULE_SOURCE_FINGERPRINT,
        },
        "rules": RULES,
        "five_year": five,
        "recent_two_year": two,
        "development_pass": development_pass,
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "development_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "exact_frozen_r47_lineage_required": True,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "signals_suppressed": False,
            "zero_risk_allowed": False,
            "post_entry_outcome_runtime_feature": False,
            "calendar_or_year_runtime_feature": False,
            "certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "candidate_id": CANDIDATE_ID,
                "rule_fingerprint": RULE_FINGERPRINT,
                "development_pass": report["development_pass"],
                "five_year": report["five_year"],
                "recent_two_year": report["recent_two_year"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
