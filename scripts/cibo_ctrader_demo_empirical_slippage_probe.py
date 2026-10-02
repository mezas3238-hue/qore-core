"""Export read-only empirical cTrader DEMO slippage calibration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ctrader_demo_empirical_slippage import (
    collect_ctrader_demo_empirical_slippage,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def build_report() -> dict[str, object]:
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        calibration = collect_ctrader_demo_empirical_slippage(client)
    finally:
        client.close()
    payload = _jsonable(asdict(calibration))
    if not isinstance(payload, dict):
        raise TypeError("empirical slippage payload must be object")
    payload["schema"] = "qore.cibo.ctrader_demo.empirical_slippage.v1"
    payload["status"] = (
        "EMPIRICAL_SLIPPAGE_READY"
        if calibration.empirical_slippage_calibrated
        else "EMPIRICAL_SLIPPAGE_NOT_READY"
    )
    payload["read_only"] = True
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
