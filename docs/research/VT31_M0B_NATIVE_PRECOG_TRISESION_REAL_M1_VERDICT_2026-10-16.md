# VT31 — Dictamen M0-B: admisión causal NATIVA PRE-COG de las tres Silver Bullet — 16 OCT 2026

**Mandato Owner:** certificar un ÚNICO VT31 por metodología y cognitiva **por separado** para London, New York AM y New York PM. No métricas económicas, no sizing. Este documento es la auditoría de **ingeniería causal M0-B**, **NO certificado del trader**.

## 1. Resultado auténtico y verificable

- **[GitHub Actions #38901532268 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38901532268)**, commit de código ejecutado `c7628bf42c6007e2d898a2181c1a85ed0ca54cfc`: **Ruff PASS, 202/202 pytest PASS**, historial NAS100 M1 verificable de **1.059.784 velas** SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`.
- Origen: [PR #987 M7-A](https://github.com/mezas3238-hue/qore-core/pull/987), BASE exacto `5df19499e38f5d2cd42e20d15ac0119635e3a4fc`; prereg ANTES del código nuevo commit **`db60ccdc949bd04250680face8c27d5455b3555d`**.
- Ejecución **doble**: mismo G3 original alimentado por el replay referencia #982 y por el **VT31Trader G3 nativo con fuente M0 estricta habilitada**. Ambos leen las 1.059.784 M1 cronológicamente. SOLO cuando **terminan los dos replays** se abre la fuente de cobertura independiente [#980](https://github.com/mezas3238-hue/qore-core/pull/980), fuente 775 NY días × 3 ventanas = **2.325** expedientes.
- **Casebook JSON íntegro idéntico para ambos**: SHA256 `cae03ff5faaaebabef4c6f4eed736d802061bfc8598f311fb4a0e27129591de1`. No se eligieron tolerancias ni contadores nuevos después de resultados.
- **[Artefacto final #12045819123](https://github.com/mezas3238-hue/qore-core/actions/runs/38901532268/artifacts/12045819123)**, ZIP SHA256 `d05f21ed2597a03393b9e755c80d77e0b12ce80f9ef34fa30399aa1222cd2c9d` con JUnit, salida completa auditada, resumen de estados y hashes.
- COG original blob `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9` y OPS original `0ce9707314aecb71155de8b57044b6ec028847b2` preservados sin modificación ni debilitamiento de sus validadores.

## 2. Por qué esto cierra un problema real

**Antes**, [M7-A #987](https://github.com/mezas3238-hue/qore-core/pull/987) reparó COG G3 → OPS G3, pero para bloquear una H1 TTrades incompleta en NY AM y gaps en las horas Silver Bullet el productor seguía necesitando un **driver externo**. Si un integrador llamaba directamente `VT31Trader.on_closed_m1` con una M1 NYAM a las 10:00 sin haber observado las 60 barras de 09:00–10:00, el COG se podía invocar aunque faltara evidencia.

**Ahora**, la instancia opt-in **`VT31Trader(framework_policy=G3_MSS_FRAMEWORK_POLICY, strict_source_admission=True)`** implementa el gate **dentro del coordinador nativo**. Se exige exactamente 60 M1 confirmadas 09:00–09:59 del día NY actual ANTES de la primera evaluación NYAM, y se registra la fuente solo cuando llegan velas reales M1 cerradas. Un déficit retorna `SOURCE_09H_INCOMPLETE_WAIT` con `cognition=None` y `operational_phase=None`. London y NY PM ICT general NO exigen H1 09 TTrades.

Para las tres ventanas la primera M1 debe comenzar en minuto 00. Falta => `SOURCE_START_MISSING_WAIT`, sin COG/OPS. Si la fuente tiene un salto luego de haber emitido assessments, desde ese minuto se retorna `SOURCE_GAP_WAIT` irreversible dentro de la fecha/ventana: las evaluaciones anteriores conservan su `as_of`, **no se borran por saber el futuro**, y la memoria sigue recibiendo únicamente los M1 que existen. No se inventan velas ni se infiere que el CFD estuviera cerrado.

La admisión estricta está **congelada en constructor** y requiere G3 explícito: `strict_source_admission=True` con LEGACY, valor distinto de bool, o hot-swap de `strict_source_admission` es rechazado antes de observar mercado. **LEGACY/default y G3 sin opt-in preservan su comportamiento previo**; este cambio no habilita ejecución ni enciende nada automáticamente. `source_method_profiles_unsigned` identifica las tres fuentes de investigación sin simular consentimiento o firma del Owner.

## 3. Sesiones en el mismo trader

| Ventana NY | Perfil de investigación, aún no homologado | Gate interno causal | M1 históricas completas de 775 fechas |
|---|---|---|---:|
| London **03–04** | `ICT_GENERAL_2023` | M1 03h desde :00 sin gaps; jamás exige H1 09 | **774/775** |
| NY AM **10–11** | `TTRADES_NY_AM_2025` | **H1 09 exacta 60M1 antes de COG**, y M1 10h sin gaps | **769/775** |
| NY PM **14–15** | `ICT_GENERAL_2023` | M1 14h desde :00 sin gaps; jamás exige H1 09 | **741/775** |

**La categoría COMPLETE mide solo integridad de fuente**, no setups autorales. Los 41 contextos deficitarios requieren metadata point-in-time del símbolo/bróker NAS100 CFD: no inventar festivo broker/horario CFD ni interpolar M1.

## 4. Comprobación de cognitiva real bajo el nuevo gate

| Sesión | Evaluaciones COG G3 sobre M1 cerrada | Observaciones M1 con hipótesis QORE G3 (NO trades) | Días con alguna hipótesis |
|---|---:|---:|---:|
| London | **46.440** | **27.986** | 773 |
| New York AM | **46.235** | **19.302** | 745 |
| New York PM | **44.515** | **15.630** | 672 |
| **Total** | **137.190** | **62.918** | No sumar como independencia |

Los números son **evaluaciones y observaciones repetibles**, nunca entradas, operaciones ni evidencia de rentabilidad. NY AM mantiene **2 días** con 09H incompleta pero 10h presente vetados online ANTES de COG; los otros 2 casos de 09H incompleta tenían 0 M1 10h, por lo que no hubo intento de evaluación. London y NY PM, 0 veto H1 NYAM. Long/short/WAIT del G3 original no equivale a fidelidad TTrades/ICT: pivote y desplazamiento `1.25 × median5`, DOL y MIN10 son convenciones QORE pendientes de adjudicación.

## 5. Brechas por gates antes de CERTIFICAR

- **M0:** M0-B admisión temporal/source online estricta NATIVA **PASS_RESEARCH_ONLY**. Perfil de método ICT_GENERAL vs TTrades seleccionado en la investigación, **sin firma Owner como contrato productivo**; exige predecisión completa, no solo fuentes M1.
- **M1:** integridad M1 auténtica, reloj NY DST y failclosed PASS ingeniería; **41 evaluaciones día/sesión** sin fuente completa y calendario histórico broker PIT pendiente.
- **M2:** especificación DOL/liquidez autoral ICT London y NY PM, TTrades NYAM H1 09 fuente opuesta vs DOL QORE cash/MIN10 sin resolver.
- **M3:** desplazamiento/MSS/swing intermedio de fuente autoral; #977 V6 113 geometrías únicas, 44 múltiples, 161 ninguna sobre 318 ambiguos, **NO confirmaciones autorales de MSS**.
- **M4:** cuatro familias de entrada por método (incluyendo displacement directo, FVG, OB, Breaker) NO certificadas.
- **M5:** swing causante y stop/invalidez causal de autor faltantes, sin sizing.
- **M6:** dos firmas humanas independientes COG + OPS [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) ausentes.
- **M7:** integrar perfil autorizado M0 junto con M2–M5 y validación independiente por las tres ventanas. Falta expediente de producción; **NO activar ninguna orden, broker fill, posición, demo/live/VPS**.

**Limitación de seguridad a resolver:** al detectarse gap posterior, un OPS research ya creado conserva su último snapshot pero **no recibe más evaluaciones**; solo se prohíbe su uso y se devuelve WAIT. En un futuro runtime de ejecución real, cualquier tesis/orden pendiente debería cancelarse transaccionalmente de modo causal y verificable; ese desarrollo no existe ni está autorizado en este PR. La capa QORE G3 original sigue congelada.

**Dictamen:** `M0B_NATIVE_PRECOG_SOURCE_ENGINEERING=PASS_RESEARCH_ONLY`. `LONDON_CERTIFIED=NO`, `NY_AM_CERTIFIED=NO`, `NY_PM_CERTIFIED=NO`, `VT31_CERTIFICADO=NO`. PR en **DRAFT**, sin merge a main, órdenes, sizing, PnL, PF, DD, Sharpe ni Sortino.
