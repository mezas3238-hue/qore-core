# VT-31 Silver Bullet V2 — Source Audit 002

Status: **SOURCE-BOUND RECONSTRUCTION / RESEARCH ONLY / NO DEMO OR LIVE AUTHORITY**

Primary Human Owner file: `1000856441.mp4`

Canonical source identity: `youtube:o0v4KQxZbpU` — TTrades, `ICT Silver Bullet Strategy - No Daily Bias | With Backtest!`

Human Owner file SHA-256: `bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf`

Observed duration: approximately `00:29:08`.

The supplied file is byte-identical to the earlier Human Owner file `1000854800.mp4`; therefore this audit confirms the existing `VT-31 v2` methodology identity rather than creating another Trader identity.

## Classification vocabulary

Every observation is classified as exactly one of:

- `EXPLICIT_RULE`
- `REPEATED_BEHAVIOR`
- `SINGLE_EXAMPLE`
- `DISCRETIONARY_COMMENT`
- `UNRESOLVED_AMBIGUITY`
- `OPERATIONAL_CONTAINMENT`

A discretionary comment, single example, or unresolved ambiguity is not silently promoted into a source rule.

## Timestamp → rule → operationalization → test matrix

| Video time | Observed fact | Verbal / visual evidence | Class | Algorithmic treatment | Required proof |
|---|---|---|---|---|---|
| 00:11–00:20 | AM Silver Bullet, NQ ticker | narrator names AM session and NQ; chart material is NASDAQ/NQ | `EXPLICIT_RULE` | source-bound market is canonical `NAS100` only | wrong-instrument abstention; provider alias cannot substitute instrument |
| 00:29–00:37 | entries only 10:00–11:00 | narrator says only entries appearing between 10 and 11 | `EXPLICIT_RULE` | `[10:00,11:00)` in `America/New_York`; no fixed UTC offset | EST/EDT test; 11:00 signal invalid |
| 00:48–01:04 | freeze previous hour / 09:00 H1 high and low | narrator marks 09:00 hourly candle high/low when 10:00 arrives | `EXPLICIT_RULE` | build exact `[09:00,10:00)` range from sixty closed M1 bars; freeze at 10:00 | complete-range, missing-minute, future/open/duplicate tests |
| 01:06–01:24 | take one range side, target the other | high taken → target low; low taken → target high | `EXPLICIT_RULE` | strict range-side raid determines direction and opposite H1 boundary target | LONG/SHORT target tests |
| 01:40–01:52 | execution on M1 | chart drops to one minute and marks 10–11 window | `EXPLICIT_RULE` | exact M1 evidence only | M5 substitution rejected |
| 01:55–02:05 | stop raid required before entry model | waits for stop raid below low or above high | `EXPLICIT_RULE` | strict `>` / `<`; equality is not a raid | equality, no-raid tests |
| 02:13–02:30 | raid alone is insufficient; waits for reversal/displacement | says no displacement down; price pushes higher; later identifies entry context | `REPEATED_BEHAVIOR` | post-raid reversal evidence must be causal and use only closed M1 bars | raid-without-structure abstains |
| 02:30–02:55 | order block + FVG + midnight-open/CE confluence used in one example | visual/narrated confluence; target opposite prior-hour side | `SINGLE_EXAMPLE` | do **not** make midnight open universal; record confluence if present; CE remains an entry-price formalization only where configured | provenance test; no midnight-open requirement |
| 03:35–03:41 | no range-side sweep → no trade | explicit narrated negative example | `EXPLICIT_RULE` | `ABSTAIN/NO_RAID` | golden no-trade fixture |
| 05:01–05:18 | shallow sweep is disliked but still observed | calls sweep shallow; continues evaluation | `DISCRETIONARY_COMMENT` | no invented minimum sweep distance | shallow sweep cannot be rejected solely by numeric threshold |
| 05:31–05:52 | close below low that made new high → breaker short | narrator waits for structural close then marks breaker | `REPEATED_BEHAVIOR` | structural anchor tracks extreme-producing candle; confirming close must occur after raid | causal breaker SHORT fixture |
| 06:03–06:24 | LIMIT order may fill immediately before 11 | sell limit fills right before 11 | `EXPLICIT_RULE` | pending LIMIT valid until exact 11:00 boundary | 10:59 fill valid; 11:00 fill prohibited |
| 06:30–06:58 | once price reaches 3R move stop to breakeven; target may occur next day | narrator moves stop at 3R and leaves trade open until next-day target | `EXPLICIT_RULE` | post-fill lifecycle must arm BE only after causal 3R touch; no 11:00 time exit | 3R→BE test; open position survives 11; next-day target permitted |
| 07:12–07:43 | low sweep + close above relevant up-close candle → bullish breaker | explicitly calls breaker and enters long | `REPEATED_BEHAVIOR` | mirrored causal breaker LONG | bullish breaker fixture |
| 08:20–08:40 | small FVG is possible but presenter waits for more aggressive displacement, then uses up-close candle as entry | narrated preference and later entry | `DISCRETIONARY_COMMENT` | no hidden ATR/body threshold; structural-close baseline is the versioned displacement formalization | no ATR/body-ratio parameter; formalization recorded |
| 09:30–09:48 | FVG order that does not fill before 11 is cancelled | explicit narrated cancellation | `EXPLICIT_RULE` | pending entry expires exactly 11:00 New York | unfilled-before-window-end test |
| 09:58–10:03 | equal high/touch is not a sweep | narrator explicitly rejects equality as sweep | `EXPLICIT_RULE` | strict inequality only | equality test |
| 10:22–10:52 | order block inside mitigation/breaker after close below structural candle | narrated order-block entry with stop on high and opposite-side target | `REPEATED_BEHAVIOR` | causal Order Block candidate is allowed after confirmed reversal | order-block fixture |
| 11:34–12:24 | FVG selected; breaker alternative would have filled | narrator notes alternative entry would differ materially | `UNRESOLVED_AMBIGUITY` | no hidden universal model priority; simultaneous non-equivalent models are recorded as confluence and resolved only by explicit versioned selection policy | ambiguity/confluence test |
| 12:55–13:16 | aggressive return into range; FVG entry; about 2.85R accepted | narrated | `REPEATED_BEHAVIOR` | no universal `5R` or `3R` minimum entry filter | geometry may be <5R |
| 13:30–14:17 | valid-looking FVG examples can lose | narrated losses | `REPEATED_BEHAVIOR` | fidelity is independent of profitability | losing fixture |
| 14:34–15:16 | unclear displacement / unattractive price action leads to no entry | narrator declines discretionary example | `DISCRETIONARY_COMMENT` | no numeric displacement or equal-high buffer invented | ambiguity retained; no look-ahead rationalization |
| 15:19–15:30 | ~2.5R described as unattractive | narrator says not a fan | `DISCRETIONARY_COMMENT` | do not impose minimum R:R | test no hard R:R threshold |
| 15:53–16:21 | prefers immediate aggressive displacement / lower-timeframe sweep | narrator preference | `DISCRETIONARY_COMMENT` | no invented mandatory lower-timeframe-sweep depth | formalization provenance only |
| 16:28–17:16 | FVG inside breaker taken; trade stops out | visual/narrated losing case | `REPEATED_BEHAVIOR` | confluence supported; conservative terminal handling | losing/confluence fixture |
| 17:42–18:12 | order-block entry after aggressive reversal | narrated | `REPEATED_BEHAVIOR` | Order Block candidate supported | order-block positive fixture |
| 18:21–18:49 | sweep without acceptable structure/displacement → no trade by 11 | narrated negative example | `REPEATED_BEHAVIOR` | structure required | no-structure fixture |
| 18:54–19:52 | close below structure but presenter dislikes late location near target; order also never fills before 11 | narrated | `DISCRETIONARY_COMMENT` + `EXPLICIT_RULE` | no premium/discount or minimum remaining-distance threshold; unfilled cancellation remains mandatory | no hidden location filter; expiration test |
| 20:01–20:25 | breaker long and explicit 3R→BE | narrated | `REPEATED_BEHAVIOR` + `EXPLICIT_RULE` | breaker + lifecycle management | breaker + BE fixture |
| 20:42–21:01 | cannot see structure → no action | narrated | `REPEATED_BEHAVIOR` | insufficient structure abstains | missing/ambiguous structure fixture |
| 21:07–21:30 | low sweep, displacement, long, stop low, target opposite side; trade loses | narrated | `REPEATED_BEHAVIOR` | LONG geometry must remain source-bound; losing outcome retained | losing LONG fixture |
| 21:42–22:02 | sweep but no aggressive displacement → no trade | narrated | `DISCRETIONARY_COMMENT` / negative example | baseline mechanization must not claim an author-specified numeric aggression threshold | formalization test |
| 22:08–22:44 | high already taken; displacement down; FVG; 3R→BE | narrated | `REPEATED_BEHAVIOR` | FVG candidate + lifecycle | FVG + BE fixture |
| 22:59–23:15 | close below body → breaker; trade stops | narrated | `REPEATED_BEHAVIOR` | breaker candidate can lose | losing breaker fixture |
| 23:27–24:08 | sweep; structure initially unclean; later aggressive down/order block but presenter waits for further confirmation and ultimately does not enter | narrated | `DISCRETIONARY_COMMENT` / `UNRESOLVED_AMBIGUITY` | no retroactive entry after seeing outcome; ambiguous discretionary gate remains explicit | no-look-ahead negative fixture |
| 24:17–24:36 | price already below low, no reversal before 11 → no trade | narrated | `REPEATED_BEHAVIOR` | no reversal → abstain | session-without-trade fixture |
| 24:50–25:22 | high sweep; aggressive displacement; breaker **or** FVG both available; presenter enters without defining universal priority | narrated | `UNRESOLVED_AMBIGUITY` | register `BREAKER_BLOCK+FAIR_VALUE_GAP` confluence; deterministic selection policy must be separately versioned, never called an explicit source rule | confluence-policy test |
| 25:44–26:18 | low sweep but no required close/clean reversal before 11 → no trade | narrated | `REPEATED_BEHAVIOR` | fail closed on insufficient structure | negative fixture |
| 26:37–27:19 | shallow sweep disliked; later displacement; low R:R disliked but trade still taken | narrated | `DISCRETIONARY_COMMENT` + positive example | proves shallow-sweep and R:R preferences are not hard source thresholds | no hidden threshold tests |
| 27:34–28:24 | 45 days, 15 trades, average R:R about 5, average duration 1h29m, illustrated total growth about 44.4% | analytics screen and narration | `SINGLE_EXAMPLE` / plausibility control | compare only as a plausibility benchmark; never optimize rules to reproduce aggregate | source replay report only |

