# QORE CORE — HANDOFF MAESTRO DE INVESTIGACIÓN FORENSE — ROUND 2 HARDENED

## TURTLE SOUP CANDIDATE R1

### MANAGEMENT, RE-ENTRY, INTRADAY AGE, SESSION DATA, GAP SEMANTICS & MECHANICAL-EXIT CLOSURE

**Checkpoint:** 14 de septiembre de 2026  
**Repositorio de verdad:** `mezas3238-hue/qore-core`  
**Issue:** `#551`  
**PR autoritativo:** `#553` — DRAFT  
**Research identity:** `turtle-soup-candidate-r1`  
**Canonical Trader Code:** `CODE_UNASSIGNED`  
**Investigador:** DeepSeek — Source Reconstruction  
**Ingeniería posterior:** QORE Engineering — implementación, replay, falsificación, backtest y certificación

---

# 0. ORDEN MAESTRA

Este Round 2 NO es una nueva explicación general de Turtle Soup.

Tu Round 1 fue útil como mapa de variantes, pero contenía errores materiales de reconstrucción y NO tiene autoridad ejecutable. QORE Engineering ya lo adjudicó contra texto recuperable de Connors/Raschke `Street Smarts`.

Tu tarea ahora es cerrar, con máxima profundidad y disciplina de fuente, SOLO los blockers que todavía impiden convertir la metodología source-faithful en un replay económico defendible.

NO debes devolver:

- un resumen de blogs;
- una recopilación de variantes modernas;
- una opinión;
- una estrategia mejorada;
- una recomendación de optimización;
- un backtest propio como sustituto de reglas de fuente;
- una respuesta `probablemente` sin evidencia;
- `UNRESOLVED` sin documentar exhaustivamente qué buscaste;
- una regla inventada porque parezca razonable.

Debes trabajar como investigador forense adversarial.

Cadena obligatoria:

`FUENTE -> LOCALIZADOR -> TEXTO/OBSERVACIÓN -> CLAIM -> CONTRA-EVIDENCIA -> VEREDICTO -> FORMALIZACIÓN -> AUTOMATIZABLE/NO`

---

# 1. PREMISAS CONGELADAS — NO REABRIR SIN EVIDENCIA DIRECTA SUPERIOR

## 1.1 Classic Turtle Soup

QORE congela como autoridad actual:

- reference family: `20-period extreme`;
- previous extreme: al menos **4 trading sessions earlier**;
- entrada Classic: **same-session reversal stop entry**, NO Day-2;
- daily/futures entry: **5–10 ticks** más allá del anterior extremo de 20 períodos en dirección de reversión;
- orden válida solamente para la sesión/día actual;
- stop inicial: **1 tick más allá del extremo de la sesión/breakout actual**;
- la fuente permite re-entry en el original entry price si el trade fue stopped out durante Trade Day 1 o Trade Day 2;
- trailing/tightening del stop está autorizado por fuente, pero el algoritmo exacto no está cerrado;
- NO existe autoridad actual para un target fijo de 5 períodos;
- NO existe autoridad actual para 2R fijo.

## 1.2 Turtle Soup Plus One

QORE congela:

- reference family: `20-period extreme`;
- previous extreme: al menos **3 trading sessions earlier**;
- breakout bar cierra at/beyond el anterior nivel de 20 períodos;
- entrada en la siguiente barra/día;
- stop-entry en el **earlier 20-period level**;
- cancelar si no se ejecuta en esa siguiente barra/día;
- stop inicial: 1 tick más allá del extremo combinado de breakout bar + entry bar;
- fuente autoriza tomar parciales dentro de **2–6 bars** y trail el balance;
- exact partial fraction, trigger y trailing algorithm permanecen sin resolver.

## 1.3 Intraday

NO clasifiques Turtle Soup como Daily-only.

QORE ya recuperó evidencia de que Connors/Raschke presentan ambas metodologías como aplicables a todos los timeframes y muestran ejemplos intradía de 10 minutos.

QORE también congela como autoridad actual que la entrada intradía se expresa aproximadamente como:

- LONG: prior 20-bar low + 1 tick;
- SHORT: prior 20-bar high - 1 tick.

Lo que permanece abierto es la semántica exacta de las reglas de antigüedad 4/3 `trading sessions` cuando el gráfico es intradía.

