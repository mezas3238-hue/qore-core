# VT31 AM control audit 2026-10-13

Before looking at any new results, freeze three diagnostic tasks: compare OB and Breaker to first confirmed generic local M1 pivot, compute all family day overlaps, and recompute all families from their shared displacement timestamp. All tests are descriptive, no fills, no live trading or economic claims. The 3-year development set is already explored. Do not select winning families from these numbers.

## Fixed methods (registered before programming)

The generic control on each valid post-sweep/displacement day is the FIRST strict 3-candle local pivot after displacement: for LONG center M1 low strictly lower than both neighbors; for SHORT center high strictly higher. Its timestamp is the close of the RIGHT neighbor (never the pivot center), with the 15-minute signed open-to-open metric from the next M1. Missing 16 consecutive M1 => missing, not zero. No rule selects a profitable pivot, and no broker fill is inferred.

Matched family-control differences use the same NY day and direction when both have valid returns, with 2000 ISO-week cluster bootstraps seeded 13102026. Report n matched, both return means, mean paired difference, confidence interval, time lag, and missing controls. A paired comparison still has DIFFERENT confirmation times and does not isolate a causal factor.

For common-time comparison, each family membership is mapped to that day's DISPLACEMENT_DIRECT confirmation; 15m next-M1 opening gross return is exactly the same on any one day. Report own-time return, common-time return, both n, and the family-to-displacement lag. Later family membership is unavailable at the common anchor, making it POST-HOC only.

Report all pairwise intersections and 16 complete 4-bit membership masks (including no candidates) on all 775 NY dates. Assert expected original counts 212 Direct, 205 FVG, 116 OB, 84 Breaker and union 212 to detect any drift of frozen implementation. No external source or unsealed holdout, no new model settings or downstream orders.
