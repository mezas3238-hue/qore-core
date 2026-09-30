"""V48 ICT primary-source binding status.

Primary video identities are preserved, but V48 requires exact timestamp-level evidence
before ICT claims can be promoted into the new source-faithful productive grammar.
The older V2 CONTENT_REVIEWED flag is not sufficient for V48 hard-gate authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_ICT_SOURCE_BINDING_STATUS"


class V48ICTBindingState(StrEnum):
    PRIMARY_VIDEO_ID_VERIFIED = "PRIMARY_VIDEO_ID_VERIFIED"
    TIMESTAMP_BINDING_REQUIRED = "TIMESTAMP_BINDING_REQUIRED"


@dataclass(frozen=True, slots=True)
class V48ICTSourceBinding:
    source_id: str
    title: str
    youtube_url: str
    video_state: V48ICTBindingState = V48ICTBindingState.PRIMARY_VIDEO_ID_VERIFIED
    timestamp_state: V48ICTBindingState = V48ICTBindingState.TIMESTAMP_BINDING_REQUIRED
    productive_hard_gate_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.source_id or self.source_id != self.source_id.upper():
            raise ValueError("ICT source_id must be non-empty uppercase")
        if not self.youtube_url.startswith("https://www.youtube.com/watch?v="):
            raise ValueError("ICT V48 source requires primary YouTube URL")
        if self.timestamp_state is V48ICTBindingState.TIMESTAMP_BINDING_REQUIRED:
            if self.productive_hard_gate_authorized:
                raise ValueError("unbound ICT source cannot authorize a V48 hard gate")


SOURCES: tuple[V48ICTSourceBinding, ...] = (
    V48ICTSourceBinding(
        "ICT_2022_MENTORSHIP_EP3",
        "2022 ICT Mentorship Episode 3",
        "https://www.youtube.com/watch?v=nQfHZ2DEJ8c",
    ),
    V48ICTSourceBinding(
        "ICT_2022_MENTORSHIP_EP6",
        "2022 ICT Mentorship Episode 6",
        "https://www.youtube.com/watch?v=Bkt8B3kLATQ",
    ),
    V48ICTSourceBinding(
        "ICT_2022_MENTORSHIP_EP7",
        "2022 ICT Mentorship Episode 7",
        "https://www.youtube.com/watch?v=G8-z91acgG4",
    ),
    V48ICTSourceBinding(
        "ICT_HIGH_PROBABILITY_SCALPING_V1",
        "ICT - Mastering High Probability Scalping Vol. 1 of 3",
        "https://www.youtube.com/watch?v=uE-aaP16nOw",
    ),
)


@dataclass(frozen=True, slots=True)
class V48ICTSourceBindingStatus:
    identity: str = IDENTITY
    sources: tuple[V48ICTSourceBinding, ...] = SOURCES
    old_content_reviewed_flag_sufficient_for_v48_hard_gate: bool = False
    exact_timestamp_binding_required: bool = True
    partial_source_block_blocks_ttrades_reconstruction: bool = False
    fresh_holdout_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 ICT binding identity is frozen")
        if self.old_content_reviewed_flag_sufficient_for_v48_hard_gate:
            raise ValueError("V48 requires stronger timestamp provenance")
        if not self.exact_timestamp_binding_required:
            raise ValueError("V48 ICT source must be timestamp-bound before productive use")
        if self.partial_source_block_blocks_ttrades_reconstruction:
            raise ValueError("ICT timestamp gap must not stop independent TTrades reconstruction")
        if self.fresh_holdout_authorized:
            raise ValueError("ICT binding status grants no Fresh Holdout authority")


V48_ICT_SOURCE_BINDING_STATUS = V48ICTSourceBindingStatus()