---

# 2. FUENTES Y JERARQUÍA OBLIGATORIA

## TIER A — PRIMARY / DIRECT ORIGINAL

Prioridad máxima:

1. `Street Smarts: High Probability Short-Term Trading Strategies` — Connors & Raschke.
2. Ediciones legales, previews, scans o reproducciones verificables del texto original.
3. Código, apéndices, tablas, captions y ejemplos del propio libro.

## TIER B — DIRECT AUTHOR MATERIAL

Solo material directamente atribuible a Connors o Raschke:

- LBRGroup;
- artículos de la autora;
- seminarios/webinars;
- transcripts;
- entrevistas;
- material de curso;
- publicaciones directas;
- código publicado o distribuido por los autores.

## TIER C — SECONDARY

Oxfordstrat, MQL5, FBS, WH SelfInvest, EasyTradeWeb, TradingView, blogs, foros, etc.

Tier C sirve para:

- descubrir pistas;
- localizar vocabulario;
- encontrar referencias a páginas o seminarios.

Tier C NO puede cerrar por sí solo un blocker canónico.

Si la única evidencia es Tier C:

`VERDICT = NOT_CLOSED_BY_AUTHORITATIVE_SOURCE`

---

# 3. REGLA DE PRUEBA PARA CERRAR UN BLOCKER

Un blocker solo puede marcarse `CLOSED` si existe:

1. evidencia Tier A o B con localizador preciso;
2. texto suficiente para sostener la regla;
3. búsqueda adversarial de contradicciones;
4. ausencia de contradicción de mayor autoridad;
5. formalización ejecutable sin introducir información futura.

Si no se cumplen los cinco criterios:

`UNRESOLVED_WITH_EVIDENCE`

NO usar `probablemente`, `parece`, `se suele`, `generalmente`, `puede ser` como sustituto de un veredicto.

---

# 4. SOURCE PACKET OBLIGATORIO POR CADA HALLAZGO

Cada claim material debe venir acompañado de:

```text
SOURCE_ID:
TIER:
AUTHOR:
TITLE:
PUBLICATION_DATE:
URL_OR_ARCHIVE:
ACCESS_DATE:
PAGE_OR_SECTION:
EXACT_LOCATOR:
EXCERPT:
CONTEXT_BEFORE_AFTER:
CLAIM_SUPPORTED:
CONTRADICTION_SEARCHED:
CONTRADICTION_FOUND:
CONFIDENCE:
```

No aceptar:

- snippets de buscador como evidencia final;
- citas sin página/sección si la fuente tiene estructura localizable;
- atribuciones de segunda mano a Raschke;
- una URL sin mostrar qué parte sostiene el claim.

---

# 5. BLOCKER A — CLASSIC TRAILING STOP

Objetivo: determinar si existe un algoritmo de trailing suficientemente mecánico y atribuible a Connors/Raschke.

Investiga explícitamente:

- previous-bar low/high;
- two-bar low/high;
- N-bar swing;
- ATR/volatility stop;
- fixed tick trail;
- percentage retracement;
- break-even movement;
- stop under/over prior bar;
- close-based trail;
- structural swing trail;
- time stop;
- end-of-day exit;
- multi-day time exit;
- parabolic move exit;
- scale-out + stop adjustment.

Debes responder:

```text
CLASSIC_TRAILING_EXISTS = YES / NO / PARTIAL
ACTIVATION_CONDITION =
UPDATE_FREQUENCY =
LONG_FORMULA =
SHORT_FORMULA =
STOP_CAN_LOOSEN = YES / NO / UNRESOLVED
BE_RULE =
FINAL_EXIT_RULE =
```

Si no existe fórmula mecánica autoral:

`CLASSIC_MANAGEMENT_DISCRETIONARY`

Eso es preferible a inventar una regla.

---

# 6. BLOCKER B — PLUS ONE PARTIAL PROFITS + TRAILING

La fuente actual solo cierra:

`take partial profits within 2–6 bars and trail balance`

Investiga exactamente:

- partial fraction;
- partial count;
- earliest bar;
- latest bar;
- exact bar choice;
- price trigger;
- R-multiple trigger si existe;
- percent move trigger si existe;
- break-even rule;
- stop adjustment after partial;
- trailing formula;
- final exit;
- time expiry.

