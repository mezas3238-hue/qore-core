# VT31 · MC-P1 Certificación metodológica y cognitiva — dictamen del COG REAL (14 octubre 2026)

## Estado oficial

**`M1_CAUSAL_ENGINEERING_PASS`**, **`TTRADES_NY_AM_2025_FIDELITY_FAIL_FOR_WITNESSED_CASE`**, **`ICT_GENERAL_2023_SOURCE_FIDELITY_PARTIAL_UNCERTIFIED`**, **`METHOD_CERTIFICATION_PENDING`**, **`COGNITIVE_CERTIFICATION_PENDING`**, **`TRADER_NOT_CERTIFIED`**, **`NO_LIVE`**.

Es una auditoría de fidelidad y cognición (no matemática de PnL), acordada con la directiva del propietario. No extrapola un único ejemplo a todos los días, ni transforma tests de ingeniería en rentabilidad.

## Preregistro y ejecución real

- [PR maestro método/cognitiva #926](https://github.com/mezas3238-hue/qore-core/pull/926), CI precedente [#38546461272](https://github.com/mezas3238-hue/qore-core/actions/runs/38546461272): comprobador independiente TTrades y 62 tests (13 específicos +49 regresiones), sin usar COG para generar casos.
- Prerregistro **ANTES de escribir módulo o tests de esta ronda**: `docs/research/VT31_MC_P1_REAL_COG_SOURCE_PROFILE_ADVERSARIAL_PREREG_2026-10-14.md`, commit **`1f65915f45fcfb41884f122a922315afc5523b33`**.
- **[Run GitHub Actions #38579110581 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38579110581)**, código exacto **`755fff9e761f6bd5432e87df532a6872fbc6b1a1`**: Ruff PASS; **20/20** testigos metodológicos (7 NUEVOS COG real +13 heredados de #926) y **49/49** regresiones reales cleanroom cognition/OPS/M1/G3, **69/69 PASS**. QA Prereg ancestor PASS, G3 COG/OPS + Acta blob identity PASS.
- Artifact de salida JSON con testigo verdadero `actual_cog_vs_ttrades_am.json` + SHA256SUMS y commit SHA: **[#11902302689](https://github.com/mezas3238-hue/qore-core/actions/runs/38579110581/artifacts/11902302689)**, artifact SHA256 **`8747fc4e4efdeb259deec5b269474a5d7b1d2f8c9e047a41eddedd803f4f4be6`**, caduca 2027-01-12.
- Primer CI de esta P1 [#38578965442](https://github.com/mezas3238-hue/qore-core/actions/runs/38578965442) falló Ruff F401 **por import `Side` no utilizado** en script nuevo; se corrigió y rehizo run verde sin cambiar método COG ni cambiar el criterio de resultado. Guardar esta trazabilidad.

## Experimento falsable con verdadero productor COG

Se procesaron mediante **`VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY)` original** las velas cerradas M1 de un caso **SINTÉTICO** (NO Nasdaq histórico real; NO cohorte V1):
1. Viernes 2026-01-02 previo: NY cash previo 09:30–16:00 390 M1 completos, techo 150 como pool unswept DOL.
2. Lunes 2026-01-05: Asia completa 00–03, London 03–05, continuación 05–09, el **H1 NY 09–10 60 M1** completo con high `110`, low `90`; ninguna vela tras 10 NY cruza esos dos extremos antes de decisión.
3. Desde 10:00 NY: seis M1 cerradas con estructura de micropivote y displacement. A las 10:06 NY, la **lógica auténtica de COG** produce `CognitiveDecision` LONG con `structure_break_confirmed_at` última M1, `mss_anchor_close=107`, target del `PRIOR_NY_CASH_SESSION_HIGH = 150`. Existen H1/M15 confirmados y frescos, no hay dato futuro, y el potencial supera los 10 puntos QORE. No se utilizó `dataclasses.replace` para fabricar el DTO entregado al testigo.
4. El verificador **distinto** `assess_ttrades_am_context` del PR #926 recibe ese **DTO realmente generado**, el H1 09 completo y el prefijo 10am hasta el as-of. Devuelve **`REJECTED`**, causas exactas:
   - `NO_PRE_SIGNAL_9AM_H1_SWEEP`: no hay barrido HIGH ni LOW del H1 09 en ventana 10 NY.
   - `DOL_NOT_OPPOSITE_9AM_H1_EXTREME`: target COG 150 por cash anterior en vez del HIGH 09 a 110 para LONG tras el barrido LOW (que además no ocurrió).
5. Sin inferir fills ni ganancias: resultado `ACTUAL_COG_NOT_TTRADES_AM_SOURCE_CONFORMANT`, **no defecto universal de ICT**.

**Testigos adversariales adicionales**: (a) COG no puede volver atrás en as-of tras consumir una M1 futura; (b) el verificador no puede aceptar una 10AM M1 fuera del as-of; (c) TTrades H1 09 no es veto universal para London/NY PM originales de ICT; (d) estructura MSS y fecha DOL provienen de datos anteriores; (e) reportaje implica `method_certified=false`, `cognitive_certified=false`, `trading_authorized=false` incluso cuando el software pasa CI.

## Dictamen gate por gate

| Gate | Resultado esta ronda | Interpretación |
|---|---|---|
| M0 — identidad fuente | **PROFILES_SEPARATE** | ICT 2023 vs TTrades AM 2025 vs formalización QORE; fuente contrastada, selector de runtime todavía NO implementado |
| M1 — cronología y testigo M1 | **ENGINEERING_PASS(69/69)** | Solo asegura los casos cubiertos, no todos los estados cognitivos de mercado |
| M2 — raid/DOL NY AM TTrades | **FAIL de conformidad del COG QORE en contraejemplo sintético real-producer** | No presentar QORE como réplica TTrades por llevar etiqueta Silver Bullet |
| M3 — desplazamiento MSS posterior al raid | **UNVERIFIED para TTrades** | QORE MSS puede ser causal sin raid previo; no equiparar doctrina |
| M4 — cuatro familias entrada | **PENDING** | PR #906 detecta proxies source-only; falta autoridad/fidelidad autoral OB/Breaker y perfil |
| M5 — stops/DOL por perfil | **PENDING** | G3 QORE C2 no equivale SL swing TTrades; no adjudicar fills |
| M6 — revisión COG/OPS | **PENDING** | #897 ninguna doble firma independiente; owner authorizes research, not counterfeit signatures |
| M7 — economía | **NO EDGE EVIDENCE** | No rentable demostrado; aislado de método/COG |

## Próxima misión CERTIFICADORA no cuantitativa

1. Congelar qué se intenta certificar: `ICT_GENERAL_2023` (tres sesiones) o `TTRADES_NY_AM_2025` (variante exclusivamente AM) y QORE-specific choices claramente etiquetadas. **Recomendación:** NO imponer TTrades AM como regla universal ICT; proseguir primero una auditoría de fidelidad a ICT general en London/NY y dejar TTrades AM como perfil separado. No habilitar `TTRADES` sin implementar su contexto sweep/target.
2. Añadir `CognitiveEvidenceV2` immutable, versionado POR PERFIL: high/low H1 9AM as-of para TTrades, raid timestamp e invalidez, MSS estructural con testigo de pivote y desplazamiento, destino DOL as-of y razón `UNKNOWN`; separando observaciones de inferencias. Ningún evento de source error debe generar entrada.
3. Tests adversariales específicos M2/M3 con **COG real**, no DTO favorable, y casos autorales fuente primarios en M4 OB/Breaker solo donde haya especificación concreta; faltantes marcar ambiguos, no inventar geometrías.
4. Review metodológica por COG y contraste de datos OPS independientes, con firmas conforme autoridad disponible y eventual actualización explícita de gobernanza por el propietario si solo hay una cuenta. No llamarlo aprobado hasta evidencias. Tras M0–M6 procede Gate M7 independiente, sin introducción de lotaje trader.

**Frontera congelada intacta:** G3 act commit `a446afa17ed6e411b8f0b6fc182b103a78959a97` y código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`. Sin merge/main, sin paper OMS, sin live, sin cartera ni sizing, sin holdout, sin PnL ni replays económicos en MC-P1. El éxito aquí es que **una metodología incorrectamente etiquetada no puede pasar como certificada**, y el próximo paso está técnicamente definido.
