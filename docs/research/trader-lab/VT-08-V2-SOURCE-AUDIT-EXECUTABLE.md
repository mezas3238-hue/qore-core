# VT-08 V2 — source audit and executable reconstruction

Checkpoint: 2026-09-11  
Primary source: `1000854868.mp4` / `youtube:FAKWJ-1NlLE`  
SHA-256: `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`  
Measured duration: 1275.727528 seconds  
Methodology: `ttrades-h4-po3-source@v2.6-source-executable`

## Verdict of the falsification attempt

The old universal conclusion, “the video cannot determine entry or target”, is
false. The video demonstrates several executable families. It does **not** teach
one entry or one target for all contexts. VT-08 therefore models the families
separately and abstains only when the evidence does not select one unambiguously.

The source never supplies a numerical definition of “shallow” or “large”. Those
labels remain qualitative source evidence; no wick ratio, ATR threshold, moving
average, RSI, volume filter, daily-trend formula, or minimum R:R was introduced.

## Complete chronological matrix

| Video | Narration and visual fact | Class | Executable consequence | Code / test |
|---|---|---|---|---|
| 00:00–00:56 | Power of Three is accumulation, manipulation and distribution; the lesson applies the sequence to swing points and Candle 2/Candle 3. | `EXPLICIT_RULE` | Preserve H4 AMD and two named scenarios. | `Vt08CrtH4AmdV2Scenario`; scenario tests |
| 00:57–01:39 | Candle 1 accumulates. Candle 2 can manipulate and distribute when the adverse run is small/shallow. A large opposing run calls for Candle 3 distribution. | `EXPLICIT_RULE` | Shallow C2 may continue; large C2 must abstain with `WAIT_FOR_CANDLE3`; C3 requires the completed C2 reversal. | `evaluate_reversal_expansion_candle2`; `evaluate_continuation_expansion_candle3` |
| 01:40–03:30 | Chart examples show both paths; an expansion meeting opposing expansion and closing through the opposing candle/body creates CISD and a protected swing. | `REPEATED_BEHAVIOR` | CISD is a close through the opening level of the opposing sequence after its extreme; that extreme is protected. | `_protected_swing`; LONG/SHORT CISD and swing tests |
| 03:31–04:08 | Use Daily/H4 closures for directional context; allow the wick to form, then trade the body. | `EXPLICIT_RULE` | Bias is required causal context. No universal D1 formula is synthesized. | `bias_side`; missing-bias test |
| 04:09–05:33 | Timing slide pairs H4 with M15; Forex repeats 01/05/09/13/17/21 and futures 02/06/10/14/18/22 New York. | `EXPLICIT_RULE` plus `OPERATIONAL_CONTAINMENT` | M15 only. Owner scope restricts Forex to 01/05/09 and futures to 02/06/10, DST-aware. | timing-family/anchor validation and DST tests |
| 04:28–06:44 | Friday bias continues toward Thursday high after Thursday closes outside Wednesday range. The 02:00 candle reverses; at 06:00 M15 sweeps a low, closes back above, trades inside an FVG, creates a protected low. Entry may be taken in the marked area; stop is the protected low; target is previous-day high. | `EXPLICIT_RULE` + `SINGLE_EXAMPLE` | Structural-target family: causal reached FVG/POI → CISD → protected swing → entry in marked zone → protected-swing stop → previous-day extreme target. | typed POI, execution plan, structural target |
| 07:06–08:45 | USDJPY weekly continuation: shallow retracement into an FVG leaves failure-swing highs as open objective. Because price first makes a large adverse range, do not force same-candle expansion. | `REPEATED_BEHAVIOR` | POI may be FVG; failure swings may be structural objectives; large adverse C2 requires waiting. | POI/target enums; Candle-3 prerequisite |
| 08:46–09:58 | Expansion is met with expansion and CISD. If the reversal entry is missed, wait for continuation. A retracement into the FVG then a close through a down-close candle produces a new protected swing. Stop uses the protected swing; trade only while the open highs offer 2R. Example realizes 2.45R. | `EXPLICIT_RULE` | Protected-swing continuation is a distinct entry model. `2R` is a room/selection condition here, not a universal TP. | `PROTECTED_SWING_CONTINUATION`; conditioned target variant |
| 09:59–11:02 | Do not carry the old execution through a new H4 after its time/range is used. A new H4 continuation may form after another sweep and close through an opposing series. The author dislikes entering over old highs. | `EXPLICIT_RULE` + `DISCRETIONARY_COMMENT` | Limit validity to the H4 cycle. Do not encode the personal dislike as a hard rule. | `valid_until` / `expires_at` |
| 11:03–13:20 | Gold illustrates the same fractal logic on 3m/5m (Gold is outside owner scope): consolidation, sweep, CISD and protected swing. A confident entry may use the confirmation area; stop can be the protected swing or an invalidation area above 50% of CISD/EQ; target shown at 2R. | `SINGLE_EXAMPLE` | Confirms multiple stop/entry variants exist. V2’s conservative executable profile requires exact protected-swing stop; alternative invalidation zones remain unresolved unless explicit evidence selects them. | exact-stop validation; XAUUSD rejection |
| 13:21–14:50 | At a new H4 open, the already confirmed protected swing permits a positional entry at the new H4 open, stop at the protected swing, target 2R. Later a new protected swing permits continuation. | `EXPLICIT_RULE` | `POSITIONAL_H4_OPEN` and continuation are separate typed models; a plan must pre-exist the signal. | entry model enum; causal-plan checks |
| 15:00–16:16 | NQ: previous-day high sweep, 06:00 reversal, 10:00 continuation and T-spot. Entry is positional in a marked zone; stop may use the opposing candle/FVG invalidation; target is 2R or −1 standard deviation. The latter is chosen because the large opposing run makes farther deviations illogical. | `EXPLICIT_RULE` + `SINGLE_EXAMPLE` | `CONDITIONED_TWO_R` and `NEGATIVE_ONE_STANDARD_DEVIATION` are contextual target types, never blanket defaults. | target enum and target validation |
| 16:17–18:53 | NQ bearish C3 closes, then V-reversal. Failure-swing highs remain objective. A shallow H4 wick reaches a POI; SMT+CISD permits reversal entry, and the 10:00 H4 open permits positional continuation. Later consolidation/sweep/new protected swing permits another entry if 2R remains. M15 is also valid. | `REPEATED_BEHAVIOR` | Multiple legitimate entries can occur only after new confirmation and remaining structural room. V2 contains frequency to one resolved execution plan per evaluator call/cycle. | plan/evidence fingerprint; one decision per call |
| 18:54–21:05 | After target, do not reverse without a new expansion close. At 14:00 a new H4 reversal uses consolidation-high manipulation plus CISD; aggressive move permits open entry and 2R target; continuation may follow. | `EXPLICIT_RULE` | A completed prior target alone cannot reverse bias; a fresh manipulation+CISD is required. 14:00 is source knowledge but outside owner operating scope. | anchor abstention and CISD prerequisite |

