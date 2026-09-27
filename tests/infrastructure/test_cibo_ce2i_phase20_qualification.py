import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationRow,
    Phase20QualificationStatus,
    run_phase20d_v2_qualification,
)

START = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
LINEAGES = (
    TraderLineage.VT31_NAS100.value,
    TraderLineage.R43_GBPUSD.value,
    TraderLineage.R34_XAUUSD.value,
    TraderLineage.R38_EURUSD.value,
    TraderLineage.R38_GBPJPY.value,
    TraderLineage.R42_AUDJPY.value,
    TraderLineage.VT08_FOREX.value,
)


def _sha(index: int) -> str:
    return f"sha256:{index + 1:064x}"


def _candidate(
    *,
    signal: str,
    trader: str,
) -> dict[str, object]:
    return {
        "candidate": {
            "signal_fingerprint": signal,
            "trader_id": trader,
            "stop_risk_usd": "10",
            "margin_usd": "10",
            "concentration_group": "ALL",
            "concentration_risk_usd": "10",
            "expectation": {
                "expected_capital_minutes": "10",
            },
        },
        "provider_observation": {
            "bid": "100",
            "ask": "100",
            "tick_size": "0.1",
            "tick_value": "1",
            "minimum_volume": "1",
            "volume_step": "1",
            "commission_per_volume_usd": "0",
            "slippage_reserve_per_volume_usd": "0",
        },
        "opportunity": {
            "minimum_execution_steps": 1,
        },
    }


def _books(
    *,
    missing_baseline_outcome: bool = False,
    negative_fold: bool = False,
) -> tuple[
    VersionedPhase20ForwardEvidenceBook,
    VersionedPhase20ForwardPolicyBook,
]:
    decisions: list[Phase20ForwardDecisionSeal] = []
    policies: list[Phase20ForwardPolicyDecisionSeal] = []
    outcomes: list[Phase20ForwardOutcomeSeal] = []

    for decision_index in range(80):
        decision_at = START + timedelta(
            days=decision_index % 28,
            minutes=decision_index,
        )
        evidence_sha = _sha(decision_index)
        signals = tuple(
            f"signal-{decision_index}-{candidate_index}"
            for candidate_index in range(3)
        )
        traders = tuple(
            LINEAGES[
                (decision_index * 3 + candidate_index) % len(LINEAGES)
            ]
            for candidate_index in range(3)
        )
        candidates = [
            _candidate(signal=signal, trader=trader)
            for signal, trader in zip(signals, traders, strict=True)
        ]
        population_slots = [
            {
                "slot_id": f"{trader}|{signal}",
                "trader_id": trader,
                "qore_symbol": f"SYMBOL-{candidate_index}",
                "observed_at": (
                    decision_at - timedelta(milliseconds=1)
                ).isoformat(),
                "disposition": "CANDIDATE",
                "reason": "VALID_TRADER_OPPORTUNITY",
                "signal_fingerprint": signal,
            }
            for candidate_index, (signal, trader) in enumerate(
                zip(signals, traders, strict=True)
            )
        ]
        payload = {
            "evidence_kind": "FORWARD_OBSERVED",
            "hard_risk_headroom_usd": "30",
            "margin_headroom_usd": "30",
            "concentration_limit_by_group": [["ALL", "30"]],
            "population_slots": population_slots,
            "candidates": candidates,
        }
        decisions.append(
            Phase20ForwardDecisionSeal(
                evidence_id=f"evidence-{decision_index}",
                decision_epoch_id=f"epoch-{decision_index}",
                evidence_sha256=evidence_sha,
                decision_at=decision_at,
                candidate_id="CIBO_PHASE20H20I_FORWARD_CANDIDATE_V2",
                code_sha="7acce68c6ece61fae1adacf3f8e60815839b6f6a",
                parameter_sha256=_sha(1000),
                signal_fingerprints=signals,
                canonical_payload_json=json.dumps(
                    payload,
                    sort_keys=True,
                ),
            )
        )
        policy_payload = {
            "allocator_decision": {
                "deployable_stop_risk_usd": "20",
                "deployable_margin_usd": "20",
                "allocation": {
                    "used_stop_risk_usd": "10",
                    "used_margin_usd": "10",
                    "concentration_used_by_group": [["ALL", "10"]],
                    "rows": [
                        {
                            "signal_fingerprint": signals[0],
                            "selected": True,
                            "reason": "selected by positive net value per risk-minute",
                        },
                        {
                            "signal_fingerprint": signals[1],
                            "selected": False,
                            "reason": "non-positive adjusted expected net value",
                        },
                        {
                            "signal_fingerprint": signals[2],
                            "selected": False,
                            "reason": "non-positive adjusted expected net value",
                        },
                    ],
                },
            },
            "mpc_plan": {
                "considered_option_ids": [],
                "horizon_fully_coverable": True,
            },
        }
        policies.append(
            Phase20ForwardPolicyDecisionSeal(
                evidence_sha256=evidence_sha,
                policy_record_sha256=_sha(2000 + decision_index),
                allocator_disposition="ALLOCATE",
                selected_signal_fingerprints=(signals[0],),
                canonical_record_json=json.dumps(
                    policy_payload,
                    sort_keys=True,
                ),
            )
        )
        for candidate_index, signal in enumerate(signals):
            if (
                missing_baseline_outcome
                and decision_index == 0
                and candidate_index == 1
            ):
                continue
            if candidate_index == 0:
                outcome_r = Decimal("2")
                if negative_fold and decision_index % 28 < 7:
                    outcome_r = Decimal("-1")
            else:
                outcome_r = Decimal("-1")
            outcomes.append(
                Phase20ForwardOutcomeSeal(
                    evidence_id=f"outcome-{decision_index}-{candidate_index}",
                    decision_evidence_sha256=evidence_sha,
                    signal_fingerprint=signal,
                    position_id=decision_index * 10 + candidate_index + 1,
                    execution_risk_evidence_id=(
                        f"risk-{decision_index}-{candidate_index}"
                    ),
                    settlement_deal_ids=(
                        decision_index * 10 + candidate_index + 10001,
                    ),
                    fill_evidence_refs=(
                        f"fill-{decision_index}-{candidate_index}",
                    ),
                    observed_at=decision_at + timedelta(hours=1 + candidate_index),
                    realized_net_pnl_usd=outcome_r * Decimal("10"),
                    executed_initial_stop_risk_usd=Decimal("10"),
                    realized_structural_outcome_r=outcome_r,
                )
            )

    return (
        VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=tuple(decisions),
            outcomes=tuple(outcomes),
        ),
        VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=tuple(policies),
        ),
    )


