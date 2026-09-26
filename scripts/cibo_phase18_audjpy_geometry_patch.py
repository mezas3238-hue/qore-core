"""Deterministic Phase-18 instrumentation for the immutable AUDJPY R40 source.

PR #651 intentionally does not vendor the AUDJPY research lineage.  The
chronological replay workflow checks out the exact source commit that produced
R40, verifies that commit, and uses this patcher only to serialize causal
geometry that the historical R40 ledger omitted.

The patch changes no trading decision, risk policy, or outcome.  It only adds
signal/entry/stop/target fields and Phase-18 output filenames.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_CODE_GIT_SHA = "a332b077598e070a42b2497b3766d55e731f7dca"
SOURCE_RELATIVE_PATH = (
    "src/qore/infrastructure/trader_lab/"
    "turtle_soup_audjpy_r40_frozen_r39_5y_validation.py"
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

_LEDGER_OLD = '"r40-5y-scaled-trades.jsonl"'
_LEDGER_NEW = '"phase18-audjpy-r40-geometry-trades.jsonl"'
_REPORT_OLD = '"r40-5y-validation-report.json"'
_REPORT_NEW = '"phase18-audjpy-r40-geometry-report.json"'


def _replace_exactly_once(source: str, old: str, new: str, *, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{label} source drift: expected one match, got {count}")
    return source.replace(old, new, 1)


def patch_r40_source(source: str) -> str:
    """Add serialization-only geometry to the exact historical R40 program."""
    patched = _replace_exactly_once(
        source,
        _DATACLASS_OLD,
        _DATACLASS_NEW,
        label="ScaledTrade dataclass",
    )
    patched = _replace_exactly_once(
        patched,
        _CONSTRUCTOR_OLD,
        _CONSTRUCTOR_NEW,
        label="ScaledTrade constructor",
    )
    patched = _replace_exactly_once(
        patched,
        _LEDGER_OLD,
        _LEDGER_NEW,
        label="ledger filename",
    )
    patched = _replace_exactly_once(
        patched,
        _REPORT_OLD,
        _REPORT_NEW,
        label="report filename",
    )
    return patched


def patch_file(source_path: Path, output_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    patched = patch_r40_source(source)
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
