from qore.infrastructure.core_stack_v2.shared_lab_runtime_probe import (
    consume_exact_output,
    fingerprint_payload,
    invoke_native_engine,
)


def native_engine(value: dict[str, int]) -> dict[str, int]:
    return {"state": value["x"] + 1}


def native_consumer(value: dict[str, int]) -> dict[str, int]:
    return {"decision": value["state"] * 2}


def test_native_invocation_emits_real_fingerprints():
    output, trace = invoke_native_engine(
        capability_id="MC09",
        engine_id="belief-state",
        engine=native_engine,
        args=({"x": 3},),
        downstream_native_consumer="MC10",
    )
    assert trace.native_receipt.passed is True
    assert trace.output_fingerprint == fingerprint_payload(output)
    assert trace.latency_ns >= 0
    assert trace.callable_qualname.endswith("native_engine")


def test_exact_output_is_consumed_without_recreation():
    output, trace = invoke_native_engine(
        capability_id="MC09",
        engine_id="belief-state",
        engine=native_engine,
        args=({"x": 3},),
        downstream_native_consumer="MC10",
    )
    result, consumption = consume_exact_output(
        producer_trace=trace,
        consumer_capability_id="MC10",
        consumer=native_consumer,
        producer_output=output,
    )
    assert result == {"decision": 8}
    assert consumption.cable_receipt.passed is True
    assert consumption.producer_output_fingerprint == consumption.consumer_input_fingerprint


def test_recreated_parent_is_rejected():
    output, trace = invoke_native_engine(
        capability_id="MC09",
        engine_id="belief-state",
        engine=native_engine,
        args=({"x": 3},),
        downstream_native_consumer="MC10",
    )
    output["state"] = 999
    try:
        consume_exact_output(
            producer_trace=trace,
            consumer_capability_id="MC10",
            consumer=native_consumer,
            producer_output=output,
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("mutated/recreated parent must be rejected")
