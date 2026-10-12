"""QORE NATIVE EVENT CPI G0 — official BLS calendar and CIBO M1 timestamps ONLY.

Never read native M1 OHLC or compute forward returns, trading signals, or PnL.
Calendar as retrieved TODAY does not establish contemporaneous schedule knowledge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

IDENTITY = "QORE_NATIVE_EVENT_MACRO_CPI_G0_SOURCE_ONLY_V1"
PREREG_SHA = "621c55ffc21d31305fe0f623cb9822b7b7b2b476"
BLS_URL = "https://www.bls.gov/schedule/{year}/"
YEARS = tuple(range(2016, 2027))
NY = ZoneInfo("America/New_York")
START = datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
CIBO_RUN = 35548099334
CIBO_ARTIFACT = 10618862813
CIBO_PRODUCER_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
CIBO_IDENTITY = "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"
DATE_PATTERN = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?P<day>\d{1,2}),?\s+(?P<year>20\d{2})\b", re.I,
)
CPI_PATTERN = re.compile(
    r"\bConsumer Price Index\s+for\s+"
    r"(?P<ref_month>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?P<ref_year>20\d{2})\b", re.I,
)
CLOCK_PATTERN = re.compile(r"\b(?P<hour>0?[0-9]|1[0-2]):(?P<minute>[0-5][0-9])\s*AM\b", re.I)
COVER_WINDOWS = {
    "PRE10": tuple(range(8 * 60 + 20, 8 * 60 + 30)),
    "PRINT0": (8 * 60 + 30,),
    "AFTER30": tuple(range(8 * 60 + 31, 9 * 60 + 1)),
    "AFTER60": tuple(range(9 * 60 + 1, 9 * 60 + 31)),
}
SELECTED = {x for slot in COVER_WINDOWS.values() for x in slot}


@dataclass(frozen=True, slots=True)
class CPIEvent:
    ny_date: str
    ref_month: str
    ref_year: int
    local_ny_clock: str
    timestamp_utc: str
    source_calendar_url: str
    provenance: str = "BLS_CALENDAR_ROW_RETROSPECTIVE_NOT_ASOF"


class Rows(HTMLParser):
    """Table row and td contents, robust to nested BLS anchors/bold markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_row = False
        self.in_cell = False
        self.cell_text: list[str] = []
        self.cells: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.in_row, self.in_cell, self.cells = True, False, []
        elif self.in_row and tag in ("td", "th"):
            self.in_cell, self.cell_text = True, []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.in_row and tag in ("td", "th") and self.in_cell:
            self.cells.append(" ".join(" ".join(self.cell_text).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.cells:
                self.rows.append(self.cells[:])
            self.in_row, self.in_cell, self.cells = False, False, []


def parse_bls_year(html: str, year: int) -> list[CPIEvent]:
    if year not in YEARS:
        raise ValueError("BLS calendar year outside prereg")
    reader = Rows()
    reader.feed(html)
    values: dict[str, CPIEvent] = {}
    for cells in reader.rows:
        row = " ".join(cells)
        if "Consumer Price Index for" not in row:
            continue
        found_date = DATE_PATTERN.search(row)
        ref = CPI_PATTERN.search(row)
        clock = CLOCK_PATTERN.search(row)
        if not (found_date and ref and clock):
            raise ValueError("BLS CPI schedule row lacks date/reference month/time")
        chosen_day = date(
            int(found_date.group("year")),
            datetime.strptime(found_date.group("month"), "%B").month,
            int(found_date.group("day")),
        )
        if chosen_day.year != year:
            raise ValueError("BLS CPI schedule row publication year mismatch")
        hh = int(clock.group("hour"))
        mm = int(clock.group("minute"))
        if (hh, mm) != (8, 30):
            raise ValueError("BLS CPI event clock not 08:30 Eastern: needs new prereg")
        ref_month = datetime.strptime(ref.group("ref_month"), "%B").strftime("%B")
        ref_year = int(ref.group("ref_year"))
        local = datetime(chosen_day.year, chosen_day.month, chosen_day.day,
                         hh, mm, tzinfo=NY)
        event = CPIEvent(
            ny_date=chosen_day.isoformat(), ref_month=ref_month,
            ref_year=ref_year, local_ny_clock="08:30",
            timestamp_utc=local.astimezone(UTC).isoformat(),
            source_calendar_url=BLS_URL.format(year=year),
        )
        key = f"{event.ref_year}-{event.ref_month}"
        if key in values:
            if values[key] != event:
                raise ValueError("contradictory BLS rows for same CPI reference month")
        else:
            values[key] = event
    return sorted(values.values(), key=lambda x: x.ny_date)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for buf in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def calendar_inventory(output: Path) -> dict[str, Any]:
    """Only BLS.gov, no mirroring/estimated months; failures are explicit."""
    output.mkdir(parents=True, exist_ok=True)
    source_rows: list[dict[str, Any]] = []
    all_events: list[CPIEvent] = []
    for year in YEARS:
        url = BLS_URL.format(year=year)
        result: dict[str, Any] = {"year": year, "url": url}
        try:
            request = urllib.request.Request(
                url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; QORE-ResearchSourceCensus/1.0)",
                    "Accept": "text/html",
                }
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                code = response.status
                final_url = response.geturl()
                if final_url != url and final_url != url.rstrip("/"):
                    raise ValueError("BLS calendar redirect destination changed")
                if code != 200:
                    raise ValueError("BLS calendar non-200 response")
                html_data = response.read(2_500_001)
            if len(html_data) > 2_500_000:
                raise ValueError("BLS calendar response too large")
            raw_sha = hashlib.sha256(html_data).hexdigest()
            yearly = parse_bls_year(html_data.decode("utf-8", errors="strict"), year)
            if not 1 <= len(yearly) <= 13:
                raise ValueError("BLS calendar abnormal CPI row count")
            result.update(status="CALENDAR_ROWS_EXTRACTED", event_count=len(yearly),
                          source_html_sha256=raw_sha, http_status=code)
            all_events.extend(yearly)
        except (urllib.error.URLError, TimeoutError, UnicodeError, ValueError) as error:
            # Type/error code only; never publish full exception (which can leak
            # networking internals). No fallback to non-BLS estimated dates.
            result.update(status="SOURCE_UNAVAILABLE_OR_UNPARSEABLE",
                          failure_class=type(error).__name__)
        source_rows.append(result)
    counts = Counter(x.ny_date for x in all_events)
    if any(count != 1 for count in counts.values()):
        raise ValueError("duplicate CPI NY publication dates in BLS row inventory")
    observed = [
        e for e in all_events
        if START <= datetime.fromisoformat(e.timestamp_utc) < END
    ]
    good = sum(row["status"] == "CALENDAR_ROWS_EXTRACTED" for row in source_rows)
    status = ("BLS_CALENDAR_ROWS_VERIFIED" if good == len(YEARS)
              else "SOURCE_BLS_UNAVAILABLE")
    result = {
        "identity": IDENTITY, "prereg_sha": PREREG_SHA, "status": status,
        "source_provider": "www.bls.gov",
        "source_rows_by_year": source_rows, "source_years_pass": good,
        "source_years_expected": len(YEARS), "all_publication_rows_count": len(all_events),
        "source_rows_within_cibo_date_range": len(observed),
        "calendar_retrieved_today_not_asof_proof": True,
        "archived_release_individual_confirmation_pending": True,
        "consensus_forecast_asof_verified": False,
        "event_broker_cost_verified": False,
        "no_price_or_economic_outcome_read": True,
        "retrospective_bls_schedule_only": True,
        "cpi_october_2025_archive_cancellation_aware": True,
        "no_live_no_mt5_no_trades": True,
    }
    (output / "cpi-bls-g0-source-report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "cpi-bls-g0-dated-events.json").write_text(
        json.dumps([asdict(e) for e in observed], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def cibo_source(root: Path) -> dict[str, Any]:
    path = root / "m1-clone-manifest.json"
    witness = root / "MANIFEST_SHA256SUMS.txt"
    if not path.is_file() or not witness.is_file():
        raise ValueError("CIBO native M1 manifest/witness missing")
    token = witness.read_text().strip().split(maxsplit=1)
    if len(token) != 2 or token[0] != sha256(path) or token[1] != path.name:
        raise ValueError("CIBO native M1 manifest SHA mismatch")
    m = json.loads(path.read_text())
    required = {
        "identity": CIBO_IDENTITY,
        "canonical_symbol": "NAS100",
        "provider_symbol": "USTEC",
        "provider_native_m1": True,
        "synthetic_m1": False,
        "interpolated_m1": False,
        "read_only": True,
        "live_authorized": False,
        "production_authorized": False,
        "contradictory_m1": 0,
        "target_start": START.isoformat(),
        "target_end_exclusive": END.isoformat(),
    }
    for key, expected in required.items():
        if type(m.get(key)) is not type(expected) or m[key] != expected:
            raise ValueError("CIBO source identity mismatch: " + key)
    if [entry.get("partition") for entry in m["partitions"]] != [
        str(x) for x in YEARS
    ] or len(m["partitions"]) != len(YEARS):
        raise ValueError("annual partition sequence differs from archive contract")
    return m


def cibo_timestamp_coverage(
    root: Path, events_path: Path, output: Path
) -> dict[str, Any]:
    """Only time/identity are read from native bar rows. Never OHLC."""
    events_data = json.loads(events_path.read_text())
    if not isinstance(events_data, list) or not events_data:
        raise ValueError("CPI inventory missing; fail closed")
    events = [CPIEvent(**row) for row in events_data]
    for event in events:
        instant = datetime.fromisoformat(event.timestamp_utc)
        local = instant.astimezone(NY)
        if (event.local_ny_clock != "08:30"
                or local.hour != 8 or local.minute != 30
                or local.date().isoformat() != event.ny_date
                or not START <= instant < END):
            raise ValueError("BLS source event time outside locked local timezone/range")
    per_event: dict[str, set[int]] = {event.ny_date: set() for event in events}
    manifest = cibo_source(root)
    previous: datetime | None = None
    total = 0
    annual_counts: dict[str, int] = {}
    dates = set(per_event)
    for part in manifest["partitions"]:
        year = part["partition"]
        path = root / "RAW_M1_LEDGER" / f"{year}.jsonl"
        if not path.is_file() or sha256(path) != part.get("raw_sha256"):
            raise ValueError("native M1 yearly SHA256 mismatch: " + year)
        n = 0
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                # Intentionally do not access/open_price/high_price/low_price/close_price.
                if (row.get("schema") != "qore.capitalizer.cibo.raw_m1.v1"
                        or row.get("identity") != CIBO_IDENTITY
                        or row.get("canonical_symbol") != "NAS100"
                        or row.get("provider_symbol") != "USTEC"
                        or row.get("provider_symbol_id") != manifest["provider_symbol_id"]
                        or row.get("digits") != manifest["digits"]):
                    raise ValueError("native M1 raw timestamp provider identity drift")
                at = datetime.fromisoformat(row["opened_at"])
                if at.tzinfo is None or at.utcoffset() is None:
                    raise ValueError("native timestamp missing timezone")
                at = at.astimezone(UTC)
                if (not START <= at < END or str(at.year) != year
                        or at.second != 0 or at.microsecond != 0
                        or row.get("utc_timestamp_in_minutes") != int(at.timestamp() // 60)
                        or (previous is not None and at <= previous)):
                    raise ValueError("CIBO native M1 timestamp/order/identity failed")
                previous = at
                local = at.astimezone(NY)
                if local.date().isoformat() in dates:
                    minute = local.hour * 60 + local.minute
                    if minute in SELECTED:
                        slots = per_event[local.date().isoformat()]
                        if minute in slots:
                            raise ValueError("two native candles for same CPI local minute")
                        slots.add(minute)
                n += 1
        if n != part.get("retained_m1"):
            raise ValueError("native M1 partition bar count mismatch")
        annual_counts[year] = n
        total += n
    if total != manifest.get("retained_m1"):
        raise ValueError("native M1 total provider bar count mismatch")

    witnesses = []
    for event in events:
        seen = per_event[event.ny_date]
        slotcounts = {k: len(seen.intersection(v)) for k, v in COVER_WINDOWS.items()}
        all_present = all(slotcounts[k] == len(v) for k, v in COVER_WINDOWS.items())
        witnesses.append({
            "date_ny": event.ny_date, "source_calendar_url": event.source_calendar_url,
            "reference_month": event.ref_month, "reference_year": event.ref_year,
            "expected_utc_timestamp": event.timestamp_utc,
            "minute_presence_counts": slotcounts,
            "window_all_candles_present": all_present,
            "provider_ohlc_read": False, "provider_bidask_fills_observed": False,
        })
    full = sum(row["window_all_candles_present"] for row in witnesses)
    report = {
        "identity": IDENTITY, "prereg_sha": PREREG_SHA,
        "status": "SOURCE_METADATA_COVERAGE_ONLY" if full else "SOURCE_CPI_M1_NO_FULL_WINDOWS",
        "source_cibo_run": CIBO_RUN, "source_cibo_artifact": CIBO_ARTIFACT,
        "source_cibo_producer_sha": CIBO_PRODUCER_SHA,
        "cibo_manifest_sha256": sha256(root / "m1-clone-manifest.json"),
        "all_11_original_annual_partition_sha256_verified": True,
        "provider_symbol": "USTEC", "source_native_m1_total": total,
        "source_native_m1_by_year": annual_counts,
        "cpi_calendar_events_in_window": len(events),
        "events_with_all_71_minutes": full,
        "events_incomplete_or_no_m1": len(events) - full,
        "all_windows": {k: len(v) for k, v in COVER_WINDOWS.items()},
        "consensus_asof_unverified": True,
        "released_at_exact_time_verified_from_archived_release": False,
        "historical_calendar_asof_unverified": True,
        "event_spreads_and_fills_unverified": True,
        "zero_price_values_consumed": True,
        "zero_economic_outcomes_calculated": True,
        "no_orderflow_inference": True,
        "no_trades_no_vps_no_mt5_no_live": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "cpi-nas100-m1-g0-coverage-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (output / "cpi-nas100-m1-g0-event-presence.json").write_text(
        json.dumps(witnesses, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    cal = sub.add_parser("calendar")
    cal.add_argument("output", type=Path)
    coverage = sub.add_parser("coverage")
    coverage.add_argument("cibo_native_m1_root", type=Path)
    coverage.add_argument("bls_g0_events", type=Path)
    coverage.add_argument("output", type=Path)
    args = p.parse_args()
    if args.mode == "calendar":
        result = calendar_inventory(args.output)
        print(json.dumps({"status": result["status"],
                          "years": result["source_years_pass"],
                          "in_cibo_window": result["source_rows_within_cibo_date_range"],
                          "no_returns": True}, sort_keys=True))
    else:
        result = cibo_timestamp_coverage(
            args.cibo_native_m1_root, args.bls_g0_events, args.output
        )
        print(json.dumps({"status": result["status"],
                          "events": result["cpi_calendar_events_in_window"],
                          "complete_presence": result["events_with_all_71_minutes"],
                          "no_returns": True}, sort_keys=True))


if __name__ == "__main__":
    main()
