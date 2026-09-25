# VT08 INDEX — CIBO MARKET INTELLIGENCE 001

Status: diagnostic only / consumed evidence only.

Evidence base: Market Journey / Target Atlas over 2,294 reconstructed V7 trades from consumed 2018-09-15..2026-09-12 evidence. V7 rule fingerprint remains `a7f3b7afa3a98bfcb4daad1595762ce3925000fb256e2cbd2db84b8ec80b1308`.

## 1. Core journey observation

The journey atlas follows price after each frozen V7 signal independently of whether the trader was already stopped. Therefore `hit 2R/3R` below means that the market eventually reached that distance from the original entry within the diagnostic horizon; it does NOT mean the current stop survived long enough to realize it.

- NAS100: n=761; stop rate ~67.5%; eventual 1R 77.8%; 2R 59.3%; 3R 44.4%; median time to 2R 240 min; median time to 3R 330 min. About 46.7% of stopped trades later reached 2R from the original entry.
- SP500: n=747; stop rate ~64.0%; eventual 1R 77.1%; 2R 56.2%; 3R 43.2%; median time to 2R 225 min; median time to 3R 300 min. About 40.0% of stopped trades later reached 2R.
- US30: n=786; stop rate ~63.7%; eventual 1R 75.2%; 2R 58.7%; 3R 44.7%; median time to 2R 240 min; median time to 3R 330 min. About 42.5% of stopped trades later reached 2R.

Interpretation: a large fraction of losses are not simply cases where the eventual directional thesis never occurs. Timing, structural invalidation placement, and pre-expansion path are material research questions.

## 2. Time-of-day journey

Across all three markets:

- 22:00 NY: n=295; eventual 2R 78.3%; 3R 70.8%; 4R 61.0%; 5R 55.9%; median 2R time 225 min. About 66.1% of stopped trades later reached 2R.
- 02:00 NY: n=741; 2R 67.2%; 3R 53.3%; median 2R time 300 min.
- 06:00 NY: n=720; 2R 58.6%; 3R 43.3%; median 2R time 150 min.
- 10:00 NY: n=538; 2R only 33.6%; 3R 17.8%; median 2R time 480 min; primary-stress mean approximately -0.109R/trade.

This is a strong descriptive difference in natural path by anchor. It is NOT permission to delete 10:00 retrospectively.

### Market-specific anchors

US30 at 22:00 is especially expansive: n=96; eventual 2R 81.3%; 3R 71.9%; 5R 60.4%; primary-stress mean +0.2625R/trade.

SP500 at 10:00 is especially weak under frozen V7: n=184; stop rate 72.3%; eventual 2R 30.4%; 3R 18.5%; primary-stress mean about -0.219R/trade.

NAS100 shows a different problem: even at 22:00 its eventual path is expansive (2R 75.5%, 3R 71.6%), but its current V7 primary-stress mean is still slightly negative. Around 64.2% of NAS100 22:00 stops later reach 2R. This is evidence that for NAS100 the issue may be the path/timing into expansion rather than absence of later expansion.

## 3. Structural frontiers

When the previous-H4 directional extreme is actually ahead of the entry:

- NAS100: available ahead in ~53.0% of trades; median distance ~0.63R; hit ~83.4%; median hit time 60 min.
- SP500: ahead ~52.2%; median distance ~0.65R; hit ~87.2%; median 45 min.
- US30: ahead ~51.7%; median distance ~0.64R; hit ~83.5%; median 45 min.

When the previous source-day directional extreme is ahead:

- NAS100: ahead ~66.1%; median distance ~2.31R; hit ~58.1%; median hit time 180 min.
- SP500: ahead ~64.8%; median distance ~2.04R; hit ~63.0%; median 180 min.
- US30: ahead ~69.3%; median distance ~2.02R; hit ~59.8%; median 195 min.

Important implication: fixed 2R is not obviously detached from market geometry. The prior source-day boundary itself is typically around ~2R from entry when directionally ahead. The more urgent problem is often whether the trader survives the path to that boundary.

## 4. Range state before entry

Across all markets, prior-H4 compression behaves very differently from prior-H4 expansion:

