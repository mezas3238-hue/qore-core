import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load() -> ModuleType:
    path = Path("scripts/cibo_arch2_t11_cancelled_replacement_audit.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_arch2_t11_cancelled_replacement_audit",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T11 cancelled replacement audit")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = _load()


def test_cancelled_replacement_audit_freezes_exact_run_surface() -> None:
    assert audit.AUDITED_RUNS == (
        (36946792349, 1),
        (36947685956, 1),
    )
    assert audit.AUDITED_SUFFIXES == ("2349-1", "5956-1")


def test_label_matching_is_exact_to_cancelled_replacement_runs() -> None:
    assert (
        audit.label_run_suffix("CIBOA2T11:GBPJPY:2349-1:C01:L2:C1")
        == "2349-1"
    )
    assert (
        audit.label_run_suffix("CIBOA2T11:EURUSD:5956-1:C02:L1:C1")
        == "5956-1"
    )
    assert audit.label_run_suffix("CIBOA2T11:GBPJPY:7912-1:C05:L2:C1") is None
    assert audit.label_run_suffix("OTHER:2349-1") is None
