"""Immutable discovered source corpus for VT08 CRT PURE.

This registry freezes source identity and provenance only.  It does not promote any
trading rule into Strategy Identity.  Rule promotion remains governed by the separate
source-adjudication registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_identity import CrtPureSourceTier


class CrtPureSourceArtifactStatus(StrEnum):
    VERIFIED_PRIMARY_LINK = "VERIFIED_PRIMARY_LINK"
    VERIFIED_CORROBORATION_MIRROR = "VERIFIED_CORROBORATION_MIRROR"
    PENDING_PRIMARY_LOCATOR = "PENDING_PRIMARY_LOCATOR"
    PENDING_CORROBORATION_LOCATOR = "PENDING_CORROBORATION_LOCATOR"


@dataclass(frozen=True, slots=True)
class CrtPureSourceArtifact:
    artifact_id: str
    title: str
    source_name: str
    source_tier: CrtPureSourceTier
    status: CrtPureSourceArtifactStatus
    canonical_url: str | None
    provenance_url: str | None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.artifact_id or not self.title or not self.source_name:
            raise ValueError("CRT source artifact identity fields must be non-empty")
        if self.status is CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK:
            if self.source_tier not in {
                CrtPureSourceTier.LEVEL_A,
                CrtPureSourceTier.LEVEL_A_PLUS,
            }:
                raise ValueError("verified primary link must be LEVEL_A or LEVEL_A_PLUS")
            if not self.canonical_url or not self.provenance_url:
                raise ValueError("verified primary link requires canonical/provenance URLs")
        if self.status is CrtPureSourceArtifactStatus.VERIFIED_CORROBORATION_MIRROR:
            if self.source_tier is not CrtPureSourceTier.LEVEL_B:
                raise ValueError("corroboration mirror must be LEVEL_B")
            if not self.canonical_url or not self.provenance_url:
                raise ValueError("corroboration mirror requires URL provenance")
        if self.status in {
            CrtPureSourceArtifactStatus.PENDING_PRIMARY_LOCATOR,
            CrtPureSourceArtifactStatus.PENDING_CORROBORATION_LOCATOR,
        }:
            if self.canonical_url is not None:
                raise ValueError("pending locator cannot claim canonical URL")


CRT_PURE_PRIMARY_SOURCE_CORPUS: tuple[CrtPureSourceArtifact, ...] = (
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_FOUNDATION_VIDEO",
        title="What is CRT? Why do all other trading strategies suck?",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.PENDING_PRIMARY_LOCATOR,
        canonical_url=None,
        provenance_url=None,
        notes="Known official RomeoTPT video; direct primary locator still to be bound in corpus.",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP01",
        title="CRT secrets ep.1: One CRT model for life",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/T7udbrWlARI",
        provenance_url="https://t.me/s/officialRomeotpt?before=6184",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP02",
        title="CRT secrets 2: The kiss of death - CRT and turtle soup",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/FYr6J5pIDB4",
        provenance_url="https://t.me/s/officialRomeotpt?before=6214",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_KOD_PDF",
        title="KOD.pdf",
        source_name="RomeoTPT author-distributed documents",
        source_tier=CrtPureSourceTier.LEVEL_A_PLUS,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://t.me/s/officialRomeotpt?before=6214",
        provenance_url="https://t.me/s/officialRomeotpt?before=6214",
        notes="Author-distributed file attached alongside CRT Secrets episode 2.",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP03",
        title="CRT secrets ep.3: The journey",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/_oiwm8_id8c",
        provenance_url="https://t.me/s/officialRomeotpt/6221",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP04",
        title="CRT secrets ep.4: Candle anatomy",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/n2GF8kCpgVg",
        provenance_url="https://t.me/s/officialRomeotpt?after=6244",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP05",
        title="CRT secrets ep.5: Key level",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/p8UYOgVn1-g",
        provenance_url="https://t.me/s/officialRomeotpt?after=6244",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP06",
        title="CRT secrets ep.6: SMT",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.PENDING_PRIMARY_LOCATOR,
        canonical_url=None,
        provenance_url=None,
        notes="Episode existence identified; direct primary locator remains to be bound.",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP07",
        title="CRT secrets ep.7: Candle 3",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/h7NCST2wPw8",
        provenance_url="https://t.me/s/officialRomeotpt?before=6384",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP08",
        title="CRT secrets ep.8: When does CRT fail?",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/-mWYppebugo",
        provenance_url="https://t.me/s/officialRomeotpt/6455",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP09",
        title="CRT secrets ep.9: Connecting the dots",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/2sxdsgcIeYA",
        provenance_url="https://t.me/s/officialRomeotpt?before=6541",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRT_SECRETS_EP10",
        title="CRT secrets ep.10: A clean close",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.PENDING_PRIMARY_LOCATOR,
        canonical_url=None,
        provenance_url=None,
        notes="Episode existence identified; direct primary locator remains to be bound.",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRTOLOGY_EP01",
        title="CRTology episode 1: SS",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/4DZWbCzEvhM",
        provenance_url="https://t.me/s/officialRomeotpt?before=6920",
    ),
    CrtPureSourceArtifact(
        artifact_id="ROMEO_CRTOLOGY_EP02",
        title="CRTology episode 2: The Lens",
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        status=CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
        canonical_url="https://youtu.be/wkSiy27a8ps",
        provenance_url="https://t.me/s/officialRomeotpt",
    ),
)


CRT_PURE_CORROBORATION_CORPUS: tuple[CrtPureSourceArtifact, ...] = (
    CrtPureSourceArtifact(
        artifact_id="SPECULATORFL_CRT_THREAD_2024_04_28",
        title="CRT: Candle Ranges Theory — detailed thread",
        source_name="SpeculatorFL",
        source_tier=CrtPureSourceTier.LEVEL_B,
        status=CrtPureSourceArtifactStatus.VERIFIED_CORROBORATION_MIRROR,
        canonical_url="https://threadreaderapp.com/thread/1784493604473618604",
        provenance_url="https://threadreaderapp.com/thread/1784493604473618604",
        notes="Mirror of the approved secondary-source X thread; never methodology authority.",
    ),
    CrtPureSourceArtifact(
        artifact_id="TRADERFLAMESEN_CRT_THREAD_2024_05_13",
        title="Candle Range Theory: Choose the best CRT Candle",
        source_name="TraderFlameseN",
        source_tier=CrtPureSourceTier.LEVEL_B,
        status=CrtPureSourceArtifactStatus.VERIFIED_CORROBORATION_MIRROR,
        canonical_url="https://threadreaderapp.com/thread/1790141530461622525",
        provenance_url="https://threadreaderapp.com/thread/1790141530461622525",
        notes="Mirror of the approved secondary-source X thread; credits RomeoTPT.",
    ),
    CrtPureSourceArtifact(
        artifact_id="TTRADES_CRT_CORROBORATION",
        title="TTrades CRT corroboration corpus",
        source_name="TTrades",
        source_tier=CrtPureSourceTier.LEVEL_B,
        status=CrtPureSourceArtifactStatus.PENDING_CORROBORATION_LOCATOR,
        canonical_url=None,
        provenance_url=None,
        notes="Approved Level B source. Exact CRT-specific locator remains to be bound before use.",
    ),
)


def verified_primary_artifacts() -> tuple[CrtPureSourceArtifact, ...]:
    return tuple(
        artifact
        for artifact in CRT_PURE_PRIMARY_SOURCE_CORPUS
        if artifact.status is CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK
    )


def pending_primary_locators() -> tuple[CrtPureSourceArtifact, ...]:
    return tuple(
        artifact
        for artifact in CRT_PURE_PRIMARY_SOURCE_CORPUS
        if artifact.status is CrtPureSourceArtifactStatus.PENDING_PRIMARY_LOCATOR
    )


def verified_corroboration_artifacts() -> tuple[CrtPureSourceArtifact, ...]:
    return tuple(
        artifact
        for artifact in CRT_PURE_CORROBORATION_CORPUS
        if artifact.status
        is CrtPureSourceArtifactStatus.VERIFIED_CORROBORATION_MIRROR
    )


def pending_corroboration_locators() -> tuple[CrtPureSourceArtifact, ...]:
    return tuple(
        artifact
        for artifact in CRT_PURE_CORROBORATION_CORPUS
        if artifact.status
        is CrtPureSourceArtifactStatus.PENDING_CORROBORATION_LOCATOR
    )
