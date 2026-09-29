"""V47-S2 source-strategy isolation over remediated source composition.

S2-A is still pre-economic: it constructs the remediated canonical population,
proves exact provider tick fills, and runs the official V46 adapter. Outcomes,
exits and realized R remain unread.

Frozen by PR #623 comment 5900501860.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_candidate_assembly_v47_s0 as s0,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_composition_v47_s2 as s2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cibo_10y_m1_clone_v1 as m1_clone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    market_is_allowed,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_SOURCE_STRATEGY_ISOLATION_V47_S2"
PREDECLARATION_COMMENT_ID = 5900501860
COGNITIVE_TOKEN = s1.COGNITIVE_TOKEN
SOURCE_M1_RUN_ID = s1.SOURCE_M1_RUN_ID
SOURCE_M1_SHA = s1.SOURCE_M1_SHA
PERIODS = s1.PERIODS


@dataclass(frozen=True, slots=True)
class S2AdmittedFillRow:
    identity: str
    period: str
    symbol: str
    session: str
    operating_date: str
    side: str
    route: str
    upstream_confirmed_at: str
    armed_at: str
    entry_at: str
    entry_price: str
    armed_level_used: str
    entry_mode: str
    stop_price: str
    target_price: str
    target_kind: str
    target_provenance: str
    provider_tick_count: int
    provider_request_count: int
    cognitive_gate_source: str = COGNITIVE_TOKEN
    provider_native_m1: bool = True
    exact_provider_tick_fill: bool = True
    official_v46_adapter_passed: bool = True
    outcome_used_for_selection: bool = False
    terminal_outcome_read: bool = False
    realized_r_read: bool = False
    fresh_holdout_opened: bool = False
    full_trader_fidelity_claimed: bool = False
    candidate_promotion_allowed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or self.period not in PERIODS:
            raise ValueError("S2 admitted row identity/period drift")
        if self.cognitive_gate_source != COGNITIVE_TOKEN:
            raise ValueError("S2 cognitive token drift")
        if (
            not self.provider_native_m1
            or not self.exact_provider_tick_fill
            or not self.official_v46_adapter_passed
            or self.outcome_used_for_selection
            or self.terminal_outcome_read
            or self.realized_r_read
            or self.fresh_holdout_opened
            or self.full_trader_fidelity_claimed
            or self.candidate_promotion_allowed
            or self.trader_certified
        ):
            raise ValueError("S2 admitted row governance drift")


@dataclass(frozen=True, slots=True)
class S2PeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    period_start: str
    period_end_exclusive: str
    operating_days_scanned: int
    upstream_events: int
    htf_aligned: int
    m15_bound: int
    independent_m1_bound: int
    event_target_bound: int
    routed_fractal_candidates: int
    exact_fills: int
    v46_rejected_after_fill: int
    admitted_exact_fills: int
    provider_tick_requests: int
    forensic_rejections: dict[str, int] = field(default_factory=dict)
    terminal_outcome_read: bool = False
    strategy_economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or self.period not in PERIODS:
            raise ValueError("S2 report identity/period drift")
        counts = (
            self.upstream_events,
            self.htf_aligned,
            self.m15_bound,
            self.independent_m1_bound,
            self.event_target_bound,
            self.routed_fractal_candidates,
            self.exact_fills,
            self.v46_rejected_after_fill,
            self.admitted_exact_fills,
            self.provider_tick_requests,
        )
        if any(value < 0 for value in counts):
            raise ValueError("S2 report counts cannot be negative")
        if not (
            self.upstream_events
            >= self.htf_aligned
            >= self.m15_bound
            >= self.independent_m1_bound
            >= self.event_target_bound
            >= self.routed_fractal_candidates
        ):
            raise ValueError("S2 funnel monotonicity drift")
        if self.admitted_exact_fills + self.v46_rejected_after_fill > self.exact_fills:
            raise ValueError("S2 post-fill classification drift")
        if (
            self.terminal_outcome_read
            or self.strategy_economics_calculated
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("S2 report governance drift")


def _bump(store: dict[str, int], key: str) -> None:
    store[key] = store.get(key, 0) + 1


def _admitted_row(
    *,
    period: str,
    candidate: s2.S2CanonicalFractalCandidate,
    fill: s1.S1ExactFill,
    isolation: s0.SourceStrategyIsolationAssessment,
) -> S2AdmittedFillRow:
    result = isolation.canonical_result
    engine = result.source_engine_assessment
    resolution = fill.resolution
    if (
        not result.passes_to_qore_risk
        or engine is None
        or engine.trade_plan is None
        or resolution.fill_at is None
        or resolution.fill_price is None
        or result.route_resolution.route is None
    ):
        raise ValueError("S2 admitted row requires canonical Risk handoff")
    event = candidate.routed.candidate.event
    plan = engine.trade_plan
    return S2AdmittedFillRow(
        identity=IDENTITY,
        period=period,
        symbol=event.symbol,
        session=event.session.value,
        operating_date=event.operating_date.isoformat(),
        side=event.side.value,
        route=result.route_resolution.route.value,
        upstream_confirmed_at=candidate.upstream_confirmed_at.isoformat(),
        armed_at=candidate.routed.candidate.armed_at.isoformat(),
        entry_at=resolution.fill_at.isoformat(),
        entry_price=str(resolution.fill_price),
        armed_level_used=str(fill.level),
        entry_mode=fill.mode,
        stop_price=str(plan.initial_stop_price),
        target_price=str(plan.target_price),
        target_kind=plan.target_kind.value,
        target_provenance=candidate.target_provenance,
        provider_tick_count=resolution.provider_tick_count,
        provider_request_count=fill.request_count,
    )


def select_max3(
    rows: tuple[S2AdmittedFillRow, ...],
) -> tuple[S2AdmittedFillRow, ...]:
    grouped: dict[tuple[str, str], list[S2AdmittedFillRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.session, row.operating_date)].append(row)
    selected: list[S2AdmittedFillRow] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol),
        )
    )


def build_period_market_population(
    client: SpotwareCTraderOpenApiClient,
    *,
    consumed_bars: tuple[CapitalizerM1Bar, ...],
    symbol: str,
    session: CapitalizerSession,
    period: str,
    symbol_id: int,
    digits: int,
) -> tuple[S2PeriodMarketReport, tuple[S2AdmittedFillRow, ...]]:
    if period not in PERIODS:
        raise ValueError("unknown S2 period")
    if not market_is_allowed(session=session, symbol=symbol):
        raise ValueError("S2 market outside frozen universe")
    period_start, period_end = PERIODS[period]
    prepared = s1._prepare_source_series(consumed_bars)
    bars = s1._prepared_m1_between(
        prepared,
        start=period_start - s1.LOOKBACK,
        end=period_end + s1.timedelta(days=2),
    )
    opened = tuple(row.opened_at for row in bars)
    operating_days = s1._operating_days(
        bars,
        session=session,
        period_start=period_start,
        period_end=period_end,
    )

    funnel: dict[str, int] = {}
    forensic: dict[str, int] = {}
    exact_fills = 0
    v46_rejected = 0
    requests = 0
    admitted: list[S2AdmittedFillRow] = []

    for operating_day in operating_days:
        local = s1._day_slice(
            bars,
            opened,
            operating_day=operating_day,
            session=session,
        )
        if not local:
            continue
        candidates = s2.bind_s2_fractal_candidates(
            local,
            session=session,
            operating_day=operating_day,
            prepared=prepared,
            funnel=funnel,
            rejections=forensic,
        )
        for index, candidate in enumerate(candidates):
            fill, used = s1.resolve_candidate_exact_fill(
                client,
                candidate=candidate.routed,
                bars=local,
                symbol_id=symbol_id,
                digits=digits,
                request_prefix=(
                    f"capitalizer-s2:{period}:{symbol}:"
                    f"{operating_day.isoformat()}:{index}"
                ),
            )
            requests += used
            if fill is None:
                _bump(forensic, "EXACT_PROVIDER_FILL_NOT_PROVEN")
                continue
            exact_fills += 1
            bundle = s1.build_post_fill_bundle(candidate.routed, fill=fill)
            isolation = s0.assess_source_strategy_isolation_bundle(bundle)
            if not isolation.canonical_result.passes_to_qore_risk:
                v46_rejected += 1
                for reason in isolation.canonical_result.reasons:
                    _bump(forensic, f"V46:{reason}")
                for reason in (
                    isolation.canonical_result.dual_source_entry_acceptance.reasons
                ):
                    _bump(forensic, f"V46_DUAL:{reason}")
                continue
            row = _admitted_row(
                period=period,
                candidate=candidate,
                fill=fill,
                isolation=isolation,
            )
            entry_at = datetime.fromisoformat(row.entry_at).astimezone(UTC)
            if period_start <= entry_at < period_end:
                admitted.append(row)

    report = S2PeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        period_start=period_start.isoformat(),
        period_end_exclusive=period_end.isoformat(),
        operating_days_scanned=len(operating_days),
        upstream_events=funnel.get("upstream_events", 0),
        htf_aligned=funnel.get("htf_aligned", 0),
        m15_bound=funnel.get("m15_bound", 0),
        independent_m1_bound=funnel.get("independent_m1_bound", 0),
        event_target_bound=funnel.get("event_target_bound", 0),
        routed_fractal_candidates=funnel.get("routed_fractal_candidates", 0),
        exact_fills=exact_fills,
        v46_rejected_after_fill=v46_rejected,
        admitted_exact_fills=len(admitted),
        provider_tick_requests=requests,
        forensic_rejections=dict(sorted(forensic.items())),
    )
    return report, tuple(
        sorted(
            admitted,
            key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol),
        )
    )


def write_market_outputs(
    *,
    output: Path,
    report: S2PeriodMarketReport,
    rows: tuple[S2AdmittedFillRow, ...],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    slug = f"{report.period}-{report.symbol.lower()}"
    (output / f"capitalizer-s2a-{slug}-report.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-s2a-{slug}-fills.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> tuple[S2PeriodMarketReport, ...]:
    reports: list[S2PeriodMarketReport] = []
    for path in sorted(root.rglob("capitalizer-s2a-*-report.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("S2 report must be object")
        reports.append(S2PeriodMarketReport(**raw))
    return tuple(reports)


def _load_rows(root: Path) -> tuple[S2AdmittedFillRow, ...]:
    rows: list[S2AdmittedFillRow] = []
    for path in sorted(root.rglob("capitalizer-s2a-*-fills.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(S2AdmittedFillRow(**json.loads(line)))
    return tuple(rows)


def aggregate_s2a(root: Path, output: Path) -> dict[str, object]:
    reports = _load_reports(root)
    rows = _load_rows(root)
    if len(reports) != 27:
        raise ValueError(f"S2A requires 27 reports, got {len(reports)}")
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "market_period_reports": len(reports),
        "market_count": len({row.symbol for row in reports}),
        "funnel": {
            "upstream_events": sum(row.upstream_events for row in reports),
            "htf_aligned": sum(row.htf_aligned for row in reports),
            "m15_bound": sum(row.m15_bound for row in reports),
            "independent_m1_bound": sum(
                row.independent_m1_bound for row in reports
            ),
            "event_target_bound": sum(row.event_target_bound for row in reports),
            "routed_fractal_candidates": sum(
                row.routed_fractal_candidates for row in reports
            ),
            "exact_fills": sum(row.exact_fills for row in reports),
            "v46_rejected_after_fill": sum(
                row.v46_rejected_after_fill for row in reports
            ),
            "admitted_exact_fills": len(rows),
        },
        "forensic_rejections": dict(
            sorted(
                (
                    key,
                    sum(row.forensic_rejections.get(key, 0) for row in reports),
                )
                for key in {
                    key
                    for row in reports
                    for key in row.forensic_rejections
                }
            )
        ),
        "periods": {},
        "terminal_outcome_read": False,
        "realized_r_read": False,
        "strategy_economics_calculated": False,
        "fresh_holdout_opened": False,
        "candidate_promotion_allowed": False,
        "trader_certified": False,
    }
    periods: dict[str, object] = {}
    output.mkdir(parents=True, exist_ok=True)
    for period in PERIODS:
        population = tuple(row for row in rows if row.period == period)
        max3 = select_max3(population)
        periods[period] = {
            "admitted_exact_fills": len(population),
            "max3_selected_fills": len(max3),
            "max3_is_ceiling_not_quota": True,
            "outcome_used_for_selection": False,
        }
        with (output / f"capitalizer-s2a-{period}-max3.jsonl").open(
            "w",
            encoding="utf-8",
        ) as handle:
            for row in max3:
                handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    payload["periods"] = periods
    payload["next_phase"] = (
        "S2A_POPULATION_READY_FOR_FROZEN_GROSS_ECONOMICS"
        if rows
        else "S2A_ZERO_ADMITTED_POPULATION_REQUIRES_ROOT_CAUSE"
    )
    (output / "capitalizer-s2a-aggregate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _run_market(args: argparse.Namespace) -> None:
    client = SpotwareCTraderOpenApiClient(
        credentials=m1_clone._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"S2 cTrader DEMO authentication failed: {ready.error}")
        _provider_symbol, symbol_id, digits = m1_clone._selected_symbol(
            client,
            args.symbol,
        )
        consumed = s1._load_consumed_bars(args.m1_root)
        if not consumed:
            raise ValueError("S2 consumed M1 is empty")
        if any(row.symbol != args.symbol for row in consumed):
            raise ValueError("S2 consumed M1 symbol mismatch")
        for period in PERIODS:
            report, rows = build_period_market_population(
                client,
                consumed_bars=consumed,
                symbol=args.symbol,
                session=CapitalizerSession(args.session),
                period=period,
                symbol_id=symbol_id,
                digits=digits,
            )
            write_market_outputs(output=args.output, report=report, rows=rows)
            print(json.dumps(asdict(report), sort_keys=True))
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("s2a-market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("--symbol", required=True)
    market.add_argument("--session", required=True)
    market.add_argument("--output", type=Path, required=True)
    aggregate = sub.add_parser("s2a-aggregate")
    aggregate.add_argument("input", type=Path)
    aggregate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "s2a-market":
        _run_market(args)
    else:
        print(json.dumps(aggregate_s2a(args.input, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
