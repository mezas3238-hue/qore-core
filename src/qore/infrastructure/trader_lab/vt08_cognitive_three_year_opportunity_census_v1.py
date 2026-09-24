"""Three-year VT08 opportunity identity census across M15/M5/M3 and C3 shapes."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_c3_shape_opportunity_audit_v1 import (
    is_c3_closure_shape,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    _candle2_reversal_side,
    _latest_complete_source_days,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_density_recovery_v1 import (
    PROFILES,
    _ltf_window,
    _profile_bars,
    latest_confirmed_swing,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m5_fractal_density_recovery_v1 import (
    _candidate,
    _model_trade_m15_outer,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    Vt08B01ProtectedSwing,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_three_year_opportunity_census.v1"
_NY = ZoneInfo("America/New_York")
_PROFILE_LABEL: Final = {
    "M15_STANDARD": "M15",
    "M5_FRACTAL": "M5",
    "M3_FRACTAL": "M3",
}


@dataclass(frozen=True, slots=True)
class OpportunityVariant:
    market: str
    signal_at: datetime
    ny_date: date
    anchor_hour_ny: int
    side: DemoTradingSetupSide
    profile: str
    protected_swing: Vt08B01ProtectedSwing
    candidate: Vt08ExpansionCandidate

    @property
    def identity(self) -> tuple[str, datetime, str]:
        return (self.market, self.signal_at, self.side.value)

    def payload(self) -> dict[str, object]:
        return {
            "market": self.market,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "ny_date": self.ny_date.isoformat(),
            "anchor_hour_ny": self.anchor_hour_ny,
            "side": self.side.value,
            "profile": self.profile,
            "protected_swing": {
                "price": format(self.protected_swing.price, "f"),
                "confirmed_at": self.protected_swing.confirmed_at.astimezone(
                    UTC
                ).isoformat(),
                "opposing_series_opened_at": (
                    self.protected_swing.opposing_series_opened_at.astimezone(
                        UTC
                    ).isoformat()
                ),
                "cisd_level": format(self.protected_swing.cisd_level, "f"),
            },
        }


@dataclass(frozen=True, slots=True)
class C3ShapeIdentity:
    market: str
    signal_at: datetime
    ny_date: date
    anchor_hour_ny: int
    side: DemoTradingSetupSide

    @property
    def identity(self) -> tuple[str, datetime, str]:
        return (self.market, self.signal_at, self.side.value)

    def payload(self) -> dict[str, object]:
        return {
            "market": self.market,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "ny_date": self.ny_date.isoformat(),
            "anchor_hour_ny": self.anchor_hour_ny,
            "side": self.side.value,
        }


def _profile_variants(
    base_path: Path,
    *,
    profile: str,
    m3_path: Path | None,
) -> tuple[OpportunityVariant, ...]:
    _fingerprint, symbol, _checked_at, _software_sha, m15 = load_market_evidence(
        base_path
    )
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("census market outside frozen 5M universe")
    if profile not in PROFILES:
        raise ValueError("census profile outside source-authorized set")

    ltf, _minutes = _profile_bars(
        profile=profile,
        base_path=base_path,
        m3_path=m3_path,
        symbol=symbol,
        m15=m15,
    )
    m15_by_open = {bar.opened_at: bar for bar in m15}
    ltf_by_open = {bar.opened_at: bar for bar in ltf}
    result: list[OpportunityVariant] = []

    for entry_bar in m15:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue

        reference = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=8),
        )
        candle2 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=4),
        )
        if reference is None or candle2 is None or candle2.closed_at != entry_bar.opened_at:
            continue

        source_days = _latest_complete_source_days(
            m15_by_open,
            before_local=local,
        )
        if len(source_days) != 2:
            continue
        current_day, previous_day = source_days
        side = resolve_bias(previous_day=previous_day, current_day=current_day)
        if side is None:
            continue
        if _candle2_reversal_side(reference, candle2) is not side:
            continue

        rows = _ltf_window(
            profile=profile,
            bars_by_open=ltf_by_open,
            opened_at=candle2.opened_at,
            closed_at=candle2.closed_at,
        )
        if rows is None:
            continue

        important_level = (
            reference.low
            if side is DemoTradingSetupSide.LONG
            else reference.high
        )
        swings = protected_swings_in_candle2(
            rows,
            side=side,
            important_level=important_level,
        )
        if not swings:
            continue
        try:
            selected = latest_confirmed_swing(swings)
        except ValueError:
            continue

        candidate = _candidate(
            symbol=symbol,
            decision_at=entry_bar.opened_at,
            anchor=local.hour,
            reference=reference,
            candle2=candle2,
            side=side,
            protected=selected,
            entry_bar=entry_bar,
        )
        if candidate is None:
            continue
        result.append(
            OpportunityVariant(
                market=symbol,
                signal_at=entry_bar.opened_at,
                ny_date=local.date(),
                anchor_hour_ny=local.hour,
                side=side,
                profile=profile,
                protected_swing=selected,
                candidate=candidate,
            )
        )

    identities = [item.identity for item in result]
    if len(identities) != len(set(identities)):
        raise AssertionError("profile emitted duplicate opportunity identity")
    return tuple(sorted(result, key=lambda item: item.signal_at))


def _terminal_variants(
    variants: tuple[OpportunityVariant, ...],
    *,
    m15_by_open: dict[datetime, Vt08B01Bar],
) -> tuple[OpportunityVariant, ...]:
    by_day: dict[date, list[OpportunityVariant]] = defaultdict(list)
    for item in variants:
        by_day[item.ny_date].append(item)

    retained: list[OpportunityVariant] = []
    for day in sorted(by_day):
        rows = by_day[day]
        if len(rows) != 1:
            continue
        if _model_trade_m15_outer(
            rows[0].candidate,
            m15_by_open=m15_by_open,
        ) is None:
            continue
        retained.append(rows[0])
    return tuple(retained)


def _presence_mask(profiles: set[str]) -> str:
    labels = tuple(
        _PROFILE_LABEL[profile]
        for profile in PROFILES
        if profile in profiles
    )
    return "_".join(labels) if labels else "NONE"


def _union_summary(
    by_profile: dict[str, tuple[OpportunityVariant, ...]],
) -> dict[str, object]:
    membership: dict[tuple[str, datetime, str], set[str]] = defaultdict(set)
    variants_by_identity: dict[
        tuple[str, datetime, str], list[OpportunityVariant]
    ] = defaultdict(list)

    for profile, profile_rows in by_profile.items():
        for row in profile_rows:
            membership[row.identity].add(profile)
            variants_by_identity[row.identity].append(row)

    masks: Counter[str] = Counter(
        _presence_mask(profiles)
        for profiles in membership.values()
    )
    by_anchor: Counter[int] = Counter()
    by_side: Counter[str] = Counter()
    for identity_rows in variants_by_identity.values():
        exemplar = identity_rows[0]
        by_anchor[exemplar.anchor_hour_ny] += 1
        by_side[exemplar.side.value] += 1

    return {
        "distinct_opportunity_identities": len(membership),
        "profile_variant_count": sum(len(rows) for rows in by_profile.values()),
        "presence_masks": dict(sorted(masks.items())),
        "by_anchor_ny": {
            str(key): value for key, value in sorted(by_anchor.items())
        },
        "by_side": dict(sorted(by_side.items())),
    }


def _c3_shapes(base_path: Path) -> tuple[C3ShapeIdentity, ...]:
    _fingerprint, symbol, _checked_at, _software_sha, bars = load_market_evidence(
        base_path
    )
    m15_by_open = {bar.opened_at: bar for bar in bars}
    shapes: list[C3ShapeIdentity] = []

    for entry_bar in bars:
        local = entry_bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue

        c1 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=12),
        )
        c2 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=8),
        )
        c3 = source_h4_from_m15(
            m15_by_open,
            opened_at_local=local - timedelta(hours=4),
        )
        if (
            c1 is None
            or c2 is None
            or c3 is None
            or c3.closed_at != entry_bar.opened_at
        ):
            continue

        source_days = _latest_complete_source_days(
            m15_by_open,
            before_local=local,
        )
        if len(source_days) != 2:
            continue
        current_day, previous_day = source_days
        bias = resolve_bias(previous_day=previous_day, current_day=current_day)
        if bias is None:
            continue

        if _candle2_reversal_side(c1, c2) is bias:
            continue
        if not is_c3_closure_shape(c2, c3, bias=bias):
            continue

        shapes.append(
            C3ShapeIdentity(
                market=symbol,
                signal_at=entry_bar.opened_at,
                ny_date=local.date(),
                anchor_hour_ny=local.hour,
                side=bias,
            )
        )

    identities = [item.identity for item in shapes]
    if len(identities) != len(set(identities)):
        raise AssertionError("C3 audit emitted duplicate shape identity")
    return tuple(sorted(shapes, key=lambda item: item.signal_at))


def evaluate(
    base_path: Path,
    *,
    m3_path: Path,
) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, m15 = load_market_evidence(
        base_path
    )
    m15_by_open = {bar.opened_at: bar for bar in m15}

    mechanical = {
        profile: _profile_variants(
            base_path,
            profile=profile,
            m3_path=m3_path,
        )
        for profile in PROFILES
    }
    terminal = {
        profile: _terminal_variants(
            rows,
            m15_by_open=m15_by_open,
        )
        for profile, rows in mechanical.items()
    }

    mechanical_union = {
        row.identity
        for rows in mechanical.values()
        for row in rows
    }
    c3 = _c3_shapes(base_path)
    c3_ids = {row.identity for row in c3}
    c3_overlap = c3_ids & mechanical_union
    c3_only = c3_ids - mechanical_union

    return {
        "schema": SCHEMA,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "mechanical": {
            "by_profile": {
                profile: len(rows)
                for profile, rows in mechanical.items()
            },
            "union": _union_summary(mechanical),
        },
        "terminal": {
            "by_profile": {
                profile: len(rows)
                for profile, rows in terminal.items()
            },
            "union": _union_summary(terminal),
        },
        "c3_shape_only": {
            "shape_identities": len(c3_ids),
            "overlaps_c2_mechanical_union": len(c3_overlap),
            "c3_only_not_in_c2_mechanical_union": len(c3_only),
            "executable_trades": False,
        },
        "identity_rows": {
            "mechanical_profile_variants": [
                row.payload()
                for profile in PROFILES
                for row in mechanical[profile]
            ],
            "terminal_profile_variants": [
                row.payload()
                for profile in PROFILES
                for row in terminal[profile]
            ],
            "c3_shapes": [row.payload() for row in c3],
        },
        "governance": {
            "profiles_combined_for_execution": False,
            "union_is_diagnostic_only": True,
            "c3_executable": False,
            "identity_uses_pnl": False,
            "market_filtering": False,
            "anchor_filtering": False,
            "side_filtering": False,
            "live_authorized": False,
        },
    }


def to_json(base_path: Path, *, m3_path: Path) -> str:
    return json.dumps(
        evaluate(base_path, m3_path=m3_path),
        sort_keys=True,
        separators=(",", ":"),
    )
