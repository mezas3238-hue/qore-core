"""Durable CAS store for CE2I portfolio allocation reservations."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import RLock

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
    PortfolioAllocationReservation,
    PortfolioAllocationReservationState,
)

_SCHEMA = "CIBO_CE2I_PORTFOLIO_ALLOCATION_LEDGER_V1"


class DurablePortfolioAllocationError(CiboCapitalManagementError):
    """Durable portfolio allocation state cannot be trusted safely."""


@dataclass(frozen=True, slots=True)
class VersionedPortfolioAllocationLedger:
    generation: int
    ledger: PortfolioAllocationLedger

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurablePortfolioAllocationError(
                "generation must be non-negative int"
            )
        if not isinstance(self.ledger, PortfolioAllocationLedger):
            raise DurablePortfolioAllocationError(
                "ledger must be PortfolioAllocationLedger"
            )


class DurablePortfolioAllocationStore:
    """Atomic snapshot store with generation CAS and writer lock."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise DurablePortfolioAllocationError(
                "path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(
            f".{path.name}.writer-lock"
        )
        self._lock = RLock()

    def load(self) -> VersionedPortfolioAllocationLedger | None:
        with self._lock:
            if not self._path.exists():
                return None
            return self._load_existing_unlocked()

    def initialize(
        self,
        ledger: PortfolioAllocationLedger,
    ) -> VersionedPortfolioAllocationLedger:
        if not isinstance(ledger, PortfolioAllocationLedger):
            raise DurablePortfolioAllocationError(
                "ledger must be PortfolioAllocationLedger"
            )
        with self._lock:
            self._acquire_writer_lock()
            try:
                if self._path.exists():
                    raise DurablePortfolioAllocationError(
                        "portfolio allocation store already initialized"
                    )
                version = VersionedPortfolioAllocationLedger(
                    generation=1,
                    ledger=ledger,
                )
                self._write_unlocked(version)
                return version
            finally:
                self._release_writer_lock()

    def store(
        self,
        ledger: PortfolioAllocationLedger,
        *,
        expected_generation: int,
    ) -> VersionedPortfolioAllocationLedger:
        if not isinstance(ledger, PortfolioAllocationLedger):
            raise DurablePortfolioAllocationError(
                "ledger must be PortfolioAllocationLedger"
            )
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 1
        ):
            raise DurablePortfolioAllocationError(
                "expected_generation must be positive int"
            )
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_existing_unlocked()
                if current.generation != expected_generation:
                    raise DurablePortfolioAllocationError(
                        "stale portfolio allocation generation"
                    )
                next_version = VersionedPortfolioAllocationLedger(
                    generation=current.generation + 1,
                    ledger=ledger,
                )
                self._write_unlocked(next_version)
                return next_version
            finally:
                self._release_writer_lock()

    def _load_existing_unlocked(self) -> VersionedPortfolioAllocationLedger:
        if not self._path.exists():
            raise DurablePortfolioAllocationError(
                "portfolio allocation store is not initialized"
            )
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurablePortfolioAllocationError(
                "durable portfolio allocation store is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise DurablePortfolioAllocationError(
                "durable portfolio allocation schema mismatch"
            )
        generation = raw.get("generation")
        if (
            not isinstance(generation, int)
            or isinstance(generation, bool)
            or generation < 1
        ):
            raise DurablePortfolioAllocationError(
                "durable portfolio allocation generation invalid"
            )
        try:
            ledger = _ledger_from_json(raw)
        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
        ) as error:
            raise DurablePortfolioAllocationError(
                "durable portfolio allocation payload invalid"
            ) from error
        return VersionedPortfolioAllocationLedger(
            generation=generation,
            ledger=ledger,
        )

    def _write_unlocked(
        self,
        version: VersionedPortfolioAllocationLedger,
    ) -> None:
        payload = _ledger_to_json(version.ledger)
        payload["schema"] = _SCHEMA
        payload["generation"] = version.generation
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError as error:
            raise DurablePortfolioAllocationError(
                "durable portfolio allocation write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurablePortfolioAllocationError(
                "portfolio allocation writer lock already held"
            ) from error
        except OSError as error:
            raise DurablePortfolioAllocationError(
                "portfolio allocation writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurablePortfolioAllocationError(
                "portfolio allocation writer lock release failed"
            ) from error


def _ledger_to_json(
    ledger: PortfolioAllocationLedger,
) -> dict[str, object]:
    return {
        "total_stop_risk_capacity_usd": format(
            ledger.total_stop_risk_capacity_usd,
            "f",
        ),
        "total_margin_capacity_usd": format(
            ledger.total_margin_capacity_usd,
            "f",
        ),
        "concentration_limit_by_group": [
            [group, format(limit, "f")]
            for group, limit in ledger.concentration_limit_by_group
        ],
        "reservations": [
            {
                "signal_fingerprint": item.signal_fingerprint,
                "trader_id": item.trader_id.value,
                "qore_symbol": item.qore_symbol,
                "stop_risk_usd": format(item.stop_risk_usd, "f"),
                "margin_usd": format(item.margin_usd, "f"),
                "concentration_group": item.concentration_group,
                "concentration_risk_usd": format(
                    item.concentration_risk_usd,
                    "f",
                ),
                "state": item.state.value,
            }
            for item in ledger.reservations
        ],
    }


def _ledger_from_json(raw: dict[str, object]) -> PortfolioAllocationLedger:
    groups_raw = raw["concentration_limit_by_group"]
    reservations_raw = raw["reservations"]
    if not isinstance(groups_raw, list) or not isinstance(
        reservations_raw,
        list,
    ):
        raise TypeError("allocation groups/reservations must be lists")

    groups: list[tuple[str, Decimal]] = []
    for row in groups_raw:
        if not isinstance(row, list) or len(row) != 2:
            raise TypeError("allocation group row invalid")
        groups.append((str(row[0]), Decimal(str(row[1]))))

    reservations: list[PortfolioAllocationReservation] = []
    for row in reservations_raw:
        if not isinstance(row, dict):
            raise TypeError("allocation reservation row invalid")
        reservations.append(
            PortfolioAllocationReservation(
                signal_fingerprint=str(row["signal_fingerprint"]),
                trader_id=TraderLineage(str(row["trader_id"])),
                qore_symbol=str(row["qore_symbol"]),
                stop_risk_usd=Decimal(str(row["stop_risk_usd"])),
                margin_usd=Decimal(str(row["margin_usd"])),
                concentration_group=str(row["concentration_group"]),
                concentration_risk_usd=Decimal(
                    str(row["concentration_risk_usd"])
                ),
                state=PortfolioAllocationReservationState(
                    str(row["state"])
                ),
            )
        )

    return PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal(
            str(raw["total_stop_risk_capacity_usd"])
        ),
        total_margin_capacity_usd=Decimal(
            str(raw["total_margin_capacity_usd"])
        ),
        concentration_limit_by_group=tuple(groups),
        reservations=tuple(reservations),
    )