Salida obligatoria:

```text
PLUS_ONE_PARTIAL_FRACTION =
PLUS_ONE_PARTIAL_TRIGGER =
PLUS_ONE_PARTIAL_BAR_RULE =
PLUS_ONE_STOP_AFTER_PARTIAL =
PLUS_ONE_TRAIL_FORMULA =
PLUS_ONE_FINAL_EXIT =
PLUS_ONE_MANAGEMENT_VERDICT = FULLY_MECHANICAL / PARTIAL / DISCRETIONARY
```

No convertir `2–6 bars` en una elección arbitraria de barra 2, 4 o 6.

---

# 7. BLOCKER C — CLASSIC RE-ENTRY STATE MACHINE

Este blocker debe resolverse como máquina de estados, no como prosa ambigua.

Responder cada pregunta:

1. ¿Cuántos re-entry attempts como máximo?
2. ¿Uno por día o múltiples?
3. ¿Qué ocurre si stop-out sucede el mismo Trade Day 1?
4. ¿La orden se rearma inmediatamente?
5. ¿Permanece activa hasta el final de Day 1?
6. ¿Se rearma en Day 2?
7. ¿Qué condición rearma la entrada?
8. ¿Hace falta un nuevo sweep?
9. ¿Basta volver al original entry price?
10. ¿El entry price se mantiene fijo?
11. ¿El protective stop se mantiene o recalcula?
12. Si se forma un nuevo extremo, ¿cómo cambia el stop?
13. ¿Qué ocurre después de un segundo stop-out?
14. ¿Existe Day-3 re-entry?
15. ¿Cuál es la expiración final exacta?

Entregar:

```text
STATE 0 = SETUP_DETECTED
STATE 1 = INITIAL_ORDER_ARMED
STATE 2 = INITIAL_FILLED
STATE 3 = STOPPED_DAY_1
STATE 4 = REENTRY_ARMED_DAY_1
STATE 5 = REENTRY_FILLED_DAY_1
STATE 6 = DAY_2_REENTRY_ARMED
...
```

Cada transición debe tener:

- trigger;
- price;
- expiry;
- stop;
- source locator.

Si una transición no está sustentada:

`TRANSITION_UNRESOLVED`

---

# 8. BLOCKER D — INTRADAY AGE SEMANTICS

Este es prioritario.

Classic daily:

`previous extreme >= 4 trading sessions earlier`

Plus One daily:

`previous extreme >= 3 trading sessions earlier`

El libro también presenta ejemplos intradía.

Debes determinar si en intradía el autor usa:

- 4/3 bars;
- 4/3 sessions;
- otro número;
- ninguna restricción de edad;
- una regla contextual distinta.

Obligación adicional: inspeccionar cada ejemplo intradía disponible y reconstruir manualmente el índice del anterior 20-bar extreme respecto al breakout bar.

Para cada ejemplo:

```text
EXAMPLE_ID:
INSTRUMENT:
TIMEFRAME:
BREAKOUT_BAR:
PREVIOUS_20_EXTREME_BAR:
BAR_DISTANCE:
SESSION_DISTANCE:
RULE_COMPATIBLE_WITH_4_3_BARS:
RULE_COMPATIBLE_WITH_4_3_SESSIONS:
NOTES:
```

Salida final:

```text
CLASSIC_INTRADAY_AGE = BARS / TRADING_SESSIONS / OTHER / UNRESOLVED
CLASSIC_INTRADAY_AGE_VALUE =
PLUS_ONE_INTRADAY_AGE = BARS / TRADING_SESSIONS / OTHER / UNRESOLVED
PLUS_ONE_INTRADAY_AGE_VALUE =
```

No inferir por analogía.

---

# 9. BLOCKER E — ENTRY PROFILE EXACTO

Separar y verificar:

```text
CLASSIC_DAILY_FUTURES
CLASSIC_INTRADAY
CLASSIC_EQUITY_LEGACY
PLUS_ONE_DAILY_FUTURES
PLUS_ONE_INTRADAY
PLUS_ONE_EQUITY_LEGACY
```

Para cada perfil:

- offset exacto;
- tick/point units;
- si existe rango 5–10 o valor fijo;
- quién elige dentro del rango si hay rango;
- si el offset depende de volatilidad;
- si depende del instrumento;
- si el stop-entry usa exactamente el old 20-period level o un offset.

