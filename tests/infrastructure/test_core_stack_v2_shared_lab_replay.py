from qore.infrastructure.core_stack_v2.shared_lab_replay import (
    ReplayObservation,
    assess_replay_determinism,
)


def _obs(replay_id: str, output: str = "out"):
    return ReplayObservation(
        replay_id=replay_id,
        code_sha="sha",
        input_fingerprint="input",
        output_fingerprint=output,
        tool_registry_fingerprint="tools",
        seed=7,
        deterministic_contract=True,
    )


def test_identical_replays_are_proven():
    result = assess_replay_determinism((_obs("r1"), _obs("r2")))
    assert result.deterministic_replay_proven is True


def test_output_drift_fails_determinism():
    result = assess_replay_determinism((_obs("r1"), _obs("r2", output="changed")))
    assert result.deterministic_output is False
    assert result.deterministic_replay_proven is False
