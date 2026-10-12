# QORE Native H3 NAS100 NY Cash Open — ejecutado y NO_SUPPORT

**12-10-2026 UTC.** [PR #827](https://github.com/mezas3238-hue/qore-core/pull/827), [Actions exact-head #38205479893](https://github.com/mezas3238-hue/qore-core/actions/runs/38205479893) **2/2 success**, tested SHA `192a6be3149ffb4142708a1b7cbb638dfa6af23c`; prereg antes OHLC: SHA `4b26a2da961da6f778028835efaa7ea899ebda9d`. [JSON original artifact #11726953538](https://github.com/mezas3238-hue/qore-core/actions/runs/38205479893/artifacts/11726953538), SHA256 manifest outcomes `a1dd21e7cb3465c9f6e6b3c9cb4407c5896d722c6f4a70b8115a2c4fe45b149f`.

Hipótesis precongelada: NAS100 CFD proveedor USTEC original cTrader DEMO 10Y M5, señal sign de dirección 09:30–10:00 America/New_York frente a señal premarket 09:00–09:30, ambas comparadas con referencia OHLC 10:00–12:00 NY de la misma fecha. Exacta continuidad de 6/6/24 barras M5 NY/DST, sin inventar sesiones broker ni fills. Rango data development [2016-09-17,2022-09-17), diagnostic [2022-09-17,2024-09-17), precios posteriores embargados. 11 originales raw+quality year SHA previos a lectura OHLC.

| Medida pre-registrada | Development | Temporal diagnostic |
|---|---:|---:|
| n pares de días | 1.533 | 509 |
| n semanas ISO NY para bootstrap | 313 | 105 |
| media estrategia gross bps | +2,456753 | +2,852094 |
| media premarket control gross bps | +2,034692 | +0,206153 |
| delta pareada gross bps | +0,422061 | +2,645942 |
| IC **98,333%** bootstrap semanas 2000 seed 20261012, delta | [−4,665549; +5,659497] | [−6,699434; +12,518373] |
| IC 98,333% gross | [−0,938708; +5,636504] | [−3,139796; +8,778855] |
| Long / short | 811 / 722 | 275 / 234 |
| fraction positive gross | 51,9243% | 49,9018% |
| break-even mean total RT hipotético bps | 2,456753 | 2,852094 |
| mean gross menos **1bps RT supuesto** | +1,456753 | +1,852094 |
| mean gross menos **3bps RT supuesto** | −0,543247 | −0,147906 |
| Dictamen decisivo | **NO_SUPPORT** | **NO_SUPPORT** |

**Cobertura:** 2.064 NY días con al menos una barra requerida; 2.042 días de señales pareadas, 22 excluidos por falta de bloque o direcciones cero; 560.059 timestamps en segmento preembargo. Intervalos delta y media gross **incluyen cero**, pese a promedios positivos, por lo que **NO existe edge robusto demostrado**. No rescatar esta regla cambiando NAS100 a US30, cambiando la ventana o incorporando filtros retrospectivos. El supuesto RT 0bps es **solo referencia matemática bruto**; ninguna cifra es spread/commission/slippage real IC Markets. A mayor estrés, el break-even medio de 2,46/2,85bps se vuelve negativo a 3bps. No certificar netos ni PF/Sharpe operables.

Tres intentos independientes, registrados y cerrados **NO_SUPPORT**: #822 EURUSD H4, #825 XAUUSD H4, #827 NAS100 NYC Open. Alfa nominal prereg tercera prueba 1/60 (CI98,333), no FWER global (historial RESET/DRIVE anterior). **Noticia histórica as-of no validada**, estudio macro-unfiltered, no apto para sistema QORE Native NO-NEWS. Embargo OHLC 2024-2026 permanece. 0/3 traders certificados, ninguna orden, sin VPS/MT5/CIBO/Shared/QDLE/LIVE.

**Prioridad siguiente:** completar G0 restantes y dejar de inventar o escanear parámetros para salvar hipótesis fallidas; diseñar hipótesis verdaderamente causales con potencia/costes estimados antes de abrir retornos.