import importlib.util
import sys
from pathlib import Path

from qore.infrastructure.cibo_arch2_t11_execution_claim import (
    INITIAL_RUN_ATTEMPT,
    INITIAL_RUN_ID,
)


def _load():
    path = Path("scripts/cibo_arch2_t11_v1_orphan_cleanup.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_arch2_t11_v1_orphan_cleanup",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T11 V1 cleanup")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cleanup = _load()


def test_cleanup_label_scope_is_exact_cancelled_run() -> None:
    suffix = f"{INITIAL_RUN_ID}-{INITIAL_RUN_ATTEMPT}"[-6:]

    assert cleanup.label_belongs_to_cancelled_run(
        f"CIBOA2T11:GBPJPY:{suffix}:C05:L2:C1"
    )
    assert not cleanup.label_belongs_to_cancelled_run(
        "CIBOA2T11:GBPJPY:792349:C05:L2:C1"
    )
    assert not cleanup.label_belongs_to_cancelled_run(
        f"OTHER:GBPJPY:{suffix}:C05:L2:C1"
    )
