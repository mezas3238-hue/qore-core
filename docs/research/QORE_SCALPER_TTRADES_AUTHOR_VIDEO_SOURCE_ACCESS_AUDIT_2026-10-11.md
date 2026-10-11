# Auditoría de disponibilidad de VIDEO ORIGINAL TTrades — 2026-10-11

**NO reclamar que se visionaron o transcribieron íntegramente los vídeos.** Investigación PR #784: https://github.com/mezas3238-hue/qore-core/pull/784

## Fuentes primarias escritas LEÍDAS y comprobables

1. A0: https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/ (07-feb-2026) — el autor explica Daily contexto, H1 C2/C3 bias, M15 swing, M1 ejecución, SL protected, objetivos HTF.
2. A1: https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/ (10-ene-2026) — CISD lower dentro HTF y cierre C2/C3 HTF, ausencia => sin continuación.
3. A2: https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/ (29-jun-2025) — CISD primera apertura serie bullish/bearish.
4. A3: https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/ (01-jul-2025) — MSS displacement+close through swing ≠ CISD.
5. A4: https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/ (07-ago-2025) — swing protegido e invalidación estructural, alternativas wick/body.
6. A5: https://ttrades.com/using-order-blocks-for-continuations/ (01-ago-2025) — POI, serie de velas contrarias, retest y objetivos HTF.
7. A6/A7 Candle2/3: https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/ y https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/.

## Vídeos originales: URL verificada, contenido completo y timestamps NO VERIFICADOS

- **A0 vídeo scalping**: https://www.youtube.com/watch?v=eywpZT3z6GQ
- **A1 validación CISD swing**: https://www.youtube.com/watch?v=vn1RYjhJUnQ
- Se consultó la funcionalidad de transcripción del conector vidIQ para **ambos vídeos** durante 2026-10-11. En ambas consultas, el conector respondió **«Not enough credits», «No credits were charged», «Credits refresh on Oct 28»**. Su instrucción explícita fue **«Do not retry this tool»**. Se respetó el bloqueo. **No se recuperó una transcripción con marcas temporales en esta ronda**. Este evento es una limitación de acceso a la fuente audiovisual, no una refutación del método, ni una ausencia de vídeo/captions.
- Si se obtiene acceso autorizado al contenido audiovisual, registrar por cada ejemplo: URL, timestamp min:seg, captura o transcripción precisa con provenance, par, timeframe, candle closes, serie CISD, swing confirmado, entrada, stop, target, momento de conocimiento y juicio autor-explicito / interpretado; el review posterior NO modifica los resultados económicos que ya se hubiesen visto.

## Estado testificado por código / CI
[GitHub Actions #38158101874 — 1 job SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38158101874): **6/6 tests de control aprobados**, contrato con 15 reglas, 8 URLs de fuente primaria, **47 motivos de no autorización** y economic_replay_authorized=false. [Artefacto del control #11709217470](https://github.com/mezas3238-hue/qore-core/actions/runs/38158101874/artifacts/11709217470). El PASS significa **la compuerta bloquea como debe**; no equivale a «fidelidad certificada».

Hasta que los TT02–TT15 sean adjudicados con evidencia y exista test first-online independiente y cohorte OOS protegida, AUTHOR_FIDELITY_NOT_CERTIFIED / NO_ECONOMIC_REPLAY. Contratos nuevos solo con trazabilidad, nunca proxy presentado como autor.
