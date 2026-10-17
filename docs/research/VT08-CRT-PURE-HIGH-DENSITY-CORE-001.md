# VT08 CRT PURE — HIGH-DENSITY CORE CHECKPOINT 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**Status:** HIGH-DENSITY CORE FOUND / EDGE RECOVERY OPEN

## 1. R2-AM — static high-retention ablation falsified

Run: `35863335522 — SUCCESS`.

Question:
Can one already-known pre-parent context bucket be excluded while retaining at least
60% of the unfiltered valid-trade population and leaving every annual Total-R positive?

### AUDUSD 2016-2026

Base:
- 560 trades
- PF 0.99453171
- -1.07325030R
- DD 26.78757358R

Minimum residual:
- 336 trades

Result:
- **zero** qualifying single-bucket exclusions.

### USDJPY 2014-2026

Base:
- 662 trades
- PF 0.97212860
- -6.58199479R
- DD 29.29791972R

Minimum residual:
- 398 trades

Result:
- **zero** qualifying single-bucket exclusions.

Adjudication:
A single static universal context exclusion is not sufficient across 10-12 years.
Do not replace the narrow EFF gate with another static magic range.

## 2. R2-AO — rolling H4 + structural targets

Run: `35863768335 — SUCCESS`.

Contract:
- rolling H4;
- no EFF;
- one selected Model #1 hypothesis max per parent;
- structural source stop;
- C3 expiry;
- midpoint control plus fixed 1R / 1.5R / 2R;
- fixed targets do not require midpoint geometry.

### AUDUSD 2020-2026

Rolling parents:
- 2,515

Selected hypothesis:
- 1,467

Fixed-target structurally valid trades:
- 1,465
- **244.17 trades/year**

Midpoint control:
- 1,073 trades / 178.83 per year
- PF 0.95533950
- -19.58373201R

Fixed 1R:
- PF 0.98126314
- -10.79940925R

Fixed 1.5R:
- **PF 0.99895711**
- **-0.65500147R over 1,465 trades**
- DD 46.21786493R
- **4/6 annual windows positive**

Fixed 2R:
- PF 0.98504225
- -9.80941994R

Adjudication:
AUDUSD density is solved. The 1.5R high-density core is economically almost flat before
market suitability. It is the strongest broad rolling target arm.

### USDJPY 2020-2026

Fixed-target structurally valid trades:
- 1,454
- **242.33 trades/year**

Midpoint:
- PF 0.89235002

Fixed 1R:
- PF 0.90895043

Fixed 1.5R:
- **PF 0.94419161**
- -35.19439228R
- 1/6 annual windows positive

Fixed 2R:
- PF 0.93114376

Adjudication:
USDJPY density is also solved, but the broad high-density population still lacks edge.
USDJPY needs a stronger market-specific suitability model than AUDUSD.

## 3. Architecture conclusion

The engineering architecture capable of the required density is now explicit:

`ROLLING_H4 -> CRT C1/C2/C3 -> Model #1 -> structural stop -> fixed target`

It produces roughly:
- AUDUSD: 244 trades/year
- USDJPY: 242 trades/year

without:
- EFF narrow gating;
- multiple same-parent entries;
- relaxed Model #1 confirmation;
- fabricated signals.

Therefore the density problem is **closed at the capacity/architecture level**.

The remaining problem is **market suitability / edge discrimination**.

## 4. Suitability direction

Static one-bucket universal filters are falsified by R2-AM.

Next suitability must:
- be market-specific;
- use only pre-entry context;
- remain high-retention;
- avoid future leakage;
- adapt across regimes or validate across historical folds;
- map cleanly to CORE's existing
  `FAVORABLE / DEGRADED / UNSUITABLE / UNCERTAIN` world-model semantics.

## 5. Active chain

- R2-AP: AUDUSD transfer test of one 6Y toxic manipulation state onto rolling + 2R.
- R2-AQ: older historical validation of the unfiltered rolling + 1.5R high-density core.
- Next: market-specific Suitability walk-forward after AQ baseline evidence.

No VPS / DEMO / LIVE / production / real capital.
