# VT31 — Preregistro L3: paridad replay cronológico 1× frente a 32× (sólo fuente) · 2026-10-14

**PRE-CODE / PRE-DATA**. Esta versión queda preregistrada antes de implementar el experimento o consultar sus resultados.

## Posición legal de la prueba
- La fuente de verdad L1–L10 es `docs/architecture/QORE-TRADER-LAB-001.md`, Issue #473 y `trader_lab/{lifecycle,fast_forward,promotion}.py`.
- Este experimento es una **prueba preparatoria L3 SOURCE-ONLY**. NO invoca `qualify_trader_lab_fast_forward`, NO construye una falsa `TraderLabCandidateBinding`, NO transita estados del Trader Lab y **NO** aprueba oficialmente L1/L2/L3. Sin metodología íntegra congelada + ejecución de broker, no existe un replay económico genuino que cualificar.
- Base de código research de la PR #936 commit `91571de79a17cab7556d15ea2bc209700a60a611`, con productores M2/M3 #933, censo #934 y witness M4/M5 #935. G3 COG/OPS/acta fuentes originales bloqueadas por sus blob SHA. Reglas no se recalibran tras ver datos.

## Datos y evaluación congelados
- Único archivo original NAS100 CFD 3Y de GitHub Actions artifact `11459859004` (run 38018856150), **1.059.784 M1**, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. Ya analizado, **no Fresh Holdout**.
- Universo: cada NY-day con 09h o 10h en fuente original; horas 09:00–11:00 locales e inclusiones idénticas al censo #934. M1 event `available_at = closed_at`; entrada y fuente de referencia sólo M1 cerrado por hora; no vectorización con velas futuras visible en decisión.
- Comparar: ruta A censo batch ya documentado `scripts/vt31_m4_m5_ttrades_census_20261014.py::census`; ruta B productor incremental recibe cada una de las 120 M1 cerradas y conserva el **primer barrido/regreso + MSS** terminal. Nunca rescatar más tarde un regreso sin MSS. Para candidato válido, calcular witness M4/M5 en cada M1 posterior **exclusivamente con prefijo visible al cierre**; guardar el estado de fuente final.
- La ruta B simula avances explícitos de reloj externo: `factor=32`, por cada M1 de duración 60s, avance wall del runner = 1.875s frente a 60s del runner 1×; el **simulated_now** conserva el exacto `closed_at` real y mismo orden 120×N. No medir esto como una mejora real de latencia ni inferir fill, sólo verificar schedule determinista con relojes manuales.
- Identidad de experimento no es `TraderLabCandidateBinding`; `SOURCE_PARITY_EXPERIMENT_ONLY`. Registrar SHA256 de entradas, reporte de diferencias primera divergencia, sha de ledger idéntico por día/case, conteos, factor, instantes y manifest.
- Fallo si cambio de 1 bar, skip, duplicado, desorden, `available_at > simulated_now`, fuente futura, discordancia de casos, población 775/128/119 o de M5 [61,31,27]. No imputar datos ni rescatar por resultados.
- No PnL, PF, WR, DD, Sharpe, Stop broker/tick, LOT, OMS/ACK, LIVE, VPS, merge, OOS. CIBO sizing exclusivo. Gate L3 oficial permanece `NOT_QUALIFIED` hasta L1/L2 y exact candidate binding, replay integral, firma y aprobación.

## Tests prometidos antes de ejecutar
1. Trayectoria positiva sintética y días incompletos vs censo batch, 1× vs 32× idénticos.
2. DST NY verano e invierno y numeración de 120 source-M1 válidos.
3. Fuga temporal futuro/avail-before, duplicados, out-of-order, huecos sin `NO_TRADE` falso; fail closed.
4. Baseline original exacto: 775 días, 128 contextos, 119 geometrías FVG, 61 touch sin fill, 31 mismo M1 ambiguo, 27 expiran; igualdad de reporte canonical `cognitive_case_evidence` y categorías M2/M4/M5.
5. Blob SHA original G3, CI Ruff + py_compile + pytest familia #932–#935 + pruebas nuevas + evidence ZIP SHA256.
6. **No promover** por este ensayo: verificador exige `trader_lab_L3_qualified=false`, `candidate_binding_present=false`, `entry_fills=0`, `economic_results=null`.

Defecto observado que obliga a fallar bloqueado (no adaptar datos): si el coste/tiempo de ejecutar CI no permite verificar el corpus exacto, informar `BLOCKED_INCOMPLETE_PARITY_RUN`, no inventar PASS.
