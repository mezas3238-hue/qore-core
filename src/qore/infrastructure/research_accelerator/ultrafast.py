"""QORE Research Accelerator ultra-fast research CLI, never an execution authority."""
from __future__ import annotations

import argparse
import csv
import json
import os
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.research_accelerator.core import (
    DatasetManifest,
    ResearchDataError,
    assert_same_venue,
    canonical,
    checked_time,
    digest,
    ingest,
    load_bars,
    load_quotes,
    verify_lake,
)
from qore.infrastructure.research_accelerator.execution import LimitOrder, simulate_ticks
from qore.infrastructure.research_accelerator.experiments import (
    ExperimentSpec,
    read_signals,
    screen,
)
from qore.infrastructure.research_accelerator.memory import file_sha256, read_ledger, register


def _sha(value: str) -> str:
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise ResearchDataError("explicit full commit SHA40 required")
    return value


def _write_once(path: Path, result: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical(result) + b"\n"
    digest_value = sha256(raw).hexdigest()
    with path.open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    path.with_name(path.name + ".sha256").write_text(digest_value + "\n", encoding="ascii")
    return digest_value


def _read_orders(path: Path, tick: Decimal) -> tuple[LimitOrder, ...]:
    required = {
        "event_id", "known_at", "activated_at", "expires_at",
        "forced_exit_at", "side", "limit_ce", "stop_c2", "target_dol",
    }
    orders: list[LimitOrder] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or set(reader.fieldnames) != required:
            raise ResearchDataError("invalid CE/C2/DOL orders schema")
        for row in reader:
            event_id = row["event_id"]
            if not event_id or event_id in seen:
                raise ResearchDataError("duplicate or empty event id")
            seen.add(event_id)
            activated = checked_time(row["activated_at"])
            if checked_time(row["known_at"]) > activated:
                raise ResearchDataError("lookahead: C2/CE/DOL available after activation")
            try:
                extreme = Decimal(row["stop_c2"])
                limit = Decimal(row["limit_ce"])
                target = Decimal(row["target_dol"])
            except InvalidOperation as exc:
                raise ResearchDataError("invalid order price") from exc
            side = row["side"]
            orders.append(LimitOrder(
                event_id=event_id,
                activated_at=activated,
                expires_at=checked_time(row["expires_at"]),
                forced_exit_at=checked_time(row["forced_exit_at"]),
                side=side,
                limit=limit,
                stop=extreme - tick if side == "long" else extreme + tick,
                target=target,
            ))
    if not orders:
        raise ResearchDataError("no orders supplied")
    return tuple(orders)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest="command", required=True)
    q = s.add_parser("ingest")
    for name in ("source", "manifest", "lake"):
        q.add_argument("--" + name, type=Path, required=True)
    q = s.add_parser("verify")
    q.add_argument("--lake", type=Path, required=True)
    q = s.add_parser("memory")
    q.add_argument("--registry", type=Path, required=True)
    q = s.add_parser("screen")
    for name in ("bars", "manifest", "signals", "spec", "out", "registry"):
        q.add_argument("--" + name, type=Path, required=True)
    q.add_argument("--code-sha", type=_sha, required=True)
    q = s.add_parser("execute")
    for name in ("quotes", "quote-manifest", "bar-manifest", "orders", "out", "registry"):
        q.add_argument("--" + name, type=Path, required=True)
    q.add_argument("--code-sha", type=_sha, required=True)
    q.add_argument("--tick-size", type=Decimal, required=True)
    q.add_argument("--slippage-ticks", type=Decimal, default=Decimal("0"))
    q.add_argument("--commission-points", type=Decimal, default=Decimal("0"))
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "ingest":
        print(json.dumps(ingest(args.source, args.manifest, args.lake), sort_keys=True))
        return 0
    if args.command == "verify":
        print(json.dumps({"verified": verify_lake(args.lake)}))
        return 0
    if args.command == "memory":
        print(json.dumps({"verified_records": len(read_ledger(args.registry))}))
        return 0
    if args.command == "screen":
        m = DatasetManifest.read(args.manifest)
        spec = ExperimentSpec.read(args.spec)
        result = screen(spec, load_bars(args.bars, m), read_signals(args.signals))
        config_sha = digest({
            "code_sha": args.code_sha,
            "manifest": m.as_dict(),
            "signals_sha": file_sha256(args.signals),
            "spec_sha": file_sha256(args.spec),
        })
        if any(
            x["payload"]["config_sha256"] == config_sha
            for x in read_ledger(args.registry)
        ):
            raise ResearchDataError("equivalent experiment already exists")
        result["binding_sha256"] = config_sha
        result["code_sha"] = args.code_sha
        artifact = _write_once(args.out, result)
        register(args.registry, {
            "config_sha256": config_sha, "artifact_sha256": artifact,
            "experiment": spec.name, "verdict": "PENDING_INDEPENDENT_REVIEW",
            "economic_status": "DIRECTIONAL_BID_ONLY",
        })
        print(json.dumps({"sha256": artifact, "status": "DIAGNOSTIC_ONLY"}))
        return 0
    if args.command == "execute":
        m = DatasetManifest.read(args.bar_manifest)
        q = DatasetManifest.read(args.quote_manifest)
        assert_same_venue(m, q)
        orders = _read_orders(args.orders, args.tick_size)
        ledger = simulate_ticks(
            load_quotes(args.quotes, q), orders,
            tick_size=args.tick_size, slippage_ticks=args.slippage_ticks,
            commission_per_unit=args.commission_points,
        )
        config_sha = digest({
            "code_sha": args.code_sha, "bar_manifest": m.as_dict(),
            "quote_manifest": q.as_dict(),
            "orders_sha": file_sha256(args.orders),
            "tick": str(args.tick_size), "slippage": str(args.slippage_ticks),
            "commission_in_price_points_per_side_per_unit": str(args.commission_points),
        })
        if any(
            x["payload"]["config_sha256"] == config_sha
            for x in read_ledger(args.registry)
        ):
            raise ResearchDataError("equivalent execution already exists")
        artifact = _write_once(args.out, {
            "schema": "qore.accelerator.execution.v1",
            "status": "OBSERVED_QUOTES_NOT_BROKER_ACK_OR_USD_PNL",
            "unit": "price_points_per_unit", "binding_sha256": config_sha,
            "code_sha": args.code_sha, "ledger": ledger,
        })
        register(args.registry, {
            "config_sha256": config_sha, "artifact_sha256": artifact,
            "experiment": "quote_side_execution",
            "verdict": "PENDING_BROKER_HOMOLOGATION",
        })
        print(json.dumps({"sha256": artifact, "orders": len(orders)}))
        return 0
    raise ResearchDataError("unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
