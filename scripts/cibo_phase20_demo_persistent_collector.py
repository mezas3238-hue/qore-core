"""Persistent launcher for the CIBO Phase20D cTrader DEMO collector.

This wrapper intentionally refuses CI/ephemeral execution. It launches the
resident DEMO runtime only from a persistent host after the exact Owner-bound
activation receipt has been validated against the current Git SHA.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from qore.infrastructure.cibo_phase20_demo_execution_activation import (  # type: ignore[import-untyped]
    load_phase20_demo_execution_activation,
)

_RUNTIME_KIND = "PERSISTENT_CTRADER_DEMO_PHASE20D"
_RUNTIME_FILE = "scripts/qore_ctrader_demo_free_runtime.py"


def _git_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--activation",
        type=Path,
        default=Path("var/ctrader_demo_free/demo-runtime.json"),
    )
    args = parser.parse_args()

    if os.environ.get("CI", "").strip().lower() == "true":
        raise RuntimeError(
            "Phase20D execution collector refuses ephemeral CI runtime"
        )
    if os.environ.get("QORE_CIBO_PHASE20D_RUNTIME_KIND", "") != _RUNTIME_KIND:
        raise RuntimeError(
            "persistent Phase20D DEMO runtime kind is not explicitly confirmed"
        )

    root = Path(__file__).resolve().parents[1]
    activation = (
        args.activation
        if args.activation.is_absolute()
        else root / args.activation
    )
    sha = _git_sha(root)
    load_phase20_demo_execution_activation(
        activation,
        expected_git_sha=sha,
    )

    binding = root / "var" / "ctrader_demo_free" / "binding.json"
    if not binding.is_file():
        raise RuntimeError(
            "Phase20D persistent collector requires armed DEMO binding"
        )
    state_dir = root / "var" / "ctrader_demo_signal_runtime"
    state_dir.mkdir(parents=True, exist_ok=True)

    runtime = root / _RUNTIME_FILE
    if not runtime.is_file():
        raise RuntimeError("cTrader DEMO runtime entrypoint is missing")

    os.execv(
        sys.executable,
        [
            sys.executable,
            str(runtime),
            "--mode",
            "demo",
            "--activation",
            str(activation),
        ],
    )


if __name__ == "__main__":
    main()
