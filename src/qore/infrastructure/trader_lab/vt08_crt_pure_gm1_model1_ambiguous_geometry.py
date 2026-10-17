"""Source-neutral Model #1 geometry over actual blinded H4/M15 cases.

Enumerate both RAW H4 extrema as hypotheses and ALL causally observed M15 source
candles without choosing a winning level, creating an entry, using future C3,
sizing or claiming Romeo authored a reference-selection procedure.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_gm1_reference_challenge import (
    enumerate_reference_dispute,
)
from qore.infrastructure.traders.crt_pure_model1 import (
    CrtPureModel1Bar,
    CrtPureModel1Reference,
    CrtPureModel1ReferenceKind,
    CrtPureModel1State,
    assess_model1_confirmation,
    detect_model1_candidate,
)

SCHEMA = "qore.vt08.crt_pure.gm1_model1_raw_level_geometry.v1"


def _as_model_bar(d: dict[str, Any]) -> CrtPureModel1Bar:
    return CrtPureModel1Bar(
        opened_at=datetime.fromisoformat(d["opened_at_utc"]),
        open_price=d["open_relative"],
        high_price=d["high_relative"],
        low_price=d["low_relative"],
        close_price=d["close_relative"],
    )


def enumerate_case_model1_geometry(blind: dict[str, Any]) -> dict[str, Any]:
    """Observed prefix ONLY. Every candidate is strictly UNAUTHENTICATED."""
    dispute = enumerate_reference_dispute(blind)
    prefix = [_as_model_bar(bar) for bar in blind["M15_observed_prefix_through_C2"]]
    observations: list[dict[str, Any]] = []
    for raw_ref in dispute["two_raw_h4_extrema"]:
        kind = (
            CrtPureModel1ReferenceKind.OLD_LOW
            if raw_ref["raw_extremum_kind"] == "H4_LOW"
            else CrtPureModel1ReferenceKind.OLD_HIGH
        )
        ref = CrtPureModel1Reference(
            kind=kind,
            price=raw_ref["raw_extremum_relative"],
            evidence_id="UNADJUDICATED_" + raw_ref["origin"],
        )
        for i, candle in enumerate(prefix):
            candidate = detect_model1_candidate(reference=ref, candle=candle)
            if candidate is None:
                continue
            first_confirmed: datetime | None = None
            # Source allows a later body close; search only *already closed*
            # M15 bars, not hidden future C3 and not a broker entry fill.
            for later in prefix[i + 1 :]:
                confirmation = assess_model1_confirmation(
                    candidate=candidate, candle=later
                )
                if confirmation.state is CrtPureModel1State.CONFIRMED:
                    first_confirmed = confirmation.decision_at
                    break
            observations.append(
                {
                    "unapproved_reference": ref.evidence_id,
                    "raw_H4_price": ref.price,
                    "source_m15_opened_at": candle.opened_at.isoformat(),
                    "mechanical_direction": candidate.direction.value,
                    "first_body_confirmation_known_at": (
                        first_confirmed.isoformat()
                        if first_confirmed is not None else None
                    ),
                    "mechanical_body_confirmed_by_C2": first_confirmed is not None,
                    "Romeo_old_level_eligibility": "NOT_ADJUDICATED",
                    "source_event_authenticity": False,
                    "entry_authorized": False,
                }
            )
    affected = sorted({x["unapproved_reference"] for x in observations})
    return {
        "schema": SCHEMA,
        "market": blind["market"],
        "case_id": blind["case_id"],
        "decision_clock_utc": blind["decision_clock_utc"],
        "observed_M15_prefix": len(prefix),
        "source_neutral_raw_reference_origins": 2,
        "mechanical_source_candle_hypotheses": len(observations),
        "mechanical_confirmations_by_C2": sum(
            int(x["mechanical_body_confirmed_by_C2"]) for x in observations
        ),
        "reference_origins_with_observations": affected,
        "observations": observations,
        "reference_selector_source_approved": False,
        "all_model1_source_events_authenticated": False,
        "methodological_gate_passed": False,
        "not_trades_no_sizing": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("blind_cases", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    blind = [
        json.loads(line)
        for line in args.blind_cases.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [enumerate_case_model1_geometry(case) for case in blind]
    if not rows or len(set(row["case_id"] for row in rows)) != len(rows):
        raise ValueError("missing/duplicate causal G-M2 real cases")
    counts = Counter(
        str(len(row["reference_origins_with_observations"])) for row in rows
    )
    manifest = {
        "schema": SCHEMA,
        "cases": len(rows),
        "mechanical_hypotheses": sum(
            row["mechanical_source_candle_hypotheses"] for row in rows
        ),
        "mechanical_body_confirmations": sum(
            row["mechanical_confirmations_by_C2"] for row in rows
        ),
        "cases_by_raw_reference_origins_with_observations": dict(sorted(counts.items())),
        "old_crth_crtl_authenticity_source_approved": False,
        "methodology_cognitive_certified": False,
        "GM1_PASS": False,
        "GM2_PASS": False,
        "GM3_PASS": False,
        "GM4_PASS": False,
        "GM5_issued": False,
        "sizing_or_trading_performed": False,
        "not_fresh_holdout": True,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "gm1-model1-raw-reference-summary.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.output / "gm1-model1-raw-reference-observations.jsonl").open(
        "w", encoding="utf-8"
    ) as out:
        for row in rows:
            out.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
