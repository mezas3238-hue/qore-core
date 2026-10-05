"""Canonical build identity for QORE Shared Lab."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

LAB_CONTRACT_ID = "QORE_SHARED_LAB_CONSTRUCTION_CONTRACT_001"
LAB_VERSION = "0.1.0-foundation"


@dataclass(frozen=True, slots=True)
class SharedLabBuildManifest:
    lab_version: str
    contract_id: str
    code_sha: str
    branch: str
    tool_registry_fingerprint: str
    core_lane_id: str
    data_sensor_lane_id: str
    authority_free: bool
    protected_holdout_opened: bool
    productive_runtime_mutated: bool

    def __post_init__(self) -> None:
        for value in (
            self.lab_version,
            self.contract_id,
            self.code_sha,
            self.branch,
            self.tool_registry_fingerprint,
            self.core_lane_id,
            self.data_sensor_lane_id,
        ):
            if not value.strip():
                raise ValueError("Shared Lab build manifest fields must be explicit")
        if self.contract_id != LAB_CONTRACT_ID:
            raise ValueError("unexpected Shared Lab construction contract")
        if self.protected_holdout_opened:
            raise ValueError("Shared Lab construction cannot open protected holdout")
        if self.productive_runtime_mutated:
            raise ValueError("Shared Lab construction cannot mutate productive runtime")
        if not self.authority_free:
            raise ValueError("Shared Lab build must remain authority-free")

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def build_manifest(
    *,
    code_sha: str,
    branch: str,
    tool_registry_fingerprint: str,
) -> SharedLabBuildManifest:
    return SharedLabBuildManifest(
        lab_version=LAB_VERSION,
        contract_id=LAB_CONTRACT_ID,
        code_sha=code_sha,
        branch=branch,
        tool_registry_fingerprint=tool_registry_fingerprint,
        core_lane_id="ARCHITECT_1_CORE_COGNITION_INTEGRITY",
        data_sensor_lane_id="ARCHITECT_2_DATA_SENSOR_REALITY",
        authority_free=True,
        protected_holdout_opened=False,
        productive_runtime_mutated=False,
    )
