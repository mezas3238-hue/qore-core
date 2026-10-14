"""G-M2 real Atlas H4/M15/M5 casebook for blinded qualitative source review.

NOT an entry detector, strategy tester, trade simulator, cognitive witness, or
certification gate PASS. Selection uses C2-known information only, never outcome.
Every historical price is a provider-relative integer from SHA-verified Atlas M5.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    FOLD_1_END,
    ReplayBar,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_n3_c2_m5_causal_clock import (
    c2_purge_return,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15,
    M15Bar,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)
from qore.infrastructure.traders.crt_pure_timing_policy import NY

SCHEMA = "qore.vt08.crt_pure.gm2_real_blinded_casebook.v1"
M5 = timedelta(minutes=5)
PER_BUCKET = 2


def _ohlc(bar: Any) -> dict[str, Any]:
    return {
        "opened_at_utc": bar.opened_at.astimezone(UTC).isoformat(),
        "open_relative": bar.open_price,
        "high_relative": bar.high_price,
        "low_relative": bar.low_price,
        "close_relative": bar.close_price,
    }


def _bucket(
    c1: M15Bar,
    c2: M15Bar,
    parent_direction: CrtPureCandidateDirection,
    prior: tuple[CrtPureCandidateDirection, ...],
) -> tuple[str, CrtPureCandidateDirection | None]:
    """Only C1, completed C2, and previously closed signals are admissible."""
    low_sweep = c2.low_price < c1.low_price
    high_sweep = c2.high_price > c1.high_price
    direction = c2_purge_return(c1, c2)
    if direction is None:
        if low_sweep and high_sweep:
            return "TWO_SIDED_SWEEP", None
        if not low_sweep and not high_sweep:
            return "NO_SWEEP", None
        return "ONE_SIDED_OUTSIDE_CLOSE", None
    if any(previous is not direction for previous in prior):
        return "PRIOR_OPPOSITE_C2_CONTEXT", direction
    if direction is parent_direction:
        return "ALIGNED_C2_CONTEXT", direction
    return "OPPOSITE_C2_CONTEXT", direction


def create_blind_casebook(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
    *,
    per_bucket: int = PER_BUCKET,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Stratify by C2-known geometry; release C3 M5 only in a separate sealed file.

    This casebook is drawn from the EXISTING original R2-C complete-H4-parent
    cohort. It is not a fresh, prospective or source-approved Model #1 sample.
    """
    if market not in (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY):
        raise ValueError("only original AUDUSD/USDJPY cohort; BTCUSD frozen")
    if per_bucket < 1:
        raise ValueError("per_bucket must be positive")
    m15 = {bar.opened_at: bar for bar in aggregate_complete_m15(bars)}
    m5 = {bar.opened_at: bar for bar in bars}
    if len(m5) != len(bars):
        raise ValueError("duplicate M5 timestamp")
    parents = build_parent_crts(market, bars)
    selected: Counter[tuple[str, str]] = Counter()
    selected_parent: set[tuple[str, str, str]] = set()
    blinded: list[dict[str, Any]] = []
    sealed: list[dict[str, Any]] = []
    scanned: Counter[str] = Counter()

    for parent in sorted(parents, key=lambda item: item.c3_opened_at):
        parent_id = parent.c3_opened_at.astimezone(UTC).isoformat()
        parent_m15 = tuple(
            m15[parent.c3_opened_at + i * M15] for i in range(16)
        )
        previous: list[CrtPureCandidateDirection] = []
        for i in range(14):  # reserve a subsequent M15-C3 for later reveal
            c1, c2 = parent_m15[i:i + 2]
            bucket, direction = _bucket(
                c1, c2, parent.direction, tuple(previous)
            )
            if direction is not None:
                previous.append(direction)
            cohort = (
                "COHORT_1" if c2.opened_at < FOLD_1_END else "COHORT_2"
            )
            key = (cohort, bucket)
            scanned[bucket] += 1
            if (
                selected[key] >= per_bucket
                or (cohort, bucket, parent_id) in selected_parent
            ):
                continue

            # All eligibility, bucket and parent selection decisions END HERE.
            # No C3 bars, later results, gains, losses or profits were consulted.
            evidence_at = c2.closed_at
            witness_open = evidence_at
            future = tuple(
                m5[witness_open + n * M5] for n in range(3)
            )
            if future[0].opened_at != evidence_at:
                raise ValueError("M5 reveal clock not contiguous with C2")
            identifier = hashlib.sha256(
                f"{market.value}|{parent_id}|{c1.opened_at.isoformat()}|"
                f"{c2.opened_at.isoformat()}".encode("utf-8")
            ).hexdigest()[:20]
            prefix = parent_m15[:i + 2]
            blind = {
                "schema": SCHEMA,
                "case_id": identifier,
                "market": market.value,
                "decision_clock_utc": evidence_at.astimezone(UTC).isoformat(),
                "decision_clock_ny": evidence_at.astimezone(NY).isoformat(),
                "parent_H4_c3_opened_at_utc": parent_id,
                "parent_H4_direction_context": parent.direction.value,
                "parent_H4_C1_ohlc": _ohlc(parent.c1),
                "parent_H4_C2_ohlc": _ohlc(parent.c2),
                "M15_observed_prefix_through_C2": [_ohlc(b) for b in prefix],
                "reference_level_selection": "UNRESOLVED_BY_PRIMARY_SOURCE",
                "author_model1_equivalence": "NOT_ADJUDICATED",
                "decision_to_be_made_by_reviewer": "EXECUTE_CONCEPTUAL_OR_WAIT_OR_ABSTAIN",
                "is_execution_authorized": False,
                "not_new_holdout": True,
                "future_C3_withheld_from_blind_file": True,
            }
            sealed_witness = {
                "case_id": identifier,
                "market": market.value,
                "stratum_known_at_C2": bucket,
                "cohort": cohort,
                "C2_diagnostic_direction": direction.value if direction else None,
                "C3_M5_reveal_after_independent_review": [
                    _ohlc(b) for b in future
                ],
                "warning": "NOT_A_TRADE_NOT_SOURCE_AUTHORIZED_NO_AUTOMATIC_GATE_PASS",
            }
            blinded.append(blind)
            sealed.append(sealed_witness)
            selected[key] += 1
            selected_parent.add((cohort, bucket, parent_id))

    if not blinded or len(blinded) != len(sealed):
        raise RuntimeError("missing/mismatched real casebook")
    if len({case["case_id"] for case in blinded}) != len(blinded):
        raise RuntimeError("repeated case identifier")
    if {row["case_id"] for row in blinded} != {
        row["case_id"] for row in sealed
    }:
        raise RuntimeError("reveal case IDs do not reconcile")
    summary = {
        "schema": SCHEMA,
        "market": market.value,
        "original_atlas_m5_rows": len(bars),
        "source_cohort": "R2-C_EXISTING_COMPLETE_H4_PARENTS_NOT_FRESH_HOLDOUT",
        "parent_H4_contexts": len(parents),
        "case_count": len(blinded),
        "sampling": "FIRST_TWO_DISTINCT_H4_PARENTS_PER_C2_KNOWN_BUCKET_AND_COHORT",
        "selected_bucket_counts": {
            f"{cohort}:{bucket}": count
            for (cohort, bucket), count in sorted(selected.items())
        },
        "observed_C2_bucket_counts": dict(sorted(scanned.items())),
        "reader_must_not_open_sealed_reveal_before_review": True,
        "no_C3_used_for_selection": True,
        "methodology_source_gate": "G-M1_OPEN_MODEL_1_REFERENCE_SELECTION",
        "methodology_cognition_gate": "G-M2_EVIDENCE_ONLY_HUMAN_REVIEW_PENDING",
        "gm3_reconciled_with_real_cognitive_output": False,
        "gm4_end_to_end_passed": False,
        "gm5_certificate_issued": False,
        "global_certified": False,
        "demo_authorized": False,
        "live_authorized": False,
    }
    return summary, tuple(blinded), tuple(sealed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=("AUDUSD", "USDJPY"))
    parser.add_argument("original_atlas_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.original_atlas_root)
    manifest, blind, sealed = create_blind_casebook(market, bars)
    manifest["source_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "gm2-real-casebook-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for filename, records in (
        ("gm2-blind-cases.jsonl", blind),
        ("gm2-sealed-c3-witness.jsonl", sealed),
    ):
        with (args.output / filename).open("w", encoding="utf-8") as output:
            for record in records:
                output.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
