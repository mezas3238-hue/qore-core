"""Synthetic trust-boundary tests for source-first QORE Research mission intake."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest
from dataclasses import replace
from typing import Any, cast

from qore.infrastructure.trader_lab import qore_research_zero_budget_intake_v1 as q


def _synthetic_cf11_closed_plan() -> dict[str, object]:
    """Artificial CF-11-shaped fixture. Never emitted as a real GitHub receipt."""
    h = "a" * 64
    return {
        "schema": "qore.research.cf11.science-only-closed-experiment.v1",
        "plan_code": "research.eia.futures-a-f1f2-closure",
        "question_code": "research.question.f1f2-directional-probability",
        "hypothesis_code": "research.hypothesis.backwardation-predicts-f1-up",
        "stage": "experiment",
        "evidence_status": "insufficient",
        "evidence_reasons": [
            "diagnostic.no-economic-fills", "hypothesis.no-support",
            "holdout.sealed", "market.contract-expiry-unknown",
            "market.first-published-at-unknown",
        ],
        "evidence_references": ["evidence:research-eia:science-sha256:" + h],
        "data_requirements": [
            "evidence:source-eia:wti-f1:" + "1" * 64,
            "evidence:source-eia:wti-f2:" + "2" * 64,
            "evidence:source-eia:ng-f1:" + "3" * 64,
            "evidence:source-eia:ng-f2:" + "4" * 64,
        ],
        "as_of": "2026-10-13T19:20:00+00:00",
        "receipt_sha256": h,
        "plan_fingerprint": "b" * 64,
        "scientific_decision": "NO_SUPPORT_UNDER_PREREG",
        "source_artifact_authenticated_upstream": True,
        "trader_lab_state": "draft",
        "trader_lab_stage_evidence_produced": False,
        "runnable_trader_created": False,
        "economic_backtest_performed": False,
        "demo_eligible": False,
        "risk_authority_issued": False,
        "cibo_authority_issued": False,
        "market_provenance_certified": False,
        "fresh_holdout_consumed": False,
        "merge_authorized": False,
    }


class TestQoreZeroBudgetResearchIntake(unittest.TestCase):
    def test_ledger_exact_two_entries(self) -> None:
        obj = q.build_source_first_queue(_synthetic_cf11_closed_plan()).to_json()
        self.assertEqual(obj["schema"], "qore.research.zero-budget-intake-ledger.v1")
        self.assertEqual(len(obj["entries"]), 2)
        self.assertEqual([x["status"] for x in obj["entries"]], [
            "closed_no_support", "source_blocked",
        ])
        self.assertEqual([x["next_action"] for x in obj["entries"]], [
            "stop_and_archive", "acquire_valid_source_within_zero_budget",
        ])
        self.assertTrue(obj["archive_scientific_outcomes_without_retesting"])
        self.assertFalse(obj["economic_replay_performed"])
        self.assertFalse(obj["production_execution_enabled"])

    def test_eia_not_promoted_despite_real_experiment_stage(self) -> None:
        entry = q.eia_closed_from_verified_cf11_json(_synthetic_cf11_closed_plan())
        self.assertEqual(entry.scientific_decision, "NO_SUPPORT_UNDER_PREREG")
        self.assertEqual(entry.trader_lab_state, "draft")
        self.assertFalse(entry.experiment_runnable)
        self.assertFalse(entry.can_open_fresh_holdout)

    def test_ledger_deterministic_sha_and_tamper_sensitive(self) -> None:
        entry = _synthetic_cf11_closed_plan()
        a = q.build_source_first_queue(entry).to_json()
        b = q.build_source_first_queue(entry).to_json()
        self.assertEqual(a["ledger_sha256"], b["ledger_sha256"])
        digest = a.pop("ledger_sha256")
        expected = hashlib.sha256(json.dumps(
            a, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest()
        self.assertEqual(digest, expected)

    def test_missing_receipt_or_wrong_plan_fingerprint_rejected(self) -> None:
        for case in ("receipt_sha256", "plan_fingerprint"):
            with self.subTest(case=case):
                item = _synthetic_cf11_closed_plan()
                item[case] = "x"
                with self.assertRaisesRegex(ValueError, "INVALID_SHA"):
                    q.eia_closed_from_verified_cf11_json(item)

    def test_forged_liveness_or_eligibility_rejected(self) -> None:
        for key in (
            "trader_lab_stage_evidence_produced", "runnable_trader_created",
            "economic_backtest_performed", "demo_eligible",
            "risk_authority_issued", "cibo_authority_issued",
            "market_provenance_certified", "fresh_holdout_consumed",
            "merge_authorized",
        ):
            with self.subTest(key=key):
                raw = _synthetic_cf11_closed_plan()
                raw[key] = True
                with self.assertRaisesRegex(ValueError, "CF11_FAKE_APPROVAL"):
                    q.eia_closed_from_verified_cf11_json(raw)

    def test_forged_economic_provenance_rejected(self) -> None:
        raw = _synthetic_cf11_closed_plan()
        raw["evidence_status"] = "sufficient"
        with self.assertRaisesRegex(ValueError, "CF11_RECEIPT_CONTRADICTION"):
            q.eia_closed_from_verified_cf11_json(raw)

    def test_a_reopened_hypothesis_rejected(self) -> None:
        raw = _synthetic_cf11_closed_plan()
        raw["scientific_decision"] = "CANDIDATE_DESERVES_HOLDOUT_PROPOSAL"
        with self.assertRaisesRegex(ValueError, "CF11_RECEIPT_CONTRADICTION"):
            q.eia_closed_from_verified_cf11_json(raw)

    def test_fake_free_data_availability_rejected(self) -> None:
        item = q.blocked_futures_a_m0()
        for attr in (
            "research_source_ohlcv_native_certified",
            "contract_expiry_asof_verified",
            "source_rights_verified",
            "experiment_runnable", "governance_approval_granted",
            "trader_certified", "can_open_fresh_holdout",
        ):
            with self.subTest(attribute=attr):
                with self.assertRaisesRegex(ValueError, "FALSE_SOURCE_OR_PROMOTION"):
                    cast(Any, replace)(item, **{attr: True})

    def test_budget_must_remain_zero(self) -> None:
        with self.assertRaisesRegex(ValueError, "MARKET_DATA_BUDGET_NOT_ZERO"):
            replace(q.blocked_futures_a_m0(), funding_ceiling_usd=1)

    def test_extra_arbitrary_family_rejected(self) -> None:
        raw = _synthetic_cf11_closed_plan()
        raw["simulated_pf"] = 2.4
        with self.assertRaisesRegex(ValueError, "CF11_PLAN_SCHEMA_CHANGED"):
            q.eia_closed_from_verified_cf11_json(raw)

    def test_cannot_borrow_closed_decision_with_blocked_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "NONCLOSED_CANNOT_BORROW_CF11_PLAN"):
            replace(q.blocked_futures_a_m0(), scientific_plan_fingerprint="f" * 64)

    def test_source_blocked_never_can_request_experiment(self) -> None:
        with self.assertRaisesRegex(ValueError, "INVALID_SOURCE_FIRST_TRANSITION"):
            replace(q.blocked_futures_a_m0(), next_action=q.NextResearchAction.WRITE_NEW_PREREG)

    def test_closed_result_never_can_request_retest(self) -> None:
        item = q.eia_closed_from_verified_cf11_json(_synthetic_cf11_closed_plan())
        with self.assertRaisesRegex(ValueError, "INVALID_SOURCE_FIRST_TRANSITION"):
            replace(item, next_action=q.NextResearchAction.WRITE_NEW_PREREG)

    def test_duplicate_root_evidence_requirement_rejected(self) -> None:
        raw = _synthetic_cf11_closed_plan()
        req = copy.deepcopy(raw["data_requirements"])
        assert isinstance(req, list)
        req[3] = req[2]
        raw["data_requirements"] = req
        with self.assertRaisesRegex(ValueError, "CF11_SCIENCE_OR_SOURCE_REFS_NOT_COMPLETE"):
            q.eia_closed_from_verified_cf11_json(raw)

    def test_wrong_mission_identity_rejected(self) -> None:
        raw = _synthetic_cf11_closed_plan()
        raw["plan_code"] = "research.fake-cl"
        with self.assertRaisesRegex(ValueError, "CF11_RECEIPT_CONTRADICTION"):
            q.eia_closed_from_verified_cf11_json(raw)


    def test_new_proposals_register_only_without_signal_or_certification(self) -> None:
        base = q.build_source_first_queue(_synthetic_cf11_closed_plan())
        expanded = q.register_unfrozen_proposal(
            base,
            code="research.proposal.new-mechanism-a",
            question_code="research.question.regime-conditional-seasonality",
            data_requirement_code="cme.native-delivery-contract-d1",
            research_root_count=6,
        )
        view = expanded.to_json()
        self.assertEqual(len(view["entries"]), 3)
        self.assertEqual(view["new_hypotheses_registered"], 1)
        proposed = next(x for x in view["entries"] if x["status"] == "proposal_only")
        self.assertEqual(proposed["next_action"], "write_new_prereg")
        self.assertEqual(proposed["scientific_decision"], "NOT_TESTED")
        self.assertFalse(proposed["experiment_runnable"])
        self.assertFalse(proposed["can_open_fresh_holdout"])
        self.assertFalse(proposed["trader_certified"])
        self.assertEqual(view["spent_usd"], 0)

    def test_duplicate_proposal_is_rejected(self) -> None:
        base = q.build_source_first_queue(_synthetic_cf11_closed_plan())
        expanded = q.register_unfrozen_proposal(
            base,
            code="research.proposal.new-mechanism-a",
            question_code="research.question.regime-conditional-seasonality",
            data_requirement_code="cme.native-delivery-contract-d1",
            research_root_count=6,
        )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PROPOSAL"):
            q.register_unfrozen_proposal(
                expanded,
                code="research.proposal.new-mechanism-a",
                question_code="research.question.regime-conditional-seasonality",
                data_requirement_code="cme.native-delivery-contract-d1",
                research_root_count=6,
            )

    def test_reopening_original_eia_as_new_proposal_rejected(self) -> None:
        base = q.build_source_first_queue(_synthetic_cf11_closed_plan())
        with self.assertRaisesRegex(ValueError, "NEW_PROPOSAL_REQUIRES_OWN_IDENTITY"):
            q.register_unfrozen_proposal(
                base,
                code="research.eia.futures-a-f1f2-closure",
                question_code="research.question.reopen-old-outcomes",
                data_requirement_code="eia.f1f2.reference-close-only",
                research_root_count=2,
            )

    def test_source_blocked_cannot_be_changed_to_favorable(self) -> None:
        base = q.build_source_first_queue(_synthetic_cf11_closed_plan())
        old = next(x for x in base.entries if x.code.endswith("native-6roots-d1"))
        with self.assertRaisesRegex(ValueError, "NEW_PROPOSAL_REQUIRES_OWN_IDENTITY"):
            replace(
                old,
                status=q.IntakeStatus.PROPOSAL_ONLY,
                next_action=q.NextResearchAction.WRITE_NEW_PREREG,
            )


    def test_frozen_eia_identity_cannot_be_rewritten(self) -> None:
        entry = q.eia_closed_from_verified_cf11_json(_synthetic_cf11_closed_plan())
        mutations = {
            "question_code": "research.question.different-claimed-question",
            "data_requirement_code": "cme.native-delivery-contract-d1",
            "research_root_count": 6,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "BASE_EIA_IDENTITY_MISMATCH"):
                    cast(Any, replace)(entry, **{key: value})

    def test_frozen_futures_identity_cannot_be_rewritten(self) -> None:
        entry = q.blocked_futures_a_m0()
        mutations = {
            "question_code": "research.question.different-claimed-question",
            "data_requirement_code": "unverified.contract-data",
            "research_root_count": 2,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "BASE_FUTURES_IDENTITY_MISMATCH"):
                    cast(Any, replace)(entry, **{key: value})

    def test_proposal_cannot_launder_closed_question_or_eia_data(self) -> None:
        base = q.build_source_first_queue(_synthetic_cf11_closed_plan())
        attacks = (
            ("research.question.f1f2-directional-probability", "other.native.source"),
            ("research.question.native-commodity-futures-edge", "other.native.source"),
            ("research.question.fresh-conditional-structure", "eia.f1f2.reference-close-only"),
        )
        for i, (question, requirement) in enumerate(attacks):
            with self.subTest(i=i):
                with self.assertRaisesRegex(
                    ValueError, "RECYCLED_QUESTION_OR_NONNATIVE_EIA_SOURCE"
                ):
                    q.register_unfrozen_proposal(
                        base,
                        code=f"research.proposal.launder-attempt-{i}",
                        question_code=question,
                        data_requirement_code=requirement,
                        research_root_count=2,
                    )

    def test_new_code_cannot_duplicate_an_existing_research_question(self) -> None:
        base = q.build_source_first_queue(_synthetic_cf11_closed_plan())
        first = q.register_unfrozen_proposal(
            base,
            code="research.proposal.fresh-idea-1",
            question_code="research.question.unique-new-effect",
            data_requirement_code="source.native-verified-required",
            research_root_count=6,
        )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_RESEARCH_QUESTION"):
            q.register_unfrozen_proposal(
                first,
                code="research.proposal.fresh-idea-2",
                question_code="research.question.unique-new-effect",
                data_requirement_code="source.native-verified-required",
                research_root_count=6,
            )

    def test_direct_api_enforces_twenty_proposal_cap(self) -> None:
        current = q.build_source_first_queue(_synthetic_cf11_closed_plan())
        for i in range(20):
            current = q.register_unfrozen_proposal(
                current,
                code=f"research.proposal.candidate-{i:02d}",
                question_code=f"research.question.candidate-{i:02d}",
                data_requirement_code="source.native-verified-required",
                research_root_count=6,
            )
        self.assertEqual(current.to_json()["new_hypotheses_registered"], 20)
        with self.assertRaisesRegex(ValueError, "QUEUE_EXCEEDS_PROPOSAL_LIMIT"):
            q.register_unfrozen_proposal(
                current,
                code="research.proposal.candidate-20",
                question_code="research.question.candidate-20",
                data_requirement_code="source.native-verified-required",
                research_root_count=6,
            )


if __name__ == "__main__":
    unittest.main()
