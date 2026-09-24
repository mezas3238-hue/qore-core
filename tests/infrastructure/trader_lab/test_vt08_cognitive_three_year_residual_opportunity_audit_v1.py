from qore.infrastructure.trader_lab.vt08_cognitive_three_year_residual_opportunity_audit_v1 import (
    SCHEMA,
)


def test_residual_audit_schema_is_frozen() -> None:
    assert SCHEMA.endswith("three_year_residual_opportunity_audit.v1")