Investigar decimalización de equities y cualquier aclaración posterior del autor sobre el histórico `1/8 point`.

---

# 10. BLOCKER F — DAY SESSION / NIGHT DATA

Determina si las referencias de 20 períodos para futures usan:

- RTH/day-session only;
- full session;
- overnight included;
- regla por instrumento;
- regla por timeframe.

No asumir que lenguaje encontrado en otro capítulo aplica globalmente.

Debes clasificar cada evidencia como:

`GLOBAL_BOOK_RULE`

`TURTLE_SOUP_SPECIFIC`

`OTHER_STRATEGY_ONLY`

Salida:

```text
TURTLE_SOUP_NIGHT_DATA = EXCLUDE_CONFIRMED / INCLUDE_CONFIRMED / SOURCE_CONFLICT / UNRESOLVED
REFERENCE_SESSION_DEFINITION =
```

---

# 11. BLOCKER G — GAP EXECUTION

Separar:

## Entry gap

¿Qué ocurre si el mercado abre más allá del stop-entry?

## Protective-stop gap

¿Qué ocurre si abre más allá del protective stop?

Buscar tratamiento autoral en:

- ejemplos Turtle Soup;
- ejemplos Plus One;
- money management chapter;
- notas generales del libro;
- código oficial.

Salida:

```text
ENTRY_GAP_FILL = AT_OPEN / AT_STOP / SLIPPAGE_MODEL / DISCRETIONARY / UNRESOLVED
PROTECTIVE_STOP_GAP_FILL = AT_OPEN / AT_STOP / SLIPPAGE_MODEL / DISCRETIONARY / UNRESOLVED
```

No usar convenciones de backtester moderno como si fueran fuente.

---

# 12. BLOCKER H — AUTHOR MECHANICAL RESEARCH EXIT

Buscar si Connors/Raschke utilizaron una salida mecánica exclusivamente para investigación estadística de Turtle Soup aunque la operativa real fuera discrecional.

Buscar:

- fixed N-bar hold;
- close after N bars;
- N-period high/low;
- fixed R;
- fixed tick target;
- volatility target;
- previous-bar trail;
- stop-and-reverse;
- end-of-day;
- end-of-next-day;
- event-based exit.

Autoridad requerida: Tier A/B.

No usar WH SelfInvest, Oxfordstrat, MQL5, TradingView o blogs para cerrar este punto.

Salida:

```text
AUTHOR_MECHANICAL_RESEARCH_EXIT_EXISTS = YES / NO
RULE =
SOURCE =
```

Si después de búsqueda exhaustiva no aparece:

`NO_AUTHOR_MECHANICAL_RESEARCH_EXIT_FOUND`

---

# 13. BLOCKER I — MONEY MANAGEMENT CHAPTER APPLICABILITY

Street Smarts remite a money management general.

Debes separar las reglas del capítulo en:

### MECHANICAL

Reglas con trigger y acción deterministas.

### CONTEXTUAL

Reglas parcialmente especificadas.

### DISCRETIONARY

Reglas dependientes del juicio del trader.

Para cada regla:

```text
RULE_ID:
TEXT:
APPLIES_TO_TURTLE_SOUP = YES / NO / UNCLEAR
CLASS = MECHANICAL / CONTEXTUAL / DISCRETIONARY
FORMALIZATION =
```

No transformar lenguaje cualitativo en +1R, 50%, BE, ATR o swing rules sin fuente.

---

# 14. BÚSQUEDA ADVERSARIAL OBLIGATORIA

Por cada blocker debes intentar falsificar tu propia conclusión.

Ejemplo:

Si encuentras `previous bar low` como trailing:

- busca otra edición;
- busca contexto completo;
- verifica si pertenece a Turtle Soup o a otra estrategia;
- busca aclaración posterior;
- verifica si es ejemplo descriptivo o regla general.

Debes incluir una tabla:

| Blocker | Hipótesis inicial | Evidencia a favor | Evidencia en contra | Veredicto |
|---|---|---|---|---|

Una conclusión sin contra-búsqueda explícita no es aceptable.

---

# 15. SEARCH EXHAUSTION LOG

No puedes escribir `not found` sin entregar el log de búsqueda.

