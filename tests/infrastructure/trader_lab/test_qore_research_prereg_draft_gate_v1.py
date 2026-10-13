"""Synthetic scientific prereg DRAFT, fail-closed chronology and intake tests."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest
from typing import Any, cast
from unittest.mock import patch

from qore.infrastructure.trader_lab import qore_research_prereg_draft_gate_v1 as p
from qore.infrastructure.trader_lab import qore_research_zero_budget_intake_v1 as q
from test_qore_research_zero_budget_intake_v1 import _synthetic_cf11_closed_plan


def _draft() -> dict[str, Any]:
    return {
        "proposal_code": "research.proposal.independent-native-mechanism",
        "question_code": "research.question.independent-native-mechanism",
        "hypothesis_code": "research.hypothesis.independent-native-mechanism",
        "version": 1,
        "hypothesis": "Predeclared contract-specific effect will exceed the control.",
        "market_mechanism": "An inventory perturbation changes term delivery scarcity.",
        "data_requirement_code": "cme.native-expiry-with-first-publication",
        "roots": ["CL", "NG"],
        "primary_outcome": "Difference in a prespecified future event rate.",
        "exposure": "Contract-specific daily settlement metadata observable at the cutoff.",
        "comparison": "Same contract family in the control state at the same horizon.",
        "direction": "greater",
        "sample_unit": "Contract-specific delivery-month event, one per calendar month.",
        "statistical_test": "fisher_exact",
        "alpha_ppm": 50000,
        "family_size": 2,
        "multiple_testing": "bonferroni",
        "minimum_effect_ppm": 100000,
        "minimum_group_events": 8,
        "train_start": "2012-01-01",
        "train_end": "2018-12-31",
        "diagnostic_start": "2019-01-01",
        "diagnostic_end": "2021-12-31",
        "holdout_start": "2022-01-01",
        "holdout_end": "2024-04-05",
        "data_license_verified": False,
        "first_publication_asof_verified": False,
        "source_snapshot_sha256": None,
        "inspected_outcomes": False,
        "fresh_holdout_consumed": False,
        "experiment_runnable": False,
        "budget_usd": 0,
    }


def _ledger(with_proposal: bool = True) -> dict[str, Any]:
    ledger = q.build_source_first_queue(_synthetic_cf11_closed_plan())
    if with_proposal:
        ledger = q.register_unfrozen_proposal(
            ledger,
            code="research.proposal.independent-native-mechanism",
            question_code="research.question.independent-native-mechanism",
            data_requirement_code="cme.native-expiry-with-first-publication",
            research_root_count=2,
        )
    return ledger.to_json()


def _manifest(drafts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema": p.MANIFEST_SCHEMA, "drafts": drafts}


class TestPreregDraftGate(unittest.TestCase):
    def test_empty_manifest_and_real_queue_shape(self) -> None:
        obj = p.build_draft_receipt(_manifest([]), _ledger(False))
        self.assertEqual(obj["draft_count"], 0)
        self.assertFalse(obj["scientific_prereg_frozen"])
        self.assertFalse(obj["can_execute"])
        self.assertFalse(obj["can_open_holdout"])
        self.assertFalse(obj["data_rights_certified"])
        self.assertFalse(obj["provenance_git_ancestor_attested"])
        self.assertFalse(obj["economic_backtest_performed"])
        self.assertEqual(obj["market_data_spend_usd"], 0)

    def test_independent_draft_is_deterministic_but_not_frozen(self) -> None:
        a = p.build_draft_receipt(_manifest([_draft()]), _ledger())
        b = p.build_draft_receipt(_manifest([_draft()]), _ledger())
        self.assertEqual(a, b)
        self.assertEqual(a["draft_count"], 1)
        self.assertEqual(len(a["drafts"][0]["draft_sha256"]), 64)
        self.assertFalse(a["scientific_prereg_frozen"])
        self.assertFalse(a["trader_lab_eligible"])
        self.assertFalse(a["can_execute"])

    def test_requires_exact_complete_prereg_fields(self) -> None:
        for change in ("missing", "extra"):
            with self.subTest(change=change):
                spec = _draft()
                if change == "missing":
                    spec.pop("primary_outcome")
                else:
                    spec["observed_win_rate"] = 99
                with self.assertRaisesRegex(ValueError, "PREREG_DRAFT_FIELDS_MISMATCH"):
                    p.build_draft_receipt(_manifest([spec]), _ledger())

    def test_no_prereg_for_unregistered_proposal(self) -> None:
        with self.assertRaisesRegex(ValueError, "ONE_TO_ONE"):
            p.build_draft_receipt(_manifest([_draft()]), _ledger(False))

    def test_registered_proposal_requires_one_matching_draft(self) -> None:
        with self.assertRaisesRegex(ValueError, "ONE_TO_ONE"):
            p.build_draft_receipt(_manifest([]), _ledger())

    def test_false_source_rights_or_experiment_claims_refused(self) -> None:
        for field, value in (
            ("data_license_verified", True),
            ("first_publication_asof_verified", True),
            ("source_snapshot_sha256", "0" * 64),
            ("inspected_outcomes", True),
            ("fresh_holdout_consumed", True),
            ("experiment_runnable", True),
            ("budget_usd", 1),
        ):
            with self.subTest(field=field):
                spec = _draft()
                spec[field] = value
                with self.assertRaisesRegex(ValueError, "PREREG_"):
                    p.build_draft_receipt(_manifest([spec]), _ledger())

    def test_reopen_original_eia_hypothesis_refused(self) -> None:
        spec = _draft()
        spec["hypothesis_code"] = "research.hypothesis.backwardation-predicts-f1-up"
        with self.assertRaisesRegex(ValueError, "ARCHIVED_HYPOTHESIS_REUSE"):
            p.build_draft_receipt(_manifest([spec]), _ledger())

    def test_root_count_and_sorting_enforced(self) -> None:
        for roots in (["CL"], ["NG", "CL"], ["CL", "CL"], ["BTCUSD", "NG"]):
            with self.subTest(roots=roots):
                spec = _draft()
                spec["roots"] = roots
                with self.assertRaisesRegex(ValueError, "INVALID_NATIVE_ROOTS"):
                    p.build_draft_receipt(_manifest([spec]), _ledger())

    def test_version_and_threshold_precommit_fixed(self) -> None:
        for field, bad in (
            ("version", 2), ("alpha_ppm", 50001),
            ("family_size", 0), ("minimum_effect_ppm", -1),
            ("minimum_group_events", 4), ("alpha_ppm", 0),
            ("multiple_testing", "uncorrected"),
            ("statistical_test", "winner-pick"),
        ):
            with self.subTest(field=field):
                spec = _draft()
                spec[field] = bad
                with self.assertRaisesRegex(ValueError, "PREREG_"):
                    p.build_draft_receipt(_manifest([spec]), _ledger())

    def test_holdout_and_split_overlap_refused(self) -> None:
        for field, bad in (
            ("diagnostic_start", "2018-12-31"),
            ("holdout_start", "2021-12-31"),
            ("train_end", "2025-01-01"),
            ("holdout_end", "2021-01-01"),
            ("holdout_start", "2022-02-31"),
        ):
            with self.subTest(field=field):
                spec = _draft()
                spec[field] = bad
                with self.assertRaisesRegex(ValueError, "PREREG_"):
                    p.build_draft_receipt(_manifest([spec]), _ledger())

    def test_rewriting_registered_question_or_source_is_rejected(self) -> None:
        for field, bad in (
            ("question_code", "research.question.not-the-registered-question"),
            ("data_requirement_code", "eia.f1f2.reference-close-only"),
        ):
            with self.subTest(field=field):
                spec = _draft()
                spec[field] = bad
                with self.assertRaisesRegex(ValueError, "PROPOSAL_NOT_IN_SOURCE_FIRST_QUEUE"):
                    p.build_draft_receipt(_manifest([spec]), _ledger())

    def test_unverifiable_intake_digest_is_rejected(self) -> None:
        bad = _ledger()
        bad["entries"][0]["status"] = "open"
        with self.assertRaisesRegex(ValueError, "QUEUE_HASH_MISMATCH"):
            p.build_draft_receipt(_manifest([_draft()]), bad)

    def test_duplicate_hypothesis_codes_and_prereg_candidates_are_rejected(self) -> None:
        led = q.build_source_first_queue(_synthetic_cf11_closed_plan())
        for i in (1, 2):
            led = q.register_unfrozen_proposal(
                led,
                code=f"research.proposal.new-{i}",
                question_code=f"research.question.new-{i}",
                data_requirement_code="cme.native-expiry-with-first-publication",
                research_root_count=2,
            )
        a, b = copy.deepcopy(_draft()), copy.deepcopy(_draft())
        a["proposal_code"], a["question_code"] = (
            "research.proposal.new-1", "research.question.new-1",
        )
        b["proposal_code"], b["question_code"] = (
            "research.proposal.new-2", "research.question.new-2",
        )
        with self.assertRaisesRegex(ValueError, "DUPLICATED_OR_UNSORTED_DRAFTS"):
            p.build_draft_receipt(_manifest([a, b]), led.to_json())

    def test_git_chronology_rejects_bad_refs(self) -> None:
        for before, after in (
            ("a" * 40, "a" * 40),
            ("NOT_SHA", "b" * 40),
        ):
            with self.subTest(before=before):
                with self.assertRaisesRegex(ValueError, "INVALID_OR_EQUAL_GIT_COMMITS"):
                    p.verify_prereg_before_outcome_git(
                        before, after, prereg_path="docs/research/prereg.json",
                        draft_sha256="1" * 64, proposal_code=_draft()["proposal_code"],
                    )

    def test_git_chronology_rejects_bad_witness_and_changed_draft(self) -> None:
        spec = _draft()
        digest = hashlib.sha256(json.dumps(
            spec, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest()
        frozen = json.dumps(_manifest([spec])).encode()
        fake_ok = subprocess_result(0, frozen)
        fake_fail = subprocess_result(1, b"")
        with patch.object(p.subprocess, "run", side_effect=[fake_fail, fake_ok]):
            with self.assertRaisesRegex(ValueError, "GIT_ANCESTRY_OR_SOURCE_NOT_VERIFIED"):
                p.verify_prereg_before_outcome_git(
                    "a" * 40, "b" * 40, prereg_path="docs/research/prereg.json",
                    draft_sha256=digest, proposal_code=spec["proposal_code"],
                )
        with patch.object(p.subprocess, "run", side_effect=[fake_ok, fake_ok]):
            with self.assertRaisesRegex(ValueError, "HISTORICAL_DRAFT_WAS_CHANGED"):
                p.verify_prereg_before_outcome_git(
                    "a" * 40, "b" * 40, prereg_path="docs/research/prereg.json",
                    draft_sha256="0" * 64, proposal_code=spec["proposal_code"],
                )

    def test_git_ancestry_helper_is_read_only_and_not_authority(self) -> None:
        spec = _draft()
        digest = hashlib.sha256(json.dumps(
            spec, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest()
        historical = json.dumps(_manifest([spec])).encode()
        with patch.object(
            p.subprocess, "run",
            side_effect=[subprocess_result(0, b""), subprocess_result(0, historical)],
        ) as patched:
            self.assertTrue(p.verify_prereg_before_outcome_git(
                "a" * 40, "b" * 40, prereg_path="docs/research/prereg.json",
                draft_sha256=digest, proposal_code=spec["proposal_code"],
            ))
        self.assertEqual(patched.call_count, 2)
        self.assertFalse(p.build_draft_receipt(
            _manifest([spec]), _ledger(),
        )["scientific_prereg_frozen"])


def subprocess_result(returncode: int, stdout: bytes) -> Any:
    return cast(Any, type("Result", (), {"returncode": returncode, "stdout": stdout})())


if __name__ == "__main__":
    unittest.main()
