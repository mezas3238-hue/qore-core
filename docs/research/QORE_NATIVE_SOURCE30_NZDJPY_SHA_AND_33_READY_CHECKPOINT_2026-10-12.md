# QORE Native — Checkpoint incremental 30/33 + NZDJPY G0 individual (sin sobredeclarar 33)

**2026-10-12 UTC, solo investigación GitHub.** Respuesta al Owner: continuar auditando 33 instrumentos mientras captura #38193802541 sigue activa, sin esperar a BID/ASK históricos ni comerciar.

## Evidencia G0 disponible hoy

| Fase | Prueba GitHub | Fuentes | M5 originales | Estado |
|---|---|---:|---:|---|
| 12 CIBO DEMO iniciales | G0 [#816](https://github.com/mezas3238-hue/qore-core/pull/816), G0B [Actions #38201368296](https://github.com/mezas3238-hue/qore-core/actions/runs/38201368296) | 12 | 8.726.985 | SHA verificado |
| Original + primeros 11 nuevos | [PR #821](https://github.com/mezas3238-hue/qore-core/pull/821), [Actions #38202227551](https://github.com/mezas3238-hue/qore-core/actions/runs/38202227551) | 23 | 16.924.567 | Manifest 23 G0 |
| + GBPNZD AUDCAD AUDCHF | [PR #823](https://github.com/mezas3238-hue/qore-core/pull/823) | 26 | 19.160.586 | Manifest 26 G0 |
| + AUDNZD | [PR #824](https://github.com/mezas3238-hue/qore-core/pull/824) | 27 | 19.905.871 | Manifest 27 G0 |
| + CADJPY CADCHF | [PR #826](https://github.com/mezas3238-hue/qore-core/pull/826) [Actions #38205083910](https://github.com/mezas3238-hue/qore-core/actions/runs/38205083910) 4/4 pass | 29 | 21.396.360 | Manifest 29 G0 |
| + CHFJPY | [PR #828](https://github.com/mezas3238-hue/qore-core/pull/828) [Actions #38205741712](https://github.com/mezas3238-hue/qore-core/actions/runs/38205741712) 3/3 pass | **30** | **22.141.699** | **Último manifiesto G0 firmado: #11727276821** |
| NZDJPY 10Y | [PR #829](https://github.com/mezas3238-hue/qore-core/pull/829), [Actions #38206111777](https://github.com/mezas3238-hue/qore-core/actions/runs/38206111777) matriz individual pass | +1 archivo | 745.313 | **G0 SHA individual solamente, NO está aún dentro del manifiesto 30** |

La fuente de NZDJPY fue reaudita contra RAW y QUALITY SHA originales 11 particiones, identidad cTrader IC Markets DEMO, cronología M5; ejecución exacta `e91ddf9e512d4e481b0754cc47cfa591042c53f4`; [testigo original #11727566371](https://github.com/mezas3238-hue/qore-core/actions/runs/38206111777/artifacts/11727566371). Los tres datasets no incorporados aún al manifiesto 30 son NZDJPY, NZDCAD, NZDCHF; dos no publicaron artifact al último chequeo.

**No afirmar 31/33 ni 33/33 con solo NZDJPY:** existe auditoría individual válida NZDJPY, pero el manifiesto oficialmente integrado sigue **30 fuentes** hasta producir union 33, por ser un contrato que exige exactamente 3 nuevos SHA witnesses.

## Pipeline final fail-closed ya implementado

- [PR #829](https://github.com/mezas3238-hue/qore-core/pull/829), rama `research/qore-native-final33-tail-ready-g0-20261012`.
- Código `src/qore/infrastructure/trader_lab/qore_native_final33_three_m5_g0_v1.py` congela 30 source IDs y sha parent: manifest `96b6709022905215d582abdc20edb452c7766dd42fd945e76144de8a29d29283`; exact HEAD `7c41bc4d0b135efb0885c17bafe9869342a5c377`, fuente original 30 M5 22.141.699.
- CI `.github/workflows/qore-native-final33-m5-g0.yml`: source tests → catálogo de artifacts fuente de corrida #38193802541 (sin OAuth) → audita **cada fuente realmente publicada** con 11× RAW+quality SHA → gate final. **Sólo si NZDJPY, NZDCAD, NZDCHF pasan las 3 auditorías en el MISMO workflow run**, generará `qore-native-complete33-source-m5.json` y su `OUTPUT_SHA256SUMS.txt`.
- Primera ejecución [#38206014020](https://github.com/mezas3238-hue/qore-core/actions/runs/38206014020) verificó contrato y bloqueó correctamente el 33 por falta de artifacts. Actualizada [#38206111777](https://github.com/mezas3238-hue/qore-core/actions/runs/38206111777) aprobó contrato y presencia, y auditó NZDJPY, bloqueando la publicación por NZDCAD/NZDCHF ausentes.
- **Cuando se publiquen los dos archivos faltantes**: volver a verificar su presencia original, activar una nueva ejecución del workflow con commit de trigger bajo `docs/research/QORE_NATIVE_FINAL33_RECHECK_TRIGGER_2026-10-12.md` (path específico habilitado en el workflow); el nuevo run audita los tres simultáneamente desde fuente original y da 33 si/no con SHA. No re-descargar manualmente ni fabricar manifest; no interpretar un CI preflight GREEN con trabajos de unión SKIPPED como 33 PASS.

## Investigación económica / stop rule

Tres hipótesis originales ensayadas y **tres NO_SUPPORT**, documentos resultados originales sin cambios de parámetros posteriores:
- EURUSD persistencia H4 [#822](https://github.com/mezas3238-hue/qore-core/pull/822) n=1526/510, CI95 delta contiene cero.
- XAUUSD reversión H4 [#825](https://github.com/mezas3238-hue/qore-core/pull/825) n=1480/495, IC97.5 delta contiene cero.
- NAS100 continuación tras open NY [#827](https://github.com/mezas3238-hue/qore-core/pull/827), gross media +2.457/+2.852bps (dev/diagnóstico), pero delta frente a premkt +0.422/+2.646 y **IC98.333 delta cruza cero** (n=1533/509). Resultado NO_SUPPORT; NO afirmar ventaja por bruto positivo.

No optimizar horarios, par o dirección de esos tres para rescatar resultados: ese barrido introduciría sesgo de multiplicidad y falsa robustez. No se han consultado OHLC 2024-09-17→2026-09-17 en esos motores. Aun con fuente completa 33, solo será G0 de M5: faltan spreads BID/ASK históricos, broker calendario/sesiones/ejecución real, noticia histórica known-as-of, stops/fills, y testeo neto verdadero. El programa admite gross pre-registrado y stress de coste **hipotético** sin falsear spread 0.

**Estado operativo:** 0/3 traders Native certificados, sin CIBO, Shared, QDLE, VPS, MT5 ni LIVE modificados, investigación únicamente en ramas DRAFT (sin merge).
