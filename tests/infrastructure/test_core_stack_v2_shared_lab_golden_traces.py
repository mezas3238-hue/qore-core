from qore.infrastructure.core_stack_v2.shared_lab_golden_traces import GoldenTrace, GoldenTraceLibrary, deterministic_replay_identity, fingerprint_raw_input


def test_golden_trace_is_deterministic_and_versioned() -> None:
    raw = b"EURUSD|1.1000|1.1002"
    replay = deterministic_replay_identity({"trace": "fx-001", "version": "1"})
    trace = GoldenTrace(
        trace_id="fx-001", version="1", origin="engineering-fixture", source_type="tick",
        instrument="EUR/USD", canonical_identity="FX:EURUSD", asset_class="FX",
        provider="fixture-provider", timeframe_or_tick_mode="tick",
        observed_at="2024-03-10T06:59:59.999Z", available_at="2024-03-10T07:00:00.000Z",
        market_session_context="DST_BOUNDARY", raw_input_fingerprint=fingerprint_raw_input(raw),
        expected_invariants=("no_future_leakage", "identity_stable"),
        perturbations_allowed=("timestamp", "provider", "identity"),
        provenance=(("fixture", "engineering"),), expected_failure_classifications=("FUTURE_LEAKAGE",),
        deterministic_replay_identity=replay,
    )
    lib = GoldenTraceLibrary()
    lib.register(trace)
    assert lib.get("fx-001").fingerprint() == trace.fingerprint()
    assert lib.replay_identity("fx-001") == replay
