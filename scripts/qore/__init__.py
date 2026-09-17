"""Bind operational scripts to the QORE source tree beside this scripts directory."""
from pathlib import Path

__version__ = "0.1.0"
__path__ = [str(Path(__file__).resolve().parents[2] / "src" / "qore")]
