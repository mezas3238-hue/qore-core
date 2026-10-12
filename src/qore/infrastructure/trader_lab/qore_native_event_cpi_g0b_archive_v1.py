"""BLS CPI G0B: verify archive-index and archived release HEADER, no prices.

Never load CIBO M1, CPI numeric values, consensus, outcomes, or broker quotes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

IDENTITY = "QORE_NATIVE_EVENT_CPI_G0B_RELEASE_HEADER_ONLY_V1"
PREREG_SHA = "c8092917ea27afbeee2d6b4cb4df1d2cbe245d1a"
CALENDAR_RUN = 38189483643
CALENDAR_ARTIFACT = 11720651765
INDEX_URL = "https://www.bls.gov/bls/news-release/cpi.htm"
BASE = "https://www.bls.gov"
FILE_NAME = re.compile(r"^/news\.release/archives/cpi_(\d{2})(\d{2})(20\d{2})\.htm$", re.I)
MONTHS = ("January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December")
MONTH_RE = "|".join(MONTHS)
ANCHOR = re.compile(rf"\b(?P<month>{MONTH_RE})\s+(?P<year>20\d{{2}})\s+Consumer Price Index\b", re.I)
EMBARGO = re.compile(
    rf"embargoed\s+until\s+8:30\s+a\.?\s*m\.?\s*\((?:ET|EDT|EST)\)\s*"
    rf"(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?"
    rf"(?P<month>{MONTH_RE})\s+(?P<day>\d{{1,2}}),?\s+(?P<year>20\d{{2}})",
    re.I,
)
REFERENCE = re.compile(
    rf"CONSUMER\s+PRICE\s+INDEX\s*[-–]\s*(?P<month>{MONTH_RE})\s+(?P<year>20\d{{2}})",
    re.I,
)


@dataclass(frozen=True, slots=True)
class ArchivedEntry:
    release_day: str
    ref_month: str
    ref_year: int
    url: str


class ArchiveAnchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.href: str | None = None
        self.words: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.words = []

    def handle_data(self, data: str) -> None:
        if self.href is not None:
            self.words.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href is not None:
            self.anchors.append((self.href, " ".join(" ".join(self.words).split())))
            self.href = None
            self.words = []


class HeaderText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.words: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.words.append(data)

    def normalized(self) -> str:
        return " ".join(unescape(" ".join(self.words)).split())


def parse_index(text: str) -> dict[str, ArchivedEntry]:
    p = ArchiveAnchors()
    p.feed(text)
    indexed: dict[str, ArchivedEntry] = {}
    for href, label in p.anchors:
        absolute = urljoin(INDEX_URL, href)
        parsed = urlparse(absolute)
        if parsed.scheme != "https" or parsed.hostname != "www.bls.gov":
            continue
        fname = FILE_NAME.fullmatch(parsed.path)
        label_match = ANCHOR.search(label)
        if not (fname and label_match) or parsed.query or parsed.fragment:
            continue
        mon, day, year = (int(x) for x in fname.groups())
        actual_day = date(year, mon, day).isoformat()
        label_month = label_match.group("month").title()
        label_year = int(label_match.group("year"))
        item = ArchivedEntry(actual_day, label_month, label_year, absolute)
        old = indexed.get(actual_day)
        if old is not None and old != item:
            raise ValueError("contradictory indexed release identity for a date")
        indexed[actual_day] = item
    return indexed


def decode_archived_header(raw: bytes) -> str:
    """Decode legacy BLS releases without destroying CP1252 en-dash separators."""
    for charset in ("utf-8", "cp1252"):
        try:
            return raw.decode(charset, errors="strict")
        except UnicodeError:
            continue
    return raw.decode("latin-1").replace("\x96", "\u2013")


def parse_header(text: str) -> tuple[str | None, str | None, int | None]:
    h = HeaderText()
    h.feed(text)
    beginning = h.normalized()[:24000]
    embargo = EMBARGO.search(beginning)
    reference = REFERENCE.search(beginning)
    date_ = None
    if embargo:
        date_ = date(
            int(embargo.group("year")), MONTHS.index(embargo.group("month").title()) + 1,
            int(embargo.group("day"))
        ).isoformat()
    return (
        date_,
        reference.group("month").title() if reference else None,
        int(reference.group("year")) if reference else None,
    )


def fetch_official(url: str, *, limit: int = 350_000) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "www.bls.gov":
        raise ValueError("non-BLS URL cannot be fetched")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; QORE-CPI-SourceResearch/1.0)",
                 "Accept": "text/html"},
    )
    with urllib.request.urlopen(req, timeout=16) as response:
        if response.status != 200:
            raise ValueError("non-200 archived BLS response")
        target = response.geturl()
        if target != url and target != url.rstrip("/"):
            raise ValueError("archive BLS redirect changed destination")
        # CPI reports include long data tables; only the bounded release
        # HEADER PREFIX is relevant to this source-only embargo audit.
        # Do not reject long official reports merely because of their size.
        raw = response.read(limit)
    return raw


def read_locked_calendar(root: Path) -> list[dict[str, Any]]:
    source = root / "cpi-bls-g0-dated-events.json"
    witness = root / "OUTPUT_SHA256SUMS.txt"
    if not source.is_file() or not witness.is_file():
        raise ValueError("original G0 BLS metadata artifact/witness missing")
    expected: dict[str, str] = {}
    for line in witness.read_text().splitlines():
        columns = line.split()
        if len(columns) == 2 and len(columns[0]) == 64:
            expected[columns[1]] = columns[0]
    if expected.get(source.name) != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError("G0 official calendar JSON SHA256 mismatch")
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) != 119:
        raise ValueError("calendar G0 event population changed")
    prior: str | None = None
    used = set()
    for row in data:
        day = row["ny_date"]
        if day in used or (prior is not None and day <= prior):
            raise ValueError("G0 CPI event ordering or uniqueness violated")
        used.add(day)
        prior = day
        if (row["local_ny_clock"] != "08:30"
                or row["provenance"] != "BLS_CALENDAR_ROW_RETROSPECTIVE_NOT_ASOF"
                or not row["source_calendar_url"].startswith("https://www.bls.gov/schedule/")):
            raise ValueError("G0 release provenance or clock altered")
    return data


def inspect_entry(calendar_event: dict[str, Any], indexed: ArchivedEntry | None
                  ) -> dict[str, Any]:
    row = {
        "date_ny": calendar_event["ny_date"],
        "reference_month": calendar_event["ref_month"],
        "reference_year": calendar_event["ref_year"],
        "calendar_class": "BLS_CALENDAR_ROW_RETROSPECTIVE_NOT_ASOF",
        "archive_index_match": False,
        "archive_header_confirmed": False,
        "source_ohlc_read": False,
        "source_consensus_read": False,
    }
    if indexed is None:
        row["status"] = "ARCHIVE_INDEX_NO_MATCH"
        return row
    row["archived_release_url"] = indexed.url
    if (indexed.ref_month != calendar_event["ref_month"]
            or indexed.ref_year != calendar_event["ref_year"]):
        row["status"] = "ARCHIVE_CONTRADICTION"
        row["difference"] = "REFERENCE_MONTH_OR_YEAR_MISMATCH"
        return row
    row["archive_index_match"] = True
    row["status"] = "ARCHIVE_INDEX_LINK_ONLY"
    try:
        raw = fetch_official(indexed.url)
        row["archived_header_prefix_sha256"] = hashlib.sha256(raw).hexdigest()
        heading_date, ref_month, ref_year = parse_header(decode_archived_header(raw))
        if heading_date is None or ref_month is None or ref_year is None:
            row["status"] = "ARCHIVE_HEADER_UNPARSEABLE"
        elif (heading_date != calendar_event["ny_date"]
              or ref_month != calendar_event["ref_month"]
              or ref_year != calendar_event["ref_year"]):
            row["status"] = "ARCHIVE_CONTRADICTION"
            row["difference"] = "ARCHIVE_HEADER_DATE_REFERENCE_OR_CLOCK_MISMATCH"
            row["header_embargo_date"] = heading_date
            row["header_reference_month"] = ref_month
            row["header_reference_year"] = ref_year
        else:
            row["status"] = "ARCHIVED_RELEASE_HEADER_MATCH"
            row["archive_header_confirmed"] = True
    except (ValueError, urllib.error.URLError, UnicodeError, TimeoutError) as err:
        row["status"] = "ARCHIVE_HEADER_UNAVAILABLE"
        row["failure_class"] = type(err).__name__
    return row


def run(source: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    calendar = read_locked_calendar(source)
    source_hash: str | None = None
    error_class: str | None = None
    try:
        index_bytes = fetch_official(INDEX_URL, limit=500_000)
        source_hash = hashlib.sha256(index_bytes).hexdigest()
        indexed = parse_index(index_bytes.decode("utf-8", errors="strict"))
        if len(indexed) < 100:
            raise ValueError("BLS CPI archive index unexpectedly sparse")
        rows = [None] * len(calendar)
        # Limit outbound concurrency and request burst. No retries when blocked;
        # missing rows are not guessed from dates or prices.
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            for ix, event in enumerate(calendar):
                futures[executor.submit(
                    inspect_entry, event, indexed.get(event["ny_date"])
                )] = ix
                time.sleep(0.12)
            for future in as_completed(futures):
                rows[futures[future]] = future.result()
    except (ValueError, urllib.error.URLError, UnicodeError, TimeoutError) as err:
        indexed = {}
        error_class = type(err).__name__
        rows = [{
            "date_ny": event["ny_date"],
            "reference_month": event["ref_month"],
            "reference_year": event["ref_year"],
            "status": "SOURCE_BLS_ARCHIVE_BLOCKED",
            "archive_index_match": False,
            "archive_header_confirmed": False,
            "source_ohlc_read": False,
            "source_consensus_read": False,
        } for event in calendar]
    counts = dict(Counter(row["status"] for row in rows))
    contrad = counts.get("ARCHIVE_CONTRADICTION", 0)
    matched = counts.get("ARCHIVED_RELEASE_HEADER_MATCH", 0)
    if error_class is not None:
        status = "SOURCE_BLS_ARCHIVE_BLOCKED"
    elif contrad:
        status = "ARCHIVE_DATE_CONTRADICTION"
    elif matched == len(calendar):
        status = "ARCHIVE_HEADER_ALL_MATCH"
    else:
        status = "ARCHIVE_HEADER_PARTIAL"
    result = {
        "identity": IDENTITY,
        "prereg_sha": PREREG_SHA,
        "status": status,
        "locked_calendar_run": CALENDAR_RUN,
        "locked_calendar_artifact": CALENDAR_ARTIFACT,
        "calendar_events": len(calendar),
        "archive_index_links_count": len(indexed),
        "archive_index_source_sha256": source_hash,
        "source_error_class": error_class,
        "archive_status_counts": counts,
        "archived_headers_confirmed": matched,
        "archive_no_numeric_CPI_values_recorded": True,
        "calendar_archive_not_proven_asof": True,
        "consensus_asof_verified": False,
        "event_spread_cost_verified": False,
        "economic_G1_authorized": False,
        "price_or_forward_return_read": False,
        "no_mt5_no_vps_no_live_no_traders": True,
    }
    (output / "g0b-release-header-audit.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    (output / "g0b-release-header-by-date.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("g0_bls_artifact", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    result = run(args.g0_bls_artifact, args.out)
    print(json.dumps({
        "status": result["status"],
        "events": result["calendar_events"],
        "header_matches": result["archived_headers_confirmed"],
        "archive_status_counts": result["archive_status_counts"],
        "no_price_or_return": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
