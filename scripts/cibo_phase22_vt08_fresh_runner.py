"""CLI wrapper for the frozen VT08 Phase22 V2 fresh-lane runner."""
# ruff: noqa: I001

from qore.infrastructure.cibo_phase22_vt08_fresh_runner import run_cli


if __name__ == "__main__":
    raise SystemExit(run_cli())
