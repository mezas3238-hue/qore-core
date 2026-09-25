from qore.infrastructure.trader_lab.vt08_cognitive_no_ps_forensics_v1 import (
    _profile_failure_class,
)


def test_no_ps_forensics_exports_profile_classifier() -> None:
    assert callable(_profile_failure_class)
