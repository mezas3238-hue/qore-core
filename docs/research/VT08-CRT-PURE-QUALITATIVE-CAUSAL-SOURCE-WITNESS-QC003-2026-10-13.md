# VT08 CRT PURE — QC-003: TESTIGO CAUSAL DE NIVEL ANTIGUO → VELA FUENTE → COGNITIVA

**Fecha:** 13-OCT-2026 · **PR:** #626 DRAFT · **Modo:** OWNER SOURCE-FIRST / NO NUEVA INVESTIGACIÓN CUANTITATIVA  
**Tipo:** ingeniería de fidelidad semántica y pruebas causales sintéticas — SIN datos/resultado PnL, SIN backtest.  
**Checkpoint anterior:** [QC-002](VT08-CRT-PURE-QUALITATIVE-COGNITIVE-SOURCE-CODE-AUDIT-QC002-2026-10-13.md).

## 1. Causa raíz y objetivo

En el Model #1 histórico, `CrtPureModel1Reference` llevaba `kind/price/evidence_id`, pero **no** la vela origen, su disponibilidad antes de la fuente, la relación con el H4 C3 ni una unión verificable al `CrtPureSituationModel`. Los productores R2-BY/BZ/CC/CD crean `SituationModel` con `source_event_present=True` y `confirmation_complete=True` para un trade ya seleccionado; esos booleanos **no** prueban la propiedad del antiguo nivel.

**Objetivo:** crear un puente **opt-in de investigación cualitativa**, reversible y sin autoridad operativa, que transporte un testigo verificable en cuanto a **coherencia de tiempo y geometría**, nunca inventar el origen del mercado ni un algoritmo de "mejor nivel".

### Código agregado

`src/qore/infrastructure/traders/crt_pure_model1_cognitive_witness.py`

- `CrtPureModel1CausalWitness`: objeto inmutable con mercado, identidad CRT padre, ventana H4/C3, vela M15 de origen de nivel, instante `reference_known_at`, lista de referencias elegibles, objeto original `CrtPureModel1Confirmation` y `observed_at`.
- Comprueba que el old-high/low de `candidate.reference` sea exactamente el máximo/mínimo de la vela de origen declarada.
- Comprueba que esa vela haya cerrado **antes** de considerarse disponible; `reference_known_at <= source.opened_at`. Cualquier referencia conocida después de la apertura de la fuente se rechaza como retrospectiva.
- Comprueba que fuente abra dentro del H4 C3, que confirmación M15 empiece una vez cerrada la fuente y que la decisión de confirmación ocurra dentro de C3. La lectura cognitiva no puede preceder la confirmación.
- Reejecuta semánticamente `detect_model1_candidate` y `assess_model1_confirmation` sobre velas entregadas; si el candidato o el estado declarado no coincide con la geometría, el testigo se rechaza. Wicks no equivalen a cierre corporal.
- Rechaza IDs duplicados/vacíos y referencia elegida ausente de la lista; el `source_event_id` proviene de `market + parent + source_M15 + direction`, **no** del número de viejos niveles atravesados.
- `build_model1_cognitive_situation` crea observaciones `CrtPureCausalObservation` con sus instantes causales reales y el vínculo explícito al `reference.evidence_id`, separando disponibilidad del nivel, vela fuente y confirmación.
- Todas las banderas externas se exigen como parámetros explícitos: integridad datos, identidad estratégica, disponibilidad de destino, frescura de ejecución. El testigo no puede mentir asumiendo automáticamente que tales gates están `True`.

**Seguridad epistémica:** incluso si la lista de niveles tiene solo uno, `knowledge_state=PARTIAL`, `uncertainties=(MODEL_1_REFERENCE_SELECTION_AMBIGUOUS, MODEL_1_REFERENCE_ELIGIBILITY_IS_UPSTREAM_ATTESTED)`, porque la fuente primaria documentada no ha cerrado un algoritmo de selección old-level ni se verifica aquí la autenticidad de las velas upstream. **No promueve `KNOWN`, no produce `EXECUTE` del razonador a partir de estos testigos.** En caso de datos explícitamente no íntegros, la cognitiva puede `ABSTAIN`.

## 2. Ejemplo de razonamiento: SOLO SINTÉTICO

Caso bajista académico con valores enteros arbitrarios que **NO** pertenecen a AUDUSD real:

