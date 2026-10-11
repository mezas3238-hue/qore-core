"""Reconcile REAL 2876 source-DST witnesses into nine-market M1 perception.

Source market clocks can be established from V49 source ID/operating date and
provider-native closed bar without claiming a BROKER quote or microstructure.
Thus an exact M1 source perception may become DEGRADED, never GOOD. The
other eight markets are not automatically declared session/quote ready.
Nothing in this overlay changes V49 source selection or trade risk.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_a1_native_source_session_clock_attestation_v1 as clock,
)
from qore.infrastructure.trader_lab.capitalizer_a1_native_nine_market_bar_witness_v1 import (
    A1NativeMarketObservation,
)
from qore.infrastructure.trader_lab.capitalizer_a1_native_nine_market_epistemic_inputs_v1 import (
    A1NineMarketNativeCognitiveInputs,
    build_epistemic_inputs,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerMarketPerceptionSnapshot,
    CapitalizerPerceptionFacts,
    CapitalizerPerceptionStatus,
    assess_perception_integrity,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionResolution,
)

IDENTITY = "QORE_SCALPER_A1_NATIVE_SOURCE_CLOCK_BOUND_PERCEPTION_V2"


@dataclass(frozen=True, slots=True)
class A1ClockBoundPerceptionBarrier:
    native: A1NineMarketNativeCognitiveInputs
    perceptions: tuple[CapitalizerMarketPerceptionSnapshot, ...]
    source_clock_ids: tuple[str, ...]
    verified_source_market_clocks: tuple[str, ...]
    full_master_frame_executed: bool = False
    all_quotes_attested: bool = False
    author_killzone_attested: bool = False
    market_regimes_supported: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if len(self.perceptions) != 9 or {
            p.symbol for p in self.perceptions
        } != set(NINE_MARKET_UNIVERSE):
            raise ValueError("source clock cannot drop global Market Brain perceptions")
        if any(p.observed_at != self.native.observed_at for p in self.perceptions):
            raise ValueError("source-clock upgraded perception from the future")
        if not set(self.verified_source_market_clocks) <= set(
            self.native.observations[i].symbol for i in range(9)
        ):
            raise ValueError("clock witness outside nine-market universe")
        if any(
            p.assessment.status is CapitalizerPerceptionStatus.GOOD
            for p in self.perceptions
        ):
            raise ValueError("native OHLC with clock does not prove BID/ASK quote GOOD")
        if len(set(self.source_clock_ids)) != len(self.source_clock_ids):
            raise ValueError("source-clock witness ID duplicated at same decision time")
        if any((
            self.full_master_frame_executed, self.all_quotes_attested,
            self.author_killzone_attested, self.market_regimes_supported,
            self.live_authorized,
        )):
            raise ValueError("session clock cannot grant full cognition or live authority")


def bind_source_clocks_to_perceptions(
    *,
    observations: tuple[A1NativeMarketObservation, ...],
    source_clocks: tuple[clock.A1V49SourceClockEvidence, ...],
) -> A1ClockBoundPerceptionBarrier:
    """Promote QORE operational clock ONLY for an actually attested source bar."""
    native = build_epistemic_inputs(observations=observations)
    by_symbol = {x.symbol: x for x in native.observations}
    seen: set[str] = set()
    verified: set[str] = set()
    for witness in source_clocks:
        if witness.source_opportunity_id in seen:
            raise ValueError("duplicated original source clock evidence")
        seen.add(witness.source_opportunity_id)
        if witness.symbol not in by_symbol:
            raise ValueError("source clock market outside native closed nine")
        observed = by_symbol[witness.symbol]
        if (
            witness.observed_at != observed.decision_at
            or witness.m1_opened_at != observed.last_native_m1_opened_at
            or not observed.has_exact_predecision_m1
        ):
            raise ValueError("clock witness lacks exact physically closed original M1")
        if (
            witness.qore_bucket_reconfirmed
            is clock.ClockAttestationStatus.QORE_BUCKET_RECONFIRMED
            and witness.local_operating_day_reconfirmed
        ):
            verified.add(witness.symbol)
    upgraded: list[CapitalizerMarketPerceptionSnapshot] = []
    for perception in native.perceptions:
        obs = by_symbol[perception.symbol]
        if perception.symbol not in verified:
            upgraded.append(perception)
            continue
        # Quote freshness and full microstructure are still UNKNOWN even
        # when the source's civil clock and operational bucket are proven.
        upgraded.append(replace(perception, assessment=assess_perception_integrity(
            CapitalizerPerceptionFacts(
                quote_fresh=False,
                bars_complete=obs.has_exact_predecision_m1,
                timestamps_ordered=True,
                session_clock_valid=True,
                provenance_valid=obs.provider_native_m1,
                microstructure_complete=False,
            ),
        )))
    return A1ClockBoundPerceptionBarrier(
        native=native, perceptions=tuple(upgraded),
        source_clock_ids=tuple(sorted(seen)),
        verified_source_market_clocks=tuple(sorted(verified)),
    )


def audit_clock_bound_nine_market(
    *, native_root: Path, clock_root: Path, target: Path,
) -> dict[str, object]:
    books = sorted(native_root.rglob("scalper-a1-native-market-witness.jsonl"))
    clock_files = sorted(clock_root.rglob(
        "scalper-a1-native-v49-source-clock-evidence.jsonl"
    ))
    if len(books) != 9 or len(clock_files) != 1:
        raise ValueError("clock-bound perceptions require exactly 9 M1 and 1 V49 clock books")
    by_symbol: dict[str, tuple[A1NativeMarketObservation, ...]] = {}
    for path in books:
        rows = tuple(
            A1NativeMarketObservation(**json.loads(line))
            for line in path.read_text().splitlines() if line.strip()
        )
        if not rows or len({row.symbol for row in rows}) != 1:
            raise ValueError("invalid nine-market native witness book")
        if rows[0].symbol in by_symbol:
            raise ValueError("duplicate historical market")
        by_symbol[rows[0].symbol] = rows
    if set(by_symbol) != set(NINE_MARKET_UNIVERSE):
        raise ValueError("must preserve nine original markets")
    n = len(next(iter(by_symbol.values())))
    if n != 2822 or any(len(rows) != n for rows in by_symbol.values()):
        raise ValueError("frozen native 2822 decision instants not preserved")
    clock_rows: list[clock.A1V49SourceClockEvidence] = []
    for line in clock_files[0].read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        clock_rows.append(clock.A1V49SourceClockEvidence(
            **{
                **obj,
                "source_session": CapitalizerSession(obj["source_session"]),
                "qore_bucket_reconfirmed": clock.ClockAttestationStatus(
                    obj["qore_bucket_reconfirmed"]
                ),
                "methodology_window_resolution": CapitalizerSourceSessionResolution(
                    obj["methodology_window_resolution"]
                ),
            }
        ))
    if len(clock_rows) != 2876 or len({
        row.source_opportunity_id for row in clock_rows
    }) != 2876:
        raise ValueError("original 2876 source clocks duplicated or dropped")
    clocks_at: dict[str, list[clock.A1V49SourceClockEvidence]] = defaultdict(list)
    for row in clock_rows:
        clocks_at[row.observed_at].append(row)
    used: set[str] = set()
    counts: Counter[str] = Counter()
    target.mkdir(parents=True, exist_ok=True)
    with (target / "scalper-a1-source-clock-bound-nine-perceptions.jsonl").open("w") as f:
        for i in range(n):
            bundle = tuple(by_symbol[s][i] for s in sorted(by_symbol))
            at = bundle[0].decision_at
            reviews = tuple(clocks_at.get(at, ()))
            enriched = bind_source_clocks_to_perceptions(
                observations=bundle, source_clocks=reviews,
            )
            for row in reviews:
                if row.source_opportunity_id in used:
                    raise ValueError("source clock used at multiple as-of barriers")
                used.add(row.source_opportunity_id)
            if len(enriched.native.cross_market_graph.edges) != 36:
                raise ValueError("36 unknown cross-market relations required")
            for p in enriched.perceptions:
                counts["PERCEPTION:" + p.assessment.status.value] += 1
            counts["SOURCE_CLOCKS_ADMITTED"] += len(
                enriched.verified_source_market_clocks
            )
            counts["NATIVE_EXACT_NINE:" + str(
                enriched.native.complete_exact_native_m1
            )] += 1
            f.write(json.dumps({
                "identity": IDENTITY, "observed_at": at,
                "source_clock_ids": enriched.source_clock_ids,
                "verified_operational_clock_symbols": (
                    enriched.verified_source_market_clocks
                ),
                "perceptions": [{
                    "symbol": p.symbol, "status": p.assessment.status.value,
                    "reasons": p.assessment.reasons,
                } for p in enriched.perceptions],
                "regimes_unresolved": True, "cross_market_edges_unknown": 36,
                "broker_quotes_verified": False,
                "full_master_frame_executed": False,
                "entry_vetoes": 0,
            },sort_keys=True)+"\n")
    if len(used) != 2876 or len(clocks_at) != n:
        raise ValueError("not all 2876 source clock IDs reached original barriers")
    if sum(counts["PERCEPTION:" + x.value] for x in CapitalizerPerceptionStatus) != n*9:
        raise ValueError("nine-market perception coverage lost")
    result: dict[str, object] = {
        "identity": IDENTITY, "markets": 9,
        "original_source_ids": len(used), "decision_barriers": n,
        "total_perceptions": n*9,
        "counts": dict(sorted(counts.items())),
        "quote_and_microstructure_attested": False,
        "author_killzone_attested": False,
        "regime_supported": False,
        "cross_market_causality_attested": False,
        "portfolio_ledger_rebuilt": False,
        "full_master_frame_replayed": False,
        "cognitive_pf": None, "cognitive_drawdown_r": None,
        "source_entries_filtered": 0, "live_authorized": False,
    }
    (target / "scalper-a1-source-clock-bound-perception-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n"
    )
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("nine_native_m1", type=Path)
    p.add_argument("source_clocks", type=Path)
    p.add_argument("output", type=Path)
    options = p.parse_args()
    print(json.dumps(audit_clock_bound_nine_market(
        native_root=options.nine_native_m1, clock_root=options.source_clocks,
        target=options.output,
    ),sort_keys=True))


if __name__ == "__main__":
    main()
