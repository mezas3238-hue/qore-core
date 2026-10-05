"""Determinism and replay reality for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReplayObservation:
    replay_id: str
    code_sha: str
    input_fingerprint: str
    output_fingerprint: str
    tool_registry_fingerprint: str
    seed: int | None
    deterministic_contract: bool

    def __post_init__(self) -> None:
        for value in (
            self.replay_id,
            self.code_sha,
            self.input_fingerprint,
            self.output_fingerprint,
            self.tool_registry_fingerprint,
        ):
            if not value.strip():
                raise ValueError("replay identity/fingerprints are required")


@dataclass(frozen=True, slots=True)
class ReplayRealityAssessment:
    replay_count: int
    same_code: bool
    same_input: bool
    same_tools: bool
    deterministic_output: bool
    deterministic_replay_proven: bool


def assess_replay_determinism(
    observations: tuple[ReplayObservation, ...],
) -> ReplayRealityAssessment:
    if len(observations) < 2:
        raise ValueError("determinism requires at least two replay observations")
    same_code = len({item.code_sha for item in observations}) == 1
    same_input = len({item.input_fingerprint for item in observations}) == 1
    same_tools = len({item.tool_registry_fingerprint for item in observations}) == 1
    output_same = len({item.output_fingerprint for item in observations}) == 1
    contract = all(item.deterministic_contract for item in observations)
    proven = same_code and same_input and same_tools and output_same and contract
    return ReplayRealityAssessment(
        replay_count=len(observations),
        same_code=same_code,
        same_input=same_input,
        same_tools=same_tools,
        deterministic_output=output_same,
        deterministic_replay_proven=proven,
    )
