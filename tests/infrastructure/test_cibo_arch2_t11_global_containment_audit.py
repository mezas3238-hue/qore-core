import importlib.util
import sys
from pathlib import Path


def _load():
    path = Path("scripts/cibo_arch2_t11_global_containment_audit.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_arch2_t11_global_containment_audit",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T11 global containment audit")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = _load()


def test_global_audit_classifies_frozen_lineages() -> None:
    assert audit.classify_label(
        f"CIBOA2T11:GBPJPY:{audit.INITIAL_SUFFIX}:C01:L1:C1"
    ) == "INITIAL_CANCELLED_RUN"
    assert audit.classify_label(
        f"CIBOA2T11:EURUSD:{audit.CANONICAL_SUFFIX}:C01:L1:C1"
    ) == "CONTAMINATED_REPLACEMENT_RUN"


def test_global_audit_flags_unknown_t11_namespace() -> None:
    assert audit.t11_label("CIBOA2T11:XAUUSD:9999-9:C01:L1:C1")
    assert audit.classify_label(
        "CIBOA2T11:XAUUSD:9999-9:C01:L1:C1"
    ) == "OTHER_T11_LABEL"
    assert not audit.t11_label("OTHER:XAUUSD:9999-9:C01:L1:C1")
