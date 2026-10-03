from qore.infrastructure.cibo_compound_temporal_replication_gate import (
    CompoundTemporalPopulationDisposition,
    assess_compound_temporal_population,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def test_used_holdout_is_processable_but_not_relabelled_forward() -> None:
    result = assess_compound_temporal_population(
        source_population_sha256=_sha("1"),
        provider_economics_sha256=_sha("2"),
        forward_observed=False,
    )

    assert result.disposition is (
        CompoundTemporalPopulationDisposition.INELIGIBLE_NOT_FORWARD
    )
    assert result.eligible_for_strict_replication_gate is False
    assert result.forward_observed is False
    assert result.certification_ready is False
    assert result.productive_authority is False


def test_forward_unpooled_population_is_eligible_for_strict_gate() -> None:
    result = assess_compound_temporal_population(
        source_population_sha256=_sha("3"),
        provider_economics_sha256=_sha("4"),
        forward_observed=True,
    )

    assert result.disposition is (
        CompoundTemporalPopulationDisposition.ELIGIBLE_FORWARD_UNPOOLED
    )
    assert result.eligible_for_strict_replication_gate is True


def test_pooled_outcomes_remain_ineligible_even_if_forward() -> None:
    result = assess_compound_temporal_population(
        source_population_sha256=_sha("5"),
        provider_economics_sha256=_sha("6"),
        forward_observed=True,
        outcomes_pooled=True,
    )

    assert result.disposition is (
        CompoundTemporalPopulationDisposition.INELIGIBLE_OUTCOMES_POOLED
    )
    assert result.eligible_for_strict_replication_gate is False
