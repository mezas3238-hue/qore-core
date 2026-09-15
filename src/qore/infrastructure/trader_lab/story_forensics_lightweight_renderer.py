"""TradingView Lightweight Charts renderer for governed Trader Story Forensics.

The renderer consumes an already-built QORE story pack. It never fetches market
history, changes Trader state, or creates trading authority. The generated HTML
loads only the pinned charting library; every candle, level, marker and narrative
comes from embedded QORE evidence.
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


class StoryForensicsRendererError(FirstCohortStoryForensicsError):
    """Raised when a story pack cannot be rendered without weakening its contract."""

    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise StoryForensicsRendererError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise StoryForensicsRendererError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise StoryForensicsRendererError(f"{field_name} must be a non-empty string")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise StoryForensicsRendererError(f"{field_name} must be bool")
    return value


def _safe_json(value: object) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return (
        serialized.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _validate_story_pack(payload: dict[str, object]) -> None:
    if _text(payload.get("schema"), field_name="story schema") != _STORY_SCHEMA:
        raise StoryForensicsRendererError("renderer requires story-forensics v1")
    if not _strict_bool(payload.get("research_only"), field_name="research_only"):
        raise StoryForensicsRendererError("renderer requires research-only story evidence")
    if _strict_bool(payload.get("execution_authority"), field_name="execution_authority"):
        raise StoryForensicsRendererError("renderer refuses execution-authoritative payloads")
    renderer = _object(payload.get("renderer_contract"), field_name="renderer contract")
    if _text(renderer.get("default_renderer"), field_name="default renderer") != _RENDERER:
        raise StoryForensicsRendererError("unsupported story renderer")
    if _text(renderer.get("renderer_version"), field_name="renderer version") != _RENDERER_VERSION:
        raise StoryForensicsRendererError("renderer version is not pinned to 5.2.1")
    source = _text(renderer.get("market_data_source"), field_name="market data source")
    if source != "qore-retained-evidence":
        raise StoryForensicsRendererError("chart data must originate from QORE evidence")
    if _strict_bool(
        renderer.get("tradingview_is_evidence_source"),
        field_name="TradingView evidence source flag",
    ):
        raise StoryForensicsRendererError("TradingView cannot be an evidence source")
    if _strict_bool(
        renderer.get("tradingview_has_execution_authority"),
        field_name="TradingView authority flag",
    ):
        raise StoryForensicsRendererError("TradingView cannot have execution authority")


def _episode(payload: dict[str, object], *, episode_id: str) -> dict[str, object]:
    matches: list[dict[str, object]] = []
    for item in _array(payload.get("episodes"), field_name="episodes"):
        row = _object(item, field_name="episode")
        if _text(row.get("episode_id"), field_name="episode id") == episode_id:
            matches.append(row)
    if len(matches) != 1:
        raise StoryForensicsRendererError("episode_id must identify exactly one episode")
    episode = matches[0]
    validate_story_episode_contract(episode)
    chart = _object(episode.get("chart"), field_name="episode chart")
    if _text(chart.get("renderer"), field_name="episode renderer") != _RENDERER:
        raise StoryForensicsRendererError("episode renderer contract changed")
    version = _text(chart.get("renderer_version"), field_name="episode renderer version")
    if version != _RENDERER_VERSION:
        raise StoryForensicsRendererError("episode renderer version changed")
    source = _text(chart.get("source_of_truth"), field_name="chart source of truth")
    if source != "qore-retained-evidence":
        raise StoryForensicsRendererError("episode chart is not QORE-evidence-bound")
    if not _array(chart.get("bars"), field_name="chart bars"):
        raise StoryForensicsRendererError("episode chart has no bars")
    if not _array(chart.get("frame_sequence"), field_name="frame sequence"):
        raise StoryForensicsRendererError("episode chart has no replay frames")
    return episode


def render_story_html(payload: dict[str, object], *, episode_id: str) -> str:
    """Render one exact episode into a replayable, screenshot-capable HTML document."""
    _validate_story_pack(payload)
    episode = _episode(payload, episode_id=episode_id)
    embedded = _safe_json(episode)
    trader_code = _text(episode.get("trader_code"), field_name="trader code").upper()
    symbol = _text(episode.get("symbol"), field_name="symbol")
    title = html.escape(f"{trader_code} · {symbol} · {episode_id}")
    library_url = _safe_json(_LIBRARY_URL)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{title}</title>
<style>
:root {{
  color-scheme: dark;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
}}
body {{ margin: 0; background: #0f1117; color: #e7e9ee; }}
main {{ max-width: 1280px; margin: 0 auto; padding: 18px; }}
header {{ display: grid; gap: 6px; margin-bottom: 12px; }}
h1 {{ margin: 0; font-size: 20px; }}
.meta {{ color: #aeb4c0; font-size: 13px; }}
.controls {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 12px 0;
}}
button {{
  border: 1px solid #343946;
  background: #1a1e27;
  color: #f4f6fa;
  padding: 9px 13px;
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
}}
button:disabled {{ opacity: .45; cursor: default; }}
button:focus-visible {{ outline: 2px solid #8ab4ff; outline-offset: 2px; }}
#chart {{
  width: 100%;
  height: 620px;
  border: 1px solid #2b303b;
  border-radius: 10px;
  overflow: hidden;
  background: #11141a;
}}
.grid {{
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, .8fr);
  gap: 12px;
  margin-top: 12px;
}}
.panel {{
  border: 1px solid #2b303b;
  border-radius: 10px;
  padding: 12px;
  background: #151922;
}}
.panel h2 {{ margin: 0 0 8px; font-size: 14px; }}
.panel p {{ margin: 0; line-height: 1.45; color: #d4d8e1; }}
.kv {{
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 10px;
  font-size: 13px;
}}
.kv dt {{ color: #969dab; }}
.kv dd {{ margin: 0; overflow-wrap: anywhere; }}
.badge {{
  display: inline-block;
  padding: 3px 7px;
  border: 1px solid #404757;
  border-radius: 999px;
  font-size: 12px;
}}
footer {{ margin-top: 14px; font-size: 12px; color: #949ba9; }}
footer a {{ color: #a9c8ff; }}
@media (max-width: 760px) {{
  #chart {{ height: 480px; }}
  .grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<main>
<header>
<h1>{title}</h1>
<div class=\"meta\">
<span id=\"stageBadge\" class=\"badge\">Replay</span> ·
<span id=\"frameLabel\">initializing</span>
</div>
</header>
<div class=\"controls\" aria-label=\"Replay controls\">
<button id=\"prevBtn\" type=\"button\">Previous frame</button>
<button id=\"nextBtn\" type=\"button\">Next frame</button>
<button id=\"playBtn\" type=\"button\">Play</button>
<button id=\"fullBtn\" type=\"button\">Full forensic view</button>
<button id=\"shotBtn\" type=\"button\">Save PNG</button>
</div>
<div id=\"chart\" role=\"img\" aria-label=\"QORE forensic candlestick replay\"></div>
<div class=\"grid\">
<section class=\"panel\">
<h2>Current narrative</h2>
<p id=\"narrative\"></p>
</section>
<section class=\"panel\">
<h2>Episode facts</h2>
<dl class=\"kv\" id=\"facts\"></dl>
</section>
</div>
<footer>
QORE retained evidence is the source of truth.
TradingView is visualization only; this page grants no trading authority.
Charts powered by
<a href=\"https://www.tradingview.com/\" rel=\"noreferrer\">
TradingView Lightweight Charts™
</a>.
</footer>
</main>
<script id=\"qore-episode\" type=\"application/json\">{embedded}</script>
<script type=\"module\">
const LIBRARY_URL = {library_url};
const episode = JSON.parse(document.getElementById('qore-episode').textContent);
const chartData = episode.chart;
const decision = episode.decision_time;
const post = episode.post_outcome;
const root = document.getElementById('chart');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const playBtn = document.getElementById('playBtn');
const fullBtn = document.getElementById('fullBtn');
const shotBtn = document.getElementById('shotBtn');
const frameLabel = document.getElementById('frameLabel');
const stageBadge = document.getElementById('stageBadge');
const narrative = document.getElementById('narrative');
const facts = document.getElementById('facts');
const priority = {{
  context: 0,
  signal: 1,
  entry: 2,
  mfe: 3,
  mae: 3,
  exit: 4,
  post_exit: 5,
}};
const frames = [...chartData.frame_sequence].sort((a, b) =>
  a.visible_through_unix - b.visible_through_unix ||
  (priority[a.stage] ?? 99) - (priority[b.stage] ?? 99) ||
  a.stage.localeCompare(b.stage)
);
let frameIndex = 0;
let fullView = false;
let timer = null;
let chart;
let candleSeries;
let markerApi;

function asMarker(row) {{
  const isLong = decision.side === 'long';
  const rules = {{
    signal: {{
      position: 'aboveBar',
      shape: 'circle',
      color: '#f2c94c',
    }},
    entry: {{
      position: isLong ? 'belowBar' : 'aboveBar',
      shape: isLong ? 'arrowUp' : 'arrowDown',
      color: '#56ccf2',
    }},
    mfe: {{ position: 'aboveBar', shape: 'circle', color: '#6fcf97' }},
    mae: {{ position: 'belowBar', shape: 'circle', color: '#eb5757' }},
    exit: {{
      position: isLong ? 'aboveBar' : 'belowBar',
      shape: 'square',
      color: '#bb6bd9',
    }},
  }};
  return {{
    time: row.time,
    text: row.label,
    id: `${{row.kind}}-${{row.time}}`,
    size: 1,
    ...(rules[row.kind] || rules.signal),
  }};
}}

function paintPriceLines() {{
  const lineRules = {{
    entry: {{ color: '#56ccf2', title: 'ENTRY' }},
    stop_loss: {{ color: '#eb5757', title: 'SL' }},
    take_profit: {{ color: '#6fcf97', title: 'TP' }},
  }};
  for (const row of chartData.price_lines) {{
    const rule = lineRules[row.kind];
    if (!rule) continue;
    candleSeries.createPriceLine({{
      price: Number(row.price),
      color: rule.color,
      lineWidth: 2,
      lineStyle: 2,
      axisLabelVisible: true,
      title: rule.title,
    }});
  }}
}}

function visibleThrough() {{
  if (fullView) return Number.POSITIVE_INFINITY;
  return frames[frameIndex].visible_through_unix;
}}

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

function renderFrame() {{
  const through = visibleThrough();
  const visibleBars = chartData.bars.filter(row => row.time <= through);
  const visibleMarkers = chartData.markers
    .filter(row => row.time <= through)
    .map(asMarker);
  candleSeries.setData(visibleBars);
  markerApi.setMarkers(visibleMarkers);
  chart.timeScale().fitContent();
  const frame = fullView
    ? {{ stage: 'forensic-full', visible_through: 'all retained story bars' }}
    : frames[frameIndex];
  frameLabel.textContent = `${{frame.stage}} · ${{frame.visible_through}}`;
  stageBadge.textContent = fullView
    ? 'Oracle / post-outcome permitted'
    : 'Chronological replay';
  narrative.textContent = fullView ? post.narrative : narrativeFor(frame.stage);
  prevBtn.disabled = fullView || frameIndex === 0;
  nextBtn.disabled = fullView || frameIndex === frames.length - 1;
  fullBtn.textContent = fullView ? 'Return to replay' : 'Full forensic view';
}}

function stopPlay() {{
  if (timer !== null) window.clearInterval(timer);
  timer = null;
  playBtn.textContent = 'Play';
}}

function togglePlay() {{
  if (timer !== null) {{
    stopPlay();
    return;
  }}
  fullView = false;
  if (frameIndex >= frames.length - 1) frameIndex = 0;
  playBtn.textContent = 'Pause';
  renderFrame();
  timer = window.setInterval(() => {{
    if (frameIndex >= frames.length - 1) {{
      stopPlay();
      return;
    }}
    frameIndex += 1;
    renderFrame();
  }}, 1200);
}}

function saveScreenshot() {{
  const canvas = chart.takeScreenshot(true, false);
  const link = document.createElement('a');
  const stage = fullView ? 'forensic-full' : frames[frameIndex].stage;
  link.download = `${{episode.episode_id}}-${{stage}}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}}

function fillFacts() {{
  const rows = [
    ['Trader', episode.trader_code],
    ['Market', episode.symbol],
    ['Period', episode.execution_period],
    ['Side', decision.side],
    ['Entry', decision.entry_price],
    ['SL', decision.stop_loss],
    ['TP', decision.take_profit],
    ['Session', decision.session],
    ['Trend', decision.trend_regime],
    ['Volatility', decision.volatility_regime],
    ['Exit', post.exit_reason],
    ['MFE', `${{post.close_path_mfe_r}}R`],
    ['MAE', `${{post.close_path_mae_r}}R`],
    ['Class', episode.classification],
  ];
  for (const [key, value] of rows) {{
    const dt = document.createElement('dt');
    const dd = document.createElement('dd');
    dt.textContent = key;
    dd.textContent = String(value);
    facts.append(dt, dd);
  }}
}}

try {{
  const module = await import(LIBRARY_URL);
  const {{ createChart, CandlestickSeries, createSeriesMarkers }} = module;
  chart = createChart(root, {{
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
  candleSeries = chart.addSeries(CandlestickSeries, {{
    priceLineVisible: false,
  }});
  markerApi = createSeriesMarkers(candleSeries, [], {{ autoScale: true }});
  paintPriceLines();
  fillFacts();
  renderFrame();
  prevBtn.addEventListener('click', () => {{
    stopPlay();
    fullView = false;
    frameIndex = Math.max(0, frameIndex - 1);
    renderFrame();
  }});
  nextBtn.addEventListener('click', () => {{
    stopPlay();
    fullView = false;
    frameIndex = Math.min(frames.length - 1, frameIndex + 1);
    renderFrame();
  }});
  playBtn.addEventListener('click', togglePlay);
  fullBtn.addEventListener('click', () => {{
    stopPlay();
    fullView = !fullView;
    renderFrame();
  }});
  shotBtn.addEventListener('click', saveScreenshot);
}} catch (error) {{
  const detail = error instanceof Error ? error.message : String(error);
  root.textContent = `Renderer initialization failed: ${{detail}}`;
  for (const button of [prevBtn, nextBtn, playBtn, fullBtn, shotBtn]) {{
    button.disabled = true;
  }}
}}
</script>
</body>
</html>
"""


def render_story_file(story_path: Path, *, episode_id: str, output_path: Path) -> Path:
    """Validate a story pack and write one browser-openable forensic replay page."""
    try:
        decoded: object = json.loads(story_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StoryForensicsRendererError("cannot read story pack") from error
    payload = _object(decoded, field_name="story pack")
    rendered = render_story_html(payload, episode_id=episode_id)
    try:
        output_path.write_text(rendered, encoding="utf-8")
    except OSError as error:
        raise StoryForensicsRendererError("cannot write rendered story") from error
    return output_path


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3:
        print(
            "usage: python -m qore.infrastructure.trader_lab.story_forensics_lightweight_renderer "
            "STORY_JSON EPISODE_ID OUTPUT_HTML",
            file=sys.stderr,
        )
        return 2
    try:
        render_story_file(
            Path(arguments[0]),
            episode_id=arguments[1],
            output_path=Path(arguments[2]),
        )
    except FirstCohortStoryForensicsError as error:
        print(f"story renderer failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
