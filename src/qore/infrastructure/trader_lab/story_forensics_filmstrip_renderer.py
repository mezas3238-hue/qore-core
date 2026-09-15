"""Static multi-frame filmstrip renderer for Trader Story Forensics.

The filmstrip is a visualization of an already-certified QORE story payload. It
uses TradingView Lightweight Charts only to render QORE-owned bars and markers.
No market data is requested from TradingView or any other network data source.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_story_forensics import (
    FirstCohortStoryForensicsError,
    validate_story_episode_contract,
)

_STORY_SCHEMA = "qore.trader_lab.first_cohort_story_forensics.v1"
_RENDERER = "tradingview-lightweight-charts"
_RENDERER_VERSION = "5.2.1"
_LIBRARY_URL = "https://cdn.jsdelivr.net/npm/lightweight-charts@5.2.1/+esm"


class StoryForensicsFilmstripError(FirstCohortStoryForensicsError):
    """Raised when a filmstrip cannot preserve the forensic evidence contract."""

    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise StoryForensicsFilmstripError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise StoryForensicsFilmstripError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise StoryForensicsFilmstripError(f"{field_name} must be a non-empty string")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise StoryForensicsFilmstripError(f"{field_name} must be bool")
    return value


def _safe_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _validate(payload: dict[str, object]) -> None:
    if _text(payload.get("schema"), field_name="schema") != _STORY_SCHEMA:
        raise StoryForensicsFilmstripError("filmstrip requires story-forensics v1")
    if not _strict_bool(payload.get("research_only"), field_name="research_only"):
        raise StoryForensicsFilmstripError("filmstrip requires research-only evidence")
    if _strict_bool(payload.get("execution_authority"), field_name="execution_authority"):
        raise StoryForensicsFilmstripError("filmstrip refuses execution-authoritative evidence")
    contract = _object(payload.get("renderer_contract"), field_name="renderer contract")
    if _text(contract.get("default_renderer"), field_name="renderer") != _RENDERER:
        raise StoryForensicsFilmstripError("unexpected renderer")
    if _text(contract.get("renderer_version"), field_name="renderer version") != _RENDERER_VERSION:
        raise StoryForensicsFilmstripError("renderer version must be pinned")
    if _text(contract.get("market_data_source"), field_name="market data source") != (
        "qore-retained-evidence"
    ):
        raise StoryForensicsFilmstripError("filmstrip data must come from QORE evidence")
    if _strict_bool(
        contract.get("tradingview_is_evidence_source"),
        field_name="TradingView evidence flag",
    ):
        raise StoryForensicsFilmstripError("TradingView cannot be an evidence source")
    if _strict_bool(
        contract.get("tradingview_has_execution_authority"),
        field_name="TradingView authority flag",
    ):
        raise StoryForensicsFilmstripError("TradingView cannot have execution authority")


def _episode(payload: dict[str, object], episode_id: str) -> dict[str, object]:
    matches: list[dict[str, object]] = []
    for item in _array(payload.get("episodes"), field_name="episodes"):
        row = _object(item, field_name="episode")
        if _text(row.get("episode_id"), field_name="episode id") == episode_id:
            matches.append(row)
    if len(matches) != 1:
        raise StoryForensicsFilmstripError("episode_id must resolve exactly once")
    validate_story_episode_contract(matches[0])
    chart = _object(matches[0].get("chart"), field_name="episode chart")
    if _text(chart.get("source_of_truth"), field_name="source of truth") != (
        "qore-retained-evidence"
    ):
        raise StoryForensicsFilmstripError("episode chart is not QORE-evidence-bound")
    if not _array(chart.get("bars"), field_name="bars"):
        raise StoryForensicsFilmstripError("filmstrip requires bars")
    if not _array(chart.get("frame_sequence"), field_name="frames"):
        raise StoryForensicsFilmstripError("filmstrip requires replay frames")
    return matches[0]


def render_filmstrip_html(payload: dict[str, object], *, episode_id: str) -> str:
    """Render every chronological story frame and allow one composite PNG export."""
    _validate(payload)
    episode = _episode(payload, episode_id)
    trader = _text(episode.get("trader_code"), field_name="trader code").upper()
    symbol = _text(episode.get("symbol"), field_name="symbol")
    title = html.escape(f"{trader} · {symbol} · forensic filmstrip")
    embedded = _safe_json(episode)
    library_url = _safe_json(_LIBRARY_URL)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{title}</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
body {{ margin: 0; background: #0f1117; color: #e7e9ee; }}
main {{ max-width: 1500px; margin: 0 auto; padding: 18px; }}
h1 {{ margin: 0; font-size: 20px; }}
.lead {{ margin: 5px 0 14px; color: #aeb4c0; font-size: 13px; }}
.actions {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }}
button {{
  border: 1px solid #343946;
  border-radius: 8px;
  background: #1a1e27;
  color: #f4f6fa;
  padding: 9px 13px;
  cursor: pointer;
  font: inherit;
}}
button:disabled {{ opacity: .45; cursor: default; }}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 12px;
}}
.frame {{ border: 1px solid #2b303b; border-radius: 10px; overflow: hidden; background: #151922; }}
.frame-head {{ padding: 9px 11px; display: flex; justify-content: space-between; gap: 8px; }}
.frame-title {{ font-weight: 650; font-size: 13px; }}
.frame-time {{ color: #9ca3b2; font-size: 11px; overflow-wrap: anywhere; }}
.chart {{ height: 330px; background: #11141a; }}
.frame p {{ margin: 0; padding: 9px 11px 11px; color: #cbd1dc; font-size: 12px; line-height: 1.4; }}
footer {{ margin-top: 14px; color: #949ba9; font-size: 12px; }}
footer a {{ color: #a9c8ff; }}
@media (max-width: 500px) {{
  .grid {{ grid-template-columns: 1fr; }}
  .chart {{ height: 280px; }}
}}
</style>
</head>
<body>
<main>
<h1>{title}</h1>
<p class=\"lead\">
Every panel is the same QORE episode frozen at one chronological evidence time.
</p>
<div class=\"actions\">
<button id=\"saveFilmstrip\" type=\"button\" disabled>Save filmstrip PNG</button>
</div>
<div id=\"frames\" class=\"grid\"></div>
<footer>
QORE retained evidence is authoritative; TradingView is visualization only.
Charts powered by
<a href=\"https://www.tradingview.com/\" rel=\"noreferrer\">TradingView Lightweight Charts™</a>.
</footer>
</main>
<script id=\"qore-episode\" type=\"application/json\">{embedded}</script>
<script type=\"module\">
const LIBRARY_URL = {library_url};
const episode = JSON.parse(document.getElementById('qore-episode').textContent);
const chartData = episode.chart;
const decision = episode.decision_time;
const post = episode.post_outcome;
const host = document.getElementById('frames');
const saveFilmstrip = document.getElementById('saveFilmstrip');
const priority = {{ context: 0, signal: 1, entry: 2, mfe: 3, mae: 3, exit: 4, post_exit: 5 }};
const frames = [...chartData.frame_sequence].sort((a, b) =>
  a.visible_through_unix - b.visible_through_unix ||
  (priority[a.stage] ?? 99) - (priority[b.stage] ?? 99) ||
  a.stage.localeCompare(b.stage)
);
const rendered = [];

function narrativeFor(stage) {{
  if (stage === 'context' || stage === 'signal' || stage === 'entry') {{
    return decision.narrative;
  }}
  if (stage === 'mfe') {{
    return `Peak favorable excursion: ${{post.close_path_mfe_r}}R on closed-bar evidence.`;
  }}
  if (stage === 'mae') {{
    return `Peak adverse excursion: ${{post.close_path_mae_r}}R on closed-bar evidence.`;
  }}
  return post.narrative;
}}

function marker(row) {{
  const isLong = decision.side === 'long';
  const rules = {{
    signal: {{ position: 'aboveBar', shape: 'circle', color: '#f2c94c' }},
    entry: {{
      position: isLong ? 'belowBar' : 'aboveBar',
      shape: isLong ? 'arrowUp' : 'arrowDown',
      color: '#56ccf2',
    }},
    mfe: {{ position: 'aboveBar', shape: 'circle', color: '#6fcf97' }},
    mae: {{ position: 'belowBar', shape: 'circle', color: '#eb5757' }},
    exit: {{ position: 'aboveBar', shape: 'square', color: '#bb6bd9' }},
  }};
  return {{ time: row.time, text: row.label, size: 1, ...(rules[row.kind] || rules.signal) }};
}}

function addLines(series) {{
  const rules = {{
    entry: {{ color: '#56ccf2', title: 'ENTRY' }},
    stop_loss: {{ color: '#eb5757', title: 'SL' }},
    take_profit: {{ color: '#6fcf97', title: 'TP' }},
  }};
  for (const row of chartData.price_lines) {{
    const rule = rules[row.kind];
    if (!rule) continue;
    series.createPriceLine({{
      price: Number(row.price),
      color: rule.color,
      lineWidth: 2,
      lineStyle: 2,
      axisLabelVisible: true,
      title: rule.title,
    }});
  }}
}}

function card(frame) {{
  const article = document.createElement('article');
  article.className = 'frame';
  const head = document.createElement('div');
  head.className = 'frame-head';
  const stage = document.createElement('div');
  stage.className = 'frame-title';
  stage.textContent = frame.stage;
  const at = document.createElement('div');
  at.className = 'frame-time';
  at.textContent = frame.visible_through;
  head.append(stage, at);
  const chartNode = document.createElement('div');
  chartNode.className = 'chart';
  const text = document.createElement('p');
  text.textContent = narrativeFor(frame.stage);
  article.append(head, chartNode, text);
  host.append(article);
  return chartNode;
}}

async function saveComposite() {{
  if (!rendered.length) return;
  const captures = rendered.map(row => row.chart.takeScreenshot(true, false));
  const width = Math.max(...captures.map(canvas => canvas.width));
  const labelHeight = 34;
  const height = captures.reduce((sum, canvas) => sum + canvas.height + labelHeight, 0);
  const output = document.createElement('canvas');
  output.width = width;
  output.height = height;
  const context = output.getContext('2d');
  if (!context) return;
  context.fillStyle = '#0f1117';
  context.fillRect(0, 0, width, height);
  let y = 0;
  for (let index = 0; index < captures.length; index += 1) {{
    context.fillStyle = '#e7e9ee';
    context.font = '16px sans-serif';
    const frame = rendered[index].frame;
    context.fillText(`${{index + 1}}. ${{frame.stage}} · ${{frame.visible_through}}`, 10, y + 23);
    y += labelHeight;
    context.drawImage(captures[index], 0, y);
    y += captures[index].height;
  }}
  const link = document.createElement('a');
  link.download = `${{episode.episode_id}}-filmstrip.png`;
  link.href = output.toDataURL('image/png');
  link.click();
}}

try {{
  const {{ createChart, CandlestickSeries, createSeriesMarkers }} = await import(LIBRARY_URL);
  for (const frame of frames) {{
    const node = card(frame);
    const chart = createChart(node, {{
      autoSize: true,
      layout: {{
        background: {{ type: 'solid', color: '#11141a' }},
        textColor: '#cbd1dc',
        attributionLogo: true,
      }},
      grid: {{
        vertLines: {{ color: '#232833' }},
        horzLines: {{ color: '#232833' }},
      }},
      timeScale: {{ timeVisible: true, secondsVisible: false }},
    }});
    const series = chart.addSeries(CandlestickSeries, {{ priceLineVisible: false }});
    const bars = chartData.bars.filter(row => row.time <= frame.visible_through_unix);
    const marks = chartData.markers
      .filter(row => row.time <= frame.visible_through_unix)
      .map(marker);
    series.setData(bars);
    addLines(series);
    createSeriesMarkers(series, marks, {{ autoScale: true }});
    chart.timeScale().fitContent();
    rendered.push({{ frame, chart }});
  }}
  saveFilmstrip.disabled = rendered.length === 0;
  saveFilmstrip.addEventListener('click', saveComposite);
}} catch (error) {{
  const detail = error instanceof Error ? error.message : String(error);
  host.textContent = `Filmstrip initialization failed: ${{detail}}`;
  saveFilmstrip.disabled = true;
}}
</script>
</body>
</html>
"""


def render_filmstrip_file(
    story_path: Path,
    *,
    episode_id: str,
    output_path: Path,
) -> Path:
    """Write a browser-openable chronological filmstrip for one exact episode."""
    try:
        decoded: object = json.loads(story_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StoryForensicsFilmstripError("cannot read story pack") from error
    payload = _object(decoded, field_name="story pack")
    rendered = render_filmstrip_html(payload, episode_id=episode_id)
    try:
        output_path.write_text(rendered, encoding="utf-8")
    except OSError as error:
        raise StoryForensicsFilmstripError("cannot write filmstrip") from error
    return output_path


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3:
        print(
            "usage: python -m qore.infrastructure.trader_lab.story_forensics_filmstrip_renderer "
            "STORY_JSON EPISODE_ID OUTPUT_HTML",
            file=sys.stderr,
        )
        return 2
    try:
        render_filmstrip_file(
            Path(arguments[0]),
            episode_id=arguments[1],
            output_path=Path(arguments[2]),
        )
    except FirstCohortStoryForensicsError as error:
        print(f"filmstrip renderer failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
