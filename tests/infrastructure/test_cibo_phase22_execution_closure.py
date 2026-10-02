from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase22_qualification import (
    Phase22HoldoutQualificationStatus,
)
from qore.infrastructure.cibo_phase22_execution_closure import (
    close_phase22_one_shot_execution,
)
from qore.infrastructure.cibo_phase22_execution_inputs import (
    load_phase22_sealed_fresh_batch,
    load_phase22_sealed_provider_numeric,
)
from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
    Phase22FreshTraderEvidence,
    build_phase22_fresh_opportunity_batch,
)
from qore.infrastructure.cibo_phase22_one_shot_batch import (
    Phase22OneShotClaimReceipt,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderAccountLineageReceipt,
    Phase22ProviderNumericExecutionSpec,
)
from qore.infrastructure.cibo_phase22_store_contract import (
    PHASE22_STORE_IDENTITIES,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _fresh(trader_id: str, symbol: str, index: int) -> Phase22FreshOpportunity:
    signal_at = datetime(2015, 10, 25, 12, tzinfo=UTC) + timedelta(
        days=index * 5
    )
    return Phase22FreshOpportunity(
        trader_id=TraderLineage(trader_id),
        qore_symbol=symbol,
        signal_fingerprint=_sha(f"closure-signal-{trader_id}"),
        signal_at=signal_at,
        entry_at=signal_at + timedelta(minutes=5),
        exit_at=signal_at + timedelta(hours=1),
        side="long",
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        exit_reason="target",
        gross_structural_outcome_r=Decimal("2"),
        methodology_sha256=_sha(f"method-{trader_id}"),
        source_evidence_ids=(_sha(f"source-{trader_id}"),),
    )


def _fresh_payload() -> dict[str, object]:
    symbols = {
        "VT08_FOREX": "GBPUSD",
        "R34_XAUUSD": "XAUUSD",
        "R38_EURUSD": "EURUSD",
        "R43_GBPUSD": "GBPUSD",
        "R38_GBPJPY": "GBPJPY",
        "R42_AUDJPY": "AUDJPY",
        "VT31_NAS100": "NAS100",
    }
    traders = tuple(
        Phase22FreshTraderEvidence(
            trader_id=trader_id,
            source_artifact_sha256=_sha(f"lane-{trader_id}"),
            opportunities=(_fresh(trader_id, symbols[trader_id], index),),
            fresh_outcomes_executed=True,
            methodology_changed=False,
            legacy_trader_sizing_used_for_cibo=False,
        )
        for index, trader_id in enumerate(CANONICAL_PHASE22_TRADER_IDS)
    )
    batch = build_phase22_fresh_opportunity_batch(traders)
    return {
        "schema": "qore.cibo.phase22.fresh-batch-assembly.v1",
        "candidate_id": batch.candidate_id,
        "batch_sha256": batch.fingerprint(),
        "traders": [
            {
                "trader_id": item.trader_id,
                "lane_artifact_sha256": item.source_artifact_sha256,
                "opportunity_count": len(item.opportunities),
                "evidence_sha256": item.fingerprint(),
            }
            for item in batch.traders
        ],
        "opportunities": [item.payload() for item in batch.opportunities],
        "legacy_trader_sizing_used_for_cibo": False,
        "productive_authority": False,
    }


def _provider_payload() -> dict[str, object]:
    lineage = Phase22ProviderAccountLineageReceipt(
        provider_key="ctrader-demo",
        legacy_account_fingerprint_sha256=(
            "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
        ),
        phase22_account_fingerprint_sha256=(
            "17585ecd6f116a92d19919e46948f06c027d0cbf9f1cb8d97802f20055bad17b"
        ),
        same_account_proven=True,
    )
    specs = []
    for symbol in ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD"):
        specs.append(
            Phase22ProviderNumericExecutionSpec(
                qore_symbol=symbol,
                provider_symbol=symbol,
                observed_at=datetime(2026, 10, 1, 20, tzinfo=UTC),
                bid=Decimal("100"),
                ask=Decimal("100.01"),
                display_digits=2,
                contract_size_per_volume=Decimal("1"),
                minimum_volume=Decimal("0.01"),
                maximum_volume=Decimal("100"),
                volume_step=Decimal("0.01"),
                margin_per_volume_usd=Decimal("10"),
                commission_per_volume_usd=Decimal("0"),
                worst_adverse_slippage_bps=Decimal("0"),
                quote_to_usd=Decimal("1"),
                usd_value_per_price_unit_per_volume=Decimal("1"),
                derived_price_quantum=Decimal("0.01"),
                derived_value_per_quantum_usd=Decimal("0.01"),
                source_provider_terms_artifact_sha256=_sha("terms"),
                source_empirical_execution_artifact_sha256=_sha("empirical"),
            )
        )
    return {
        "schema": "qore.cibo.phase22.provider-numeric-execution-freeze.v1",
        "status": "READY",
        "account_lineage": lineage.payload(),
        "account_lineage_sha256": lineage.fingerprint(),
        "specs": [item.payload() for item in specs],
        "holdout_market_data_read": False,
        "holdout_outcomes_used": False,
        "broker_mutation_performed": False,
        "historical_provider_economics_claimed": False,
        "productive_authority": False,
    }


def _corpora() -> tuple[Evidence, ...]:
    symbols = ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "XAUUSD")
    start = datetime(2015, 10, 18, tzinfo=UTC)
    result = []
    for symbol_index, symbol in enumerate(symbols):
        base = Decimal("100") + Decimal(symbol_index)
        bars = tuple(
            Bar(
                opened_at=start + timedelta(minutes=5 * index),
                closed_at=start + timedelta(minutes=5 * (index + 1)),
                open=base + Decimal(index) / Decimal("10000"),
                high=base + Decimal(index) / Decimal("10000") + Decimal("0.1"),
                low=base + Decimal(index) / Decimal("10000") - Decimal("0.1"),
                close=base + Decimal(index) / Decimal("10000") + Decimal("0.01"),
            )
            for index in range(3000)
        )
        result.append(Evidence(symbol=symbol, digits=2, bars=bars))
    return tuple(result)


