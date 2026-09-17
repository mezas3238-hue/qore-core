from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "qore_fundednext_rules_refresh.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("qore_rule_refresh_script_test", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load_script()

_GOOD_MLL = b"Stellar Instant has no Daily Loss Limit and a 6% trailing Maximum Loss."
_GOOD_EA = b"Stellar Instant Expert Advisors are allowed on MetaTrader 5 MT5."
_GOOD_RISK = b"Stellar Instant default risk limit is 3% cumulative across all open positions."


def _prepare_root(tmp_path: Path, *, fingerprint_matches: bool = True) -> str:
    provider = tmp_path / "src/qore/infrastructure/fundednext_stellar_instant.py"
    provider.parent.mkdir(parents=True)
    provider.write_bytes(b"provider-contract")
    fingerprint = hashlib.sha256(provider.read_bytes()).hexdigest()
    activation_fingerprint = fingerprint if fingerprint_matches else "b" * 64
    activation = tmp_path / "var/fundednext/live-activation.json"
    activation.parent.mkdir(parents=True)
    activation.write_text(
        json.dumps({"provider_rules_fingerprint": activation_fingerprint}),
        encoding="utf-8",
    )
    return fingerprint


def _sources(
    *,
    mll: bytes = _GOOD_MLL,
    ea: bytes = _GOOD_EA,
    risk: bytes = _GOOD_RISK,
) -> dict[str, bytes]:
    return {
        MODULE.MLL_URL: mll,
        MODULE.EA_URL: ea,
        MODULE.RISK_URL: risk,
    }


def test_refresh_passes_without_expiry_or_lease_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _prepare_root(tmp_path)
    pages = _sources()
    monkeypatch.setattr(MODULE, "_fetch", lambda url: pages[url])

    payload = MODULE.refresh(tmp_path)

    assert payload["schema"] == "qore.fundednext.provider-rules-refresh.v2"
    assert payload["provider_rules_fingerprint"] == expected
    assert "verified_at" not in payload
    assert "valid_until" not in payload
    facts = payload["facts"]
    assert facts["no_daily_loss_limit"] is True
    assert facts["maximum_loss_fraction"] == "0.06"
    assert facts["trailing_maximum_loss"] is True
    assert facts["ea_allowed_mt5"] is True
    assert facts["cumulative_open_risk_fraction"] == "0.03"
    assert facts["cumulative_open_risk_applies"] is True
    for name, url in {"mll": MODULE.MLL_URL, "ea": MODULE.EA_URL, "risk": MODULE.RISK_URL}.items():
        assert payload["sources"][name]["url"] == url
        assert payload["sources"][name]["sha256"] == hashlib.sha256(pages[url]).hexdigest()


def test_refresh_rejects_fingerprint_mismatch_before_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_root(tmp_path, fingerprint_matches=False)
    called = False

    def fetch(_: str) -> bytes:
        nonlocal called
        called = True
        return b"unused"

    monkeypatch.setattr(MODULE, "_fetch", fetch)
    with pytest.raises(RuntimeError, match="fingerprint mismatch"):
        MODULE.refresh(tmp_path)
    assert called is False


def test_refresh_rejects_source_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_root(tmp_path)

    def fetch(_: str) -> bytes:
        raise RuntimeError("source-read-failed")

    monkeypatch.setattr(MODULE, "_fetch", fetch)
    with pytest.raises(RuntimeError, match="source-read-failed"):
        MODULE.refresh(tmp_path)


@pytest.mark.parametrize(
    ("pages", "message"),
    [
        (
            _sources(mll=b"Stellar Instant no Daily Loss Limit trailing Maximum Loss"),
            "6% trailing Maximum Loss",
        ),
        (_sources(mll=b"Stellar Instant 6% trailing Maximum Loss"), "no-daily-loss"),
        (_sources(ea=b"Stellar Instant Expert Advisors are allowed"), "EA-on-MT5"),
        (_sources(ea=b"Stellar Instant Expert Advisors MetaTrader 5"), "EA permission"),
        (_sources(risk=b"Stellar Instant cumulative across all open positions"), "3% cumulative"),
        (_sources(risk=b"Stellar Instant default risk limit is 3%"), "cumulative open-position"),
    ],
)
def test_refresh_rejects_required_rule_text_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pages: dict[str, bytes],
    message: str,
) -> None:
    _prepare_root(tmp_path)
    monkeypatch.setattr(MODULE, "_fetch", lambda url: pages[url])
    with pytest.raises(RuntimeError, match=message):
        MODULE.refresh(tmp_path)
