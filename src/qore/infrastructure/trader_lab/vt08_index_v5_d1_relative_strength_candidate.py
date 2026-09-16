"""VT-08 Index V5 D1 frozen relative-strength candidate execution."""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import (
    ClosurePolicy,
    SwingPolicy,
    _signal,
)
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import _load_candidate_market
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    CANDIDATE_ID as BASE_CANDIDATE_ID,
)
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    RULE_FINGERPRINT as BASE_RULE_FINGERPRINT,
)
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    build_v3_candidate_report,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    AUTHORIZED_MARKETS,
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_v5_d1_relative_strength_candidate.v1"
CANDIDATE_ID = "VT08_INDEX_V5_D1_RELATIVE_STRENGTH_001"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
SOURCE_REFS = (
    "ttrades:relative-strength-weakness-smt-divergence:2026-02-28",
    "ttrades:how-to-use-smt-divergence-fractal-model:2026-05-30",
    "ttrades:ideal-formation:2026-06-27",
    "ttrades:positional-entries:2026-08-08",
)
_RULE_MATERIAL = {
    "candidate_id": CANDIDATE_ID,
    "base_candidate_id": BASE_CANDIDATE_ID,
    "base_rule_fingerprint": BASE_RULE_FINGERPRINT,
    "cross_index_scope": AUTHORIZED_MARKETS,
    "same_side_structural_signals": 2,
    "opposite_side_structural_signals": 0,
    "remaining_peer": "fail-closed-nonconfirmation",
    "peer_signal_closure": ClosurePolicy.C2_OR_C3_BODY_CLOSE.value,
    "peer_signal_swing": SwingPolicy.FARTHEST_STRUCTURAL.value,
    "source_refs": SOURCE_REFS,
}
RULE_FINGERPRINT = sha256(
    json.dumps(
        _RULE_MATERIAL,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
).hexdigest()


def _max_drawdown(values: Sequence[Decimal]) -> Decimal:
    equity = Decimal()
    peak = Decimal()
    worst = Decimal()
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def _metrics(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    values = tuple(Decimal(str(row["r_multiple"])) for row in rows)
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    total = sum(values, Decimal())
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / len(values)) if values else "0",
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(_max_drawdown(values)),
    }


def _breakdown(rows: Sequence[dict[str, object]], field: str) -> dict[str, object]:
    values = sorted({str(row[field]) for row in rows})
    return {
        value: _metrics([row for row in rows if str(row[field]) == value])
        for value in values
    }


def _load_indexes(
    paths: dict[str, Path], *, expected_software_sha: str, minimum_evidence_days: int
) -> tuple[dict[str, dict[datetime, Vt08IndexC2R1Bar]], dict[str, object]]:
    indexed: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    provenance: dict[str, object] = {}
    for symbol, path in paths.items():
        fingerprint, provider, checked_at, bars = _load_candidate_market(
            path,
            expected_symbol=symbol,
            expected_software_sha=expected_software_sha,
            minimum_evidence_days=minimum_evidence_days,
        )
        indexed[symbol] = {bar.opened_at.astimezone(UTC): bar for bar in bars}
        provenance[symbol] = {
            "account_fingerprint": fingerprint,
            "provider_symbol": provider,
            "checked_at": checked_at.isoformat(),
            "software_sha": expected_software_sha,
            "m15_bars": len(bars),
        }
    return indexed, provenance


def _accept_peer_counts(same: int, opposite: int) -> bool:
    return same == 2 and opposite == 0


def _peer_counts(
    *,
    indexed: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    decision: datetime,
    side: DemoTradingSetupSide,
) -> tuple[int, int]:
    same = 0
    opposite = 0
    for symbol in AUTHORIZED_MARKETS:
        signal = _signal(
            symbol=symbol,
            bars_by_open=indexed[symbol],
            decision_at=decision,
            closure=ClosurePolicy.C2_OR_C3_BODY_CLOSE,
            swing=SwingPolicy.FARTHEST_STRUCTURAL,
        )
        if signal is None:
            continue
        if signal.side is side:
            same += 1
        else:
            opposite += 1
    return same, opposite


def build_candidate_report(
    *,
    nas100: Path,
    sp500: Path,
    us30: Path,
    start_date: date,
    end_date_exclusive: date,
    expected_software_sha: str,
    minimum_evidence_days: int,
) -> dict[str, object]:
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    indexed, provenance = _load_indexes(
        paths,
        expected_software_sha=expected_software_sha,
        minimum_evidence_days=minimum_evidence_days,
    )
    base = build_v3_candidate_report(
        nas100=nas100,
        sp500=sp500,
        us30=us30,
        start_date=start_date,
        end_date_exclusive=end_date_exclusive,
        expected_software_sha=expected_software_sha,
        minimum_evidence_days=minimum_evidence_days,
    )
    raw_trades = cast(list[object], base["trades"])
    retained: list[dict[str, object]] = []
    for item in raw_trades:
        if type(item) is not dict:
            raise ValueError("base candidate trade payload malformed")
        trade = cast(dict[str, object], item)
        decision = datetime.fromisoformat(str(trade["signal_at"]))
        side = DemoTradingSetupSide(str(trade["side"]))
        same, opposite = _peer_counts(indexed=indexed, decision=decision, side=side)
        if _accept_peer_counts(same, opposite):
            enriched = dict(trade)
            enriched["cross_index_simultaneous_same_side_signals"] = same
            enriched["cross_index_simultaneous_opposite_side_signals"] = opposite
            retained.append(enriched)
    ordered = sorted(retained, key=lambda row: (str(row["signal_at"]), str(row["symbol"])))
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "base_candidate_id": BASE_CANDIDATE_ID,
        "base_rule_fingerprint": BASE_RULE_FINGERPRINT,
        "rules": _RULE_MATERIAL,
        "partition": {
            "start_date": start_date.isoformat(),
            "end_date_exclusive": end_date_exclusive.isoformat(),
        },
        "evidence_contract": {
            "expected_software_sha": expected_software_sha,
            "minimum_evidence_days": minimum_evidence_days,
            "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        },
        "provenance": provenance,
        "base_sample": cast(dict[str, object], base["metrics"])["sample"],
        "metrics": _metrics(ordered),
        "by_market": _breakdown(ordered, "symbol"),
        "by_side": _breakdown(ordered, "side"),
        "by_anchor": _breakdown(ordered, "anchor_hour_new_york"),
        "trades": ordered,
        "governance": {
            "research_only": True,
            "fresh_holdout_required": True,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100", type=Path, required=True)
    parser.add_argument("--sp500", type=Path, required=True)
    parser.add_argument("--us30", type=Path, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date-exclusive", type=date.fromisoformat, required=True)
    parser.add_argument("--expected-software-sha", required=True)
    parser.add_argument("--minimum-evidence-days", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_candidate_report(
        nas100=args.nas100,
        sp500=args.sp500,
        us30=args.us30,
        start_date=args.start_date,
        end_date_exclusive=args.end_date_exclusive,
        expected_software_sha=args.expected_software_sha,
        minimum_evidence_days=args.minimum_evidence_days,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            report, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": CANDIDATE_ID,
                "rule_fingerprint": RULE_FINGERPRINT,
                "sample": cast(dict[str, object], report["metrics"])["sample"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
