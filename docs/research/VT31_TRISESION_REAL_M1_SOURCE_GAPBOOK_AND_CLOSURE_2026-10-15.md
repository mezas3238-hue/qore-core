# VT31 — Primera auditoría REAL conjunta de las tres Silver Bullet (London + NY AM + NY PM)

**Fecha:** 15-OCT-2026. **Mandato Owner:** cerrar las tres sesiones por metodología y cognitiva, no por PnL ni por lotaje. Un solo VT31, **tres expedientes de sesión separados**. Esta ronda es el **M0/M1 source gapbook**; **ninguna sesión está certificada aún**.

**GitHub:** [PR #980 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/980), rama `agent/vt31-trisession-real-m1-m0-census-20261015`, hija [PR #978](https://github.com/mezas3238-hue/qore-core/pull/978) a SHA `92c0a1e224e46588e4d2642104db4a9115d80d57`. **Prerregistro antes de código** commit `a4352c9ad787111604d618f3fb10660de015230d`; parámetros de criterio fijados antes de observar resultados. La reserva de archivos fue notificada en [#727](https://github.com/mezas3238-hue/qore-core/issues/727). [Objetivo global y pendientes en issue #981](https://github.com/mezas3238-hue/qore-core/issues/981).

## 1. Evidencia y alcance verificable

[**GitHub Actions #38792171482 — SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38792171482), sobre commit de código+workflow `c6d0c6933d3b5083a31f5f0790e99d382b3777f5`. Ruff PASS, **129/129 pytest**, fuente autentica NAS100 M1 1.059.784 barras con SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, idénticos **775** días de desarrollo NY AM y categorías originales 128/483/92/65/6/1.

- 775 fechas NY AM referencia × 3 ventanas Silver Bullet = **2.325 evaluaciones dia/sesión**. Fuente M1 de desarrollo YA vista: **NO holdout/OOS**.
- Geometría horaria New York real mediante zona IANA `America/New_York`, incluyendo EST/EDT. Las ventanas deben disponer de 60 barras M1 cerradas para atestar **sólo integridad M1**. NY AM `TTRADES_NY_AM_2025` además exige H1 09–10 con exactamente 60 M1; NO aplicar H1 09 a `ICT_GENERAL_2023` London ni NY PM.
- **JSON full-casebook SHA256 scalar = 2-fork Ultra Fast** `7dba2c0ed15255ef1b4b5e5a277199940e785aa7e99c36a5d095bb18d4de501d`. [Artifact #11999769990](https://github.com/mezas3238-hue/qore-core/actions/runs/38792171482/artifacts/11999769990), ZIP SHA256 `bd0994babb38756bfc591aaeb50f4fd655f770039f596e4ae830196abcdf5d5f`, incluye los 2.325 casos y hashes. **Segunda CI #38792654129 SUCCESS** añadió un datebook fechado de cada falta M1: el ZIP original ya preservaba las fechas en cada fila.
- 16 fixtures de origen PR #978 sin cambio de decisiones: 4 TTrades research-compatible, 4 TTrades WAIT por conflicto MIN10 y 8 ICT-general `UNDERDETERMINED` del COG G3 real. Estos fixtures son **sintéticos**; el censo REAL prueba cobertura M1, no que COG autorizó una decisión en cada sesión.

## 2. Tabla por sesión — fuente REAL NAS100 M1

| Sesión (reloj Nueva York) | Perfil fijado en investigación | Ventanas M1 completas | Falta de M1 / H1 (sin declarar broker cerrado) | Semántica |
|---|---|---:|---:|---|
| **London 03–04** | ICT_GENERAL_2023 | **774/775** | **1** hora sin ninguna M1 | Estado `NO_M1_WINDOW_SOURCE_UNKNOWN`; necesita verificar fuente/horario broker, no negar mercado |
| **New York AM 10–11** | TTRADES_NY_AM_2025 | **769/775** | **2** horas 10h parciales + **4** fuentes 09h H1 incompletas | En 4 casos `TTRADES_H1_09_SOURCE_INCOMPLETE_WAIT` tiene precedencia aunque 10h pudiera estar completa |
| **New York PM 14–15** | ICT_GENERAL_2023 | **741/775** | **30** horas sin ninguna M1 + **4** parciales | El mayor bloqueo M1 observable; requiere calendario PIT CFD y procedencia broker, nunca interpolar |
| **TOTAL** | Tres subcontratos, un VT31 | **2.284/2.325** | **41/2.325** evaluaciones no completas | Estas cifras son ventanas fuente, **NO operaciones ni señales rentables** |

**Muy importante:** `COMPLETE` significa que las barras de la ventana existen. No prueba que el modelo ICT haya identificado un MSS, que el bróker estuviera abierto con bid/ask, que el stop sea causal ni que exista una entrada.

## 3. Lo certificado en ingeniería y lo NO certificado en método

- **M0:** perfiles separados y congelados en investigación #971/#978 (no política soberana firmada ni integración nativa definitiva). TTrades AM H1 09 sólo NY AM; London/NY PM pertenecen a ICT general. Si otra sesión intenta apropiarse de reglas de NYAM ⇒ rechazo, no reinterpretación.
- **M1:** avance material **PASS de ingeniería fuente**: reloj NY DST, 60 M1 exactas, huecos registrados, SHA original, full-casebook parity 2 procesos, adversariales sin órdenes. Fuente faltante ⇒ UNKNOWN/WAIT. **M1 metodología runtime integral NO certificado**.
- **M2 London/NY PM:** todavía falta DOL/target y reglas de liquidez atribuidos a ICT general más allá de geometrías QORE. No importar H1 09 de TTrades. NY AM existe H1 source-first #956 pero el G3 original tiene objetivo cash/MIN10 diferente y fuente broker PIT ausente.
- **M3:** London/NY PM falta witness autoral de displacement + swing MSS; NY AM #977 V6 obtuvo 113 geometrías single, 44 múltiples, 161 sin triple en los 318 contextos V4 ambiguos, **NO AUTHOR MSS**.
- **M4/M5:** FVG, displacement directo, OB, Breaker y swing que causó displacement no son modelos completos certificados para las tres ventanas.
- **M6:** [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) exige dos revisores humanos COG y OPS independientes sobre SHAs congelados, todavía sin firmas. No simular múltiples personas desde un login.
- **M7:** no emitir certificados hasta integración común **y** tres subcertificados de sesión; nunca usar el promedio para esconder una ventana incompleta.

## 4. Orden P0 para cerrar las tres (ninguna queda abandonada)

1. **NY PM — datos:** auditar 30 horas sin M1 y 4 parciales con fechas exactas del datebook, distinguir cierre legal del símbolo CFD frente a caída de fuente por calendario broker PIT. No usar holidays de Nasdaq cash como prueba de horario del CFD.
2. **London y NY PM — ICT author/source:** formalizar en fichas separadas DOL/liquidez, sweep, desplazamiento+MSS, cuatro entradas y stop swing causante; adyacencia M1 con lookahead cero y ventana NY exacta. Casos LONG/SHORT/WAIT/revoke/expire reales, EST/EDT, no copiar setup TTrades AM.
3. **NY AM — TTrades:** resolver first-open CISD y V6 113/44/161 con displacement/protected swing causante, 4 familias M4 y fuente DOL H1 09.
4. **VT31 único — composición:** selector M0 antes de M1, tres expedientes completos por mismo productor/versionado, OPS verificable y puertas fail-closed; persistencia no debe arrastrar tesis London a NY PM/NY AM.
5. **G3/M6/M7:** firmantes independientes + certificar metodología y cognitiva por ventana; luego expediente conjunto sin permitir demo/live/VPS/sizing automáticamente.

**Dictamen:** `TRISESSION_REAL_M1_COVERAGE_ENGINEERING_PASS`, `LONDON_METHOD_CERTIFIED=FALSE`, `NYAM_METHOD_CERTIFIED=FALSE`, `NYPM_METHOD_CERTIFIED=FALSE`, `COGNITION_RUNTIME_CERTIFIED=FALSE`, `VT31_TRADER_CERTIFICADO=FALSE`. No PnL, PF, DD, Sortino, sizing, órdenes, fills, merge ni promoción a explotación.

## 5. Datebook verificable tras segunda ejecución CI

[**GitHub Actions #38792654129 — SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38792654129), commit workflow `21c5c8a5dc1163fc3a9ea1c5fdd3697f2e31ed72`, Ruff PASS, **129 pytest PASS**, fuente original SHA PASS, mismo 2.325-casos SHA `7dba2c0ed15255ef1b4b5e5a277199940e785aa7e99c36a5d095bb18d4de501d`, scalar/fork parity TRUE. Segundo [artefacto #12000338010](https://github.com/mezas3238-hue/qore-core/actions/runs/38792654129/artifacts/12000338010), ZIP SHA256 `31eda29455dace38086a0f029c9d7568593971931537625734bd9841925467a0`, incluye `VT31_TRISESION_REAL_SOURCE_GAP_DATEBOOK.json` con los 41 eventos fechados. No se editó el cálculo para elegir mejores días ni cambiar el hash del casebook.

### London — 1 excepción de cobertura
- `2025-11-28`: **0/60 M1** en 03–04 NY. `SOURCE_UNKNOWN`. Si el mercado estuvo abierto o cerrado es información que necesita **feed/calendario específico de CFD**; no inferirlo de una bolsa distinta.

### New York AM — 6 excepciones fuente en horario TTrades
- **Hora 10–11 NY parcial con H1 09 completa:** `2023-10-12` **59/60**; `2023-12-28` **57/60**.
- **H1 09 incompleta (gating `WAIT`):** `2024-01-05` (10–11 tiene **60/60**); `2025-01-09` (10–11 **0/60**); `2025-08-05` (10–11 **60/60**); `2026-04-03` (10–11 **0/60**). Es importante: **dos** ventanas de ejecución completas siguen **WAIT** porque falta la fuente previa requerida.

### New York PM — 34 excepciones fuente ICT
- **Parciales:** `2023-10-11` (**55/60**), `2023-12-08` (**59/60**), `2023-12-28` (**59/60**), `2024-01-03` (**57/60**).
- **Sin ninguna M1, 30 fechas**:
  - 2023: `11-23`, `11-24`.
  - 2024: `01-15`, `02-19`, `05-27`, `06-19`, `07-03`, `07-04`, `09-02`, `11-28`, `11-29`, `12-24`.
  - 2025: `01-09`, `01-20`, `02-17`, `05-26`, `06-19`, `07-03`, `07-04`, `09-01`, `11-27`, `11-28`, `12-24`.
  - 2026: `01-19`, `02-16`, `04-03`, `05-25`, `06-19`, `07-03`, `09-07`.

**Observación no concluyente:** varias fechas coinciden en apariencia con festivos o vísperas de festivo de EE. UU.; la coincidencia **NO demuestra** horario de negociación NAS100 CFD de un bróker concreto. Se requiere metadata point-in-time verificable del símbolo exacto, su horario y la integridad del feed. Hasta entonces, `NO_M1_WINDOW_SOURCE_UNKNOWN`; nunca suturar gaps ni afirmar `BROKER_CLOSED`.
