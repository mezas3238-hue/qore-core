"""Research-only causal admission overlay for the CIBO 3x1Y burned lab.

Rules are calibrated only inside explicitly burned adaptive-research holdouts.
At execution time they may read predecision Trader context plus signal clock and
side. They cannot read symbol identity, outcome, exit, realized PnL, or any
future-derived field. Trader methodology is never changed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    Phase22PredecisionCandidate,
)

_FORBIDDEN_KEY_PARTS = (
    "symbol",
    "trader",
    "exit",
    "realized",
    "outcome",
    "pnl",
    "raw_net",
    "scaled_net",
    "future",
)
_CLOCK_FIELDS = ("side", "weekday", "hour_bucket")


def normalize_cibo_admission_rules(
    rules: Mapping[str, tuple[tuple[str, str], ...]] | None,
) -> dict[str, tuple[tuple[str, str], ...]]:
    """Validate and canonicalize a CIBO-only research admission rule set."""

    if rules is None:
        return {}
    if not isinstance(rules, Mapping):
        raise CiboCapitalManagementError(
            "CIBO research admission rules must be a mapping"
        )

    allowed_traders = set(CANONICAL_PHASE22_TRADER_IDS)
    normalized: dict[str, tuple[tuple[str, str], ...]] = {}
    for trader_id, atoms in rules.items():
        if trader_id not in allowed_traders:
            raise CiboCapitalManagementError(
                "CIBO research admission contains unknown Trader lineage"
            )
        if not isinstance(atoms, tuple) or not atoms:
            raise CiboCapitalManagementError(
                "CIBO research admission requires non-empty atom tuple"
            )
        seen: set[str] = set()
        canonical: list[tuple[str, str]] = []
        for atom in atoms:
            if not isinstance(atom, tuple) or len(atom) != 2:
                raise CiboCapitalManagementError(
                    "CIBO research admission atom must be key/value tuple"
                )
            key, value = atom
            if (
                not isinstance(key, str)
                or not key
                or not isinstance(value, str)
                or not value
            ):
                raise CiboCapitalManagementError(
                    "CIBO research admission atom values must be non-empty strings"
                )
            lowered = key.lower()
            if any(token in lowered for token in _FORBIDDEN_KEY_PARTS):
                raise CiboCapitalManagementError(
                    f"CIBO research admission field is forbidden: {key}"
                )
            if key not in _CLOCK_FIELDS and not (
                key.startswith("ctx_")
                or key.startswith("reg_")
                or key
                in {
                    "family",
                    "target_route",
                    "fragility_flag_count",
                    "posture",
                    "risk_ref_bucket",
                }
            ):
                raise CiboCapitalManagementError(
                    f"CIBO research admission field is not causal allowlist: {key}"
                )
            if key in seen:
                raise CiboCapitalManagementError(
                    "CIBO research admission cannot duplicate a field"
                )
            seen.add(key)
            canonical.append((key, value))
        normalized[trader_id] = tuple(sorted(canonical))
    return dict(sorted(normalized.items()))


def candidate_predecision_features(
    candidate: Phase22PredecisionCandidate,
) -> dict[str, str]:
    """Return only causal fields visible before CIBO capital admission."""

    if not isinstance(candidate, Phase22PredecisionCandidate):
        raise CiboCapitalManagementError(
            "CIBO research admission requires predecision candidate"
        )
    opportunity = candidate.projection.candidate.capital_input.opportunity
    features = dict(opportunity.decision_context)
    features.update(
        {
            "side": opportunity.side,
            "weekday": str(candidate.signal_at.weekday()),
            "hour_bucket": f"{candidate.signal_at.hour:02d}",
        }
    )
    return features


def cibo_admission_accepts(
    candidate: Phase22PredecisionCandidate,
    rules: Mapping[str, tuple[tuple[str, str], ...]] | None,
) -> bool:
    """Apply the configured Trader-lineage CIBO rule with AND semantics."""

    normalized = normalize_cibo_admission_rules(rules)
    atoms = normalized.get(candidate.trader_id)
    if atoms is None:
        return True
    features = candidate_predecision_features(candidate)
    return all(features.get(key) == value for key, value in atoms)


def cibo_admission_fingerprint(
    rules: Mapping[str, tuple[tuple[str, str], ...]] | None,
) -> str:
    normalized = normalize_cibo_admission_rules(rules)
    payload = {
        trader: [[key, value] for key, value in atoms]
        for trader, atoms in normalized.items()
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()
