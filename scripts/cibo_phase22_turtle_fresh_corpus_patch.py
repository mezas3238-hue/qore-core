"""Remove only historical corpus-length guards from proven Turtle replay code.

Phase18 parity already proves the exact frozen methodologies. Phase22 V2 has a
six-month source corpus, so the old 10-year retained-bar assertion is an
infrastructure precondition rather than a methodology rule. This patch refuses
any source that does not match one exact known assertion.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CorpusPatch:
    trader_id: str
    symbol: str
    historical_bars: int

    @property
    def old(self) -> str:
        return (
            f'    if evidence.symbol != "{self.symbol}" or '
            f'int(provenance["retained_bars"]) != {self.historical_bars}:'
        )

    @property
    def new(self) -> str:
        return f'    if evidence.symbol != "{self.symbol}":'


PATCHES = {
    "R38_GBPJPY": CorpusPatch("R38_GBPJPY", "GBPJPY", 745478),
    "R43_GBPUSD": CorpusPatch("R43_GBPUSD", "GBPUSD", 745274),
    "R38_EURUSD": CorpusPatch("R38_EURUSD", "EURUSD", 745458),
    "R34_XAUUSD": CorpusPatch("R34_XAUUSD", "XAUUSD", 707716),
    "R42_AUDJPY": CorpusPatch("R42_AUDJPY", "AUDJPY", 745468),
}


def patch_source(source: str, *, trader_id: str) -> tuple[str, dict[str, object]]:
    rule = PATCHES[trader_id]
    count = source.count(rule.old)
    if count != 1:
        raise ValueError(
            f"{trader_id} corpus guard drift: expected one match, got {count}"
        )
    patched = source.replace(rule.old, rule.new, 1)
    before = sha256(source.encode("utf-8")).hexdigest()
    after = sha256(patched.encode("utf-8")).hexdigest()
    if patched.count(rule.new) != 1:
        raise ValueError(f"{trader_id} symbol guard patch failed")
    report = {
        "schema": "qore.cibo.phase22.turtle-fresh-corpus-patch.v1",
        "trader_id": trader_id,
        "symbol": rule.symbol,
        "removed_precondition": (
            f"historical retained_bars == {rule.historical_bars}"
        ),
        "retained_precondition": f"symbol == {rule.symbol}",
        "methodology_parameters_changed": False,
        "entry_logic_changed": False,
        "stop_logic_changed": False,
        "target_logic_changed": False,
        "memory_logic_changed": False,
        "management_logic_changed": False,
        "source_sha256": f"sha256:{before}",
        "patched_sha256": f"sha256:{after}",
        "fresh_outcomes_executed": False,
        "productive_authority": False,
    }
    return patched, report


def patch_file(
    source_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    trader_id: str,
) -> None:
    source = source_path.read_text(encoding="utf-8")
    patched, report = patch_source(source, trader_id=trader_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(patched, encoding="utf-8")
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trader", choices=tuple(PATCHES), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    patch_file(
        args.source,
        args.output,
        args.report,
        trader_id=args.trader,
    )


if __name__ == "__main__":
    main()
