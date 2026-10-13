"""Synthetic adversarial witnesses for new-QORE-Research prereg provenance."""
from __future__ import annotations

import copy
import unittest

from qore.infrastructure.trader_lab import qore_research_prereg_source_gate_v1 as gate

GIT = "a" * 40
PRIOR = "research.hypothesis.backwardation-predicts-f1-up"


def proposals() -> dict[str, object]:
    return {
        "schema": "qore.research.zero-budget.proposals.v1",
        "proposals": [{
            "code": "research.proposal.inventory-seasonal-v1",
            "question_code": "research.question.inventory-impact",
            "data_requirement_code": "research.source.independent-official-inventory",
            "research_root_count": 2,
        }],
    }


def prereg() -> dict[str, object]:
    return {
        "schema": "qore.research.prereg.freeze.v1",
        "preregistrations": [{
            "proposal_code": "research.proposal.inventory-seasonal-v1",
            "hypothesis_code": "research.hypothesis.inventory-release-direction",
            "family_code": "research.family.energy-inventory-seasonal-v1",
            "data_requirement_code": "research.source.independent-official-inventory",
            "research_root_count": 2,
            "signal_definition": "Use only lagged agency inventories public before fixed timestamp.",
            "outcome_definition": "Five later common-day reference observations with no rollover.",
            "sampling_rule": "Exactly one event per calendar month and each energy source.",
            "roll_policy": "Skip every window crossing known physical expiration date.",
            "publication_asof_rule": "Require first public release time for every agency update.",
            "source_identity_and_rights_rule": "Exact official source IDs with reuse permission.",
            "execution_cost_rule": "Broker BID ASK commissions are not currently available.",
            "negative_price_policy": "Allow negative CL levels without applying logarithms.",
            "lag_observations": 2,
            "horizon_observations": 5,
            "dev_start": "2012-01-01",
            "dev_end": "2016-12-31",
            "diag_start": "2017-01-01",
            "diag_end": "2021-12-31",
            "holdout_start": "2022-01-01",
            "holdout_end": "2024-09-16",
            "test_method": "fisher_exact",
            "alternative": "greater",
            "family_size": 2,
            "family_alpha": 0.05,
            "minimum_effect": 0.1,
            "hypotheses_previously_tested": [PRIOR],
            "source_authority_verified": False,
            "prices_examined_for_this_hypothesis": False,
            "economic_test_authorized": False,
            "budget_usd": 0,
        }],
    }