Para cada blocker no resuelto:

```text
SEARCHED_SOURCE:
QUERY_OR_NAVIGATION:
DATE:
RESULT:
ACCESS_LIMITATION:
WHY_NOT_SUFFICIENT:
```

Mínimo de familias de fuente que debes intentar cuando estén disponibles:

1. Street Smarts primary text / preview / scan.
2. LBRGroup or Raschke direct material.
3. Connors direct material.
4. Interviews/transcripts with exact author speech.
5. Archived versions of removed author pages.
6. Official code/indicator/EasyLanguage if any.
7. Secondary references only to discover missing direct sources.

---

# 16. CONTRADICTION AUDIT VS ROUND 1

Debes auditar explícitamente el Round 1 y marcar cada claim relevante como:

`CONFIRMED`

`CORRECTED`

`REJECTED`

`STILL_UNRESOLVED`

Como mínimo revisar:

- Classic Day-2 entry;
- generic age 3-or-4;
- Daily-only claim;
- Plus One entry at Day-1 low/high;
- fixed 5-period target;
- stop rules;
- expiry;
- intraday authority.

No repetir un claim del Round 1 únicamente porque ya estaba escrito allí.

---

# 17. CAUSALITY / NO-LOOKAHEAD CONTRACT

Toda formalización debe responder:

> ¿Qué información conocía el trader exactamente en el instante de decisión?

Prohibido presentar como ejecutable cualquier regla que requiera conocer el futuro.

No usar en pseudocódigo:

```python
shift(-1)
shift(-2)
```

para generar una decisión en tiempo `t`.

Si el OHLC de una sola barra contiene simultáneamente:

- nuevo extremo;
- entry trigger;
- protective stop;

y no existe dato inferior para ordenar eventos:

`INTRABAR_PATH_AMBIGUOUS`

No asumir favorable-first ni stop-first.

---

# 18. CLAIM-LEVEL EVIDENCE MATRIX OBLIGATORIA

Entregar una matriz con estas columnas exactas:

| Claim ID | Blocker | Claim | Tier | Source | Exact locator | Evidence | Contra-evidence | Confidence | Deterministic rule | Residual ambiguity | Automatable |
|---|---|---|---|---|---|---|---|---|---|---|---|

Todo claim que afecte P&L debe aparecer aquí.

---

# 19. EXACT EXECUTABLE CONTRACT

Después de la investigación, si una regla queda cerrada, entregar formalización exacta.

Ejemplo de formato:

```text
RULE_ID:
VARIANT: CLASSIC / PLUS_ONE
SIDE: LONG / SHORT / BOTH
TIMEFRAME_SCOPE:
KNOWN_AT_TIME:
PRECONDITIONS:
TRIGGER:
ENTRY_PRICE:
STOP_PRICE:
PARTIAL_EXIT:
TRAIL_UPDATE:
FINAL_EXIT:
EXPIRY:
REENTRY:
EQUALITY_SEMANTICS:
GAP_SEMANTICS:
SOURCE_IDS:
CONFIDENCE:
```

No incluir una regla si no puede llenarse honestamente.

---

# 20. MACHINE-READABLE VERDICT

Al final debes entregar además este bloque JSON COMPLETO:

```json
{
  "classic_management": {
    "status": "CLOSED|PARTIAL|UNRESOLVED",
    "trailing_rule": null,
    "final_exit_rule": null,
    "source_ids": []
  },
  "plus_one_management": {
    "status": "CLOSED|PARTIAL|UNRESOLVED",
    "partial_fraction": null,
    "partial_trigger": null,
    "trail_rule": null,
    "final_exit_rule": null,
    "source_ids": []
  },
  "classic_reentry": {
    "status": "CLOSED|PARTIAL|UNRESOLVED",
    "max_attempts": null,
    "states": [],
    "source_ids": []
  },
  "intraday_age": {
    "classic_unit": "BARS|TRADING_SESSIONS|OTHER|UNRESOLVED",
    "classic_value": null,
    "plus_one_unit": "BARS|TRADING_SESSIONS|OTHER|UNRESOLVED",
    "plus_one_value": null,
    "source_ids": []
  },
  "session_data": {
    "night_data": "EXCLUDE_CONFIRMED|INCLUDE_CONFIRMED|SOURCE_CONFLICT|UNRESOLVED",
    "definition": null,
    "source_ids": []
  },
  "gap_execution": {
    "entry_gap": "AT_OPEN|AT_STOP|SLIPPAGE_MODEL|DISCRETIONARY|UNRESOLVED",
    "stop_gap": "AT_OPEN|AT_STOP|SLIPPAGE_MODEL|DISCRETIONARY|UNRESOLVED",
    "source_ids": []
  },
  "author_mechanical_research_exit": {
    "exists": "YES|NO|UNRESOLVED",
    "rule": null,
    "source_ids": []
  },
  "qore_next_path": "SOURCE_BOUND_REPLAY|PREDECLARED_EXPERIMENTAL_MANAGEMENT_GRID|BLOCKED"
}
```

