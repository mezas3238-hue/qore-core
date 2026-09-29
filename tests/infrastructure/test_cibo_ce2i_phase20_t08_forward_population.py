from __future__ import annotations

import json
from datetime import datetime, timedelta

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_forward_population import (
    assess_phase20_t08_forward_magnitude_population,
)

BASE = FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at + timedelta(hours=1)


def _candidate(
    *,
    trader: TraderLineage,
    signal: str,
    symbol: str,
    entry: str,
    stop: str,
    target: str,
    contract_size: str,
    tick_size: str,
    tick_value: str,
    minimum_volume: str = "0.01",
    volume_step: str = "0.01",
    stop_loss_per_volume: str = "1000",
) -> dict[str, object]:
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
        "stop_loss_per_volume": stop_loss_per_volume,
        "margin_per_volume": "1000",
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
        "margin_per_volume": "1000",
        "commission_per_volume_usd": "0",
        "slippage_reserve_per_volume_usd": "0",
        "observed_at": (BASE - timedelta(seconds=1)).isoformat(),
    }
    candidate = {
        "signal_fingerprint": signal,
        "trader_id": trader.value,
        "qore_symbol": symbol,
        "provider_symbol": symbol,
    }
    return {
        "provider_evidence_id": f"provider:{signal}",
        "opportunity": opportunity,
        "provider_observation": provider,
        "candidate": candidate,
    }


def _decision(
    *,
    index: int,
    candidates: list[dict[str, object]],
    evidence_kind: str = "FORWARD_OBSERVED",
    decision_at: datetime | None = None,
    sealed: bool = True,
) -> Phase20ForwardDecisionSeal:
    at = decision_at or (BASE + timedelta(minutes=index))
    payload = {
        "evidence_kind": evidence_kind,
        "candidates": candidates,
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision:{index}",
        decision_epoch_id=f"epoch:{index}",
        evidence_sha256=f"sha256:{index + 1:064x}",
        decision_at=at,
        candidate_id="candidate",
        code_sha="code",
        parameter_sha256="params",
        signal_fingerprints=tuple(
            str(item["candidate"]["signal_fingerprint"])
            for item in candidates
        ),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=(at + timedelta(milliseconds=100) if sealed else None),
        seal_deadline_at=at + timedelta(seconds=2),
    )


def test_forward_population_counts_pair_magnitude_and_blocks_nas100() -> None:
    first = _decision(
        index=0,
        candidates=[
            _candidate(
                trader=TraderLineage.R43_GBPUSD,
                signal="gbpusd-1",
                symbol="GBPUSD",
                entry="1.25",
                stop="1.24",
                target="1.27",
                contract_size="100000",
                tick_size="0.0001",
                tick_value="10",
                stop_loss_per_volume="1200",
            ),
            _candidate(
                trader=TraderLineage.VT31_NAS100,
                signal="nas100-1",
                symbol="NAS100",
                entry="20000",
                stop="19900",
                target="20200",
                contract_size="1",
                tick_size="1",
                tick_value="1",
                minimum_volume="1",
                volume_step="1",
                stop_loss_per_volume="100",
            ),
        ],
    )
    second = _decision(
        index=1,
        candidates=[
            _candidate(
                trader=TraderLineage.R38_GBPJPY,
                signal="gbpjpy-1",
                symbol="GBPJPY",
                entry="190",
                stop="189",
                target="192",
                contract_size="100000",
                tick_size="0.01",
                tick_value="6",
                stop_loss_per_volume="700",
            )
        ],
    )
    report = assess_phase20_t08_forward_magnitude_population(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=2,
            decisions=(first, second),
        )
    )

    assert report.usable_forward_epochs == 2
    assert report.candidate_epochs == 2
    assert report.candidate_instances == 3
    assert report.native_magnitude_instances == 3
    assert report.usd_magnitude_complete_instances == 3
    assert report.blocked_candidate_instances == 0
    assert report.candidate_lineages == (
        TraderLineage.R38_GBPJPY,
        TraderLineage.R43_GBPUSD,
        TraderLineage.VT31_NAS100,
    )
    assert report.magnitude_lineages == (
        TraderLineage.R38_GBPJPY,
        TraderLineage.R43_GBPUSD,
        TraderLineage.VT31_NAS100,
    )
    assert report.candidate_symbols == ("GBPJPY", "GBPUSD", "NAS100")
    assert report.magnitude_symbols == ("GBPJPY", "GBPUSD", "NAS100")
    assert report.blocked_by_symbol == ()
    assert report.source_decision_sha256s == (
        first.evidence_sha256,
        second.evidence_sha256,
    )
    assert report.risk_equivalent_instances == 0
    assert report.correlation_state_instances == 0
    assert report.netting_credit_authorized is False
    assert "USD_FACTOR_MAGNITUDE_COVERAGE_INCOMPLETE" not in report.blockers
    assert "CAUSAL_CORRELATION_STATE_NOT_IDENTIFIED" in report.blockers


def test_forward_population_excludes_pre_freeze_synthetic_and_unsealed() -> None:
    usable = _decision(
        index=10,
        candidates=[
            _candidate(
                trader=TraderLineage.R34_XAUUSD,
                signal="xauusd-usable",
                symbol="XAUUSD",
                entry="3800",
                stop="3790",
                target="3820",
                contract_size="100",
                tick_size="0.01",
                tick_value="1",
            )
        ],
    )
    pre_freeze = _decision(
        index=11,
        candidates=[],
        decision_at=(
            FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at
            - timedelta(seconds=1)
        ),
    )
    synthetic = _decision(
        index=12,
        candidates=[],
        evidence_kind="SYNTHETIC_CONTRACT",
    )
    unsealed = _decision(
        index=13,
        candidates=[],
        sealed=False,
    )

    report = assess_phase20_t08_forward_magnitude_population(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=4,
            decisions=(pre_freeze, synthetic, unsealed, usable),
        )
    )

    assert report.usable_forward_epochs == 1
    assert report.candidate_epochs == 1
    assert report.candidate_instances == 1
    assert report.usd_magnitude_complete_instances == 1
    assert report.blocked_candidate_instances == 0
    assert report.magnitude_symbols == ("XAUUSD",)
    assert report.source_decision_sha256s == (usable.evidence_sha256,)
    assert "USD_FACTOR_MAGNITUDE_COVERAGE_INCOMPLETE" not in report.blockers
    assert (
        "FACTOR_NOTIONAL_TO_SIGNED_RISK_USD_MAPPING_NOT_IDENTIFIED"
        in report.blockers
    )
