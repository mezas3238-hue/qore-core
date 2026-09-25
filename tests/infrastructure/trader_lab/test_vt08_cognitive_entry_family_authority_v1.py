import pytest

from qore.infrastructure.trader_lab.vt08_cognitive_entry_family_authority_v1 import (
    EntryFamilyMachineStatus,
    authority_for,
    require_historical_fill_authority,
)
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import VT08EntryFamily


def test_only_positional_is_machine_complete_in_current_line() -> None:
    positional = authority_for(VT08EntryFamily.POSITIONAL_ENTRY)
    assert positional.status is EntryFamilyMachineStatus.MACHINE_COMPLETE_CURRENT_LINE
    assert positional.historical_fill_authorized is True

    for family in VT08EntryFamily:
        if family is VT08EntryFamily.POSITIONAL_ENTRY:
            continue
        authority = authority_for(family)
        assert authority.status is EntryFamilyMachineStatus.SOURCE_IDENTITY_ONLY
        assert authority.historical_fill_authorized is False
        with pytest.raises(ValueError, match="no frozen historical fill contract"):
            require_historical_fill_authority(family)
