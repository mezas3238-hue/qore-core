"""Immutable, source-first preregistration *specifications*, never market evidence.

This is a prospective contract for new hypotheses: it freezes methods, windows,
primary statistic and data requirements to a Git commit before future outcomes.
It never authorizes data acquisition, a test, OOS, trading or Trader Lab stages.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from qore.infrastructure.trader_lab.qore_research_zero_budget_intake_v1 import (
    ResearchIntakeError,
)

_PREREG_SCHEMA = "qore.research.prereg.freeze.v1"
_PROPOSAL_SCHEMA = "qore.research.zero-budget.proposals.v1"
_CODE = re.compile(r"[a-z][a-z0-9._-]{2,100}\Z")
_DATE = re.compile(r"(?:19|20)\d{2}-\d{2}-\d{2}\Z")
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_MAX = 20
_TEST_METHODS = {"fisher_exact", "block_bootstrap", "permutation"}
_ALTERNATIVES = {"greater", "less", "two_sided"}
_SPEC_FIELDS = frozenset({
    "proposal_code", "hypothesis_code", "family_code", "data_requirement_code",
    "research_root_count", "signal_definition", "outcome_definition",
    "sampling_rule", "roll_policy", "publication_asof_rule",
    "source_identity_and_rights_rule", "execution_cost_rule",
    "negative_price_policy", "lag_observations", "horizon_observations",
    "dev_start", "dev_end", "diag_start", "diag_end",
    "holdout_start", "holdout_end", "test_method", "alternative",
    "family_size", "family_alpha", "minimum_effect",
    "hypotheses_previously_tested", "source_authority_verified",
    "prices_examined_for_this_hypothesis", "economic_test_authorized",
    "budget_usd",
})
_PROPOSAL_FIELDS = frozenset({
    "code", "question_code", "data_requirement_code", "research_root_count",
})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hex_digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _token(value: Any, field: str) -> str:
    if type(value) is not str or not _CODE.fullmatch(value):
        raise ResearchIntakeError(f"BAD_TOKEN_{field}")
    return value


def _description(value: Any, field: str) -> str:
    if type(value) is not str or len(value.strip()) < 18 or len(value) > 1200:
        raise ResearchIntakeError(f"UNSPECIFIED_{field}")
    if any(ch in value for ch in ("\x00", "\x1b")):
        raise ResearchIntakeError(f"BAD_CHAR_{field}")
    return value


def _day(value: Any, field: str) -> date:
    if type(value) is not str or not _DATE.fullmatch(value):
        raise ResearchIntakeError(f"BAD_DATE_{field}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ResearchIntakeError(f"INVALID_DATE_{field}") from exc


def _new_proposals(proposals: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (
        type(proposals) is not dict
        or set(proposals) != {"schema", "proposals"}
        or proposals["schema"] != _PROPOSAL_SCHEMA
        or type(proposals["proposals"]) is not list
        or len(proposals["proposals"]) > _MAX
    ):
        raise ResearchIntakeError("PROPOSAL_MANIFEST_SCHEMA")
    result: dict[str, dict[str, Any]] = {}
    for proposal in proposals["proposals"]:
        if type(proposal) is not dict or set(proposal) != _PROPOSAL_FIELDS:
            raise ResearchIntakeError("PROPOSAL_FIELDS_OR_RESULTS_ATTACHED")
        code = _token(proposal["code"], "proposal")
        if not code.startswith("research.proposal."):
            raise ResearchIntakeError("PROPOSAL_MUST_HAVE_NEW_IDENTITY")
        _token(proposal["question_code"], "question")
        _token(proposal["data_requirement_code"], "source")
        if type(proposal["research_root_count"]) is not int or proposal["research_root_count"] not in (2, 6):
            raise ResearchIntakeError("PROPOSAL_BAD_ROOT_COUNT")
        if code in result:
            raise ResearchIntakeError("DUPLICATE_PROPOSAL_IDENTITY")
        result[code] = proposal
    return result


@dataclass(frozen=True, slots=True)
class FrozenHypothesis:
    """A verified spec hash. The source remains UNVERIFIED and blocked."""

    proposal_code: str
    hypothesis_code: str
    family_code: str
    spec_sha256: str
    dev: str
    diag: str
    sealed_holdout: str
    familywise_p_ceiling: float
    next_action: str = "SOURCE_AUTHORITY_REQUIRED"
    experiment_runnable: bool = False
    economic_test_authorized: bool = False
    holdout_opened: bool = False
    market_data_budget_usd: int = 0
    trader_lab_state: str = "draft"

    def to_json(self) -> dict[str, Any]:
        return {
            "proposal_code": self.proposal_code,
            "hypothesis_code": self.hypothesis_code,
            "family_code": self.family_code,
            "spec_sha256": self.spec_sha256,
            "dev": self.dev,
            "diag": self.diag,
            "sealed_holdout": self.sealed_holdout,
            "familywise_p_ceiling": self.familywise_p_ceiling,
            "next_action": self.next_action,
            "experiment_runnable": self.experiment_runnable,
            "economic_test_authorized": self.economic_test_authorized,
            "holdout_opened": self.holdout_opened,
            "market_data_budget_usd": self.market_data_budget_usd,
            "trader_lab_state": self.trader_lab_state,
        }


def _freeze_one(spec: Any, proposals: dict[str, dict[str, Any]]) -> FrozenHypothesis:
    if type(spec) is not dict or set(spec) != _SPEC_FIELDS:
        raise ResearchIntakeError("PREREG_FIELDS_OR_OUTCOMES_ATTACHED")
    code = _token(spec["proposal_code"], "identity")
    if code not in proposals:
        raise ResearchIntakeError("NO_MATCHING_PRIOR_PROPOSAL")
    proposal = proposals[code]
    _token(spec["hypothesis_code"], "hypothesis")
    _token(spec["family_code"], "family")
    if (
        spec["data_requirement_code"] != proposal["data_requirement_code"]
        or type(spec["research_root_count"]) is not int
        or spec["research_root_count"] != proposal["research_root_count"]
    ):
        raise ResearchIntakeError("PROPOSAL_SOURCE_OR_UNIVERSE_CHANGED")
    for label in (
        "signal_definition", "outcome_definition", "sampling_rule",
        "roll_policy", "publication_asof_rule", "source_identity_and_rights_rule",
        "execution_cost_rule", "negative_price_policy",
    ):
        _description(spec[label], label)
    for label in ("lag_observations", "horizon_observations", "family_size"):
        if type(spec[label]) is not int or not 1 <= spec[label] <= 250:
            raise ResearchIntakeError(f"INVALID_INT_{label}")
    if spec["lag_observations"] + spec["horizon_observations"] > 250:
        raise ResearchIntakeError("HORIZON_EXCEEDS_SOURCE_CONTRACT")
    if spec["test_method"] not in _TEST_METHODS or type(spec["test_method"]) is not str:
        raise ResearchIntakeError("TEST_METHOD_NOT_PREDECLARED")
    if spec["alternative"] not in _ALTERNATIVES or type(spec["alternative"]) is not str:
        raise ResearchIntakeError("ALTERNATIVE_NOT_PREDECLARED")
    if type(spec["family_alpha"]) is not float or spec["family_alpha"] != 0.05:
        raise ResearchIntakeError("FAMILY_ALPHA_MUST_BE_FIXED_005")
    if type(spec["minimum_effect"]) not in (float, int) or not 0 < spec["minimum_effect"] <= 1:
        raise ResearchIntakeError("MIN_EFFECT_INVALID")
    if type(spec["hypotheses_previously_tested"]) is not list or any(
        type(x) is not str or not _CODE.fullmatch(x)
        for x in spec["hypotheses_previously_tested"]
    ):
        raise ResearchIntakeError("MISSING_PREVIOUS_FAMILY_DECLARATION")
    if len(set(spec["hypotheses_previously_tested"])) != len(spec["hypotheses_previously_tested"]):
        raise ResearchIntakeError("DUPLICATE_PRIOR_HYPOTHESIS")
    for field in (
        "source_authority_verified", "prices_examined_for_this_hypothesis",
        "economic_test_authorized",
    ):
        if spec[field] is not False:
            raise ResearchIntakeError(f"UNAUTHORIZED_PRE_RESULTS_ASSERTION_{field}")
    if type(spec["budget_usd"]) is not int or spec["budget_usd"] != 0:
        raise ResearchIntakeError("NONZERO_MARKET_DATA_BUDGET")
    days = [
        _day(spec[x], x) for x in (
            "dev_start", "dev_end", "diag_start", "diag_end",
            "holdout_start", "holdout_end",
        )
    ]
    if not all(a < b for a, b in zip(days, days[1:])):
        raise ResearchIntakeError("WINDOWS_OVERLAP_OR_NOT_ASCENDING")
    if spec["hypothesis_code"] in spec["hypotheses_previously_tested"]:
        raise ResearchIntakeError("REUSING_TESTED_HYPOTHESIS")
    return FrozenHypothesis(
        proposal_code=code,
        hypothesis_code=spec["hypothesis_code"],
        family_code=spec["family_code"],
        spec_sha256=_hex_digest(spec),
        dev=spec["dev_start"] + "/" + spec["dev_end"],
        diag=spec["diag_start"] + "/" + spec["diag_end"],
        sealed_holdout=spec["holdout_start"] + "/" + spec["holdout_end"],
        familywise_p_ceiling=spec["family_alpha"] / spec["family_size"],
    )


def freeze_prereg_manifest(
    manifest: dict[str, Any],
    proposals: dict[str, Any],
    *,
    git_commit_sha: str,
) -> dict[str, Any]:
    """Freeze content into a provenance receipt, never grant source access.

    The Actions runner must verify these manifest bytes equal git show HEAD.
    Later outcome workers MUST independently verify this commit is an ancestor
    of the result run (and use a genuinely untouched holdout).
    """
    if type(git_commit_sha) is not str or _SHA.fullmatch(git_commit_sha) is None:
        raise ResearchIntakeError("GIT_COMMIT_SHA_REQUIRED")
    proposal_map = _new_proposals(proposals)
    if (
        type(manifest) is not dict
        or set(manifest) != {"schema", "preregistrations"}
        or manifest["schema"] != _PREREG_SCHEMA
        or type(manifest["preregistrations"]) is not list
        or len(manifest["preregistrations"]) > _MAX
    ):
        raise ResearchIntakeError("PREREG_MANIFEST_SCHEMA")
    frozen = [_freeze_one(x, proposal_map) for x in manifest["preregistrations"]]
    identities = [x.proposal_code for x in frozen]
    hypotheses = [x.hypothesis_code for x in frozen]
    if len(set(identities)) != len(identities) or len(set(hypotheses)) != len(hypotheses):
        raise ResearchIntakeError("DUPLICATE_FROZEN_HYPOTHESIS")
    if set(identities) != set(proposal_map):
        raise ResearchIntakeError("UNFROZEN_PROPOSAL_IN_REGISTER")
    canonical_items = [x.to_json() for x in sorted(frozen, key=lambda x: x.proposal_code)]
    body: dict[str, Any] = {
        "schema": "qore.research.prereg.git-anchored-source-blocked.v1",
        "git_commit_sha": git_commit_sha,
        "proposal_manifest_sha256": _hex_digest(proposals),
        "prereg_manifest_sha256": _hex_digest(manifest),
        "frozen_count": len(canonical_items),
        "frozen_specs": canonical_items,
        "source_market_authority_obtained": False,
        "execution_authority": False,
        "data_spend_usd": 0,
        "economic_backtest_executed": False,
        "holdout_read": False,
        "trader_qualified": False,
        "signatures_issued": False,
    }
    return {**body, "receipt_sha256": _hex_digest(body)}
