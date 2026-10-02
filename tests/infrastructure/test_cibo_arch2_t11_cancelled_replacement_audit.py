from scripts.cibo_arch2_t11_cancelled_replacement_audit import (
    AUDITED_RUNS,
    AUDITED_SUFFIXES,
    label_run_suffix,
)


def test_cancelled_replacement_audit_freezes_exact_run_surface() -> None:
    assert AUDITED_RUNS == (
        (36946792349, 1),
        (36947685956, 1),
    )
    assert AUDITED_SUFFIXES == ("2349-1", "5956-1")


def test_label_matching_is_exact_to_cancelled_replacement_runs() -> None:
    assert (
        label_run_suffix("CIBOA2T11:GBPJPY:2349-1:C01:L2:C1")
        == "2349-1"
    )
    assert (
        label_run_suffix("CIBOA2T11:EURUSD:5956-1:C02:L1:C1")
        == "5956-1"
    )
    assert label_run_suffix("CIBOA2T11:GBPJPY:7912-1:C05:L2:C1") is None
    assert label_run_suffix("OTHER:2349-1") is None
