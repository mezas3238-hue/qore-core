import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


def _load():
    path = Path("scripts/cibo_arch2_t11_orphan_containment_cleanup.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_arch2_t11_orphan_containment_cleanup",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T11 orphan containment cleanup")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cleanup = _load()


def _item(label: str) -> SimpleNamespace:
    return SimpleNamespace(
        tradeData=SimpleNamespace(label=label),
    )


def test_cleanup_authorizes_only_initial_and_replacement_suffixes() -> None:
    assert cleanup.INITIAL_SUFFIX == "7912-1"
    assert cleanup.REPLACEMENT_SUFFIX == "2349-1"

    assert cleanup.authorized_t11_label(
        "CIBOA2T11:GBPJPY:7912-1:C05:L2:C1"
    )
    assert cleanup.authorized_t11_label(
        "CIBOA2T11:GBPJPY:2349-1:C01:L1:C1"
    )
    assert not cleanup.authorized_t11_label(
        "CIBOA2T11:GBPJPY:9999-9:C01:L1:C1"
    )
    assert not cleanup.authorized_t11_label(
        "OTHER:GBPJPY:7912-1:C05:L2:C1"
    )


def test_unknown_t11_labels_are_fail_closed() -> None:
    response = SimpleNamespace(
        position=(
            _item("CIBOA2T11:GBPJPY:7912-1:C05:L2:C1"),
            _item("CIBOA2T11:GBPJPY:9999-9:C01:L1:C1"),
        ),
        order=(),
    )

    assert cleanup._unknown_t11_labels(response) == (
        "CIBOA2T11:GBPJPY:9999-9:C01:L1:C1",
    )


def test_non_t11_labels_are_never_authorized() -> None:
    assert cleanup.any_t11_label("CIBOA2T11:EURUSD:7912-1:C01:L1:C1")
    assert not cleanup.any_t11_label("R34:XAUUSD")
    assert not cleanup.any_t11_label(None)
