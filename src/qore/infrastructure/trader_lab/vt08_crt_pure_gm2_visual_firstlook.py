"""Neutral, outcome-blind H4/M15 visual review pages for VT08 CRT PURE.

First-look reviewers get raw pre-decision OHLC only, NOT the research heuristic
direction, mechanical Model #1 outputs, cognitive ABSTAIN/WAIT, or sealed C3.
Reviewers must independently identify a source-justified CRT reference and
submit a separate adjudication before reading other diagnostic artifacts.
No sizing, trade entry, PnL, scoring, or certification authority.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_gm3_real_case_safety import (
    audit_blind_case,
)

SCHEMA = "qore.vt08.crt_pure.gm2_neutral_visual_firstlook.v1"
SOURCE_SCHEMA = "qore.vt08.crt_pure.gm2_real_blinded_casebook.v1"


def _text(value: object) -> str:
    return html.escape(str(value), quote=True)


def _plot(candles: list[dict[str, Any]], *, label: str) -> str:
    """Two-dimensional, no-lookahead SVG; no numerical signal estimation."""
    if not candles:
        raise ValueError("empty visual price prefix")
    prices = [
        int(bar[key])
        for bar in candles
        for key in ("open_relative", "high_relative", "low_relative", "close_relative")
    ]
    lo, hi = min(prices), max(prices)
    if lo == hi:
        hi += 1
    width, height, top, bottom = 640, 228, 24, 198
    count = len(candles)

    def yy(p: int) -> float:
        return top + (hi - p) * (bottom - top) / (hi - lo)

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{_text(label)}">',
        '<rect width="640" height="228" fill="#fafafa"/>',
        f'<text x="8" y="15" font-size="11">{_text(label)}</text>',
        f'<text x="6" y="36" font-size="10">{hi}</text>',
        f'<text x="6" y="197" font-size="10">{lo}</text>',
    ]
    for i, bar in enumerate(candles):
        x = 44 + (i + 0.5) * 578 / count
        o, high, low, close = (
            bar["open_relative"],
            bar["high_relative"],
            bar["low_relative"],
            bar["close_relative"],
        )
        parts.append(
            f'<line x1="{x:.2f}" y1="{yy(high):.2f}" '
            f'x2="{x:.2f}" y2="{yy(low):.2f}" stroke="#424242" '
            'stroke-width="1.4"/>'
        )
        y1, y2 = sorted((yy(o), yy(close)))
        candle_width = min(18.0, 290.0 / count)
        parts.append(
            f'<rect x="{x-candle_width/2:.2f}" y="{y1:.2f}" '
            f'width="{candle_width:.2f}" height="{max(1.0,y2-y1):.2f}" '
            'fill="#444" stroke="#222" stroke-width="0.8"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="218" text-anchor="middle" '
            f'font-size="8">{i+1}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _table(bars: list[dict[str, Any]], tag: str) -> str:
    rows = []
    for i, bar in enumerate(bars):
        cols = [
            f"{tag}{i+1}",
            bar["opened_at_utc"],
            bar["open_relative"],
            bar["high_relative"],
            bar["low_relative"],
            bar["close_relative"],
        ]
        rows.append("<tr>" + "".join(f"<td>{_text(v)}</td>" for v in cols) + "</tr>")
    return (
        "<table><thead><tr><th>Bar</th><th>Opened UTC</th><th>O</th>"
        "<th>H</th><th>L</th><th>C</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def build_visual_firstlook(
    blind_cases: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Return standalone HTML and audit manifest, NEVER adjudication results."""
    if not blind_cases:
        raise ValueError("no real blind cases")
    used: set[str] = set()
    sections: list[str] = []
    markets: set[str] = set()
    for case in blind_cases:
        if case.get("schema") != SOURCE_SCHEMA:
            raise ValueError("unexpected real case schema")
        audit_blind_case(case)  # fail closed on future or unauthorized payloads
        case_id = case["case_id"]
        if not isinstance(case_id, str) or not case_id or case_id in used:
            raise ValueError("empty or repeated case ID")
        used.add(case_id)
        markets.add(case["market"])
        h4 = [case["parent_H4_C1_ohlc"], case["parent_H4_C2_ohlc"]]
        m15 = case["M15_observed_prefix_through_C2"]
        digest = hashlib.sha256(
            json.dumps(
                {"case_id": case_id, "h4": h4, "m15": m15},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        sections.append(
            '<section class="review-case">'
            f'<h2>Case {_text(case_id)} — {_text(case["market"])}</h2>'
            f'<p><strong>Decision clock (UTC):</strong> '
            f'{_text(case["decision_clock_utc"])}. '
            '<strong>Only CLOSED earlier candles displayed.</strong></p>'
            '<h3>Previous complete H4 candles (raw — not certified CRT)</h3>'
            + _plot(h4, label="Closed H4 C1/C2 raw candles")
            + _table(h4, "H4-")
            + '<h3>Observed M15 prefix (no future beyond decision clock)</h3>'
            + _plot(m15, label="M15 fully closed observed candles")
            + _table(m15, "M15-")
            + '<h3>Blank independent review prompts</h3><p>'
            'Identify any source-authenticated old CRTH/CRTL using the ORIGINAL '
            'author source and exact locator. The two H4 raw candles shown '
            'may contain no valid old CRT levels; older unseen H4 references '
            'may be required. State BOTH qualifying and disqualifying '
            'reasons, the alternate thesis, time validity, destination and '
            'whether the correct response is conceptual EXECUTE, WAIT or ABSTAIN. '
            'No software suggestion or future outcome is provided.</p>'
            '<p class="review-lines">Primary-source URL, timestamp/frames: '
            '____________________________<br>'
            'Valid reference/none/unknown and reason: '
            '____________________________<br>'
            'Competing references / unanswered rules: '
            '____________________________<br>'
            'Decision and why, invalidation, expiry, DOL: '
            '____________________________</p>'
            f'<p class="digest">SHA256 of case H4/M15 prices+ID: {_text(digest)}</p>'
            '</section>'
        )
    style = (
        "body{font:14px system-ui,Arial,sans-serif;max-width:920px;"
        "margin:24px auto;line-height:1.45;color:#222}"
        "section{border-top:2px solid #888;padding:18px 0;break-after:page}"
        "table{border-collapse:collapse;font:11px monospace;width:100%;"
        "margin-bottom:15px}th,td{padding:3px;border:1px solid #bbb}"
        "svg{max-width:100%;height:auto;border:1px solid #ddd}"
        ".digest{font:10px monospace;overflow-wrap:anywhere}"
        ".review-lines{line-height:2.2}"
        "@media print{body{margin:0 12mm}section{page-break-after:always}}"
    )
    first = (
        '<!doctype html><html lang="en"><head><meta charset="UTF-8">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
        '<title>VT08 CRT PURE — source-neutral blind first-look</title>'
        f'<style>{style}</style></head><body>'
        '<h1>VT08 CRT PURE — FIRST-LOOK source audit</h1>'
        '<p>Only historical closed H4 and M15 OHLC are displayed. '
        'Price integers are relative provider coordinates, not quotes. '
        'The parent direction, engineering source selection, geometric '
        'hypotheses, cognitive outputs, C3 future witness, PnL, sizing '
        'and broker trades are intentionally excluded. '
        'This packet is NOT a source-approved model, not fresh OOS, '
        'not a certificate and not a trade authorization.</p>'
        '<p>The original RomeoTPT lesson with exact visual evidence '
        'must be read independently. Sign and freeze reviewer findings '
        'before opening diagnostic or sealed-future packets.</p>'
    )
    document = first + "".join(sections) + "</body></html>"
    if "C3_M5_reveal_after_independent_review" in document:
        raise ValueError("future-sealed field leaked to visual document")
    manifest = {
        "schema": SCHEMA,
        "cases": len(blind_cases),
        "markets": sorted(markets),
        "case_ids_in_review_order": [c["case_id"] for c in blind_cases],
        "firstlook_html_sha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
        "upstream_methodology_review_completed": False,
        "reveal_or_cognitive_output_included": False,
        "contains_profit_or_sizing": False,
        "adjudication_authored": False,
        "source_reference_authenticated": False,
        "G_M2_passed": False,
        "G_M5_certificate_issued": False,
        "not_fresh_holdout": True,
    }
    return document, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("blind_casebook", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    blind = [
        json.loads(line) for line in args.blind_casebook.read_text().splitlines()
        if line.strip()
    ]
    html_text, manifest = build_visual_firstlook(blind)
    args.destination.mkdir(parents=True, exist_ok=True)
    (args.destination / "gm2-methodologist-firstlook.html").write_text(
        html_text, encoding="utf-8"
    )
    (args.destination / "gm2-firstlook-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
