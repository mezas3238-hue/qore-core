"""Generate a canonical Owner-bound activation receipt for Phase20D DEMO.

The receipt generator has no broker access. It only emits a local activation
file when the explicit Owner authorization token is present in the environment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

_TOKEN = "CIBO_PHASE20D_DEMO_EXECUTION_AUTHORIZED"
_SCHEMA = "qore.cibo.phase20d.demo_execution_activation.v1"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def _git_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if _SHA1_RE.fullmatch(value) is None:
        raise RuntimeError("collector Git SHA must be lowercase 40-hex")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    supplied = os.environ.get(
        "QORE_CIBO_PHASE20D_OWNER_AUTHORIZATION",
        "",
    )
    if supplied != _TOKEN:
        raise RuntimeError(
            "explicit CIBO Phase20D DEMO Owner authorization is required"
        )

    root = Path(__file__).resolve().parents[1]
    payload = {
        "schema": _SCHEMA,
        "authorization_token": _TOKEN,
        "authorized_by_owner": True,
        "environment": "demo",
        "collector_git_sha": _git_sha(root),
        "authorized_at": datetime.now(UTC).isoformat(),
        "fundednext_allowed": False,
        "live_allowed": False,
        "real_capital_allowed": False,
        "merge_allowed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "DEMO_EXECUTION_ACTIVATION_RECEIPT_WRITTEN",
                "collector_git_sha": payload["collector_git_sha"],
                "output": str(args.output),
                "broker_mutation_performed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
