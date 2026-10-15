# VT31 — Dictamen cognitivo cualitativo del COG ORIGINAL NY PM y frontera de método

**2026-10-15 · METODOLOGÍA y COGNITIVA; sin evaluación económica.** Esta revisión complementa PR #951 y PR #950, enfoca al productor G3 ORIGINAL, no a un sustituto TTrades ni a una regresión de rentabilidad. El COG G3 original sigue inalterado.

## Procedencia y verificaciones reproducibles
- [PR #953 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/953), prereg antes del código/CI commit `d2cfef4ea238c34f479bd104a03853136f8c66e0` en `docs/research/VT31_ORIGINAL_COG_NYPM_QUALITATIVE_SOURCE_PREREG_2026-10-15.md`.
- [GitHub Actions #38707397529 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38707397529), commit exacto de código/test **`2e7f178dfe2417f4a3283f0c993d5253cb73cdd3`**, **41/41** pytest PASS, Ruff y Python compile PASS, los 3 blobs originales G3 COG/OPS/acta verificaron SHA esperado.
- [Artifact #11959135942](https://github.com/mezas3238-hue/qore-core/actions/runs/38707397529/artifacts/11959135942) ZIP SHA256 **`f9ccfa7a62e467db595992819024d8b02f8b4d44b7e1dc4c41dd874020e47bfe`**, JSON de 6 escenarios, timestamps `as_of`, pruebas JUnit y hashes internos.
- Nuevo script **`scripts/vt31_original_g3_nypm_cognition_qualitative_20261015.py`**, test **`tests/infrastructure/test_vt31_original_g3_nypm_cognition_qualitative_20261015.py`** y CI `.github/workflows/vt31-original-g3-nypm-cognition.yml`. Pruebas con velas M1 sintéticas cerradas; ninguna encuesta de mercado real 3Y, PnL o holdout.

## Situaciones y decisiones AUTÉNTICAS del productor G3
| Entrada causal y condición observada | Decisión genuina | Dictamen limitado |
|---|---|---|
| M1 completo previo NY cash HIGH150, H1/M15 actuales verificados, pivote HIGH104 confirmado antes del breakout NY 14:02 close105 | LONG, target150, estructura104 | Tesis funcional QORE coherente con sus fuentes y reloj en escenario NY PM, **no** autor-certificación ICT |
| Prefijo NY PM termina antes de la M1 MSS | WAIT | Abstención genuina por no confirmar shift |
| Quitar M1 10:00–13:59 (HTF H1/M15 stale) | WAIT | No inventa contexto HTF contemporáneo |
| Nueva M1 futura cronológica hace `high=151` y consume DOL150 | WAIT | No reutiliza destino ya mitigado |
| Nueva M1 cierra 102 por debajo del pivote LONG104 | WAIT | Tesis persistida revocada correctamente |
| Después de insertar M1 nueva solicitar un `as_of` pasado | REJECT | Bloqueo de backdating/uso de información futura |

**Confrontación de perfil sobre EL MISMO `CognitiveAssessment` original:** declara `ICT_GENERAL_2023` ⇒ **`ICT_CONTEXT_WITNESS_UNDERDETERMINED`**, porque la procedencia autoral ICT exacta de DOL contextual no está homologada. Declara `TTRADES_NY_AM_2025` ⇒ **`PROFILE_SESSION_REJECTED`**: la metodología de 09h H1 barrido NY 10:00–11:00 no aplica universalmente al Silver Bullet NY PM. No se atribuyó al ICT autor ninguna regla QORE de body≥1.25×mediana5 ni stop C2 como si fuera obligatoria.

## Cierre parcial de M0–M3, pendientes
- **M0 IDENTIDAD**: auditor de frontera de PR #951 distingue ICT GENERAL y TTrades y evita atribución cruzada. Todavía NO hay selector oficial de perfil predecisión integrado en el trader, firmado ni autorizado; instrumento solo investigación sombra.
- **M1 CAUSALIDAD**: originales London/NY AM/NY PM conservan reloj M1 y rechazan retro-as-of en escenarios observados. Faltan pruebas espejo de sesiones, DST EST/EDT y transición completa por días calendario en COG original.
- **M2 LIQUIDEZ**: confirma destino QORE válido en London y NY PM; para TTrades NY AM, PR #950 halló DOL 150 vs exigido 110, no conforme a perfil autoral TTrades. El testigo ICT GENERAL de procedencia independiente aún incompleto; no llamar esto certificación de fuente.
- **M3 ESTRUCTURA**: rechaza señal antes de MSS, revalida tesis y revoca al romper pivote en London/NY PM; MSS estructural `1.25×median5` solo formalización QORE y falta prueba autoral.
- **M4/M5**: permanecen ambigüedades autorales Order Block/Breaker y swing stop (PR #943, #945), y selector de familia/invalidación; no aprobar método entero por tests M0–M3.
- **M6 GOVERNANCE**: falta doble firma humana COG/OPS independiente issue #897 sobre versión exacta. Automático CI PASS ≠ juicio cognitivo certificado.

## Próximo trabajo P0 para arquitecto sucesor
1. Diseño de identidad metodológica: bajo una misma entidad VT31, perfiles gobernados separados; decidir oficialmente si NY AM sigue ICT GENERAL QORE o se adopta TTrades AM. NO convertir esta auditoría de solo lectura en veto ejecutable sin autorización del Owner y acta G3.
2. Ejecución real del **COG original** con escenarios espejo SHORT de las tres ventanas, no solo LONG; contrafactual único M1 que cambie primer sweep vs no-sweep; clasificar `WAIT/UNKNOWN/REJECT` como juicios válidos; incorporar CognitiveTelemetry de cada contexto.
3. Etiquetas de doctrina: cotejar ejemplos primarios ICT/TTrades verificables con swing, MSS y familia FVG/OB/Breaker. Etiquetar formalizaciones QORE cuando no hay regla textual determinista; no adaptar parámetros a retornos antiguos.
4. Preparar dos expedientes humanos separados `CERTIFICADO_METODOLOGIA` y `CERTIFICADO_COGNITIVA` y exigir evidencia y firmantes auténticos. PF/DD/Sharpe pertenecen exclusivamente al eventual expediente económico Trader Lab; no son criterios de estos dos certificados.

**Estado final:** `METODOLOGIA=PENDIENTE`, `COGNITIVA=PENDIENTE`, `VT31=NO_CERTIFICADO`, `NO_DEMO/LIVE`. Sin merge/main, órdenes, FundedNext LIVE, VPS, sizing propio (CIBO CMA reservado) ni optimización económica. Texto de dictamen añadido luego del commit de CI probado; no reclamar que su propio HEAD fue ejecutado.