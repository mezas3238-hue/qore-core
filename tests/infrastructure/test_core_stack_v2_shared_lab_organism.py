from qore.infrastructure.core_stack_v2.shared_lab_organism import build_organism_trace
from qore.infrastructure.core_stack_v2.shared_lab_runtime_probe import (
    consume_exact_output,
    invoke_native_engine,
)


def engine_a(value: int) -> dict[str, int]:
    return {"belief": value + 1}


def engine_b(value: dict[str, int]) -> dict[str, int]:
    return {"physics": value["belief"] * 2}


def engine_c(value: dict[str, int]) -> dict[str, int]:
    return {"decision": value["physics"] - 1}


def test_three_native_engines_form_l9_trace():
    a_out, a = invoke_native_engine(
        capability_id="MC09",
        engine_id="belief",
        engine=engine_a,
        args=(2,),
        downstream_native_consumer="MC10",
    )
    b_out, ab = consume_exact_output(
        producer_trace=a,
        consumer_capability_id="MC10",
        consumer=engine_b,
        producer_output=a_out,
    )
    b_native_out, b = invoke_native_engine(
        capability_id="MC10",
        engine_id="physics",
        engine=engine_b,
        args=(a_out,),
        downstream_native_consumer="STI",
    )
    assert b_native_out == b_out
    c_out, bc = consume_exact_output(
        producer_trace=b,
        consumer_capability_id="STI",
        consumer=engine_c,
        producer_output=b_out,
    )
    _, c = invoke_native_engine(
        capability_id="STI",
        engine_id="sti",
        engine=engine_c,
        args=(b_out,),
        downstream_native_consumer="TRADER",
    )
    assert c_out == {"decision": 5}

    result = build_organism_trace((a, b, c), (ab, bc))
    assert result.node_count == 3
    assert result.edge_count == 2
    assert result.broken_edges == ()
    assert result.l9_end_to_end_proven is True


def test_missing_terminal_native_node_blocks_l9():
    a_out, a = invoke_native_engine(
        capability_id="A",
        engine_id="a",
        engine=engine_a,
        args=(1,),
        downstream_native_consumer="B",
    )
    _, ab = consume_exact_output(
        producer_trace=a,
        consumer_capability_id="B",
        consumer=engine_b,
        producer_output=a_out,
    )
    result = build_organism_trace((a,), (ab,))
    assert result.l9_end_to_end_proven is False
