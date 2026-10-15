# VT31 — Dictamen real M7-A: coordinador nativo G3/OPS integrado para tres Silver Bullet (RESEARCH, NO certificación)

**Fecha: 15 de octubre de 2026.** Propósito del Owner: un SOLO VT31 con London (03:00–04:00), New York AM (10:00–11:00), New York PM (14:00–15:00), todas en `America/New_York`; certificar **metodología y cognitiva**, NO métricas económicas ni sizing. Este resultado cierra un **bloqueo de ingeniería M7-A en rama DRAFT**, no M7 ni certificados por sesión.

## Evidencia reproducible y resultado comprobado

- **[GitHub Actions #38820275105 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38820275105)**, ejecutó commit de código `88785a933290c3f70a1e04afa0462d680bcc364e`: **Ruff PASS + 172/172 pytest**, SHA origen mercado y G3/OPS congelados, fuente auténtica **1.059.784** M1 NAS100 SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, 775 fechas NY ×3 ventanas.
- Prerregistro ANTES de implementar: commit `09b285911087374282dd9b9d29e598b1821f589d`, [prereg](./VT31_M7A_NATIVE_G3_COORDINATOR_TRISESION_PREREG_2026-10-15.md).
- El nuevo `VT31Trader` con **opt-in explícito** `framework_policy=G3_MSS_FRAMEWORK_POLICY` produce exactamente los **mismos 2.325 casos completos** que el testigo anterior G3 original de [PR #982](https://github.com/mezas3238-hue/qore-core/pull/982). **SHA256 JSON full-casebook EXACTAMENTE idéntico para ambos:** `cae03ff5faaaebabef4c6f4eed736d802061bfc8598f311fb4a0e27129591de1`. No se adaptaron números esperados para fabricar resultado.
- [Artifact #12012408376](https://github.com/mezas3238-hue/qore-core/actions/runs/38820275105/artifacts/12012408376), ZIP SHA256 `355acff0ca2b442a0bb26ff42fae623bd0271fc015342bc218862585a4a7cb31`; contiene salida JSON de paridad, JUnit, hashes, commit y resumen.
- **No se alteró** código original COG blob Git `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, OPS `0ce9707314aecb71155de8b57044b6ec028847b2`, contratos ni acta original G3 `e99c70b4e018d626fb620d9a21b9314a51abc36d`. Source code modificado ÚNICAMENTE en el **coordinador** `src/qore/infrastructure/traders/vt31_ict_cleanroom/trader.py`, además de scripts/test/workflow de investigación.

## Corrección técnica M7-A

**Antes:** `VT31Trader(cognition=VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY))` creaba OPS `LEGACY_FRAMEWORK_POLICY` por defecto y, cuando surgía decisión G3, fallaba `ValueError: G3 cognition cannot feed legacy OPS`. Reproducción [issue #984](https://github.com/mezas3238-hue/qore-core/issues/984), [run original #38794447738](https://github.com/mezas3238-hue/qore-core/actions/runs/38794447738).

**Ahora:** El coordinador admite **política de framework explícita opt-in**. Con `framework_policy=G3_MSS_FRAMEWORK_POLICY` selecciona COG G3 original y construye OPS G3 original **en las tres sesiones**. Sin opt-in mantiene el contrato `LEGACY` previo. COG suministrado con política distinta es rechazado **en constructor**, antes de recibir M1; política desconocida o cambio posterior se rechaza **antes de mutar memoria cognitiva o ejecutar OPS**. Se preservan todas las comprobaciones originales de MSS anchor M1, DOL, gaps e invalidación de OPS: NO se elude la guarda por permitir G3.

Las pruebas adversariales cubren LEGACY default, G3 explícito, mismatches y hot-swap, LONG/SHORT de muestra, EST/EDT, 3 ventanas, 09 H1 TTrades NY AM sin contaminar London/NY PM, gaps/WAIT, cero broker orders/positions, una identidad/memoria. Reejecución de tests existentes y triple censo real: 172 PASS.

**Alcance de la integración:** El coordinador *nativo* G3 está **cableado correctamente y auditado RESEARCH**. El veto NY AM H1 y la procedencia de método siguen en el **driver de investigación** con admisión previa, no en un runtime productivo firmado. No significa que se haya cerrado la integración M0/M7 completa.

## Paridad e interpretación cognitiva exacta (NO operaciones)

| Sesión Silver Bullet, NY timezone | Invocaciones originales G3 sobre M1 cerradas | Observaciones con hipótesis G3 (reiteraciones, NO señales/trades) | Días con 1+ hipótesis QORE G3 |
|---|---:|---:|---:|
| London 03–04, ICT-general | **46.440** | **27.986** | **773** |
| NY AM 10–11, TTrades | **46.235** | **19.302** | **745** |
| NY PM 14–15, ICT-general | **44.515** | **15.630** | **672** |
| **Total** | **137.190** | **62.918** | no sumar días como independencia |

Estas observaciones son M1 consecutivas, muchas repiten hipótesis. **No hay 62.918 operaciones**. Los criterios del G3 actual (pivote, desplazamiento cuerpo 1,25×mediana5, DOL QORE, MIN10) son **convenciones QORE**, NO certificación textual del método ICT ni de TTrades. Paridad cognitiva demuestra consistencia reproducible, no calidad de método ni edge.

Fuente M1 anterior independiente [PR #980](https://github.com/mezas3238-hue/qore-core/pull/980) dictamina: London **774/775** ventanas 60 M1 completas, NY AM **769/775** con fuente 09 H1 válida y NY PM **741/775**; en las **41** excepciones no atribuir `BROKER_CLOSED` sin calendario PIT NAS100 CFD de origen. Para NY AM **dos días** con ventana 10h y H1 09 incompleta producen WAIT ANTES de COG (además dos sin ventana 10h); London/NYPM no heredan H1 09 autoral de TTrades.

## Estado restante y trabajo P0

| Gate | Evidencia lograda | Pendiente real para certificar |
|---|---|---|
| M0 | Router y perfiles investigación #971/#978 + opt-in G3 | decisión/preselección fuente ICT/TTrades aprobada por Owner y aplicada antes de primera M1 en runtime único |
| M1 | 1.059.784 M1 SHA, DST NY, H1 WAIT sólo NYAM, paridad 2325 | metadatos bróker CFD histórico point-in-time y adjudicación 41 source gaps |
| M2 | Testigos causales QORE fuentes cash/Asia/London | prueba primaria de DOL/objetivo **ICT general London y NY PM**; TTrades NY AM fuente H1 opuesta y conflicto MIN10 |
| M3 | #977 V6 113/44/161 triples geométricos sobre 318 ambiguos NYAM | desplazamiento autoral y protected swing confirmado de MSS, tres sesiones |
| M4 | FVG original QORE/OPS existente | 4 entradas displacement/FVG/OB/Breaker de fuente correspondiente, tres ventanas |
| M5 | stop/swing QORE investigados | invalidación y swing exacto causante de displacement por perfil, sin sizing |
| M6 | hashes G3 originales preservados | dos firmas **humanas independientes** COG y OPS [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) |
| M7 | **M7-A: native COG G3 → OPS G3 ENGINEERING PASS** en PR DRAFT | ensamblaje M0+M1+M2–M5 autorizado, integridad revisada, 3 certificados independientes y certificado VT31 conjunto |

**Resultado formal de esta rama:**
`NATIVE_G3_OPS_FRAMEWORK_ENGINEERING=PASS_RESEARCH_ONLY`,
`FULL_CASEBOOK_2325_PARITY=PASS`,
`LONDON_METODOLOGIA=NOT_CERTIFIED`,
`NY_AM_METODOLOGIA=NOT_CERTIFIED`,
`NY_PM_METODOLOGIA=NOT_CERTIFIED`,
`COGNITIVA_FORMAL=NOT_CERTIFIED`,
`VT31_TRADER_CERTIFICADO=FALSE`.
El PR debe seguir **DRAFT**, sin merge a `main`, OMS, demo/live/VPS, broker fills, lotes/sizing ni PnL.
