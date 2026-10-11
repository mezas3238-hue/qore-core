"""Real narrow-B01 CandidateEvent snapshots plus independently hashed M15 lineage.

Research only. Adds observed daily-bias cutoff to A's immutable CandidateEvent
snapshot WITHOUT modifying A's versioned contract or faking other situation
features. The cognitive B gate still MUST fail closed on other missing inputs
and unsigned bilateral contract; no order/fill/PNL authority.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_candidate_event_v1 import (
    from_narrow_b01_candidate,
)
from qore.infrastructure.trader_lab.vt08_5m_source_bias_asof_attestation_v1 import (
    SOURCE_SHA,
    _sha_bars,
    attest_bias,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _window_bars,
    evaluate_expansion_at_entry_indexed,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)

SCHEMA: Final = "qore.trader_lab.vt08_5m_a_b_narrow_source_lineage.research.v1"
_NY = ZoneInfo("America/New_York")


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()


def attest_narrow_candidate(
    *,
    candidate,
    bars_by_open,
) -> dict[str, object]:
    """Source values rederived from original as-of M15, not copied timestamps."""
    decision = candidate.decision_at.astimezone(UTC)
    proof = attest_bias(bars_by_open, decision_at=decision)
    if proof is None or proof.bias is None or proof.bias is not candidate.side:
        raise ValueError("candidate bias cannot be independently source attested")
    raw_c1 = _window_bars(
        bars_by_open,
        opened_at=candidate.reference_h4.opened_at,
        closed_at=candidate.reference_h4.closed_at,
    )
    raw_c2 = _window_bars(
        bars_by_open,
        opened_at=candidate.candle2.opened_at,
        closed_at=candidate.candle2.closed_at,
    )
    if raw_c1 is None or raw_c2 is None:
        raise ValueError("candidate H4 constituent M15 missing")
    if (
        candidate.reference_h4.closed_at > decision
        or candidate.candle2.closed_at != decision
        or candidate.protected_swing.confirmed_at > decision
    ):
        raise ValueError("candidate consumes future C1/C2/CISD")
    if candidate.protected_swing.confirmed_at not in {
        x.closed_at for x in raw_c2
    }:
        raise ValueError("PS confirmation not a real closed C2 M15 bar")
    # Prove raw source H4 boundaries match values used by the frozen evaluator.
    for expected, rows in (
        (candidate.reference_h4, raw_c1),
        (candidate.candle2, raw_c2),
    ):
        if (
            rows[0].open != expected.open
            or rows[-1].close != expected.close
            or max(x.high for x in rows) != expected.high
            or min(x.low for x in rows) != expected.low
        ):
            raise ValueError("candidate H4 value not authenticated by raw M15")
    material = {
        "current_source_day_m15_sha256": proof.current_day.m15_sha256,
        "previous_source_day_m15_sha256": proof.previous_day.m15_sha256,
        "c1_m15_sha256": _sha_bars(raw_c1),
        "c2_m15_sha256": _sha_bars(raw_c2),
        "cisd_confirmed_at": candidate.protected_swing.confirmed_at.astimezone(
            UTC
        ).isoformat(),
        "decision_at": decision.isoformat(),
    }
    event = from_narrow_b01_candidate(candidate, evidence_sha256=_digest(material))
    envelope = event.envelope()
    if envelope["source_event_id"] != event.source_event_id():
        raise AssertionError("A source-event stability contract violation")
    bias_cutoff = proof.current_day.day.closed_at.astimezone(UTC)
    if not bias_cutoff <= decision:
        raise ValueError("daily bias proof crosses decision")
    envelope["bias_feature_cutoff"] = bias_cutoff.isoformat()
    # Deliberately omit cognitive_feature_cutoffs: not yet reconstructed;
    # an inspecting B must still return cognitive_ready=False.
    envelope["bias_asof_evidence"] = proof.payload()
    envelope["h4_source_m15_provenance"] = material
    envelope["source_lineage_sha256"] = _digest({
        "envelope_snapshot_event_id": envelope["event_id"],
        "bias_asof": proof.payload(),
        "source_h4": material,
    })
    envelope["cognitive_feature_provenance_complete"] = False
    envelope["joint_a_b_contract_signed"] = False
    envelope["trades_executed"] = 0
    envelope["pnl_evaluated"] = False
    return envelope


def audit_market(path: Path) -> dict[str, object]:
    fp, symbol, checked_at, sha, m15 = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS or sha != SOURCE_SHA:
        raise ValueError("invalid consumed narrow B01 provenance input")
    by_open = {bar.opened_at: bar for bar in m15}
    candidates: list[dict[str, object]] = []
    by_day: Counter[str] = Counter()
    candidate_windows: Counter[str] = Counter()
    all_anchors = 0
    for bar in m15:
        local = bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.second != 0 or local.hour not in ANCHORS_NY:
            continue
        all_anchors += 1
        outcome = evaluate_expansion_at_entry_indexed(
            symbol=symbol,
            bars_by_open=by_open,
            decision_at=bar.opened_at,
        )
        if outcome.candidate is None:
            continue
        event = attest_narrow_candidate(
            candidate=outcome.candidate, bars_by_open=by_open,
        )
        if event["market"] != symbol:
            raise AssertionError("source event market drift")
        nyday = local.date().isoformat()
        by_day[nyday] += 1
        candidate_windows[str(local.hour)] += 1
        candidates.append(event)
    unique_ids = {row["source_event_id"] for row in candidates}
    if len(unique_ids) != len(candidates):
        raise AssertionError("two distinct structural candidates share source ID")
    accepted_days = sum(n == 1 for n in by_day.values())
    ambiguous_candidates = sum(n for n in by_day.values() if n != 1)
    if accepted_days + ambiguous_candidates != len(candidates):
        raise AssertionError("Owner daily cardinality mismatch")
    return {
        "schema": SCHEMA,
        "market": symbol,
        "evidence_source_software_sha": sha,
        "checked_at": checked_at.isoformat(),
        "account_fingerprint": fp,
        "all_owner_anchors": all_anchors,
        "source_candidates_with_real_bias_proof": len(candidates),
        "unique_daily_candidates": accepted_days,
        "ambiguous_day_candidates_excluded": ambiguous_candidates,
        "by_anchor_hour": dict(sorted(candidate_windows.items())),
        "events": candidates,
        "all_cognitive_features_verified": False,
        "joint_contract_approved": False,
        "pnl_evaluated": False,
        "trades_executed": 0,
        "live_authorized": False,
    }
