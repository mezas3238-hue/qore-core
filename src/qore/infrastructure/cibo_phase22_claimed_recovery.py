"""Claimed-run-only recovery for the burned Phase22 VT31 fresh lane.

This module never executes Trader logic and never reads holdout market data.
It projects the already-emitted immutable VT31 lane artifact onto the CIBO
executable-opportunity surface. Classification is based only on pre-existing
geometry fields required by TraderOpportunityEnvelope construction; realized
outcome values are never consulted to decide inclusion.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
)

SOURCE_RUN_ID = 37007253157
SOURCE_RUN_ATTEMPT = 1
VT31_ARTIFACT_ID = 11226930079
VT31_ARTIFACT_SHA256 = (
    "sha256:1a81b9be93b1aa5bb97d5a034e4c2373565a421643cbe659125bc612781b0d07"
)
EXPECTED_VT31_EMITTED_ROWS = 82
EXPECTED_VT31_CENSORED_ROWS = 20
EXPECTED_VT31_EXECUTABLE_ROWS = 62
_REQUIRED_GEOMETRY_FIELDS = ("entry", "stop", "target")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _diagnostic_censored_count(payload: Mapping[str, object]) -> int:
    try:
        binding = payload["binding_diagnostics"]
        path = binding["path_causal_diagnostics"]  # type: ignore[index]
        capacity = path["capacity_diagnostics"]  # type: ignore[index]
        value = capacity["censored_geometry_count"]  # type: ignore[index]
    except (KeyError, TypeError) as error:
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery censored diagnostic missing"
        ) from error
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery censored diagnostic invalid"
        )
    return value


def _is_geometry_censored(row: Mapping[str, object]) -> bool:
    """Classify without reading realized_r or any terminal economic outcome."""

    return any(row.get(field) is None for field in _REQUIRED_GEOMETRY_FIELDS)


def canonicalize_claimed_native_opportunity_order(
    payload: Mapping[str, object],
) -> dict[str, Any]:
    """Canonicalize serialization order only; never select by outcome."""

    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list) or any(
        not isinstance(row, dict) for row in opportunities
    ):
        raise CiboCapitalManagementError(
            "Phase22 claimed native opportunity surface invalid"
        )
    projected = copy.deepcopy(dict(payload))
    rows = [dict(row) for row in opportunities]
    rows.sort(
        key=lambda row: (
            str(row.get("signal_at", "")),
            str(row.get("trader_id", payload.get("trader_id", ""))),
            str(row.get("signal_fingerprint", "")),
        )
    )
    if sorted(_canonical_sha(row) for row in rows) != sorted(
        _canonical_sha(dict(row)) for row in opportunities
    ):
        raise CiboCapitalManagementError(
            "Phase22 claimed native canonicalization changed population"
        )
    projected["opportunities"] = rows
    projected["opportunity_count"] = len(rows)
    return projected


@dataclass(frozen=True, slots=True)
class Phase22Vt31ClaimedRecoveryReceipt:
    candidate_id: str
    source_run_id: int
    source_run_attempt: int
    source_artifact_id: int
    source_artifact_sha256: str
    source_payload_sha256: str
    recovered_payload_sha256: str
    emitted_row_count: int
    censored_diagnostic_count: int
    censored_excluded_count: int
    executable_retained_count: int
    excluded_signal_fingerprints: tuple[str, ...]
    inclusion_fields: tuple[str, ...] = _REQUIRED_GEOMETRY_FIELDS
    classifier: str = "VT31_REQUIRED_EXECUTABLE_GEOMETRY_V1"
    selection_uses_realized_r: bool = False
    geometry_reconstructed: bool = False
    fresh_lane_population_regenerated: bool = False
    second_fresh_execution: bool = False
    productive_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.phase22.vt31-claimed-recovery.v1",
            "candidate_id": self.candidate_id,
            "source_run_id": self.source_run_id,
            "source_run_attempt": self.source_run_attempt,
            "source_artifact_id": self.source_artifact_id,
            "source_artifact_sha256": self.source_artifact_sha256,
            "source_payload_sha256": self.source_payload_sha256,
            "recovered_payload_sha256": self.recovered_payload_sha256,
            "emitted_row_count": self.emitted_row_count,
            "censored_diagnostic_count": self.censored_diagnostic_count,
            "censored_excluded_count": self.censored_excluded_count,
            "executable_retained_count": self.executable_retained_count,
            "excluded_signal_fingerprints": list(
                self.excluded_signal_fingerprints
            ),
            "inclusion_fields": list(self.inclusion_fields),
            "classifier": self.classifier,
            "selection_uses_realized_r": False,
            "geometry_reconstructed": False,
            "fresh_lane_population_regenerated": False,
            "second_fresh_execution": False,
            "productive_authority": False,
        }

    def fingerprint(self) -> str:
        return _canonical_sha(self.payload())


def recover_vt31_claimed_payload(
    payload: Mapping[str, object],
    *,
    source_artifact_id: int,
    source_artifact_sha256: str,
    source_run_id: int,
    source_run_attempt: int,
) -> tuple[dict[str, Any], Phase22Vt31ClaimedRecoveryReceipt]:
    """Recover the exact immutable VT31 lane into an executable CIBO surface."""

    if (
        source_run_id != SOURCE_RUN_ID
        or source_run_attempt != SOURCE_RUN_ATTEMPT
        or source_artifact_id != VT31_ARTIFACT_ID
        or source_artifact_sha256 != VT31_ARTIFACT_SHA256
        or _SHA256_RE.fullmatch(source_artifact_sha256) is None
    ):
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery immutable source identity drift"
        )
    if (
        payload.get("candidate_id") != CANDIDATE_ID
        or payload.get("trader_id") != "VT31_NAS100"
        or payload.get("fresh_outcomes_executed") is not True
        or payload.get("methodology_changed") is not False
        or payload.get("legacy_trader_sizing_used_for_cibo") is not False
        or payload.get("productive_authority") is not False
    ):
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery lane governance/identity drift"
        )

    raw_opportunities = payload.get("opportunities")
    if not isinstance(raw_opportunities, list) or any(
        not isinstance(row, dict) for row in raw_opportunities
    ):
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery opportunities invalid"
        )
    if len(raw_opportunities) != EXPECTED_VT31_EMITTED_ROWS:
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery emitted population drift"
        )

    retained: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    for row in raw_opportunities:
        if _is_geometry_censored(row):
            excluded.append(dict(row))
        else:
            retained.append(dict(row))

    if any(
        not all(row.get(field) is None for field in _REQUIRED_GEOMETRY_FIELDS)
        for row in excluded
    ):
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery partial geometry requires new forensics"
        )

    diagnostic_count = _diagnostic_censored_count(payload)
    if (
        diagnostic_count != EXPECTED_VT31_CENSORED_ROWS
        or len(excluded) != EXPECTED_VT31_CENSORED_ROWS
        or len(retained) != EXPECTED_VT31_EXECUTABLE_ROWS
        or diagnostic_count != len(excluded)
    ):
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery censored population mismatch"
        )

    excluded_fingerprints = tuple(
        str(row.get("signal_fingerprint", "")) for row in excluded
    )
    retained_fingerprints = tuple(
        str(row.get("signal_fingerprint", "")) for row in retained
    )
    if (
        any(_SHA256_RE.fullmatch(item) is None for item in excluded_fingerprints)
        or any(_SHA256_RE.fullmatch(item) is None for item in retained_fingerprints)
        or len(set(excluded_fingerprints)) != len(excluded_fingerprints)
        or len(set(retained_fingerprints)) != len(retained_fingerprints)
        or set(excluded_fingerprints) & set(retained_fingerprints)
    ):
        raise CiboCapitalManagementError(
            "Phase22 VT31 recovery signal identity drift"
        )

    recovered = copy.deepcopy(dict(payload))
    recovered["opportunities"] = retained
    recovered["opportunity_count"] = len(retained)
    recovered["claimed_recovery_projection"] = {
        "schema": "qore.cibo.phase22.vt31-executable-projection.v1",
        "source_run_id": SOURCE_RUN_ID,
        "source_run_attempt": SOURCE_RUN_ATTEMPT,
        "source_artifact_id": VT31_ARTIFACT_ID,
        "source_artifact_sha256": VT31_ARTIFACT_SHA256,
        "classifier": "VT31_REQUIRED_EXECUTABLE_GEOMETRY_V1",
        "inclusion_fields": list(_REQUIRED_GEOMETRY_FIELDS),
        "censored_excluded_count": len(excluded),
        "geometry_reconstructed": False,
        "selection_uses_realized_r": False,
        "fresh_lane_population_regenerated": False,
        "second_fresh_execution": False,
        "productive_authority": False,
    }

    source_sha = _canonical_sha(dict(payload))
    recovered_sha = _canonical_sha(recovered)
    receipt = Phase22Vt31ClaimedRecoveryReceipt(
        candidate_id=CANDIDATE_ID,
        source_run_id=source_run_id,
        source_run_attempt=source_run_attempt,
        source_artifact_id=source_artifact_id,
        source_artifact_sha256=source_artifact_sha256,
        source_payload_sha256=source_sha,
        recovered_payload_sha256=recovered_sha,
        emitted_row_count=len(raw_opportunities),
        censored_diagnostic_count=diagnostic_count,
        censored_excluded_count=len(excluded),
        executable_retained_count=len(retained),
        excluded_signal_fingerprints=excluded_fingerprints,
    )
    return recovered, receipt