No dejar valores inconsistentes entre JSON y narrativa.

---

# 21. DEFINITION OF DONE

No consideres el trabajo terminado hasta que hayas entregado:

1. inventario de fuentes;
2. source packets;
3. search exhaustion log;
4. contradiction audit;
5. blocker verdict matrix;
6. claim-level evidence matrix;
7. Classic trailing verdict;
8. Plus One management verdict;
9. Classic re-entry state machine;
10. intraday age verdict;
11. entry profile verdicts;
12. day/night data verdict;
13. gap execution verdict;
14. author mechanical research exit verdict;
15. money-management applicability classification;
16. exact executable contract para toda regla cerrada;
17. machine-readable JSON final;
18. lista final de blockers residuales.

---

# 22. PROHIBICIONES ABSOLUTAS

- No reutilizar VT-09.
- No asignar VT-XX.
- No mezclar Classic y Plus One.
- No cambiar Classic=4 ni Plus One=3 salvo prueba Tier A/B superior con localizador exacto.
- No volver a introducir Classic Day-2 salvo evidencia primaria inequívoca.
- No volver a declarar Daily-only.
- No usar 5-period target como canónico sin evidencia autoral directa.
- No usar 2R.
- No introducir FVG/OB/EMA/ICT/SMC.
- No usar WH SelfInvest como autoridad de Raschke.
- No optimizar parámetros.
- No recomendar mercados por rentabilidad.
- No declarar DEMO_ELIGIBLE.
- No declarar trader aprobado.
- No declarar LIVE.
- No rellenar huecos de fuente con criterio propio.
- No usar community consensus para cerrar reglas.

---

# 23. VEREDICTO FINAL OBLIGATORIO

Tu respuesta debe terminar exactamente con estas secciones:

## A. CLASSIC MANAGEMENT VERDICT

`FULLY_MECHANICAL / PARTIAL / DISCRETIONARY / UNRESOLVED`

## B. PLUS ONE MANAGEMENT VERDICT

`FULLY_MECHANICAL / PARTIAL / DISCRETIONARY / UNRESOLVED`

## C. CLASSIC RE-ENTRY VERDICT

`CLOSED / PARTIAL / UNRESOLVED`

## D. INTRADAY AGE VERDICT

Classic:

Plus One:

## E. SESSION DATA VERDICT

## F. GAP EXECUTION VERDICT

## G. AUTHOR MECHANICAL RESEARCH EXIT VERDICT

## H. REMAINING BLOCKERS

Solo blockers reales que sobreviven a la búsqueda.

## I. QORE ENGINEERING PATH

Solo uno:

`SOURCE_BOUND_REPLAY`

`PREDECLARED_EXPERIMENTAL_MANAGEMENT_GRID`

`BLOCKED`

## J. SELF-AUDIT

Confirmar explícitamente:

- no rules invented;
- no secondary-only rule promoted to canonical;
- no lookahead;
- all material claims have locators;
- unresolved claims include search exhaustion evidence;
- JSON and narrative are consistent.

---

# 24. PRINCIPIO RECTOR

No buscamos que DeepSeek "complete" Turtle Soup.

Buscamos saber exactamente qué enseñaron Connors/Raschke, qué parte es mecánica, qué parte es discrecional y dónde termina la autoridad de fuente.

Si una regla no existe en fuente, la respuesta correcta es demostrar rigurosamente que no existe evidencia suficiente.

QORE Engineering decidirá después si construye un management experimental separado.

**FIN DEL HANDOFF HARDENED ROUND 2**