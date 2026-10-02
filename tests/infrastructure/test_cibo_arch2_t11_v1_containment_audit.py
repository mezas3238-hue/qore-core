import importlib.util
import sys
from pathlib import Path

from qore.infrastructure.cibo_arch2_t11_execution_claim import (
    RUN_ATTEMPT,
    RUN_ID,
)


def _load():
    path = Path("scripts/cibo_arch2_t11_v1_containment_audit.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_arch2_t11_v1_containment_audit",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T11 containment audit")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = _load()


def test_claimed_suffix_is_exact_run_attempt_suffix() -> None:
    assert audit.claimed_run_suffix() == (
        f"{INITIAL_RUN_ID}-{INITIAL_RUN_ATTEMPT}"[-6:]
    )


def test_only_exact_claimed_run_labels_match() -> None:
    suffix = audit.claimed_run_suffix()

    assert audit.label_belongs_to_claimed_run(
        f"CIBOA2T11:EURUSD:{suffix}:C01:L1:C1"
    )
    assert not audit.label_belongs_to_claimed_run(
        "CIBOA2T11:EURUSD:000000:C01:L1:C1"
    )
    assert not audit.label_belongs_to_claimed_run(
        f"OTHER:EURUSD:{suffix}:C01:L1:C1"
    )
    assert not audit.label_belongs_to_claimed_run(None)
