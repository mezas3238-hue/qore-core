# QORE NATIVE — G0 12 activos M5 originales ejecutado y reproducido

**2026-10-11 America/Asuncion (GitHub Actions 2026-10-12 UTC).** Dictamen: `G0_12_OF_12_ORIGINAL_M5_SOURCE_PASS` en ámbito de estructura/integridad; `G1_ECONOMICS_NOT_AUTHORIZED`. Sin señales, precios analíticos, PnL ni promoción.

**Preregistro fechado y congelado ANTES de examinar nuevos resultados:** [QORE_NATIVE_EXISTING12_M5_G0_PREREG_SOURCE_ONLY_2026-10-11.md](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-existing12-m5-g0-normal-regimes-20261011/docs/research/QORE_NATIVE_EXISTING12_M5_G0_PREREG_SOURCE_ONLY_2026-10-11.md), commit `7309ac368e2ba306bda311d73a1b13692872d825`. Diseño de 12 fijo, sin sustituir mercados ni crear OHLC sintético.

## 1. Evidencia original y nuevo testigo

**Fuentes:** [Atlas producer Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), producer commit `ab782b8e9f890f86a2b6500070f0556b4b685e3d`, [aggregate original #10476615509](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458/artifacts/10476615509), aggregate manifest SHA256 `47f5763d7ea2c10dd32fa40a84d7480c8124f1a512b623c1299ef2ba7b8c51c2`. Cada uno de los **12 artefactos M5 diez años** del productor fue recuperado de ese run, no se llamó a cTrader ni se mezclaron las 21 descargas nuevas.

**Auditoría independiente** [GitHub Actions **#38196127168**](https://github.com/mezas3238-hue/qore-core/actions/runs/38196127168), commit probado **`1336a86ff4d9ef1a076fc7cfc1803590580de159`**. Trabajos **14/14 SUCCESS**: calidad + 12 archivos de símbolos + cierre agregado. Contrato Ruff y Pytest PASS. **8.726.985/8.726.985** M5 recontadas, 11 particiones anuales por símbolo, 12×11=**132 raw SHA256** revalidados, así como 132 SHA de calidad y 132 manifest SHA originales. Mismatches por recuento/identidad/orden UTC/doble timestamp: **0** en el pase completo.

**Resultados exactos** [artifact agregado **#11723327973**](https://github.com/mezas3238-hue/qore-core/actions/runs/38196127168/artifacts/11723327973), `existing12-M5-G0-final.json`, SHA256 **`b701075c24fa899e05e833f0940b034c70a70d6d91790f8622448a9c34281050`**, cotejado localmente contra su `OUTPUT_SHA256SUMS.txt`. También 12 artifacts individuales por mercado en la misma acción, cada uno con 11 años de SHA y métricas UTC.

## 2. Presencia de timestamps M5 — NO señal, NO sesión del broker

| Mercado | M5 originales recontadas | UTC H4 completas (48/48 M5, bloque activo) | UTC D1 completos (288/288 M5, día activo) |
|---|---:|---:|---:|
| AUDJPY | 745.468 | 14.881 | 1.945 |
| AUDUSD | 745.283 | 14.760 | 1.835 |
| EURUSD | 745.458 | 14.867 | 1.932 |
| GBPJPY | 745.478 | 14.916 | 1.979 |
| GBPUSD | 745.274 | 14.804 | 1.871 |
| NAS100 / USTEC | 701.457 | 12.681 | **0** |
| SP500 / US500 | 693.064 | 11.431 | **0** |
| US30 | 700.856 | 12.592 | **0** |
| USDCAD | 745.088 | 14.722 | 1.797 |
| USDJPY | 745.327 | 14.832 | 1.899 |
| XAGUSD | 706.516 | 12.417 | **0** |
| XAUUSD | 707.716 | 12.762 | **0** |
| **TOTAL** | **8.726.985** | — | — |

**Matiz de calidad clave:** `H4_UTC` y `D1_UTC` son **bitmaps de disponibilidad M5 en intervalos del calendario UTC**, *NO* velas H4/D1 del broker ni calendario de sesiones de IC Markets. **0 días UTC completos para índices/metales NO significa cero días comerciables**: estos CFDs no publican 288 M5 diarias por sus pausas de sesión/horarios/cierres. No rellenar los huecos con interpolación, valores cero o forward-fill, ni descartarlos como corrupción. H4 UTC parcial tampoco es prueba automática de feed defectuoso. Día de 288 M5 es una observación exigente que mezcla cierres de mercado y pérdidas de feed; existe `UNVERIFIED_BROKER_SESSION_CALENDAR`. Todo H4/D1 real requiere reloj de mercado fuente/autorizado, DST y cierres reales.

**FX:** ~745k M5 por mercado; miles de bloques H4 completos disponibles para investigación, sin que esto implique miles de trades independentes. Requerirá N efectivo por día/semana, variación de spread y exclusión macro conocida as-of. Las cifras de H4 completas no afirman M1 (9/12 tienen M1 original 10Y, SP500/US30/XAGUSD no la tienen en el conjunto CIBO original).

## 3. Selección científica a continuación (NO grid de retorno)

**Primera investigación recomendada tras G0:** pre-G1 normal-regime **UNA** hipótesis de horizonte multihora en **una clase predefinida**, p. ej. FX líquido (EURUSD/GBPUSD) o índices US en sesiones verificadas, justificada por mecanismo y acceso a precios ejecutables; aún no se ha elegido ni operado una regla. Priorizar:
1. verificar fuente broker real, horarios de sesiones y rollover (UTC/NY/broker), segmentación de calendario conocido antes de decisión para evitar exposición no autorizada a macro alto impacto; huecos conocidos vs feed real ausente;
2. costes BID/ASK por activo y tramo + comisión + slippage + conversion/tick/lot, sobrevivencia stop al ensanchamiento spread; no usar 0 por falta de coste;
3. una hipótesis con lado, entrada, gestión de tiempo, stop, target o vencimiento, baseline causal, magnitud económica suficiente, potencia y splits cronológicos declarados antes de PnL; evitar buscar la mejor regla de 12 mercados y muchas duraciones.
4. 12 M5 diez años son datos históricos consumidos por distintos trabajos CIBO. Ningún holdout se etiqueta *virgen* por defecto; mapear reutilización antes de G1/OOS.

**Segunda cohorte:** 21 restantes del cupo 33 [PR #811](https://github.com/mezas3238-hue/qore-core/pull/811) **no fueron incorporados ni certificados en este estudio**; se ejecutará G0 de nuevos artifacts y se comparará manifest fuente únicamente cuando existan realmente y tengan SHA. No inferir de un workflow `queued` que se completó.

**Dictamen formal:** `SOURCE_INTEGRITY_PASS_12_OF_12`, `H4_D1_TIMESTAMP_PRESENCE_MEASURED`, `BROKER_SESSIONS_UNVERIFIED`, `SPREAD_COST_UNKNOWN`, `G1_NOT_AUTHORIZED`, `ZERO_EDGE_MEASUREMENTS`, `ZERO_TRADERS_CERTIFIED`. Investigación solo GitHub, cero live/VPS/MT5/CIBO/Shared.
