# VT08 R33 — Verificación independiente de 316 rupturas R25 contra M3 RAW

Fecha: 20-oct-2026. Fuente: 5 ZIP originales R25 (run 39338842612) + 5 ZIP M3 nativos (run 35941643396), descargados de GitHub Actions, sin PnL.

## Método
Para cada uno de los 2.657 `case_id_sha256` oficiales R25, seleccionar los 316 con `post_cisd_lower_than_reanchored_low=true`. Buscar por `first_new_low_after_reanchor_closed_at_utc` una barra real del M3 RAW del mismo mercado, y contrastar `bar.low < reanchored_as_of_cisd_closed_low` usando Decimal (comparación estricta, no aproximada). Validar que el cierre de esa barra sea posterior a `first_cisd_closed_at_utc` y anterior o igual a `c3_decision_at_utc`. No interpolar velas, no confundir timestamps de apertura y cierre.

| Mercado | Breaches R25 | Barra M3 presente | Low inferior al ancla | Reloj causal válido |
|---|---:|---:|---:|---:|
| EURJPY | 74 | 74 | 74 | 74 |
| USDCHF | 60 | 60 | 60 | 60 |
| NZDUSD | 53 | 53 | 53 | 53 |
| CADJPY | 64 | 64 | 64 | 64 |
| USDCAD | 65 | 65 | 65 | 65 |
| **TOTAL** | **316** | **316** | **316** | **316** |

**0 fallos de reloj, 0 source bars ausentes, 0 violaciones de comparación.** Esto demuestra el hecho físico de la ruptura bajo el ancla corregida de R25. NO demuestra invalidación de un Protected Swing TTrades auténtico, ni un nuevo CISD, ni POI importante, ni un trade, ni rentabilidad. El caso NZDUSD de R32 sigue con hueco C3 posterior al breach; el breach concreto sí fue contrastado con su barra original.

## Evidencia y continuidad
Script de reproducción `vt08_r33_breach_native_verification.py` y JSON `vt08_r33_native_breach_verification_2026-10-20.json` entregados como archivos de sesión; no subir RAW licenciado. Los IDs y timestamps de diez ejemplos están en el JSON. Para repetir: descargar los diez ZIP con IDs documentados R26/R31, colocar en directorio indicado por `VT08_ARTIFACT_DIR` y ejecutar `python vt08_r33_breach_native_verification.py`. Se requieren auditoría semántica de PS/POI/CISD por fuente, dos revisores genuinos y Gates económicos preregistrados.

Estado: **VT08_NOT_CERTIFIED**. Sin merge, LIVE/DEMO/VPS, sizing, holdout 7Y ni QORE-alpha.