from qore.infrastructure.core_stack_v2.shared_lab_flight_recorder import (
    FlightNode,
    FlightStage,
    assess_flight_trace,
)


def node(
    stage: FlightStage,
    output_id: str,
    input_ids: tuple[str, ...],
    consumers: tuple[str, ...],
) -> FlightNode:
    return FlightNode(
        stage=stage,
        component_id=f"component-{stage.name}",
        timestamp_ns=int(stage),
        code_sha="sha",
        input_ids=input_ids,
        output_id=output_id,
        confidence=0.8,
        uncertainty=0.2,
        provenance_ids=("source",),
        consumer_ids=consumers,
    )


def test_full_flight_trace_reconstructs_every_stage():
    nodes = []
    previous = ()
    for stage in FlightStage:
        output = f"out-{int(stage)}"
        consumers = () if stage is FlightStage.OBSERVABLE_EFFECT else ("next",)
        nodes.append(node(stage, output, previous, consumers))
        previous = (output,)
    result = assess_flight_trace(tuple(nodes))
    assert result.missing_stages == ()
    assert result.broken_parent_refs == ()
    assert result.l9_flight_trace_proven is True


def test_missing_middle_stage_fails_full_organism_trace():
    nodes = (
        node(FlightStage.PROVIDER, "provider", (), ("sensor",)),
        node(FlightStage.SENSOR, "sensor", ("provider",), ("representation",)),
        node(
            FlightStage.OBSERVABLE_EFFECT,
            "effect",
            ("sensor",),
            (),
        ),
    )
    result = assess_flight_trace(nodes)
    assert FlightStage.REPRESENTATION in result.missing_stages
    assert result.l9_flight_trace_proven is False


def test_recreated_parent_reference_is_rejected():
    nodes = (
        node(FlightStage.PROVIDER, "provider", (), ("sensor",)),
        node(FlightStage.SENSOR, "sensor", ("not-provider",), ("next",)),
    )
    result = assess_flight_trace(
        nodes,
        required_stages=frozenset({FlightStage.PROVIDER, FlightStage.SENSOR}),
    )
    assert result.broken_parent_refs
    assert result.l9_flight_trace_proven is False