## Source formalizations

| ID | Source evidence | Formalization | Alternatives rejected | Falsification condition |
|---|---|---|---|---|
| SF-01 | 01:40–03:30, 06:15–06:44, 08:46–09:58 | CISD LONG closes strictly above the open of the opposing down-close sequence; SHORT mirrors it. The most adverse extreme in that sequence is the protected swing. | N-bar pivot and wick-ratio pivots | A golden example confirms CISD without this close relation. |
| SF-02 | 06:15–06:44, 08:46–09:58 | A resolved POI is a typed bounded object formed and confirmed no later than signal, with unique evidence IDs and selection reason. | Nearest arbitrary level or retrospective best FVG | A source-positive entry has no identifiable pre-signal POI. |
| SF-03 | 06:15–06:44 | `CISD_CONFIRMATION_CLOSE` uses the confirming close only when that price lies inside the source-marked POI zone. | Treat every CISD close as entry | A positive example places the executable order elsewhere despite the same selected family. |
| SF-04 | 08:46–09:58, 11:03–16:16 | The conservative automatic stop equals the protected-swing extreme exactly; no buffer. | Opposing-candle/FVG alternative without selecting evidence | A golden example explicitly requires a different exact stop. |
| SF-05 | 09:08–09:58, 13:21–16:16, 18:54–21:05 | `CONDITIONED_TWO_R` is valid only when the selected example/plan explicitly invokes 2R; its target must calculate to exactly 2R. | Universal fixed 2R | A selected 2R example yields a non-2R marked target. |
| SF-06 | complete lesson | An execution plan and its POI must be observed by CISD confirmation and expire no later than the H4 close. | Post-signal annotations and future Candle 3 evidence | Any accepted setup consumes an evidence timestamp after signal. |

No economic result was used to choose any formalization. Sensitivity must vary
normalization/fill assumptions around a frozen formalization, never rewrite it.

## Video → code → test traceability

| Timestamp | Observation | Class | Rule | Code symbol | Required test result |
|---|---|---|---|---|---|
| 00:57–01:39 | Shallow C2 vs large C2/C3 | `EXPLICIT_RULE` | Separate causal paths | evaluators | C2 setup; C3 setup; wait-C3 |
| 01:40–03:30 | CISD/protected swing | `REPEATED_BEHAVIOR` | SF-01 | `_protected_swing` | LONG/SHORT exact levels |
| 03:31–04:08 | bias/context | `EXPLICIT_RULE` | no invented formula | `_validate_common` | missing context abstains |
| 04:09–05:33 | H4/M15 and clocks | `EXPLICIT_RULE` | owner 3+3 containment | `_valid_m15_window`, anchors | six anchors + DST |
| 06:15–06:44 | FVG entry, protected low, PDH TP | `SINGLE_EXAMPLE` | structural execution family | `ExecutionPlan`, `PointOfInterest` | golden LONG geometry |
| 08:46–09:58 | continuation and 2R room | `EXPLICIT_RULE` | continuation family | `EntryModel` | golden C3 |
| 13:21–14:50 | new-H4-open position | `EXPLICIT_RULE` | positional family | `POSITIONAL_H4_OPEN` | causal creation/expiry |
| 15:00–16:16 | 2R or −1 SD by context | `EXPLICIT_RULE` | contextual targets | `TargetType` | target type/price tests |

## Remaining ambiguity and containment

- The video does not define a numeric shallow/large boundary. An unresolved
  classification abstains; no percentage is inferred.
- Several examples say “anywhere in here”. The executable close-entry profile
  is permitted only when the confirming close is within the retained POI bounds.
- The video permits alternative invalidation zones. The implemented conservative
  profile uses the exact protected swing. Other alternatives require their own
  evidence-backed future profile.
- Same-M15-bar stop and target ordering is unknowable without causal lower-
  timeframe evidence; the backtester must resolve it stop-first and label it
  `OPERATIONAL_CONTAINMENT`.
- Gold examples inform methodology but XAUUSD remains operationally rejected.

## Economic governance

The invalid 13,468-trade campaign and the 16,197 mechanical candidates are not
trades and supply no wins, losses, expectancy or geometry to this reconstruction.
A new campaign is admissible only after golden fixtures and full quality gates
pass on the exact software SHA. A setup is not a filled trade; a limit may fill
only after its signal, and unfilled expiry remains unfilled.
