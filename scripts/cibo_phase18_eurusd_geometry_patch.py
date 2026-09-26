"""Deterministic Phase-18 instrumentation for immutable EURUSD R38.

PR #651 does not vendor the EURUSD research lineage. The replay workflow
checks out the exact commit that produced the authoritative R38 corrected
ledger, verifies that commit, and adds serialization-only technical geometry.

No signal, entry, stop, target, risk policy, market path or outcome is changed.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_CODE_GIT_SHA = "324fb91d44a6fa328e66de2e22ace7386630c7aa"
SOURCE_RELATIVE_PATH = (
    "src/qore/infrastructure/trader_lab/"
    "turtle_soup_eurusd_r38_5y_structural_risk_correction.py"
)

_DATACLASS_OLD = """class ScaledTrade:
    entry_at: str
"""
_DATACLASS_NEW = """class ScaledTrade:
    signal_at: str
    entry_at: str
    entry_price: str
    structural_stop: str
    technical_target: str
"""

_CONSTRUCTOR_OLD = """            ScaledTrade(
                entry_at=runtime.entry_at.isoformat(),
"""
_CONSTRUCTOR_NEW = """            ScaledTrade(
                signal_at=signal.cisd_at.isoformat(),
                entry_at=runtime.entry_at.isoformat(),
                entry_price=str(entry),
                structural_stop=str(signal.protected_swing),
                technical_target=str(decision.target.level),
"""

_LEDGER_OLD = '"r38-5y-corrected-trades.jsonl"'
_LEDGER_NEW = '"phase18-eurusd-r38-geometry-trades.jsonl"'
_REPORT_OLD = '"r38-5y-correction-report.json"'
_REPORT_NEW = '"phase18-eurusd-r38-geometry-report.json"'


def _replace_once(source: str, old: str, new: str, *, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{label} source drift: expected one match, got {count}")
    return source.replace(old, new, 1)


def patch_r38_source(source: str) -> str:
    patched = _replace_once(
        source,
        _DATACLASS_OLD,
        _DATACLASS_NEW,
        label="ScaledTrade dataclass",
    )
    patched = _replace_once(
        patched,
        _CONSTRUCTOR_OLD,
        _CONSTRUCTOR_NEW,
        label="ScaledTrade constructor",
    )
    patched = _replace_once(
        patched,
        _LEDGER_OLD,
        _LEDGER_NEW,
        label="ledger filename",
    )
    patched = _replace_once(
        patched,
        _REPORT_OLD,
        _REPORT_NEW,
        label="report filename",
    )
    return patched


def patch_file(source_path: Path, output_path: Path) -> None:
    patched = patch_r38_source(source_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(patched, encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    patch_file(Path(args.source), Path(args.output))


if __name__ == "__main__":
    main()
