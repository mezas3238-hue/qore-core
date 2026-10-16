# VT31 — M2 real: procedencia contextual QORE DOL en las TRES ventanas, evidencia NAS100 1.059.784 M1

**16 de octubre de 2026 — INFORME DE AUDITORÍA, NO certificado ICT/TTrades.** Un único `VT31Trader` original, G3/M0 strict PRECOG de [PR #989](https://github.com/mezas3238-hue/qore-core/pull/989), distinto de las adjudicaciones documentales M3–M5 de [PR #991](https://github.com/mezas3238-hue/qore-core/pull/991). Este expediente se emite sin órdenes, sizing, PnL ni holdout.

## Fuente, prereg y primera corrida exitosa

[**GitHub Actions #38975489319 SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38975489319), commit de ejecución `0b9ea6fc8769291e9f768c72e7f11b5cf5bb7026`, **127/127 pytest PASS + Ruff PASS**, NAS100 original **1.059.784 M1** fuente SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. Cohorte independiente sellada **775 días NY ×3 = 2.325 expedientes**, ledger abierto solamente después de consumir todo el histórico. Preregistrado **ANTES del código** commit `2e24b6ac2f08644441116d1df1f27ef8e011e161`. Source COG blob `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9` y OPS blob `0ce9707314aecb71155de8b57044b6ec028847b2` intactos.

**[Artefacto primera corrida #12079415451](https://github.com/mezas3238-hue/qore-core/actions/runs/38975489319/artifacts/12079415451)**, ZIP SHA256 `69665375034348ce14c1c91537ec8ea28279e4d80019fc6db031c22e202a4c46`; full-casebook 2325 JSON SHA `0429096009dbd1170a79c976fc9ce9167bff12496df3f54debf7df5fff700cab`. La segunda versión añade testigos fechados del mismo algoritmo SIN modificar decisiones; **su SHA puede cambiar por los campos adicionales** y tendrá otro CI artifact, no se debe pretender que los hashes anteriores y nuevos sean iguales.

## Resultado de la primera vela cerrada de cada sesión (03:01 / 10:01 / 14:01 NY)

| Sesión | `CONFIRMED` QORE source-only | `UNKNOWN` | `REJECTED` | sin primera M1 | primera M1 presente | G3 DTO positivo (NO trades) |
|---|---:|---:|---:|---:|---:|---:|
| London ICT-general | 283 | 489 | **2** | 1 | 774 | 398 |
| NY AM TTrades | 97 | 668 | **8** | 2 | 773 | 203 |
| NY PM ICT-general | 65 | 670 | **8** | 32 | 743 | 160 |
| **Total** | **445** | **1.827** | **18** | **35** | **2.290** | **761** |

Descomposición exacta de las **761 hipótesis positivas G3 en el primer minuto M1**: **445** niveles QORE reconciliados con source M1 y no consumidos, **298** con disponibilidad temporal no demostrable por M1 incompleta (113 London + 98 NY AM + 87 NY PM), **18** desacuerdos temporales REJECTED. Los otros **1.529 UNKNOWN** no tenían DTO válido (incluye fuente M0 WAIT); no confundir ausencia de DTO con error de precio. No son 761 operaciones ni 445 setups ICT válidos: son un muestreo de primer minuto de cada día y ventana.

**Causa común de los 18 `REJECTED`: `COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE`.** COG sitúa la observación del nivel antes de cerrarse el intervalo de fuente reconstruido independientemente. Es un problema de coherencia documental/temporal **potencial**, que debe adjudicarse caso a caso: puede ser semántica incorrecta del campo `draw_level_observed_at`, no necesariamente una señal adelantada o una transacción. **No** se debe modificar G3 congelado para hacer desaparecer los 18 casos. Se abrió el [**Issue P0 #994**](https://github.com/mezas3238-hue/qore-core/issues/994) con contrato para reconstruir cada fecha, familia, nivel, end fuente y adelanto temporal.

## Hallazgo de reloj y anticontaminación metodológica

Para London a las 03:01 NY la fuente contextual `LONDON_NY_CLOCK` abarca 03:00–05:00 NY: **en las 774 sesiones con primera vela vista** sus dos niveles HIGH/LOW quedaron `UNKNOWN` y sin nivel, como exige causalidad. El rango 03–05 sí puede estar completo al NY AM 10:01 y NY PM 14:01, pero su estado sigue dependiendo del toque/consumo y de gaps posteriores. La H1 09:00 TTrades solo interviene en NY AM, nunca se hereda a London/NY PM.

El `PRIOR_NY_CASH_SESSION` contextual no tiene evidencia suficiente de continuidad para declarar `UNCONSUMED` en numerosos casos: el auditor presenta `UNKNOWN` en lugar de inventar un holiday calendar de NAS100 CFD ni dar liquidez libre por supuesto. Los 35 `NO_FIRST_M1` tampoco son broker CLOSED sin metadata PIT.

## Gates que esta evidencia NO cierra

- `M0`: método ICT/TTrades en PREDECLARED research, **sin firma Owner**.
- `M1`: histórico real y reloj DST, pero 41 contextos fuente incompletos, sin calendario broker PIT.
- `M2`: **source facts QORE** probados para 445 DTOs, 298 fuente incierta y 18 REJECTED; **ICT-general London/PM DOL autoral y TTrades NYAM fuente H1 opuesta NO CERTIFICADOS**.
- `M3`: MSS displacement/CISD y swing confirmado no homologados a fuente.
- `M4`: FVG/OB/Breaker y cuatro modalidades TTrades siguen fuentes pendientes.
- `M5`: swing causante/displacement-stop pendiente sin sizing.
- `M6`: dos revisores humanos independientes COG+OPS [#897](https://github.com/mezas3238-hue/qore-core/issues/897), sin firma.
- `M7`: tres subcertificados separados London / NY AM / NY PM y autorización de integración formal pendientes.

**DICTAMEN:** `M2_REAL_QORE_SOURCE_PROVENANCE_CENSUS=PASS_RESEARCH_ONLY`; `M2_AUTHOR_METODOLOGIA=BLOCKED`; `LONDON_CERTIFIED=FALSE`; `NYAM_CERTIFIED=FALSE`; `NYPM_CERTIFIED=FALSE`; `VT31_CERTIFICADO=FALSE`. No merge a main, no broker, ni órdenes, ni sizing, ni métricas económicas para certificar.

## 6. EXPEDIENTE FECHADO COMPLETO de los 18 `REJECTED` — causa más precisa

**[CI final #38975891228 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38975891228)**, commit ejecutado `a4d8cc4ad4efe245e024a1787d3a0c24cb6c5839`, **127/127 pytest**, Ruff PASS. **[Artifact #12079131643](https://github.com/mezas3238-hue/qore-core/actions/runs/38975891228/artifacts/12079131643)**, ZIP SHA256 `30de8306225941208ecea73ab4b9ba9b88b625b8b1e9794f47c758ea3fdce07a`. Casebook extendido con observación y cierre nominal del rango DOL: SHA256 `d74b24242c4b8c5656547727b88886ecd1a18243c362d9d366825880bddbfc21`. Las tasas permanecen **exactamente iguales** a la primera CI. El SHA anterior es distinto porque este segundo casebook incluye columnas adicionales de procedencia, **no porque hayan cambiado gates o resultados**.

**Advertencia interpretativa P0:** el helper independiente `vt31_ict_dol_source_v1_20261014.py` define `PRIOR_NY_CASH_SESSION` como `_previous_weekday(day)`, o sea **día hábil nominal inmediato anterior**, con intervalo 09:30–16:00 NY. Los **18** REJECTED tienen TODOS familia `PRIOR_NY_CASH_SESSION_{HIGH|LOW}` y timestamp original G3 más antiguo que el cierre del día nominal inmediatamente anterior. Así, `COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE` es **la etiqueta técnica del tribunal al contrastar dos políticas de selección de día**, **NO prueba de acceso de G3 al futuro**: G3 podría usar el último cash real completo observado previamente y el auditor requerir el último weekday aunque fuera festivo/incompleto. Ambos deben reconciliarse con calendario point-in-time símbolo/bróker y semántica de `draw_level_observed_at` antes de adjudicar falsos históricos. Prohibido declarar fraude/lookahead o corregir G3 core sin esa evidencia.

| Fecha NY | Ventana | G3 observó nivel cash en UTC | Cierre cash nominal anterior UTC | Diferencia (min) | Precio G3 |
|---|---|---|---|---:|---:|
| 2023-10-13 | NY AM | 2023-10-10 20:00 | 2023-10-12 20:00 | 2.880 | 15040.60 LOW |
| 2023-11-08 | NY PM | 2023-11-03 20:00 | 2023-11-07 21:00 | 5.820 | 14964.30 LOW |
| 2023-11-27 | NY AM | 2023-11-22 21:00 | 2023-11-24 21:00 | 2.880 | 16122.80 HIGH |
| 2023-12-14 | NY AM | 2023-12-12 21:00 | 2023-12-13 21:00 | 1.440 | 16175.80 LOW |
| 2023-12-27 | NY PM | 2023-12-22 21:00 | 2023-12-26 21:00 | 5.760 | 16697.10 LOW |
| 2023-12-29 | NY AM | 2023-12-27 21:00 | 2023-12-28 21:00 | 1.440 | 16856.10 LOW |
| 2024-01-16 | NY PM | 2024-01-12 21:00 | 2024-01-15 21:00 | 4.320 | 16900.10 HIGH |
| 2024-05-28 | NY AM | 2024-05-24 20:00 | 2024-05-27 20:00 | 4.320 | 18666.13 LOW |
| 2024-06-20 | NY AM | 2024-06-18 20:00 | 2024-06-19 20:00 | 1.440 | 19848.46 LOW |
| 2024-12-26 | NY PM | 2024-12-23 21:00 | 2024-12-25 21:00 | 2.880 | 21188.95 LOW |
| 2025-07-04 | NY AM | 2025-07-02 20:00 | 2025-07-03 20:00 | 1.440 | 22440.00 LOW |
| 2025-07-07 | NY AM | 2025-07-02 20:00 | 2025-07-04 20:00 | 2.880 | 22440.00 LOW |
| 2025-08-04 | NY PM | 2025-07-31 20:00 | 2025-08-01 20:00 | 1.440 | 23613.50 HIGH |
| 2025-12-26 | NY PM | 2025-12-23 21:00 | 2025-12-25 21:00 | 2.880 | 25395.30 LOW |
| 2026-01-02 | London | 2025-12-31 21:00 | 2026-01-01 21:00 | 1.440 | 25481.00 HIGH |
| 2026-01-20 | NY PM | 2026-01-16 21:00 | 2026-01-19 21:00 | 4.320 | 25733.60 HIGH |
| 2026-02-17 | London | 2026-02-13 21:00 | 2026-02-16 21:00 | 4.320 | 24920.80 HIGH |
| 2026-04-06 | NY PM | 2026-04-02 20:00 | 2026-04-03 20:00 | 1.440 | 23501.40 LOW |

Los cierres están en UTC; tras cambios EST/EDT difieren las horas nominales, no se han normalizado a offset fijo. **No inferir que un NAS100 CFD estuvo cerrado en esos festivos: requieren metadata histórico PIT del proveedor.**

### Decisión técnica formal

1. **H0**: G3 usa nivel del último cash realmente completo, que estaba totalmente cerrado antes de emitir el DTO; `draw_level_observed_at` es correcto, el calendario nominal del testigo es insuficiente.
2. **H1**: G3 declaró un nivel de cash antiguo cuando su método requería el cash del día hábil nominal inmediato anterior o un pool distinto; es selección contextual errónea aunque no lookahead.
3. **H2**: el timestamp G3 no representa fin de pool, sino observación parcial, y debe separarse semánticamente de `source_completed_at`; no homologar sin una nueva especificación y no mutar el DTO congelado.
4. Testigos para resolver: **intervalos M1 09:30–16 del weekday nominal y del efectivo anterior**, calendario NAS100 CFD PIT, exactitud OHLC de extremos, consumo hasta `as_of`, y fuente ICT/TTrades escrita para definir cuál es el pool exigido. Requiere juicio revisor independiente M2 y dos firmas M6. Issue [#994](https://github.com/mezas3238-hue/qore-core/issues/994).

**Condición de cierre de #994:** los 18 casos fechados deben quedar clasificados como `SOURCE_CALENDAR_MISMATCH` fundamentado, `G3_POLICY_ERROR` fundamentado o `UNRESOLVED_WAIT` — sin modificar números para fabricar un PASS. `M2_ICT_AUTHOR_CERTIFIED=FALSE` hasta fuente validada, y 3 sesiones no certificadas.
