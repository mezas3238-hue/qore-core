from qore.infrastructure.trader_lab.vt08_cognitive_5m_density_pf_truth_audit_v1 import (
    SOURCE_HEAD,
    SOURCE_RUN_ID,
)


def test_density_pf_truth_audit_is_bound_to_immutable_1095d_source() -> None:
    assert SOURCE_RUN_ID == 35934924907
    assert SOURCE_HEAD == "b2d33e1b4829d8b4afc76983decca8a99131403c"