def _claim(store_root: Path) -> Phase22OneShotClaimReceipt:
    manifest = build_phase22_execution_manifest()
    return Phase22OneShotClaimReceipt(
        candidate_id=manifest.candidate_id,
        execution_manifest_sha256=manifest.fingerprint(),
        provider_execution_calibration_sha256=(
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ),
        runner_git_sha="a" * 40,
        run_id=123,
        run_attempt=1,
        started_at=datetime(2026, 10, 2, 7, tzinfo=UTC),
        trader_ids=CANONICAL_PHASE22_TRADER_IDS,
        store_paths=tuple(
            item.relative_path for item in PHASE22_STORE_IDENTITIES
        ),
    )


def test_closure_burns_one_shot_even_when_qualification_not_ready(
    tmp_path: Path,
) -> None:
    fresh = load_phase22_sealed_fresh_batch(_fresh_payload())
    provider = load_phase22_sealed_provider_numeric(_provider_payload())
    store_root = tmp_path / "phase22-v2-stores"
    claim = _claim(store_root)

    closure = close_phase22_one_shot_execution(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
        corpora=_corpora(),
        store_root=store_root,
        replay_started_at=datetime(2026, 10, 2, 7, tzinfo=UTC),
        completed_at=datetime(2026, 10, 2, 7, 5, tzinfo=UTC),
        claim=claim,
        consumption_claim=claim.consumption_claim(),
    )

    assert closure.qualification.status in {
        Phase22HoldoutQualificationStatus.NOT_READY,
        Phase22HoldoutQualificationStatus.FAIL,
        Phase22HoldoutQualificationStatus.INVALID,
        Phase22HoldoutQualificationStatus.PASS,
    }
    assert closure.consumed.claim_committed is True
    assert closure.consumed.outcomes_emitted is True
    assert closure.second_fresh_execution_authorized is False
    assert closure.completion.fresh_outcomes_emitted is True
    assert closure.qualification_recorded_without_override is True
    assert all(path.is_file() for path in (
        store_root / "holdout-forward-evidence.json",
        store_root / "holdout-policy.json",
        store_root / "executed-risk.json",
        store_root / "cma-settlement.json",
        store_root / "t20-release.json",
    ))


def test_closure_store_set_is_create_once(tmp_path: Path) -> None:
    fresh = load_phase22_sealed_fresh_batch(_fresh_payload())
    provider = load_phase22_sealed_provider_numeric(_provider_payload())
    store_root = tmp_path / "phase22-v2-stores"
    claim = _claim(store_root)
    kwargs = dict(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
        corpora=_corpora(),
        store_root=store_root,
        replay_started_at=datetime(2026, 10, 2, 7, tzinfo=UTC),
        completed_at=datetime(2026, 10, 2, 7, 5, tzinfo=UTC),
        claim=claim,
        consumption_claim=claim.consumption_claim(),
    )
    close_phase22_one_shot_execution(**kwargs)

    try:
        close_phase22_one_shot_execution(**kwargs)
    except Exception as error:
        assert "create-once" in str(error) or "pristine" in str(error)
    else:
        raise AssertionError("second Phase22 store persistence must fail closed")
