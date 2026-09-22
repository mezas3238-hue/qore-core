# VT-08 Revision 3.2 — Ambiguity Register

Status: frozen unresolved methodology. These items may not be resolved from P&L.

| Topic | Current state | Allowed treatment | Prohibited treatment |
| --- | --- | --- | --- |
| shallow vs large boundary | source qualitative, no numeric threshold | retain qualitative evidence or separately version an `EXPERIMENTAL_FORMALIZATION` | claim wick %, ATR, or fixed ratio is TTrades source rule |
| entry-family priority | unresolved universally | retain multiple candidates; require source/Owner adjudication before daily selection | silently choose first found / best P&L |
| protected-swing priority | multiple valid protected swings can coexist | preserve identities/provenance and abstain/contain if execution needs unresolved choice | nearest/best retrospective swing |
| target-family priority | context-dependent, not universal | retain compatible target candidates and coherent bundle provenance | always 2R / best historical target |
| body-low stop applicability | family exists but universal conditions are unresolved | admit only with source-bound example/rule provenance | apply body-low stop to every family |
| SMT algorithm | concept present, executable definition unresolved | research register only | mandatory filter or synthetic divergence formula |
| failure swing algorithm | concept present, exact universal algorithm unresolved | research register / structural provenance only | retrospective best level selection |
| T-spot algorithm | concept present, exact executable algorithm unresolved | research register only | mandatory entry filter |
| expansion-met-with-expansion | concept present, exact algorithm unresolved | retain source observation and falsification cases | invented threshold/indicator |
| daily setup priority | source does not define a universal winner among complete same-day opportunities | explicit `OWNER_EXECUTION_POLICY` required if a deterministic priority is adopted | relabel Owner policy as TTrades source rule |
| M15 vs M5 vs M3 | independent profiles | run separately and label results | use one timeframe to retroactively confirm another |
| source timing vs Owner timing | separate profiles | source-complete and Owner-subset backtests remain separate | merge statistics without profile identity |

## Hard containment

Where an ambiguity is necessary to create executable geometry and no source-coherent bundle resolves it, the candidate may remain diagnostic but must not become a selected executable setup.

No ambiguity may be resolved using later stop/target outcomes, same-day hindsight, future candles, or fresh-holdout performance.
