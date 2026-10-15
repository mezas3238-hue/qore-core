# VT31 — Cambio de prioridad por orden del Owner: metodología y cognitiva (dictamen inicial de escenarios)

**14-OCT-2026 · Perfil TTRADES_NY_AM investigación · NO certificación todavía.** Directiva Owner: certificar VT31 por SU METODOLOGÍA y SU COGNITIVA, no por trading cuantitativo, PnL, PF, WR, Sharpe, Sortino, DD ni frecuencia. Este documento es el resultado de un procedimiento cualitativo de decisiones, no un backtest económico.

## Orden y jerarquía de pruebas
- Mandato registrado en docs/research/VT31_DIRECTIVA_OWNER_CERTIFICACION_METODOLOGICA_COGNITIVA_SIN_PNL_2026-10-14.md, PR #946 DRAFT, rama agent/vt31-method-cognitive-scenario-certification-20261014.
- Pre-registro anterior al código: SHA d8d1aa4354b4f63602dc5706c0eed3a735ecafe6, archivo docs/research/VT31_TRIBUNAL_METODOLOGIA_COGNITIVA_ESCENARIOS_PREREG_2026-10-14.md.
- [CI SUCCESS #38659592247](https://github.com/mezas3238-hue/qore-core/actions/runs/38659592247) commit exacto cf6bf46b9fb4f316128b64c019882016c1cc5b31; Ruff PASS, py_compile PASS y 115/115 tests funcionales/regresión PASS; blobs fuente G3 COG/OPS/acta LOCK verificados.
- [Artefacto revisión de decisiones #11938800808](https://github.com/mezas3238-hue/qore-core/actions/runs/38659592247/artifacts/11938800808) ZIP SHA256 0b7965c2d04777ea350d97c9a17dea9eca3396edf6d21344d7e513fca445f7df; JSON `VT31_METHOD_COG_JUDGMENT_SCENARIOS_NO_PNL.json` con caso a caso y razón.
- SIN abrir dataset de NAS100 3Y en esta ejecución, SIN mercado futuro/OOS, SIN costes, trades ni estadísticas económicas.

## Juicio cognitivo cualitativo observado (ejemplos sintéticos, no autor etiquetado)
| Situación | Acción COG research observada | Interpretación |
|---|---|---|
| Sweep LOW H1 09h; regreso confirmado, MSS en M1 cerrada, destino high09 | **LONG** | Propuesta contextual coherente con fuente TTrades AM, no entrada autorizada |
| Sweep HIGH H1 09h; espejo de regreso MSS, target low09 en invierno | **SHORT** | Coherencia direccional y DST EST/EDT respetados |
| Nunca barrida liquidez 09h | **WAIT** | Abstención correcta según perfil TTrades |
| Ambas puntas H1 barridas misma vela M1 | **WAIT** | Intrabar desconocido, no fabricar orden high/low |
| Retorno sin pivote/MSS proxy confirmado | **WAIT** | No fabricar confirmación, aunque el precio pueda seguir |
| Sólo 59 M1 del H1 anterior | **WAIT** | Datos incompletos, no imputar H1 |
| Vela del futuro incluida en historia | **REJECT** | Prohibida anticipación de información |
| Aplicar perfil AM TTrades a sesión Londres | **REJECT** | Segregación ICT_GENERAL vs TTRADES |
| Primer retorno antiguo frente al as-of posterior | **WAIT** | No revivir entrada tardía usando confirmación futura |
| DTO con destino falso 150 frente al high09 real 110 | **REJECT** | Verificador independiente detecta DOL contrario |

Los escenarios reflejan el productor `scripts/vt31_ttrades_am_native_cog_v1_20261014.py`, sometido a un testigo independiente V2; **éste es un COG de investigación, NO es la implementación original de G3 `cognition.py`**. Los casos son fabricados para aislar reglas sin información de beneficio, y por sí solos NO prueban que todo el COG real actúe igual ni que el algoritmo de MSS 1,25× sea doctrina TTrades.

## Dos certificaciones, dos actas
**METODOLOGÍA PENDIENTE**: faltan fuentes/testigos autorales completos de Order Block, Breaker y swing stop; decidir si certificar el perfil TTrades autoral o metodología QORE original declarada, reglas de elección/invalidación y política de salida fuente-compatibles. La auditoría #943 C2 vs pre-MSS (116 distintos de proxy) y #945 4-leg son hallazgos cualitativos de definición, no aprobaciones ni filtros económicos.
**COGNITIVA PENDIENTE**: el COG G3 original no fue examinado directamente por este tribunal; necesita escenarios de decisiones auténticas con entradas sin etiquetas, logs de porqué/contexto/memoria causal, revisión humana de la conducta frente a fuentes, contrafactuales espejo que no dependan de PnL y manejo de abstención. Requiere validación independiente, ninguna firma inventada #897.
**EVALUACIÓN ECONÓMICA FUERA DE ESTA CERTIFICACIÓN**: las obligaciones oficiales Trader Lab L1–L10 permanecen para futura elegibilidad DEMO, pero no serán utilizadas como atajo o sustituto para firmar estos dos certificados de conocimiento.

## Siguiente trabajo P0
1. Someter al **COG G3 real**, no sólo al productor research, a una batería de situaciones de mercado causales donde deba justificar DOL, MSS, FVG, ausencia de setup, datos incompletos e identidad de método por sesión; guardar salida cruda y razones, sin alterar su código y sin conocimiento de PnL.
2. Crear pares fuente autoral/contraejemplo TTrades AM e ICT GENERAL independientes; si el COG G3 discrepa, registrar divergencia y corregir únicamente con versión nueva y revisión metodológica, no optimizar con trades antiguos.
3. Producir expediente humano por Gate M0–M6 con clasificación cualitativa `METODO_CONFORME`, `COG_CONFORME`, `NECESITA_CORRECCION`, `INDETERMINADO_POR_FUENTE`, `RECHAZADO`. Buenas abstenciones se consideran buen criterio, no errores de baja densidad.
4. Sólo emitir `CERTIFICADO_METODOLOGIA` y `CERTIFICADO_COGNITIVA` cuando las dos revisiones sean completas y con firmantes independientes reales (Issue #897). De otro modo mantener estado PENDING, incluso con todos los tests en verde.

NO MERGE, NO PRODUCCIÓN, NO LIVE, NO VPS, NO FundedNext LIVE, NO OMS, NO sizing propio del trader. La autonomía de volumen corresponde a CIBO/CMA/QDLE. El informe fue agregado después de la CI exitosa y no afirma que su propio HEAD documental se haya reejecutado.