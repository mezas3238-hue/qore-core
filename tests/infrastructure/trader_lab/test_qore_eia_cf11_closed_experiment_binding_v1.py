"""Actual CF-11 CiboResearchPlan scientific-closure integration tests, no promotions."""
from __future__ import annotations

import copy
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast

from test_qore_eia_research_science_handoff_v1 import fixture_from_original_actions_log

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalBlockedError,
)
from qore.infrastructure.cibo.research_director import (
    CiboResearchDirector,
    CiboResearchStage,
)
from qore.infrastructure.trader_lab import qore_eia_cf11_closed_experiment_binding_v1 as cf11
from qore.infrastructure.trader_lab import qore_eia_research_science_handoff_v1 as source
from qore.kernel.result import Failure

_AT = datetime(2026, 10, 13, 19, 30, tzinfo=UTC)


def fixture() -> tuple[dict[str, object], source.ScientificHandoffReceipt]:
    raw = cast(dict[str, object], fixture_from_original_actions_log())
    return raw, source.build_handoff_receipt(raw)


class TestGenuineCF11ClosedExperimentBinding(unittest.TestCase):
    def test_real_cf11_plan_is_insufficient_science_not_fake_trader(self) -> None:
        raw, receipt = fixture()
        result = cf11.bind_closed_eia_to_cf11(
            raw, receipt, verified_source=True, as_of=_AT
        )
        plan = result.plan
        self.assertEqual(plan.stage, CiboResearchStage.EXPERIMENT)
        self.assertEqual(plan.evidence.status, CiboEvidenceStatus.INSUFFICIENT)
        self.assertEqual(len(plan.data_requirements), 4)
        self.assertIn(receipt.scientific_receipt_sha256, plan.evidence.evidence_refs[0].value)
        self.assertIn("hypothesis.no-support", plan.evidence.reasons)
        self.assertFalse(result.demo_eligible)
        self.assertFalse(result.economic_backtest_performed)
        self.assertEqual(result.to_json()["trader_lab_state"], "draft")
        self.assertFalse(result.to_json()["trader_lab_stage_evidence_produced"])

    def test_director_cannot_advance_to_trader_lab_without_authority(self) -> None:
        raw, receipt = fixture()
        close = cf11.bind_closed_eia_to_cf11(
            raw, receipt, verified_source=True, as_of=_AT
        )
        outcome = CiboResearchDirector().advance(
            close.plan,
            to_stage=CiboResearchStage.TRADER_LAB,
            evidence=close.plan.evidence,
            updated_at=_AT,
        )
        self.assertIsInstance(outcome, Failure)
        if isinstance(outcome, Failure):
            self.assertIsInstance(outcome.error, CiboFunctionalBlockedError)

    def test_director_cannot_advance_to_demo_without_authority(self) -> None:
        raw, receipt = fixture()
        close = cf11.bind_closed_eia_to_cf11(
            raw, receipt, verified_source=True, as_of=_AT
        )
        outcome = CiboResearchDirector().advance(
            close.plan,
            to_stage=CiboResearchStage.DEMO,
            evidence=close.plan.evidence,
            updated_at=_AT,
        )
        from qore.kernel.result import Failure

        self.assertIsInstance(outcome, Failure)

    def test_unverified_artifact_blocked(self) -> None:
        raw, receipt = fixture()
        with self.assertRaisesRegex(ValueError, "MISSING_EXTERNAL_GITHUB_ATTESTATION"):
            cf11.bind_closed_eia_to_cf11(
                raw, receipt, verified_source=False, as_of=_AT
            )

    def test_nan_or_naive_clock_blocked(self) -> None:
        raw, receipt = fixture()
        with self.assertRaisesRegex(ValueError, "TIMESTAMP_MUST_BE_TIMEZONE_AWARE"):
            cf11.bind_closed_eia_to_cf11(
                raw, receipt, verified_source=True,
                as_of=datetime(2026, 10, 13),
            )

    def test_forged_upstream_receipt_cannot_self_certify(self) -> None:
        raw, receipt = fixture()
        forged = replace(receipt, qore_research_classification="DEMO_ELIGIBLE")
        with self.assertRaisesRegex(ValueError, "RESULT_OR_RECEIPT_MISMATCH"):
            cf11.bind_closed_eia_to_cf11(
                raw, forged, verified_source=True, as_of=_AT
            )

    def test_forged_economic_fills_rejected(self) -> None:
        raw, receipt = fixture()
        forged = replace(receipt, has_economic_returns_or_fills=True)
        with self.assertRaisesRegex(ValueError, "RESULT_OR_RECEIPT_MISMATCH"):
            cf11.bind_closed_eia_to_cf11(
                raw, forged, verified_source=True, as_of=_AT
            )

    def test_root_p_value_tampered_rejected(self) -> None:
        raw, receipt = fixture()
        mutable = copy.deepcopy(raw)
        roots = cast(list[dict[str, object]], mutable["results"])
        ng = roots[1]
        diag = cast(dict[str, object], ng["diag"])
        diag["one_sided_fisher_p"] = 0.00001
        with self.assertRaisesRegex(ValueError, "TAMPERED_FISHER_P"):
            cf11.bind_closed_eia_to_cf11(
                mutable, receipt, verified_source=True, as_of=_AT
            )

    def test_source_hash_tampering_rejected(self) -> None:
        raw, receipt = fixture()
        mutable = copy.deepcopy(raw)
        hashes = cast(dict[str, str], mutable["source_SHA256"])
        hashes["NG_F1"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_SOURCE_DATA_HASH"):
            cf11.bind_closed_eia_to_cf11(
                mutable, receipt, verified_source=True, as_of=_AT
            )

    def test_open_fresh_holdout_rejected(self) -> None:
        raw, receipt = fixture()
        mutable = copy.deepcopy(raw)
        mutable["holdout_2022_2024"] = "OPEN"
        with self.assertRaisesRegex(ValueError, "CONTRADICTS_FROZEN_PROTOCOL"):
            cf11.bind_closed_eia_to_cf11(
                mutable, receipt, verified_source=True, as_of=_AT
            )

    def test_determinism_same_as_of(self) -> None:
        raw, receipt = fixture()
        one = cf11.bind_closed_eia_to_cf11(raw, receipt, verified_source=True, as_of=_AT)
        two = cf11.bind_closed_eia_to_cf11(raw, receipt, verified_source=True, as_of=_AT)
        self.assertEqual(one.plan.logical_values(), two.plan.logical_values())
        self.assertEqual(one.plan_fingerprint, two.plan_fingerprint)

    def test_plan_fingerprint_changes_with_time(self) -> None:
        raw, receipt = fixture()
        one = cf11.bind_closed_eia_to_cf11(
            raw, receipt, verified_source=True, as_of=_AT
        )
        two = cf11.bind_closed_eia_to_cf11(
            raw, receipt, verified_source=True,
            as_of=_AT + timedelta(seconds=1),
        )
        self.assertNotEqual(one.plan_fingerprint, two.plan_fingerprint)

    def test_cannot_launder_wrong_result_for_wti(self) -> None:
        raw, receipt = fixture()
        mutable = copy.deepcopy(raw)
        roots = cast(list[dict[str, object]], mutable["results"])
        roots[0]["decision"] = "CANDIDATE_DESERVES_HOLDOUT_PROPOSAL"
        with self.assertRaisesRegex(ValueError, "TAMPERED_ROOT_DECISION"):
            cf11.bind_closed_eia_to_cf11(
                mutable, receipt, verified_source=True, as_of=_AT
            )


if __name__ == "__main__":
    unittest.main()
