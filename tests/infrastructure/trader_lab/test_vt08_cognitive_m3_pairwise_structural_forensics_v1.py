from qore.infrastructure.trader_lab.vt08_cognitive_m3_pairwise_structural_forensics_v1 import (
    PAIRS,
    SCHEMA,
)


def test_m3_pairwise_structural_forensics_freeze() -> None:
    assert len(PAIRS) == 10
    assert ("ps_cardinality", "ps_age") in PAIRS
    assert SCHEMA.endswith("m3_pairwise_structural_forensics.v1")
