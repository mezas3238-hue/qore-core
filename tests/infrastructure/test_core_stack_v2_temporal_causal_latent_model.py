from qore.infrastructure.core_stack_v2.temporal_causal_latent_model import (
    TemporalCausalDisposition,
    TemporalCausalLatentRelation,
)


def _relation() -> TemporalCausalLatentRelation:
    return TemporalCausalLatentRelation(
        latent_concept_id="LATENT_CONCEPT_TEST001",
        target_name="CONTINUATION",
        disposition=TemporalCausalDisposition.CONSUMED_TEMPORAL_REPLICATED,
        discovery_effect_bps=800,
        r6_effect_bps=700,
        r5_effect_bps=650,
        discovery_sign_stability_bps=9000,
        r6_sign_stability_bps=8500,
        r5_sign_stability_bps=8200,
        discovery_regime_stability_bps=9000,
        r6_regime_stability_bps=8500,
        r5_regime_stability_bps=8200,
        source_threshold_low_milli_z=-500,
        source_threshold_high_milli_z=500,
        evidence_refs=("mc14:test",),
    )


def test_consumed_temporal_relation_remains_research_only() -> None:
    relation = _relation()
    assert relation.fresh_validation_used is False
    assert relation.knowledge_promotion_authority is False
    assert relation.methodology_authority is False
    assert relation.execution_authority is False


def test_relation_fingerprint_is_deterministic() -> None:
    assert _relation().fingerprint() == _relation().fingerprint()
