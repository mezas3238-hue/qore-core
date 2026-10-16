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
