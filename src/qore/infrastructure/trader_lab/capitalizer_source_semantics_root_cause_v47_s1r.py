"""V47-S1R pre-economic source-semantics root-cause audit.

This audit measures whether V47-S1 population collapse is caused by legitimate
source conditions or by composition coupling introduced by S0. It never admits
a trade and never reads terminal outcomes/economics.

Frozen in PR #623 comment 5896367436.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_candidate_assembly_v47_s0 as s0,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_context_binders_v47_s0 as binders,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    _pivot_indices,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import detect_cisd
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    bar_interacts_with_poi,
    detect_fair_value_gap,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
)

IDENTITY = "QORE_CAPITALIZER_SOURCE_SEMANTICS_ROOT_CAUSE_AUDIT_V47_S1R"
PREDECLARATION_COMMENT_ID = 5896367436


class M15FailureClass(StrEnum):
    STRICT_PRE_EVENT_PASS = "STRICT_PRE_EVENT_PASS"
    HTF_UNRESOLVED = "HTF_UNRESOLVED"
    HTF_DIRECTION_NOT_ALIGNED = "HTF_DIRECTION_NOT_ALIGNED"
    PRE_EVENT_CISD_EXISTS_POI_REINTERACTION_ONLY_BLOCKER = (
        "PRE_EVENT_CISD_EXISTS_POI_REINTERACTION_ONLY_BLOCKER"
    )
    POST_EVENT_STRICT_CISD_BEFORE_DEADLINE = (
        "POST_EVENT_STRICT_CISD_BEFORE_DEADLINE"
    )
    POST_EVENT_CISD_EXISTS_POI_REINTERACTION_ONLY_BLOCKER = (
        "POST_EVENT_CISD_EXISTS_POI_REINTERACTION_ONLY_BLOCKER"
    )
    OPPOSING_SERIES_EXISTS_NO_CLOSE_THROUGH = (
        "OPPOSING_SERIES_EXISTS_NO_CLOSE_THROUGH"
    )
    NO_CAUSAL_OPPOSING_SERIES = "NO_CAUSAL_OPPOSING_SERIES"


@dataclass(frozen=True, slots=True)
class _M15Scan:
    strict_confirmed: bool
    structural_without_poi_confirmed: bool
    opposing_series_seen: bool
    close_through_seen: bool


@dataclass(frozen=True, slots=True)
class IndependentM1Audit:
    local_sweep_cisd: bool
    validated_order_block: bool
    m1_mss: bool
    displacement_fvg: bool

    @property
    def owner_m1_triad_complete(self) -> bool:
        return self.validated_order_block and self.m1_mss and self.displacement_fvg


@dataclass(frozen=True, slots=True)
class S1RPeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    source_events: int
    m15_failure_classes: dict[str, int]
    current_context_passes: int
    current_m1_passes: int
    current_m1_failures_audited: int
    independent_m1_local_sweep_cisd: int
    independent_m1_validated_ob: int
    independent_m1_mss: int
    independent_m1_displacement_fvg: int
    independent_m1_owner_triad_complete: int
    current_s0_ftm_route_mechanically_reachable: bool = False
    ftm_separate_population_census_complete: bool = False
    terminal_outcome_read: bool = False
    economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    admission_changed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S1R identity drift")
        if self.period not in s1.PERIODS:
            raise ValueError("S1R period drift")
        if (
            self.current_s0_ftm_route_mechanically_reachable
            or self.ftm_separate_population_census_complete
            or self.terminal_outcome_read
            or self.economics_calculated
            or self.fresh_holdout_opened
            or self.admission_changed
            or self.trader_certified
        ):
            raise ValueError("S1R governance drift")
        if sum(self.m15_failure_classes.values()) != self.source_events:
            raise ValueError("S1R M15 classification must cover every source event")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("S1R requires aware timestamps")
    return value.astimezone(UTC)


def _direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


def _source(bar: CapitalizerM1Bar) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _opposing(
    bar: CapitalizerSourceBar,
    direction: CapitalizerSourceDirection,
) -> bool:
    if bar.close == bar.open:
        return False
    if direction is CapitalizerSourceDirection.BULLISH:
        return bar.close < bar.open
    return bar.close > bar.open


def _scan_m15(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    htf: CapitalizerSourceClosureObservation,
    pois: tuple[CapitalizerSourcePOI, ...],
    after: datetime,
    before: datetime,
) -> _M15Scan:
    """Separate CISD structure from same-HTF-POI reinteraction."""

    after_at = _aware(after)
    before_at = _aware(before)
    if before_at <= after_at:
        return _M15Scan(False, False, False, False)

    frames = tuple(
        frame
        for frame in _aggregate_tf(bars, minutes=15)
        if after_at < frame.closed_at <= before_at
    )
    opposing_seen = False
    close_seen = False
    no_poi_confirmed = False

    for index, confirmation in enumerate(frames):
        cursor = index - 1
        if cursor < 0 or not _opposing(frames[cursor].source, direction):
            continue
        start = cursor
        while start > 0 and _opposing(frames[start - 1].source, direction):
            start -= 1
        series_frames = frames[start:index]
        if not series_frames:
            continue
        opposing_seen = True
        series = tuple(frame.source for frame in series_frames)
        structural = detect_cisd(
            causal_series=series,
            confirmation_bar=confirmation.source,
            direction=direction,
            important_level_reached=True,
            higher_timeframe_closure=htf,
        )
        if not structural.setup_confirmed:
            continue
        close_seen = True
        actual_poi = any(
            bar_interacts_with_poi(bar=bar, poi=poi)
            for bar in (*series, confirmation.source)
            for poi in pois
        )
        if actual_poi:
            return _M15Scan(True, no_poi_confirmed, True, True)
        no_poi_confirmed = True

    return _M15Scan(False, no_poi_confirmed, opposing_seen, close_seen)


def classify_m15_source_event(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    event: s0.S0ICTSourceEvent,
) -> M15FailureClass:
    direction = _direction(event.side)
    htf = binders.bind_latest_h1_context(
        bars,
        decision_at=event.source_event_at,
    )
    if htf is None:
        return M15FailureClass.HTF_UNRESOLVED
    if (
        htf.closure.direction is not direction
        or htf.daily_bias.direction is not direction
    ):
        return M15FailureClass.HTF_DIRECTION_NOT_ALIGNED

    pre = _scan_m15(
        bars,
        direction=direction,
        htf=htf.closure,
        pois=htf.poi_context.interacting_pois,
        after=htf.confirmed_at,
        before=event.source_event_at,
    )
    if pre.strict_confirmed:
        return M15FailureClass.STRICT_PRE_EVENT_PASS
    if pre.structural_without_poi_confirmed:
        return M15FailureClass.PRE_EVENT_CISD_EXISTS_POI_REINTERACTION_ONLY_BLOCKER

    post = _scan_m15(
        bars,
        direction=direction,
        htf=htf.closure,
        pois=htf.poi_context.interacting_pois,
        after=event.source_event_at,
        before=event.h1_deadline,
    )
    if post.strict_confirmed:
        return M15FailureClass.POST_EVENT_STRICT_CISD_BEFORE_DEADLINE
    if post.structural_without_poi_confirmed:
        return M15FailureClass.POST_EVENT_CISD_EXISTS_POI_REINTERACTION_ONLY_BLOCKER
    if pre.close_through_seen or post.close_through_seen:
        # Defensive: close-through with aligned HTF should already have been
        # captured as strict or no-POI structural confirmation.
        return M15FailureClass.OPPOSING_SERIES_EXISTS_NO_CLOSE_THROUGH
    if pre.opposing_series_seen or post.opposing_series_seen:
        return M15FailureClass.OPPOSING_SERIES_EXISTS_NO_CLOSE_THROUGH
    return M15FailureClass.NO_CAUSAL_OPPOSING_SERIES


def _opposing_series_ending_at(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    end_index: int,
    side: CapitalizerSide,
) -> tuple[int, ...]:
    selected: list[int] = []
    index = end_index
    while index >= 0:
        bar = bars[index]
        opposing = (
            bar.close < bar.open
            if side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if not opposing:
            break
        selected.append(index)
        index -= 1
    selected.reverse()
    return tuple(selected)


def _directional_fvg(
    first: CapitalizerSourceBar,
    middle: CapitalizerSourceBar,
    third: CapitalizerSourceBar,
    *,
    direction: CapitalizerSourceDirection,
) -> bool:
    poi = detect_fair_value_gap(
        candle1=first,
        candle2=middle,
        candle3=third,
    )
    if poi is None:
        return False
    if direction is CapitalizerSourceDirection.BULLISH:
        return poi.kind.value == "BULLISH_FVG"
    return poi.kind.value == "BEARISH_FVG"


def audit_independent_m1_after_m15(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    htf: CapitalizerSourceClosureObservation,
    after: datetime,
    before: datetime,
) -> IndependentM1Audit:
    """Census the retained TTrades local-sweep CISD route plus Owner M1 triad."""

    direction = _direction(side)
    selected = tuple(
        row
        for row in bars
        if _aware(after) < row.closed_at <= _aware(before)
    )
    if len(selected) < 6:
        return IndependentM1Audit(False, False, False, False)

    local_sweep_cisd = False
    validated_ob = False
    mss_ok = False
    fvg_ok = False

    for sweep_index in range(2, len(selected) - 1):
        pivots = _pivot_indices(
            selected,
            before_index=sweep_index - 1,
            high=side is CapitalizerSide.SHORT,
        )
        if not pivots:
            continue
        pivot = selected[pivots[-1]]
        swept_level = pivot.low if side is CapitalizerSide.LONG else pivot.high
        sweep_bar = selected[sweep_index]
        swept = (
            sweep_bar.low < swept_level
            if side is CapitalizerSide.LONG
            else sweep_bar.high > swept_level
        )
        if not swept:
            continue

        series_indices = _opposing_series_ending_at(
            selected,
            end_index=sweep_index,
            side=side,
        )
        probe = sweep_index + 1
        while not series_indices and probe < len(selected) - 1:
            bar = selected[probe]
            if (
                bar.close < bar.open
                if side is CapitalizerSide.LONG
                else bar.close > bar.open
            ):
                series_indices = _opposing_series_ending_at(
                    selected,
                    end_index=probe,
                    side=side,
                )
                break
            probe += 1
        if not series_indices:
            continue

        series = tuple(_source(selected[index]) for index in series_indices)
        start_confirmation = series_indices[-1] + 1
        for confirmation_index in range(start_confirmation, len(selected)):
            confirmation = selected[confirmation_index]
            crossed = (
                confirmation.close > series[0].open
                if side is CapitalizerSide.LONG
                else confirmation.close < series[0].open
            )
            if not crossed:
                continue
            cisd = detect_cisd(
                causal_series=series,
                confirmation_bar=_source(confirmation),
                direction=direction,
                important_level_reached=True,
                higher_timeframe_closure=htf,
            )
            if not cisd.setup_confirmed:
                continue
            local_sweep_cisd = True
            ob = remediation.assess_m1_order_block(
                direction=direction,
                causal_series=series,
                poi_reached=True,
                cisd=cisd,
            )
            validated_ob = validated_ob or ob.confirmed

            causal = tuple(
                row
                for row in selected
                if row.closed_at <= _aware(before)
            )
            mss = remediation.detect_m1_mss(
                bars=causal,
                direction=direction,
                after=confirmation.opened_at,
                before=_aware(before),
            )
            if not mss.confirmed or mss.confirmed_at is None:
                continue
            mss_ok = True
            mss_index = next(
                (
                    index
                    for index, row in enumerate(causal)
                    if row.closed_at == mss.confirmed_at
                ),
                None,
            )
            if (
                mss_index is not None
                and 0 < mss_index < len(causal) - 1
                and _directional_fvg(
                    _source(causal[mss_index - 1]),
                    _source(causal[mss_index]),
                    _source(causal[mss_index + 1]),
                    direction=direction,
                )
            ):
                fvg_ok = True
            if validated_ob and mss_ok and fvg_ok:
                return IndependentM1Audit(True, True, True, True)
            break

    return IndependentM1Audit(
        local_sweep_cisd=local_sweep_cisd,
        validated_order_block=validated_ob,
        m1_mss=mss_ok,
        displacement_fvg=fvg_ok,
    )


def audit_period_market(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    symbol: str,
    session: CapitalizerSession,
    period: str,
) -> S1RPeriodMarketReport:
    start, end = s1.PERIODS[period]
    prepared = s1._prepare_source_series(bars)
    days = s1._operating_days(
        bars,
        session=session,
        period_start=start,
        period_end=end,
    )
    m15_counts: Counter[str] = Counter()
    current_context = 0
    current_m1 = 0
    m1_failures = 0
    independent_local = 0
    independent_ob = 0
    independent_mss = 0
    independent_fvg = 0
    independent_triad = 0
    source_events = 0

    opened = prepared.opened
    for day in days:
        local = s1._day_slice(
            bars,
            opened,
            operating_day=day,
            session=session,
        )
        if not local:
            continue
        events = s1.bind_source_window_ict_events(
            local,
            session=session,
            operating_day=day,
            prepared=prepared,
        )
        source_events += len(events)
        for event in events:
            classification = classify_m15_source_event(local, event=event)
            m15_counts[classification.value] += 1

            direction = _direction(event.side)
            context = binders.bind_canonical_source_context(
                local,
                direction=direction,
                entry_price=event.primary_armed_level,
                decision_at=event.source_event_at,
            )
            if context is None:
                continue
            current_context += 1
            current = binders.bind_m1_source_structure(
                local,
                direction=direction,
                higher_timeframe_closure=context.htf.closure,
                zone=event.zone,
                after=context.m15.confirmed_at,
                before=event.source_event_at,
            )
            if current is not None:
                current_m1 += 1
                continue

            m1_failures += 1
            independent = audit_independent_m1_after_m15(
                local,
                side=event.side,
                htf=context.htf.closure,
                after=context.m15.confirmed_at,
                before=event.h1_deadline,
            )
            independent_local += int(independent.local_sweep_cisd)
            independent_ob += int(independent.validated_order_block)
            independent_mss += int(independent.m1_mss)
            independent_fvg += int(independent.displacement_fvg)
            independent_triad += int(independent.owner_m1_triad_complete)

    return S1RPeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        source_events=source_events,
        m15_failure_classes=dict(sorted(m15_counts.items())),
        current_context_passes=current_context,
        current_m1_passes=current_m1,
        current_m1_failures_audited=m1_failures,
        independent_m1_local_sweep_cisd=independent_local,
        independent_m1_validated_ob=independent_ob,
        independent_m1_mss=independent_mss,
        independent_m1_displacement_fvg=independent_fvg,
        independent_m1_owner_triad_complete=independent_triad,
    )


def write_report(report: S1RPeriodMarketReport, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-v47-s1r-{report.period}-{report.symbol.lower()}.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _json_int(row: dict[str, object], key: str) -> int:
    value = row.get(key)
    if type(value) is not int:
        raise ValueError(f"S1R aggregate field {key} must be int")
    return value


def aggregate(root: Path, output: Path) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    for path in sorted(root.rglob("capitalizer-v47-s1r-*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("S1R report must be object")
        reports.append(raw)
    if len(reports) != 27:
        raise ValueError(f"S1R requires 27 reports, got {len(reports)}")

    reasons: Counter[str] = Counter()
    for report in reports:
        raw_reasons = report["m15_failure_classes"]
        if not isinstance(raw_reasons, dict):
            raise ValueError("S1R m15_failure_classes must be object")
        reasons.update({str(k): int(v) for k, v in raw_reasons.items()})

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "market_period_reports": len(reports),
        "market_count": len({str(row["symbol"]) for row in reports}),
        "source_events": sum(_json_int(row, "source_events") for row in reports),
        "m15_failure_classes": dict(sorted(reasons.items())),
        "current_context_passes": sum(
            _json_int(row, "current_context_passes") for row in reports
        ),
        "current_m1_passes": sum(
            _json_int(row, "current_m1_passes") for row in reports
        ),
        "current_m1_failures_audited": sum(
            _json_int(row, "current_m1_failures_audited") for row in reports
        ),
        "independent_m1_local_sweep_cisd": sum(
            _json_int(row, "independent_m1_local_sweep_cisd") for row in reports
        ),
        "independent_m1_validated_ob": sum(
            _json_int(row, "independent_m1_validated_ob") for row in reports
        ),
        "independent_m1_mss": sum(
            _json_int(row, "independent_m1_mss") for row in reports
        ),
        "independent_m1_displacement_fvg": sum(
            _json_int(row, "independent_m1_displacement_fvg") for row in reports
        ),
        "independent_m1_owner_triad_complete": sum(
            _json_int(row, "independent_m1_owner_triad_complete") for row in reports
        ),
        "current_s0_ftm_route_mechanically_reachable": False,
        "ftm_separate_population_census_complete": False,
        "terminal_outcome_read": False,
        "economics_calculated": False,
        "fresh_holdout_opened": False,
        "admission_changed": False,
        "trader_certified": False,
        "decision": "S1R_A_B_DIAGNOSTICS_COMPLETE_FTM_CENSUS_REMAINS",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v47-s1r-aggregate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _load_consumed(root: Path, symbol: str) -> tuple[CapitalizerM1Bar, ...]:
    rows = tuple(
        row
        for row in iter_cibo_m1(root)
        if s1.CONSUMED_LOAD_START <= row.opened_at < s1.CONSUMED_LOAD_END
    )
    if not rows:
        raise ValueError("S1R provider-native M1 is empty")
    if any(row.symbol != symbol for row in rows):
        raise ValueError("S1R symbol mismatch")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("--symbol", required=True)
    market.add_argument("--session", required=True)
    market.add_argument("--output", type=Path, required=True)

    matrix = sub.add_parser("aggregate")
    matrix.add_argument("input", type=Path)
    matrix.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "market":
        bars = _load_consumed(args.m1_root, args.symbol)
        for period in s1.PERIODS:
            report = audit_period_market(
                bars,
                symbol=args.symbol,
                session=CapitalizerSession(args.session),
                period=period,
            )
            write_report(report, args.output)
            print(json.dumps(asdict(report), sort_keys=True))
        return

    payload = aggregate(args.input, args.output)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