- 09:00 M15 vela de referencia: high = 105; `reference_known_at = 09:15`.
- 10:00 M15 vela fuente alcista: open = 104, high = 108, close = 107; penetra 105.
- 10:15 M15 confirmante: cierra = 103, por debajo de 104; `decision_at = 10:30`.
- H4 C3 = 08:00–12:00 UTC, identidad padre `h4-parent-001`.
- La construcción de testigo acepta coherencia de vela/tiempo; `CrtPureSituationModel` contiene observaciones con procedencia referenciable y `knowledge_state=PARTIAL`.
- **Dictamen en papel:** `WAIT`, porque `MODEL_1_REFERENCE_SELECTION_AMBIGUOUS` y elegibilidad de nivel **son upstream-attested, no canónicas verificadas**. No existe backtest, trade ni licencia de producción.
- Si vela confirmante solo toca por wick pero cierra por encima del cuerpo fuente: `AWAITING_CONFIRMATION` y `WAIT`.
- Si el nivel solo se conoció luego de las 10:00: constructor rechaza la prueba de antemano.
- Si integridad externa es `False`: el razonador devuelve `ABSTAIN`, sin rescatar la fuente.

## 3. Pruebas estructurales creadas

`tests/infrastructure/traders/test_crt_pure_model1_cognitive_witness.py`: casos de coherencia de referencia y confirmación, fuente única con varios niveles, rechazo de referencia reconocida tarde, origen con precio contradictorio, rechazo de "known" antes de cierre, vela fuente fuera de C3, muestra de confirmación falsificada, acceso antes del cierre, referencia no presente, integridad negativa, identidad estratégica no lista y procedencia de observaciones.

Workflows de calidad: `.github/workflows/vt08-crt-pure-cognitive-foundation.yml` y `vt08-crt-pure-cognitive-gate.yml` ejecutan Ruff/Mypy/Pytest con el nuevo módulo y test; ninguna de estas pruebas consulta cTrader, broker, capital o PnL.

**Importante:** ni el constructor ni los ejemplos sintéticos verifican que un feed cTrader concreto sea auténtico, ni que el antiguo nivel sea realmente el correcto. Solo verifican correspondencia interna de un conjunto de OHLC/procedencia **que alguien entregó**.

## 4. Límites sin ocultar

| Pregunta | Estado |
|---|---|
| ¿Cognitiva tiene un camino explícito desde la vela de origen a fuente y confirmación? | **SÍ, PILOTO DE INVESTIGACIÓN** mediante `CrtPureModel1CausalWitness` + `build_model1_cognitive_situation`. |
| ¿Prueba en cTrader datos reales de AUDUSD/USDJPY? | **NO**. Pruebas usan OHLC sintéticos y timestamps UTC fijos. |
| ¿Resuelve la propiedad/jerarquía de varios old levels? | **NO**, `MODEL_1_REFERENCE_SELECTION=AMBIGUOUS` sigue vigente. |
| ¿Prueba que referencia fue elegible por el método original? | **NO**, la disponibilidad es una declaración upstream. |
| ¿Actualiza automáticamente los 4 productores R2-BY/BZ/CC/CD? | **NO**. Permanecen históricos congelados: conectarlos activaría un cambio semántico en experimentos cuantitativos prohibidos actualmente. |
| ¿Habilita EXECUTE / órdenes / certificación? | **NO**; bridge investigador bloquea promoción por conocimiento incompleto. |
| ¿Hace lotaje/sizing/apalancamiento/capital? | **NO, PROHIBIDO**. |

## 5. Próxima labor **solo metodológica**

1. Verificar fuente original del autor en contexto sobre la pertenencia/prioridad de old HIGH/LOW; si la fuente sigue sin definirlo, mantener ambigüedad explícita en lugar de crear `strength=1` como ley del autor.
2. Obtener de datos existentes **una secuencia real H4 y M15 con provenance** y elaborar ficha vela por vela, señalando qué conocimiento estaba disponible en cada cierre; **sin** evaluar PnL.
3. Diseñar el adaptador de un proveedor real al testigo causal, con hash/source/timestamp OHLC; no se implementa ni activa una regla de selección de pivotes sin justificación original y Owner.
4. Mantener PR en DRAFT; no ejecutar WFO/Monte Carlo/optimización cuantitativa.
5. Evaluar frontera de seguridad del router R2, cuyo `action=EXECUTE` conceptual de *entry family* ya declara `grants_execution_authority=False`; este retorno no es la decisión final `reason()` y no debe tratarse como autorización.

**Gobernanza:** BTCUSD market checkpoint intacto, VT08 global `NOT CERTIFIED`, `NO SIZING/LOT/VOLUME/LEVERAGE/CAPITAL`, no merge, no VPS, no DEMO, no LIVE, no producción ni dinero real.
