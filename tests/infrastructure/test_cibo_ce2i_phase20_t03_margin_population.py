from __future__ import annotations

import json
from datetime import timedelta

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t03_margin_population import (
    assess_phase20_t03_margin_population,
)

BASE = FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at + timedelta(hours=1)

_CASES = (
    (TraderLineage.VT08_FOREX, "GBPUSD", "1.25", "100000", "0.0001", "10"),
    (TraderLineage.R34_XAUUSD, "XAUUSD", "3800", "100", "0.01", "1"),
    (TraderLineage.R38_EURUSD, "EURUSD", "1.10", "100000", "0.0001", "10"),
    (TraderLineage.R43_GBPUSD, "GBPUSD", "1.25", "100000", "0.0001", "10"),
    (TraderLineage.R38_GBPJPY, "GBPJPY", "190", "100000", "0.01", "6"),
    (TraderLineage.R42_AUDJPY, "AUDJPY", "100", "100000", "0.01", "6"),
    (TraderLineage.VT31_NAS100, "NAS100", "20000", "1", "1", "1"),
)


def _candidate(
    *,
    index: int,
    trader: TraderLineage,
    symbol: str,
    entry: str,
    contract_size: str,
    tick_size: str,
    tick_value: str,
) -> dict[str, object]:
    signal = f"signal-{index}"
    minimum_volume = "1" if symbol == "NAS100" else "0.01"
    volume_step = minimum_volume
    margin_per_volume = "100" if symbol == "NAS100" else "1000"
    stop = (
        str(int(entry) - 100)
        if symbol == "NAS100"
        else (
            "3790"
            if symbol == "XAUUSD"
            else str(float(entry) - (1 if "JPY" in symbol else 0.01))
        )
    )
    target = (
        str(int(entry) + 200)
        if symbol == "NAS100"
        else (
            "3820"
            if symbol == "XAUUSD"
            else str(float(entry) + (2 if "JPY" in symbol else 0.02))
        )
    )
    opportunity = {
        "trader_id": trader.value,
        "signal_fingerprint": signal,
        "qore_symbol": symbol,
        "provider_symbol": symbol,
        "side": "long",
        "entry_type": "market",
        "intended_entry": entry,
        "stop_loss": stop,
        "take_profit": target,
        "stop_loss_per_volume": "1000",
        "margin_per_volume": margin_per_volume,
        "volume_step": volume_step,
        "minimum_volume": minimum_volume,
        "maximum_volume": "10",
        "minimum_execution_steps": 1,
        "decision_context": [],
    }
    provider = {
        "provider_key": "ctrader-demo",
        "qore_symbol": symbol,
        "provider_symbol": symbol,
        "bid": entry,
        "ask": entry,
        "contract_size": contract_size,
        "tick_size": tick_size,
        "tick_value": tick_value,
        "minimum_volume": minimum_volume,
        "maximum_volume": "10",
        "volume_step": volume_step,
        "margin_per_volume": margin_per_volume,
        "commission_per_volume_usd": "0",
        "slippage_reserve_per_volume_usd": "0",
        "observed_at": (BASE - timedelta(seconds=1)).isoformat(),
    }
    return {
        "provider_evidence_id": f"provider:{signal}",
        "opportunity": opportunity,
        "provider_observation": provider,
        "candidate": {
            "signal_fingerprint": signal,
            "trader_id": trader.value,
            "qore_symbol": symbol,
            "provider_symbol": symbol,
        },
    }


def _book(limit: int = 7) -> VersionedPhase20ForwardEvidenceBook:
    decisions = []
    for index, case in enumerate(_CASES[:limit]):
        trader, symbol, entry, contract_size, tick_size, tick_value = case
        at = BASE + timedelta(minutes=index)
        candidate = _candidate(
            index=index,
            trader=trader,
            symbol=symbol,
            entry=entry,
            contract_size=contract_size,
            tick_size=tick_size,
            tick_value=tick_value,
        )
        payload = {
            "evidence_kind": "FORWARD_OBSERVED",
            "candidates": [candidate],
        }
        decisions.append(
            Phase20ForwardDecisionSeal(
                evidence_id=f"decision:{index}",
                decision_epoch_id=f"epoch:{index}",
                evidence_sha256=f"sha256:{index + 1:064x}",
                decision_at=at,
                candidate_id="candidate",
                code_sha="code",
                parameter_sha256="params",
                signal_fingerprints=(f"signal-{index}",),
                canonical_payload_json=json.dumps(payload, sort_keys=True),
                sealed_at=at + timedelta(milliseconds=100),
                seal_deadline_at=at + timedelta(seconds=2),
            )
        )
    return VersionedPhase20ForwardEvidenceBook(
        generation=len(decisions),
        decisions=tuple(decisions),
    )


def test_t03_forward_margin_population_covers_all_seven_lineages() -> None:
    audit = assess_phase20_t03_margin_population(evidence_book=_book())

    assert audit.candidate_instances == 7
    assert audit.margin_identified_instances == 7
    assert audit.blocked_candidate_instances == 0
    assert len(audit.represented_lineages) == 7
    assert audit.minimum_required_lineages == 7
    assert audit.frozen_lineage_coverage_met is True
    assert audit.forward_margin_population_identified is True
    assert audit.minimum_margin_usd is not None
    assert audit.maximum_margin_usd is not None
    assert audit.p50_exposure_per_margin is not None
    assert audit.p95_exposure_per_margin is not None
    assert audit.maximum_exposure_per_margin is not None
    assert audit.historical_2017_margin_terms_proven is False
    assert audit.equivalent_expression_universe_certified is False
    assert "HISTORICAL_2017_MARGIN_TERMS_NOT_PROVEN" in audit.blockers


def test_t03_forward_margin_population_does_not_promote_partial_lineages() -> None:
    audit = assess_phase20_t03_margin_population(
        evidence_book=_book(limit=3)
    )

    assert audit.candidate_instances == 3
    assert len(audit.represented_lineages) == 3
    assert audit.frozen_lineage_coverage_met is False
    assert audit.forward_margin_population_identified is False
    assert "T03_FORWARD_LINEAGE_COVERAGE_NOT_MET:3/7" in audit.blockers