def test_phase20d_fixed_runner_can_pass_without_refit() -> None:
    evidence, policy = _books()

    report = run_phase20d_v2_qualification(
        evidence_book=evidence,
        policy_book=policy,
    )

    assert report.status is Phase20QualificationStatus.PASS
    assert report.failures == ()
    assert len(report.folds) == 4
    assert all(item.policy_net_delta_usd > 0 for item in report.folds)
    assert report.policy_net_delta_usd > report.baseline_net_delta_usd
    assert (
        report.policy_settlement_cash_drawdown_usd
        <= report.baseline_settlement_cash_drawdown_usd
    )
    assert (
        report.policy_capital_productivity
        > report.baseline_capital_productivity
    )
    assert report.policy_selected_outcome_coverage == Decimal("1")
    assert report.baseline_selected_outcome_coverage == Decimal("1")
    assert report.candidate_outcome_coverage == Decimal("1")


def test_phase20d_runner_fails_if_baseline_outcome_is_missing() -> None:
    evidence, policy = _books(missing_baseline_outcome=True)

    report = run_phase20d_v2_qualification(
        evidence_book=evidence,
        policy_book=policy,
    )

    assert report.status is Phase20QualificationStatus.NOT_READY
    assert (
        "BASELINE_SELECTED_OUTCOME_COVERAGE_COMPLETE"
        in report.failures
    )
    assert report.policy_selected_outcome_coverage == Decimal("1")
    assert report.candidate_outcome_coverage > Decimal("0.95")


def test_phase20d_runner_fails_if_any_temporal_fold_is_not_positive() -> None:
    evidence, policy = _books(negative_fold=True)

    report = run_phase20d_v2_qualification(
        evidence_book=evidence,
        policy_book=policy,
    )

    assert report.status is Phase20QualificationStatus.FAIL
    assert "ALL_TEMPORAL_FOLDS_POLICY_DELTA_POSITIVE" in report.failures



def test_phase20d_row_uses_realized_net_pnl_without_double_charging_proxy() -> None:
    row = Phase20QualificationRow(
        decision_epoch_id="epoch-exact-economics",
        decision_evidence_sha256=_sha(9999),
        decision_at=START,
        signal_fingerprint="signal-exact-economics",
        trader_id=TraderLineage.VT31_NAS100.value,
        stop_risk_usd=Decimal("10"),
        margin_usd=Decimal("8"),
        concentration_group="ALL",
        concentration_risk_usd=Decimal("10"),
        expected_capital_minutes=Decimal("6"),
        provider_cost_proxy_usd=Decimal("3"),
        policy_selected=True,
        baseline_selected=True,
        realized_net_pnl_usd=Decimal("18"),
        executed_initial_stop_risk_usd=Decimal("12"),
        realized_structural_outcome_r=Decimal("1.5"),
        outcome_observed_at=START + timedelta(hours=1),
    )

    # The durable settlement already carries net realized economics.  Neither
    # candidate stop risk (10) nor the ex-ante provider proxy (3) may rewrite
    # the observed $18 result after settlement.
    assert row.policy_net_delta_usd == Decimal("18")
    assert row.baseline_net_delta_usd == Decimal("18")
    assert row.policy_net_delta_usd != (
        row.realized_structural_outcome_r * row.stop_risk_usd
        - row.provider_cost_proxy_usd
    )
