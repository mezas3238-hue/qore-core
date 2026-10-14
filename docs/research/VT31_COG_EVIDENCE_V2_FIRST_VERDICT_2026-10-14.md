# VT31 — COG_EVIDENCE_V2: avance real hacia certificación metodológica y cognitiva

**14 octubre 2026 · Fase M0–M3 (pruebas de contexto causal).** **Veredicto:** `V2_MSS_PIVOT_CONTEXT_WITNESS_PASS`; estado del trader **`COGNITIVE_METHOD_CERTIFICATION_PENDING`**. Este expediente no mide rentabilidad, no habilita órdenes y no modifica el COG real.

## Evidencia de ejecución

- Preregistro previo al código: `docs/research/VT31_COG_EVIDENCE_V2_PREREG_2026-10-14.md`, commit **`268da6ef24507f299f50d50723ba3c0c93a850ad`**.
- **[CI #38594178014 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38594178014)** con código exacto commit **`150837fd1d84ef4a16b07ce03ebf5fcf5ee400d4`**, **80/80 pruebas PASS**, Ruff/compile, checksums y blob de G3 original verificados. Artefacto **`11908981245`** con JUnit/manifest.
- Incluye 17+ pruebas de V2 (una parametrizada), 13 del M0–M3 previo y 49 de regresiones COG/OPS/M1/G3, es decir **80** verificadas. NO confundir los 80 tests con 80 trades.
- Rama **`agent/vt31-cog-evidence-v2-causal-attestation-20261014`**. Origen PR #926, independiente de PR #896 (G3), sin editar `src/qore/infrastructure/traders/vt31_ict_cleanroom/{cognition,operations}.py` ni acta G3.
- Script: `scripts/vt31_cog_evidence_v2_20261014.py`, pruebas adversariales: `tests/infrastructure/test_vt31_cog_evidence_v2_20261014.py`, CI `.github/workflows/vt31-cog-evidence-v2-semantic-gate.yml`.

## Qué hace ahora realmente el nuevo atestador

`COG_EVIDENCE_V2` usa una **decisión original existente** `CognitiveDecision` o `None`, perfil de fuente explícito, hora `as_of` externa, sesión y serie ordenada de `M1Bar` cerradas. No produce nuevas decisiones de trading y no elige señales por rendimiento.

1. **Relee de las velas** el cierre M1 exacto donde COG afirma que se produjo MSS. Si el DTO G3 dice otro precio, emite `REJECTED:MSS_ANCHOR_CLOSE_MISMATCH_WITH_M1`. No acepta último C3 como sustituto del cierre original de MSS.
2. **Contrasta el pivot** con la tríada M1 izquierda/centro/derecha, marca de confirmación de la vela derecha, extremo estricto y nivel exacto que declara COG; veda `PIVOT_LEVEL_OR_CONFIRMATION_INCONSISTENT`. Requiere continuidad en dicha tríada.
3. **Comprueba ruptura real y desplazamiento**: LONG previous close <= high pivot < MSS close y MSS bullish, SHORT inverso; cuerpo MSS >=1,25 × mediana de los 5 cuerpos cerrados de referencia conforme **formalización QORE** en código previo, sin afirmar que ICT/TTrades imponen ese multiplicador.
4. **Perfil TTrades NY AM específico**: H1 09:00–10:00 con 60 M1, barrido del extremo y orientación, MSS posterior a sweep, cierre dentro del rango y target en el H1 opuesto; el comprobador heredado PR #926 funciona como segunda verificación de contexto. Si ambos extremos se barren dentro de una M1, declara `UNKNOWN` por orden intraminuto imposible de determinar con OHLC, no un fill.
5. **Perfil ICT_GENERAL_2023**: no exige H1 09AM a Londres/PM; su DOL declarado no puede darse por corroborado sin fuentes independientes anteriores de liquidez, por lo que documenta `UNKNOWN:ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED`. Esto **no equivale a que el ICT general sea falso**.
6. Tres estados máximos `CONFIRMED/REJECTED/UNKNOWN` para **M0–M3 exclusivamente**. Incluso `CONFIRMED` mantiene `method_certified=false`, `cognition_certified=false`, `live_authorized=false`.

## Prueba clave: salida real de la COG existente, no un DTO inventado

Se construyó un testigo **sintético de mercado**, pero la decisión fue emitida por el **`VT31CleanroomCognition` auténtico** con política G3:

- Un día previo NY cash de **390 M1** con high **150**; el H1 NY 09:00–10:00 del día de prueba tiene high **110** y low **90**; en 10:00 hay barrido del low 90 y MSS LONG causal posterior, pivote 104, cierre original de MSS 105.
- La COG real seleccionó `PRIOR_NY_CASH_SESSION_HIGH=150` porque así funciona su motor de DOL contextual, y preservó correctamente pivote 104 y cierre MSS 105.
- **Resultado para `TTRADES_NY_AM_2025`: `REJECTED`** exclusivamente por `DOL_NOT_OPPOSITE_9AM_H1_EXTREME`: objetivo de TTrades AM sería **110**, no 150. **Esto demuestra con una salida genuina de COG** que el algoritmo actual no puede recibir certificación automática para esa metodología particular.
- **La misma decisión evaluada como `ICT_GENERAL_2023`: `UNKNOWN` por falta de corroboración externa independiente del DOL**, sin imposición inventada de regla 09AM. No falsar ni revocar el COG general por un requerimiento particular de TTrades.
- La muestra anterior es **una prueba adversarial sintética diseñada para revelar una incompatibilidad de contrato**, NO porcentaje de fallos en datos reales, no win rate, no demostración de falta de ventaja de todo VT31.

## Pruebas negativas superadas

MSS-close falso, pivot-price alterado, confirmación pivote incorrecta, ruptura no cruzada, vela de impulso insuficiente, falta de H1 fuente, barrido doble intrabar, DOL erróneo por perfil, decisión COG ausente, timestamp as-of falsificado, duplicados, MSS no observable, revalidación en M1 posterior al MSS, perfil ICT London sin H1 09AM, y respuesta sin permisos LIVE.

## Qué todavía impide certificar

| Etapa | Estado | Acción siguiente |
|---|---|---|
| M0 identidades ICT vs TTrades | **Diferenciadas en comprobador** | Instalar selector de perfil *explícito* solo en nueva rama de cognitiva; no mutar G3 |
| M1 causalidad timestamps | **Atestador V2 PASS** | Confirmar con flujos completos reales NY + DST y gapped M1 |
| M2 sweep y DOL | **TTrades witness PASS en escenarios sintéticos** | Construir DOL 09AM H1 nativo en nueva COG TTrades; no usar nearest prior cash por accidente |
| M3 MSS/pivot/impulso | **Atestación independiente PASS en tests** | Construir serie `COG_EVIDENCE_V2` as-of por cada M1 candidata; revisar falsas inferencias y casos UNKNOWN en replay doctrinal |
| M4 entradas FVG, OB, Breaker, displacement | **NO CERTIFICADAS** | Asociar familias con testigos fuente, OB/Breaker siguen formalizaciones QORE; sin mezclar con ICT canónico |
| M5 stops, objetivos y expiración | **NO CERTIFICADAS** | Fuente y política por perfil; lotaje reservado a CIBO/QDLE, sin sizing del trader |
| M6 firmas independientes COG/OPS | **PENDIENTES** | Issue #897; jamás firmar dos veces con la única cuenta |
| M7 ejecución y economía | **NO CERTIFICADAS** | Validación separada sin inventar fills ni PF |

**Mandato técnico siguiente:** crear un adaptador COG TTrades AM *a investigación solamente* que genere desde M1 los testigos de sweep y DOL, que puedan ser auditados por V2 antes de componer una `CognitiveDecision`; mantener `ICT_GENERAL_2023` sin filtros 09AM. Crear matrices negativas de fallos de selección de liquidez y estado `UNKNOWN`, e integrarlo solo bajo nueva rama PR, nunca dentro de código G3 bloqueado.

**Seguridad:** no se abrió holdout, no hay datos económicos nuevos, no MERGE, no OMS, no LIVE/VPS, no órdenes, no PF y no promesas de rentabilidad. G3 acta commit `a446afa17ed6e411b8f0b6fc182b103a78959a97` + code `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` intacto/unsigned. Certificación económica de VT31 no demostrada.