## Deterministic formalizations required by software

The following are **not claimed as literal source rules**. They exist only so the algorithm can be deterministic and falsifiable:

1. `STRUCTURAL_CLOSE_V1`: reversal confirmation is the first post-raid close through the structural level associated with the latest extreme-producing candle. This is grounded in repeated narrated examples but does not numerically define “aggressive”.
2. `ENTRY_ZONE_BODY_MIDPOINT_V1`: where the video names a breaker or order-block candle but does not state one exact executable price, the mechanical research adapter represents the candle body as a zone and uses its midpoint as the reproducible LIMIT price. The full zone and methodological swing remain retained so this decision can be sensitivity-tested. It is an `OPERATIONAL_CONTAINMENT`, not an author rule.
3. `FVG_CE_V1`: a three-candle FVG is represented by the strict non-overlap interval and its consequent encroachment (50% of that gap) as the deterministic LIMIT price. The source explicitly uses FVG/CE language in examples, but not every FVG example states the same exact price.
4. `NO_HIDDEN_MODEL_PRIORITY_V1`: all causal entry models available at the same decision time are retained. If they imply materially different LIMIT prices, the evaluator abstains with `AMBIGUOUS_ENTRY_MODEL_CONFLUENCE` unless the research configuration explicitly selects a named model. If zones agree at the same deterministic price, the setup records all models as confluence. This prevents a silent performance-driven priority.
5. `STOP_FIRST_SAME_BAR_V1`: before BE is armed, if stop and target/3R are all touched inside one OHLC bar and intrabar chronology cannot be known, initial stop wins. After BE is armed, if BE and target are touched in the same later bar, BE wins. This is conservative research containment, not a claimed source rule.
6. `ONE_FILL_PER_SESSION_V1`: after one fill, the backtester does not seek another trade in the same instrument/session. This is retained as `OPERATIONAL_CONTAINMENT` because the video advances session-by-session after selecting a trade but does not state a universal maximum-attempt rule.

## Explicit non-rules

This reconstruction must not add any of the following unless a future source freeze separately authorizes it:

- daily/H4/session bias;
- EMA/RSI/volume/macro-news filter;
- ATR threshold;
- minimum candle/body percentage;
- minimum sweep depth;
- arbitrary pivot count;
- equality tolerance around the 09:00 range;
- fixed-R take profit;
- universal minimum R:R;
- universal premium/discount filter;
- fixed time exit at 11:00 for already-filled positions;
- MARKET chasing after a missed LIMIT;
- cross-market source authority.

## Fidelity verdict at this checkpoint

The previous VT-31 V2 implementation correctly captured the NAS100-only scope, New York 10–11 window, frozen 09:00 range, strict raid, post-raid structural reversal, opposite-range target and pre-11 LIMIT expiry. It was **materially incomplete** because it encoded only FVG-CE entries and its historical lifecycle did not implement the source-explicit 3R→breakeven transition.

Until those gaps are corrected and the full Quality Gate passes, fidelity remains **NOT YET DEMONSTRATED**.