- compressed: n=1,020; eventual 2R 67.2%; 3R 53.9%; primary-stress mean +0.038R/trade; ~52.5% of stops later reach 2R.
- normal: n=845; eventual 2R 56.3%; 3R 42.2%; primary mean -0.036R/trade.
- expanded: n=429; eventual 2R only 39.9%; 3R 24.5%; primary mean -0.037R/trade; only ~25.4% of stops later reach 2R.

This supports a research hypothesis: expansion emerging from compression and continuation after an already-expanded H4 are different market states and should not automatically be treated as equivalent.

## 5. POI family

Frozen V7 POI cohorts:

- FVG: n=374; primary mean +0.161R/trade; eventual 2R 66.8%; 3R 53.2%.
- CISD fallback: n=1,837; primary mean -0.035R/trade; eventual 2R 56.7%; 3R 42.7%.
- relevant-swing: n=83; primary mean -0.037R/trade; eventual 2R 49.4%.

These are diagnostic associations, not automatic promotion/removal rules. In particular NAS100 remains problematic even inside its FVG cohort, so `FVG = good` is false as a universal rule.

## 6. Source-day behavior by weekday

The source-day range study is independent of trade outcome and gives a first calendar fingerprint:

- Monday is the most compressed median source day for all three markets: NAS100 median range ratio ~0.964, SP500 ~0.876, US30 ~0.897.
- Thursday has the largest median relative range for all three: NAS100 ~1.040, SP500 ~1.053, US30 ~1.056.
- Expanded-day frequency on Thursday is ~34-35% across the three markets; Monday is ~25-26% for NAS100/SP500/US30 except compression dominates especially SP500 (~37%) and US30 (~34%).

This is descriptive evidence that weekday context may matter for target expectations, but target-by-weekday inference must use complete observable horizons and account for weekly close before being promoted.

## 7. Stop afterlife

A recurring phenomenon is `stopped_then_expands`: the current Protected-Swing stop is hit first, but price later travels materially in the original direction.

Overall stopped-then-2R rates are approximately:

- NAS100 46.7%
- SP500 40.0%
- US30 42.5%

The phenomenon is highly anchor-dependent: at 22:00 it is ~66.1% across markets, but at 10:00 only ~22.5%.

This does NOT imply widening the stop. It means CIBO must classify whether the original structural premise was genuinely invalidated, whether entry occurred before the final manipulation, or whether the observed later move is a distinct setup.

## 8. Pre-entry accumulation / balance

Median four-hour pre-entry balance score is similar overall (NAS100 ~0.55, SP500 ~0.55, US30 ~0.55), so a single scalar `accumulation score` is insufficient. CIBO must examine sequence details: body flips, inside bars, local sweep direction, FVG formation, H4 range state, peer state and latency to CISD/continuation.

## 9. Cross-index obligation

Every future CIBO explanation must report NAS100/SP500/US30 contemporaneous context and distinguish one shared macro exposure from three independent signals. Existing deep-behavior evidence already shows a material share of losses clustering across indices within four hours.

## 10. Structure-definition governance

Mechanically observable now:
- FVG diagnostic.
- local liquidity sweep diagnostic.
- previous H4 directional extreme.
- previous source-day directional extreme.
- CISD / Protected Swing / V7 POI provenance.

Still unresolved and therefore NOT automated:
- Order Block.
- Breaker Block.

Those labels require a separate source-definition freeze before CIBO may emit them as typed structural facts.

## Required CIBO output format going forward

For every analyzed episode CIBO must provide:
1. market / date / side / anchor;
2. state before entry: compression/balance/displacement, FVG/sweep/POI and peer context;
3. exact reaction structure and time;
4. minutes POI→CISD→continuation;
5. whether stop occurred before expansion;
6. post-stop afterlife at 0.5R/1R/2R/3R;
7. first structural frontier ahead and distance in R;
8. previous-source-day frontier and whether/when reached;
9. natural path to 1R/2R/3R/4R/5R;
10. what NAS100/SP500/US30 did differently at the same time;
11. source-day weekday/regime context;
12. confidence/evidence status and explicit unresolved structures.

No statistic in this document changes V7. Any operational rule derived from it requires a new candidate identity, freeze, walk-forward and genuinely unseen validation.
