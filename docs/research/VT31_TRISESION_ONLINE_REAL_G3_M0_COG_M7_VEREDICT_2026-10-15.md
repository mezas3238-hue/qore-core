# VT31 — RESULTADO REAL: COG G3 ORIGINAL ONLINE en 3 Silver Bullet, veto 09H TTrades y bloqueo M7 del coordinador

**15-OCT-2026.** Esta es la continuación de [tri-sesión M1 #980](https://github.com/mezas3238-hue/qore-core/pull/980) (SHA BASE `05f46858b2bf34042c7823a5334809adc141a279`), para **un solo VT31 con London 03–04, New York AM 10–11 y New York PM 14–15**, horario `America/New_York`. Objetivo de cierre conjunto [issue #981](https://github.com/mezas3238-hue/qore-core/issues/981), NO PnL, sizing ni activación real.

## 1. Ejecución científica auténtica y con código sellado

**[GitHub Actions #38794839290 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38794839290)** sobre commit de código `2724a24e0be7ec7db4e184dc58d0b8d7e0156ac0`. **Ruff PASS, 132/132 pytest PASS**, toda la fuente original **1.059.784 NAS100 M1** SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, censo **775 NY días ×3 = 2.325** contextos, ledger previo (producido ANTES) verificado SHA `7dba2c0ed15255ef1b4b5e5a277199940e785aa7e99c36a5d095bb18d4de501d`. Prereg **antes del código** commit `71770492abec4d4429ba69097c35570854b0beaf`.

[**Artifact #12001911740**](https://github.com/mezas3238-hue/qore-core/actions/runs/38794839290/artifacts/12001911740), ZIP digest SHA256 `7c8eb749ca7b64a1c1192cee18890b80c3dc0e75b4a974b9c82072f6936bdeaf`. Casebook completo online con tiempos y estatus para las **2.325** fechas/sesiones: SHA256 `cae03ff5faaaebabef4c6f4eed736d802061bfc8598f311fb4a0e27129591de1`. Código de investigación añadió exclusivamente 4 nuevos archivos hasta informe, no tocó G3 COG ni G3 OPS.

### Resultado por sesión

| Ventana | Invocaciones originales G3 cerradas M1 | Observaciones con hipótesis G3 (puede repetirse la misma tesis) | Días con >=1 observación positiva | Días con hipótesis emitida antes de ventana que terminó incompleta |
|---|---:|---:|---:|---:|
| London ICT general 03–04 | **46.440** | **27.986** | **773** | **0** |
| NY AM TTrades 10–11 | **46.235** | **19.302** | **745** | **2** |
| NY PM ICT general 14–15 | **44.515** | **15.630** | **672** | **1** |
| **Total** | **137.190** | **62.918** | — | **3** |

**Estas 62.918 observaciones NO son trades, setups author-certified ni decisiones independientes.** El mismo COG puede repetir durante muchas M1 un DOL/MSS QORE de una sola tesis. Es una medición de juicio productor y abstención, no de éxito económico ni metodológico. En particular, Londres tiene 773 días con alguna hipótesis G3: esta elevada prevalencia por sí sola **no demuestra calidad, selectividad ni fidelidad a ICT**. Los 3 episodios de sesión posteriormente incompleta tienen as-of original válido, pero no deben promocionarse a ventanas completas; **no se borra el pasado usando una vela futura**.

### Diagnóstico de source-gaps

- El ledger #980 fija **London 774/775** horas completas, NY AM **769/775** (2 parciales 10h y 4 H1 09 incompletas) y NY PM **741/775** (30 sin ninguna M1 y 4 parciales). El ONLINE engine respeta la misma fuente pero **no leyó el ledger hasta DESPUÉS de procesar todas las M1**.
- **NY AM:** 4 días con H1 09 incompleta según ledger. En **2** había M1 en la ventana 10h (2024-01-05 y 2025-08-05) y G3 fue **VETADO desde la primera M1** con `SOURCE_09H_INCOMPLETE_WAIT`; otros **2** no tuvieron ni una M1 10h y por eso ningún intento online de invocar COG. Cuando la H1 estaba completa, los cierres NYAM se procesaron causalmente.
- **London y NY PM NO requieren H1 09 de TTrades.** Sus sesiones originales G3 se evalúan en sus ventanas NY con EST/EDT sin fingir doctrina de TTrades AM. Gap de cualquier ventana => no nuevos COG/OPS y `SOURCE_GAP_WAIT`; las barras presentes siguen en la memoria única de mercado.
- **NY PM:** cuatro días con gap/parcial requieren source validation; aunque 741 completos generan G3, no se inventan velas ni cierre del broker. Los 30 días 14h sin M1 quedan `SOURCE_UNKNOWN` por falta de metadatos PIT.

## 2. BLOQUEO CRÍTICO M7 detectado y reproducido: G3 no entra al VT31Trader actual

El **primer ensayo real de integración** con `VT31Trader(cognition=VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY))` devolvió `ValueError: G3 cognition cannot feed legacy OPS`, [Actions #38794447738 FAILURE de integración](https://github.com/mezas3238-hue/qore-core/actions/runs/38794447738). La razón concreta es que `VT31Trader.on_closed_m1` crea `IctSilverBulletOperations(session=window, day=opened)` sin propagar `framework_policy`; OPS por defecto es `LEGACY`, mientras G3 entrega DTO con `G3_MSS_FRAMEWORK_POLICY`. El guard de OPS protege un invariante auténtico y **no debe desactivarse**.

Para no tocar fuentes protegidas, el ensayo finalmente aprobado usa **UN SOLO** `VT31CleanroomCognition` real G3 y, para cada fecha/ventana, el **original** `IctSilverBulletOperations(...framework_policy=G3_MSS_FRAMEWORK_POLICY)`, unidos en un *adaptador de investigación sin OMS ni fills*. No instancia el `VT31Trader` nativo ni afirma que ese coordinador ya esté corregido. El JSON registra `native_VT31Trader_G3_integration_complete=False`. Prueba adversarial específica compara en runtime el original `VT31Trader` con G3 COG y su OPS de legado.

**Issue P0 de corrección separada: [#984 — incompatibilidad G3/Legacy](https://github.com/mezas3238-hue/qore-core/issues/984)**. Debe aprobarse, versionarse y corregirse en una lane de integración distinta con controles M0 previos y firmas. **NO** modificar el COG original blob `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9` ni OPS blob `0ce9707314aecb71155de8b57044b6ec028847b2`.

## 3. Estado de las tres certificaciones

- `M0`: investigación de perfil/ruteo #971/#978, falta decisión policy firmada para integración nativa, reconcilio H1 fuente.
- `M1`: **SOURCE INTEGRITY y causal original G3 ONLINE de investigación PASS** en tres sesiones; la fuente en 41 casos día/sesión falta y calendario broker PIT no está homologado.
- `M2`: **ICT London/NYPM fuente doctrinal DOL desconocida**, no basta source pool cash/Asia/early London QORE; NYAM H1 TTrades 09 de fuente ya gateado pero DOL conflicto QORE vs autor no resuelto.
- `M3`: G3 pivot + body 1.25 median5 **QORE proxy** no es MSS autoral. [V6 #977](https://github.com/mezas3238-hue/qore-core/pull/977) describe 113/44/161 geometrías de 318 ambiguas NYAM, NO desplazamiento protegido certificado.
- `M4/M5`: 4 entry families source + swing causante para TTrades y London/NYPM por perfil faltan; ningún G3 positivo sustituye estos contratos.
- `M6`: firmas humanas independientes COG + OPS [#897](https://github.com/mezas3238-hue/qore-core/issues/897) ausentes; un login no equivale a dos firmantes independientes.
- `M7`: **coordinador nativo G3 OPS legado falla; issue #984**, falta integración de 3 sesiones y certificados separados.

**DICTAMEN REPRODUCIBLE:** `REAL_ONLINE_G3_RESEARCH_PASS`; `M7_NATIVE_G3_INTEGRATION=BLOCKED`; `LONDON_CERTIFIED=FALSE`; `NYAM_CERTIFIED=FALSE`; `NYPM_CERTIFIED=FALSE`; `METHOD_CERTIFIED=FALSE`; `COGNITION_CERTIFIED=FALSE`; `VT31_TRADER_CERTIFICADO=FALSE`. PnL/edge no estudiados en esta certificación; **0 órdenes, 0 sizing, 0 LIVE/DEMO/VPS, 0 merge**.
