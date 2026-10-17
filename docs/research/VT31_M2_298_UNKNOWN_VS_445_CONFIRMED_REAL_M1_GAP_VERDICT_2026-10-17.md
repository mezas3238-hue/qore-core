# VT31 — Dictamen M2 sobre 298 incertidumbres DOL: cobertura causal M1 real de tres sesiones

**17 de octubre de 2026.** Fuente NAS100 **1.059.784 M1 cerradas originales**, no BTC, no NQ de otro broker, no fills. Un único VT31 con tres ventanas fuente `America/New_York`: London 03:00–04:00, NY AM 10:00–11:00 TTrades 09H gate, NY PM 14:00–15:00. Certificación por metodología y cognitiva, nunca rentabilidad/sizing.

## Evidencia final GitHub

- **[CI #39037937522 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/39037937522)**, commit de código `9ae41ba027156a6f1a937b3366ced70e90db8fd9`: **Ruff PASS + 101/101 pytest PASS**, origen NAS100 SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`.
- Prerregistro **ANTES del código** SHA commit `2fdef8113e4ea591651933d72288e89287981288` y [archivo](./VT31_M2_298_UNKNOWN_M1_GAP_FORENSIC_PREREG_2026-10-17.md), conserva las tasas previas del [PR #993](https://github.com/mezas3238-hue/qore-core/pull/993) como contrato, sin tuneo por resultado.
- Expediente M2 original **775 días NY × tres sesiones = 2.325** SHA JSON canónico `d74b24242c4b8c5656547727b88886ecd1a18243c362d9d366825880bddbfc21`, descargado desde artifact fijo **#12079131643** y verificado ZIP sha256 `30de8306225941208ecea73ab4b9ba9b88b625b8b1e9794f47c758ea3fdce07a`. El cálculo nuevo no vuelve a llamar G3, no conoce resultados de trading y no modifica COG/OPS originales.
- **[Artifact nuevo #12103380622](https://github.com/mezas3238-hue/qore-core/actions/runs/39037937522/artifacts/12103380622)**, ZIP SHA256 `6399c3d0666e2628348fa7a3c071928fb16f4846a0497aa7838499f069e918b7` con 743 intervalos individualizados, cada `as_of`, fuente DOL, M1 esperadas/observadas/perdidas, primer hueco, longitud máxima, tests JUnit y firmas SHA256SUMS.
- **SHA256 del testimonio de 743 intervalos** `a546f7c143bb59bce822890d82733e44b8941f990942c83aa9e59823c094bd4d`. COG G3 original blob `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, OPS original `0ce9707314aecb71155de8b57044b6ec028847b2`, coordinador nativo y fuente M2 anterior **sin cambios**. Este PR agrega solo archivos propios.

## Resultado original, falsado independientemente sobre cierres M1

| Silver Bullet | `CONFIRMED` QORE con **0** M1 ausentes entre fuente y as-of | `UNKNOWN` QORE con **1+** M1 ausentes | Máximo hueco individual en minutos | Sumatorio de M1 ausentes de los intervalos |
|---|---:|---:|---:|---:|
| London 03–04 | **283** | **113** | 2.946 | 61.586 |
| NY AM 10–11 | **97** | **98** | 2.991 | 43.373 |
| NY PM 14–15 | **65** | **87** | 2.946 | 51.372 |
| **Total** | **445** | **298** | 2.991 | **156.331** |

**Importante:** 156.331 es la suma de minutos faltantes **por expediente**, NO velas únicas; distintos intervalos se solapan, por lo que NO es un censo de ausencias únicas del feed. Los gaps máximos de alrededor de 49–50 horas pueden abarcar findes, cierres, faltantes o calendarios de CFD. Sin calendario NAS100 CFD PIT no se etiqueta nunca `BROKER_CLOSED` ni `TRADING_PAUSED` ni se atribuye error al bróker.

### Qué demuestra y qué NO demuestra

1. Los **445** DTO QORE con fuente M2 `CONFIRMED` por tribunal previo realmente contienen TODAS las velas cerradas del intervalo posterior al fin de su pool DOL hasta el primer cierre de sesión. Esto demuestra una propiedad **estrecha de completitud M1 observada**, no doctrina ICT/TTrades ni rentabilidad.
2. Los **298** DTO QORE con `POOL_AVAILABILITY_UNVERIFIABLE` realmente exhiben al menos un hueco M1 en ese mismo intervalo. Aunque no exista *toque observado* del nivel, el hueco impide inferir que el nivel estaba libre durante todo el intervalo. **Invariante M2: fuente gapped => disponibilidad UNKNOWN, NO promoción.**
3. Los **18** DTO positivos restantes del primer minuto bajo `COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE` en tribunal nominal original fueron analizados por la comparación del [CI #38976680827](https://github.com/mezas3238-hue/qore-core/actions/runs/38976680827): 18/18 nivel del último cash completo anterior **390/390 M1** y precio exacto, mientras nominal `_previous_weekday` incompleto; quedan como **discrepancias de política calendario M2**, no se suman a los 298 ni se certifican.
4. Población del primer minuto: 761 DTO positivos QORE = 445 + 298 + 18. Más casos sin hipótesis G3 y 35 sin primera M1 componen 2.325; no se cuentan como operaciones ni setups.
5. No puede certificar **`NO_LIQUIDITY_TOUCH` para 298** porque falta cobertura; tampoco puede certificar los 445 bajo autor ICT/TTrades sin homologar qué DOL escogió el autor. La distinción entre QORE `_verified_pools` (último cash cerrado disponible) y testigo `_previous_weekday` está documentada.

## Próximos gates obligatorios

- **M0:** Owner firma selección `ICT_GENERAL_2023` London/NY PM versus `TTRADES_NY_AM_2025`, sin trasladar H1 09 a ICT-general.
- **M1:** custodiar origen NAS100 M1, broker metadata PIT, adjudicar 41 ventanas sesión fuente incompleta y gaps intradía/nocturnos.
- **M2:** decidir, con **fuente primaria y broker PIT**, selección de `prior cash` último full 390M1 vs weekday nominal y política DOL por ventana; mantener los 298 gapped en WAIT y 18 en `SOURCE_CALENDAR_POLICY_UNKNOWN` hasta adjudicación por Owner. **Issue P0 #994** guarda los 18.
- **M3:** no confundir MSS swing+displacement con CISD first opposing-series OPEN; PRs #991, #992 y #995 del otro arquitecto prueban software/interpretación pero faltan gráficos autorales y M1 genuinas del vídeo.
- **M4:** cuatro familias de entrada por fuente sin extrapolar FVG a OB/Breaker ni sin retest M1 cerrado.
- **M5:** swing que causó displacement y stop autoral, no sizing.
- **M6:** dos firmas humanas independientes COG y OPS #897, no simular con robots.
- **M7:** certificación **separada de London, NY AM y NY PM**, y únicamente después certificado conjunto VT31. No hay autorizaciones LIVE/DEMO/VPS, broker fills, sizing, órdenes, PnL o `main` merge.

**Dictamen formal:** `M2_QORE_POSITIVE_SOURCE_M1_COVERAGE_FALSIFICATION=PASS_RESEARCH_ONLY`, `M2_AUTHOR_METODOLOGIA=NOT_CERTIFIED`, `COGNITIVA_FINAL=NOT_CERTIFIED`, `LONDON=NY_AM=NY_PM=VT31_CERTIFIED=FALSE`. Los 298 UNKNOWN con datos faltantes siguen siendo un bloqueo cognitivo de disponibilidad, no un fracaso de cobertura del auditor.
