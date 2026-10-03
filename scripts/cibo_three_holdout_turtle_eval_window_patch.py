#!/usr/bin/env python3
"""Research-only evaluation-window patcher for frozen Turtle replay programs.

Only EVAL_OPEN/EVAL_CLOSE are changed. Trading logic, memory, entry, stop,
target, risk, filters and execution semantics are untouched.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

_OPEN_RE = re.compile(
    r"^EVAL_OPEN\s*=\s*datetime\([^\n]+\)$",
    re.MULTILINE,
)
_CLOSE_RE = re.compile(
    r"^EVAL_CLOSE\s*=\s*datetime\([^\n]+\)$",
    re.MULTILINE,
)


def _literal(value: datetime) -> str:
    return (
        f"datetime({value.year}, {value.month}, {value.day}, "
        f"{value.hour}, {value.minute}, {value.second}, tzinfo=UTC)"
    )


def patch_window(
    source: str,
    *,
    start_at: datetime,
    end_exclusive_at: datetime,
) -> str:
    if (
        start_at.tzinfo is None
        or start_at.utcoffset() is None
        or end_exclusive_at.tzinfo is None
        or end_exclusive_at.utcoffset() is None
        or end_exclusive_at <= start_at
    ):
        raise ValueError("evaluation window must be aware and ordered")
    opened, n_open = _OPEN_RE.subn(
        f"EVAL_OPEN = {_literal(start_at)}",
        source,
        count=1,
    )
    if n_open != 1:
        raise ValueError(f"expected one EVAL_OPEN assignment, got {n_open}")
    closed, n_close = _CLOSE_RE.subn(
        f"EVAL_CLOSE = {_literal(end_exclusive_at)}",
        opened,
        count=1,
    )
    if n_close != 1:
        raise ValueError(f"expected one EVAL_CLOSE assignment, got {n_close}")
    return closed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start-at", required=True)
    parser.add_argument("--end-exclusive-at", required=True)
    args = parser.parse_args()

    start_at = datetime.fromisoformat(args.start_at)
    end_at = datetime.fromisoformat(args.end_exclusive_at)
    patched = patch_window(
        args.source.read_text(encoding="utf-8"),
        start_at=start_at,
        end_exclusive_at=end_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(patched, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
