# Turtle Soup Candidate R6 — Re-entry Source Adjudication

Status: **R6_REENTRY_SOURCE_UNDERDETERMINED**

Root research identity: `turtle-soup-candidate-r1`

R6 round identity: `turtle-soup-candidate-r6-reentry-exp1`

Canonical trader code: `CODE_UNASSIGNED`

Authoritative parent research: #553

R5 carrier: #563

## Executive adjudication

The Classic re-entry rule is documented consistently by recovered secondary sources, but the primary text was not directly verifiable in the adjudication round. Secondary evidence supports three limited claims: re-entry exists, the re-entry uses the original entry-price level, and the permission is limited to trade Day 1 / Day 2. The recovered evidence does not close enough state mechanics to claim a canonical executable re-entry algorithm.

The following remain source-underdetermined:

- maximum number of re-entry attempts;
- whether a new sweep is required;
- protective-stop construction after re-entry;
- exact operational semantics of `day`;
- same-bar / same-timestamp stop-out versus re-entry ordering;
- gap treatment;
- whether a second stop-out authorizes another attempt.

Therefore QORE MUST NOT promote a fully mechanical re-entry implementation as canonical Connors/Raschke Turtle Soup.

## Recovered secondary-source consensus

Recovered Tier-C sources reported materially equivalent language that, if a position is stopped out on trade Day 1 or Day 2, a trader may re-enter at the original entry-price level and only in that Day-1/Day-2 window.

Source inventory supplied to engineering:

- S2 — StockCharts.com, 2018, lines 41–44;
- S3 — TradingMethods.altervista.org, lines 24–27;
- S4 — Traderviet.tv, lines 27–30;
- S5 — MQL5 forum discussion, lines 14–16.

No recovered Tier-A/B material closed the missing mechanics.

## Rule matrix

| Rule | Status |
| --- | --- |
| Re-entry exists on Day 1 / Day 2 | Secondary-source consensus; not promoted to Tier-A canonical authority |
| Re-entry price equals original entry level | Secondary-source consensus |
| New sweep required | `SOURCE_UNDERDETERMINED` |
| Maximum attempts | `SOURCE_UNDERDETERMINED` |
| Stop after re-entry | `SOURCE_UNDERDETERMINED` |
| Exact `day` semantics | `SOURCE_UNDERDETERMINED` |
| Third attempt | `SOURCE_UNDERDETERMINED` |
| Same-bar / same-timestamp priority | `SOURCE_UNDERDETERMINED` |
| Gap treatment | `SOURCE_UNDERDETERMINED` |

## Governance consequence

A further research round may proceed only if every unresolved axis is explicitly labelled `QORE_EXPERIMENTAL_REENTRY`, frozen before economic replay, and kept separate from the canonical/source-bound rule set. Such a round is hypothesis research, not a source reconstruction claim.

Fresh OOS remains closed.

No DEMO, LIVE, FTMO, FundedNext, production, canonical-code or real-capital authority is granted by this adjudication.
