"""R2-F deterministic Model #1 hypothesis-identity ledger for VT08 CRT PURE.

R2-E proved that the R2-C first-source-only control suppresses later independent
Model #1 source events. R2-F does NOT authorize those later events as entries.
It gives every causal source event a stable identity and measures hypothesis
multiplicity/concurrency without PnL.

The ledger intentionally stops before competition/execution policy. A source can
be AWAITING_CONFIRMATION or can obtain body confirmation, but neither state
grants capital or deployment authority.

Research only. No methodology mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    FOLD_1_END,
    ReplayBar,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    ConfirmationState,
    SourceObservation,
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2F_MODEL1_HYPOTHESIS_IDENTITY_LEDGER_001"
SCHEMA = "qore.vt08.crt_pure.r2f_model1_hypothesis_identity_ledger.v1"
M15 = timedelta(minutes=15)


class LedgerState(StrEnum):
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    BODY_CONFIRMED_NO_NEXT_BAR = "BODY_CONFIRMED_NO_NEXT_BAR"
    BODY_CONFIRMED_NO_CONTIGUOUS_NEXT_BAR = (
        "BODY_CONFIRMED_NO_CONTIGUOUS_NEXT_BAR"
    )
    CONFIRMED_ENTRY_SLOT_AVAILABLE = "CONFIRMED_ENTRY_SLOT_AVAILABLE"


@dataclass(frozen=True, slots=True)
class HypothesisLedgerRow:
    schema: str
    identity: str
    market: str
    parent_c3_opened_at: str
    source_event_id: str
    hypothesis_id: str
    event_generation: int
    source_opened_at: str
    source_reference_ids: tuple[str, ...]
    source_reference_count: int
    state_at_c3_close: str
    confirmation_opened_at: str | None
    confirmation_known_at: str | None
    is_first_source: bool
    is_later_independent_source: bool
    research_only: bool = True
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False


def _state(observation: SourceObservation) -> LedgerState:
    mapping = {
        ConfirmationState.NO_BODY_CONFIRMATION: LedgerState.AWAITING_CONFIRMATION,
        ConfirmationState.BODY_CONFIRMED_NO_NEXT_BAR: (
            LedgerState.BODY_CONFIRMED_NO_NEXT_BAR
        ),
        ConfirmationState.BODY_CONFIRMED_NO_CONTIGUOUS_NEXT_BAR: (
            LedgerState.BODY_CONFIRMED_NO_CONTIGUOUS_NEXT_BAR
        ),
        ConfirmationState.EXECUTABLE_CONFIRMATION: (
            LedgerState.CONFIRMED_ENTRY_SLOT_AVAILABLE
        ),
    }
    return mapping[observation.confirmation_state]


def _stable_ids(
    *,
    market: CrtPureMarket,
    parent: ParentCrt,
    observation: SourceObservation,
) -> tuple[str, str]:
    refs = sorted(observation.reference_ids)
    payload = "|".join(
        (
            market.value,
            parent.c3_opened_at.isoformat(),
            observation.group.source_candle.opened_at.isoformat(),
            *refs,
        )
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"crt-m1-src-{digest[:20]}", f"crt-m1-hyp-{digest[:20]}"


def _row(
    *,
    market: CrtPureMarket,
    parent: ParentCrt,
    observation: SourceObservation,
    generation: int,
) -> HypothesisLedgerRow:
    source_event_id, hypothesis_id = _stable_ids(
        market=market,
        parent=parent,
        observation=observation,
    )
    confirmation_known_at = (
        None
        if observation.confirmation_opened_at is None
        else observation.confirmation_opened_at + M15
    )
    refs = tuple(sorted(observation.reference_ids))
    return HypothesisLedgerRow(
        schema=SCHEMA,
        identity=IDENTITY,
        market=market.value,
        parent_c3_opened_at=parent.c3_opened_at.isoformat(),
        source_event_id=source_event_id,
        hypothesis_id=hypothesis_id,
        event_generation=generation,
        source_opened_at=observation.group.source_candle.opened_at.isoformat(),
        source_reference_ids=refs,
        source_reference_count=len(refs),
        state_at_c3_close=_state(observation).value,
        confirmation_opened_at=(
            None
            if observation.confirmation_opened_at is None
            else observation.confirmation_opened_at.isoformat()
        ),
        confirmation_known_at=(
            None if confirmation_known_at is None else confirmation_known_at.isoformat()
        ),
        is_first_source=generation == 1,
        is_later_independent_source=generation > 1,
    )


def _max_simultaneously_awaiting(
    *,
    parent: ParentCrt,
    rows: tuple[HypothesisLedgerRow, ...],
) -> int:
    if not rows:
        return 0
    events: list[tuple[datetime, int]] = []
    for row in rows:
        opened_at = datetime.fromisoformat(row.source_opened_at)
        closed_at = (
            parent.c3_closed_at
            if row.confirmation_known_at is None
            else datetime.fromisoformat(row.confirmation_known_at)
        )
        # Close before open at the same instant: once confirmation is known, the
        # older hypothesis is no longer counted as awaiting.
        events.append((opened_at, 1))
        events.append((closed_at, -1))
    current = 0
    maximum = 0
    for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
        current += delta
        maximum = max(maximum, current)
    return maximum


def _summarize_parent(
    *,
    parent: ParentCrt,
    rows: tuple[HypothesisLedgerRow, ...],
    counter: Counter[str],
) -> None:
    counter["parent_count"] += 1
    counter["source_event_count"] += len(rows)
    if not rows:
        counter["parent_zero_source"] += 1
        return
    if len(rows) == 1:
        counter["parent_one_source"] += 1
    else:
        counter["parent_multiple_sources"] += 1
        counter["later_source_event_count"] += len(rows) - 1

    executable = sum(
        row.state_at_c3_close == LedgerState.CONFIRMED_ENTRY_SLOT_AVAILABLE.value
        for row in rows
    )
    awaiting = sum(
        row.state_at_c3_close == LedgerState.AWAITING_CONFIRMATION.value
        for row in rows
    )
    counter["confirmed_entry_slot_event_count"] += executable
    counter["awaiting_at_c3_close_event_count"] += awaiting
    if executable:
        counter["parent_with_confirmed_entry_slot"] += 1
    if len(rows) > 1 and any(
        row.event_generation > 1
        and row.state_at_c3_close
        == LedgerState.CONFIRMED_ENTRY_SLOT_AVAILABLE.value
        for row in rows
    ):
        counter["parent_with_later_confirmed_entry_slot"] += 1

    maximum = _max_simultaneously_awaiting(parent=parent, rows=rows)
    counter[f"max_awaiting_concurrency_{maximum}"] += 1
    if maximum >= 2:
        counter["parent_with_concurrent_awaiting_hypotheses"] += 1
    counter["peak_awaiting_hypotheses_sum"] += maximum


def run_ledger(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[tuple[HypothesisLedgerRow, ...], dict[str, Any]]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time: dict[datetime, M15Bar] = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    all_rows: list[HypothesisLedgerRow] = []
    full: Counter[str] = Counter()
    year_1: Counter[str] = Counter()
    year_2: Counter[str] = Counter()

    for parent in parents:
        observations = _aligned_sources(
            parent=parent,
            c3_m15=_c3_m15(parent, m15_by_time),
            breaches=breaches,
        )
        rows = tuple(
            _row(
                market=market,
                parent=parent,
                observation=observation,
                generation=index + 1,
            )
            for index, observation in enumerate(observations)
        )
        if len({row.source_event_id for row in rows}) != len(rows):
            raise RuntimeError("source_event_id collision within parent")
        if len({row.hypothesis_id for row in rows}) != len(rows):
            raise RuntimeError("hypothesis_id collision within parent")

        all_rows.extend(rows)
        _summarize_parent(parent=parent, rows=rows, counter=full)
        fold = year_1 if parent.c3_opened_at < FOLD_1_END else year_2
        _summarize_parent(parent=parent, rows=rows, counter=fold)

    if len({row.source_event_id for row in all_rows}) != len(all_rows):
        raise RuntimeError("source_event_id collision in ledger")
    if len({row.hypothesis_id for row in all_rows}) != len(all_rows):
        raise RuntimeError("hypothesis_id collision in ledger")

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "full_2y": dict(full),
        "year_1": dict(year_1),
        "year_2": dict(year_2),
        "ledger_rows": len(all_rows),
        "source_event_ids_unique": True,
        "hypothesis_ids_unique": True,
        "multiple_hypotheses_do_not_imply_multiple_entries": True,
        "competition_policy_frozen": False,
        "methodology_mutated": False,
        "trades_created": 0,
        "pnl_evaluated": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return tuple(all_rows), report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    rows, report = run_ledger(market, load_two_year_m5(market))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "hypotheses.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    print("CRT_R2F_HYPOTHESIS_LEDGER_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