class TestQoreResearchPreregFreeze(unittest.TestCase):
    def test_zero_hypotheses_reports_truthfully_and_is_not_an_experiment(self) -> None:
        data = gate.freeze_prereg_manifest(
            {"schema": "qore.research.prereg.freeze.v1", "preregistrations": []},
            {"schema": "qore.research.zero-budget.proposals.v1", "proposals": []},
            git_commit_sha=GIT,
        )
        self.assertEqual(data["frozen_count"], 0)
        self.assertFalse(data["economic_backtest_executed"])
        self.assertFalse(data["source_market_authority_obtained"])
        self.assertFalse(data["holdout_read"])
        self.assertEqual(data["data_spend_usd"], 0)

    def test_one_synthetic_prereg_freezes_method_but_is_not_runnable(self) -> None:
        result = gate.freeze_prereg_manifest(prereg(), proposals(), git_commit_sha=GIT)
        self.assertEqual(result["frozen_count"], 1)
        only = result["frozen_specs"][0]
        self.assertEqual(only["proposal_code"], "research.proposal.inventory-seasonal-v1")
        self.assertEqual(only["familywise_p_ceiling"], 0.025)
        self.assertEqual(only["next_action"], "SOURCE_AUTHORITY_REQUIRED")
        self.assertFalse(only["experiment_runnable"])
        self.assertFalse(only["economic_test_authorized"])
        self.assertFalse(only["holdout_opened"])
        self.assertEqual(only["trader_lab_state"], "draft")

    def test_same_input_deterministic_and_mutation_changes_fingerprint(self) -> None:
        a = gate.freeze_prereg_manifest(prereg(), proposals(), git_commit_sha=GIT)
        b = gate.freeze_prereg_manifest(prereg(), proposals(), git_commit_sha=GIT)
        self.assertEqual(a, b)
        changed = prereg()
        specs = changed["preregistrations"]
        assert isinstance(specs, list)
        specs[0]["signal_definition"] += " Another source version is required."
        other = gate.freeze_prereg_manifest(changed, proposals(), git_commit_sha=GIT)
        self.assertNotEqual(a["receipt_sha256"], other["receipt_sha256"])
        self.assertNotEqual(a["frozen_specs"][0]["spec_sha256"], other["frozen_specs"][0]["spec_sha256"])

    def test_no_result_payloads_or_secret_hypotheses(self) -> None:
        raw = prereg()
        raw["preregistrations"][0]["sharpe"] = 99.0
        with self.assertRaisesRegex(ValueError, "PREREG_FIELDS_OR_OUTCOMES_ATTACHED"):
            gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_missing_registered_identity_rejected(self) -> None:
        item = prereg()
        item["preregistrations"][0]["proposal_code"] = "research.proposal.unregistered-v1"
        with self.assertRaisesRegex(ValueError, "NO_MATCHING_PRIOR_PROPOSAL"):
            gate.freeze_prereg_manifest(item, proposals(), git_commit_sha=GIT)

    def test_forbidden_legacy_name_even_when_pretending_unstudied(self) -> None:
        raw = prereg()
        spec = raw["preregistrations"][0]
        spec["hypothesis_code"] = PRIOR
        with self.assertRaisesRegex(ValueError, "REUSING_TESTED_HYPOTHESIS"):
            gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_missing_full_spec_is_rejected(self) -> None:
        raw = prereg()
        del raw["preregistrations"][0]["publication_asof_rule"]
        with self.assertRaisesRegex(ValueError, "PREREG_FIELDS_OR_OUTCOMES_ATTACHED"):
            gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_historical_holdout_overlap_rejected(self) -> None:
        raw = prereg()
        raw["preregistrations"][0]["holdout_start"] = "2020-01-01"
        with self.assertRaisesRegex(ValueError, "WINDOWS_OVERLAP"):
            gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_wrong_calendar_day_rejected(self) -> None:
        raw = prereg()
        raw["preregistrations"][0]["diag_end"] = "2021-02-30"
        with self.assertRaisesRegex(ValueError, "INVALID_DATE"):
            gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_nonzero_budget_rejected(self) -> None:
        raw = prereg()
        raw["preregistrations"][0]["budget_usd"] = 1
        with self.assertRaisesRegex(ValueError, "NONZERO_MARKET_DATA_BUDGET"):
            gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_false_source_license_rejected(self) -> None:
        for key in (
            "source_authority_verified", "prices_examined_for_this_hypothesis",
            "economic_test_authorized",
        ):
            with self.subTest(key=key):
                raw = prereg()
                raw["preregistrations"][0][key] = True
                with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_PRE_RESULTS_ASSERTION"):
                    gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_unsupported_method_and_direction_rejected(self) -> None:
        for key, value in (("test_method", "best-of-100"),
                           ("alternative", "both_when_profitable")):
            with self.subTest(key=key):
                raw = prereg()
                raw["preregistrations"][0][key] = value
                with self.assertRaisesRegex(ValueError, "NOT_PREDECLARED"):
                    gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_frozen_source_cannot_change_relative_to_registry(self) -> None:
        raw = prereg()
        raw["preregistrations"][0]["data_requirement_code"] = "research.source.fake-data"
        with self.assertRaisesRegex(ValueError, "PROPOSAL_SOURCE_OR_UNIVERSE_CHANGED"):
            gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)

    def test_unfrozen_proposal_is_rejected_not_silently_dropped(self) -> None:
        with self.assertRaisesRegex(ValueError, "UNFROZEN_PROPOSAL_IN_REGISTER"):
            gate.freeze_prereg_manifest(
                {"schema": "qore.research.prereg.freeze.v1", "preregistrations": []},
                proposals(),
                git_commit_sha=GIT,
            )

    def test_duplicate_hypothesis_families_rejected(self) -> None:
        registry = proposals()
        registry["proposals"].append({
            "code": "research.proposal.other-inventory-v1",
            "question_code": "research.question.other-inventory-impact",
            "data_requirement_code": "research.source.independent-official-inventory",
            "research_root_count": 2,
        })
        m = prereg()
        same = copy.deepcopy(m["preregistrations"][0])
        same["proposal_code"] = "research.proposal.other-inventory-v1"
        m["preregistrations"].append(same)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_FROZEN_HYPOTHESIS"):
            gate.freeze_prereg_manifest(m, registry, git_commit_sha=GIT)

    def test_git_commit_must_be_exact_sha_not_arbitrary_branch(self) -> None:
        with self.assertRaisesRegex(ValueError, "GIT_COMMIT_SHA_REQUIRED"):
            gate.freeze_prereg_manifest(prereg(), proposals(), git_commit_sha="main")

    def test_tampered_proposal_results_rejected(self) -> None:
        registry = proposals()
        registry["proposals"][0]["test_p"] = 0.0001
        with self.assertRaisesRegex(ValueError, "PROPOSAL_FIELDS_OR_RESULTS_ATTACHED"):
            gate.freeze_prereg_manifest(prereg(), registry, git_commit_sha=GIT)

    def test_alpha_and_effect_must_be_fixed(self) -> None:
        for key, value in (("family_alpha", 0.2), ("minimum_effect", -0.10),
                           ("family_size", 0)):
            with self.subTest(key=key):
                raw = prereg()
                raw["preregistrations"][0][key] = value
                with self.assertRaises(ValueError):
                    gate.freeze_prereg_manifest(raw, proposals(), git_commit_sha=GIT)


if __name__ == "__main__":
    unittest.main()
