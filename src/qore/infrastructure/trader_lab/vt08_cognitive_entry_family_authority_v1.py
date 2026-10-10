"""Research authority boundary for VT08 entry families in Cognitive Expansion.

The source kernel names six entry families, but naming a family is not equivalent
to having an executable historical fill contract. This module prevents delayed
CISD/Protected-Swing shapes from being silently converted into fills.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qore.infrastructure.traders.vt08_source_kernel_r3_2 import VT08EntryFamily


class EntryFamilyMachineStatus(StrEnum):
    MACHINE_COMPLETE_CURRENT_LINE = "machine-complete-current-line"
    SOURCE_IDENTITY_ONLY = "source-identity-only"


@dataclass(frozen=True, slots=True)
class EntryFamilyAuthority:
    family: VT08EntryFamily
    status: EntryFamilyMachineStatus
    historical_fill_authorized: bool
    note: str


AUTHORITIES: Final = (
    EntryFamilyAuthority(
        family=VT08EntryFamily.POSITIONAL_ENTRY,
        status=EntryFamilyMachineStatus.MACHINE_COMPLETE_CURRENT_LINE,
        historical_fill_authorized=True,
        note=(
            "B01 research path binds positional entry to the new H4 open; "
            "confirmation must be known no later than the decision/open."
        ),
    ),
    EntryFamilyAuthority(
        family=VT08EntryFamily.REVERSAL_ENTRY,
        status=EntryFamilyMachineStatus.SOURCE_IDENTITY_ONLY,
        historical_fill_authorized=False,
        note="Source family exists; exact executable fill contract is not frozen.",
    ),
    EntryFamilyAuthority(
        family=VT08EntryFamily.CONTINUATION_ENTRY,
        status=EntryFamilyMachineStatus.SOURCE_IDENTITY_ONLY,
        historical_fill_authorized=False,
        note="Source family exists; exact executable fill contract is not frozen.",
    ),
    EntryFamilyAuthority(
        family=VT08EntryFamily.CONFIDENT_ENTRY,
        status=EntryFamilyMachineStatus.SOURCE_IDENTITY_ONLY,
        historical_fill_authorized=False,
        note="Source family exists; exact executable fill contract is not frozen.",
    ),
    EntryFamilyAuthority(
        family=VT08EntryFamily.OPEN_ENTRY,
        status=EntryFamilyMachineStatus.SOURCE_IDENTITY_ONLY,
        historical_fill_authorized=False,
        note="Source family exists; exact executable fill contract is not frozen.",
    ),
    EntryFamilyAuthority(
        family=VT08EntryFamily.POI_CONTINUATION_ENTRY,
        status=EntryFamilyMachineStatus.SOURCE_IDENTITY_ONLY,
        historical_fill_authorized=False,
        note="Source family exists; exact executable fill contract is not frozen.",
    ),
)


def authority_for(family: VT08EntryFamily) -> EntryFamilyAuthority:
    matches = tuple(item for item in AUTHORITIES if item.family is family)
    if len(matches) != 1:
        raise ValueError("VT08 entry-family authority must be unique")
    return matches[0]


def require_historical_fill_authority(family: VT08EntryFamily) -> None:
    authority = authority_for(family)
    if not authority.historical_fill_authorized:
        raise ValueError(
            f"{family.value} has source identity but no frozen historical fill contract"
        )
