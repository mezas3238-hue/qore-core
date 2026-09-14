# QORE CORE — HANDOFF MAESTRO DE INVESTIGACIÓN

## VT-09 R2 — TURTLE SOUP
### PRIMARY-SOURCE ADJUDICATION, VARIANT SEPARATION & EXECUTABLE RULE EXTRACTION

**Checkpoint:** 14 de septiembre de 2026  
**Repositorio de verdad:** `mezas3238-hue/qore-core`  
**Issue:** `#551`  
**Branch de ingeniería:** `agent/vt09-r2-turtle-soup-research-001`  
**Baseline padre:** PR `#500` HEAD `9295d01f32ecd8335f226df9f5937f97c226fbc4`  
**Trader:** `VT-09` / `vt-09`  
**Investigación:** DeepSeek, por designación expresa del Human Owner

---

# 0. ORDEN MAESTRA

ESTE TRABAJO ES DE INVESTIGACIÓN FORENSE DE FUENTE.

No entregar solamente:

- una explicación general de Turtle Soup;
- un resumen de blogs;
- reglas mezcladas de varias implementaciones;
- una estrategia “mejorada” por criterio propio;
- una receta rentable sin provenance;
- parámetros optimizados sin autoridad de fuente;
- una lista de enlaces sin matriz claim-level;
- una conclusión de “alta probabilidad” sin evidencia;
- recomendaciones vagas.

Debes producir una reconstrucción que permita a Ingeniería QORE decidir, para cada regla:

`FUENTE -> OBSERVACIÓN -> CLAIM -> VARIANTE -> REGLA -> FORMALIZACIÓN -> CONFIANZA -> AUTOMATIZABLE / NO AUTOMATIZABLE`

La prioridad es **fidelidad causal y separación de variantes**, no maximizar cantidad de reglas.

---

# 1. CONTEXTO QORE QUE NO DEBES MODIFICAR

QORE ya tiene un `VT-09 Turtle Soup` v1, pero es solo un baseline histórico simplificado:

- M15;
- sesión continua;
- swing pivot `strength=2`;
- última vela hace false break del pivot y cierra de vuelta;
- entry = close de la vela false-break;
- invalidation = precio del pivot;
- TP = 2R fijo.

Ese baseline **NO** es autoridad de metodología. Tu investigación debe falsificarlo contra fuentes.

No asumas que `M15`, `swing_strength=2` ni `2R` pertenecen a Raschke. Si no aparecen en fuente primaria, deben clasificarse como defaults/implementación histórica de QORE, no como regla canonical.

---

# 2. INFORME ENTREGADO POR EL HUMAN OWNER

El Human Owner suministró un informe que atribuye a Turtle Soup, entre otras, las siguientes ideas:

1. Origen Linda Bradford Raschke / `Street Smarts`.
2. Reversión de falsos rompimientos de máximos/mínimos recientes.
3. Referencia a máximo/mínimo de 20 períodos.
4. El máximo/mínimo de referencia habría ocurrido al menos 4 días atrás.
5. Breakout de un día que revierte/cierra dentro del rango.
6. Entrada clásica en dirección de la reversión.
7. Variante “confirmación 1 vela”.
8. Variante NY M5: rango 06:00–08:59 NY; trading 09:00–12:00 NY.
9. Stop más allá del sweep extreme.
10. Variante WH SelfInvest con 3× ATR(20) emergency stop.
11. Targets: rango opuesto, 1R–2R, 5-period high/low, y variante CRT midpoint/opposite range.
12. TBS `Turtle Body Soup` vs TWS `Turtle Wick Soup`.
13. Killzones NY/London, NY AM y NY PM.
14. FVG, Order Blocks, EMA, volumen como confluencias.
15. 1–2% risk, break-even a 1R/1.5R y una operación por día.

**Hipótesis de trabajo a falsificar:** este informe probablemente mezcla la estrategia clásica, Turtle Soup Plus One y varias implementaciones posteriores/no equivalentes.

Debes determinar exactamente qué pertenece a qué fuente y qué NO puede atribuirse a Raschke.

---

# 3. JERARQUÍA DE FUENTES OBLIGATORIA

## TIER A — AUTORIDAD PRIMARIA

Prioridad máxima:

- Linda Bradford Raschke + Laurence A. Connors, `Street Smarts: High Probability Short-Term Trading Strategies`;
- material original de `Turtle Soup`;
- material original de `Turtle Soup Plus One`;
- ediciones/reproducciones autorizadas que preserven el texto original.

Para cada claim Tier A, registrar página/capítulo/figura/sección o localizador verificable.

## TIER B — ACLARACIONES DEL AUTOR

- artículos, entrevistas, publicaciones, seminarios o material educativo atribuible directamente a Raschke que aclare Turtle Soup.

No usar Tier B para sobrescribir Tier A sin explicar la evolución temporal.

## TIER C — IMPLEMENTACIONES DERIVADAS IDENTIFICADAS

Investigar por separado, con provenance explícita:

- NY M5 Sweep 06:00–08:59 / 09:00–12:00 NY;
- WH SelfInvest;
- “CRT Turtle Soup” H4/H1/M15;
- otras implementaciones nombradas en el informe.

Tier C puede generar **variantes QORE experimentales** pero no puede llamarse “Raschke canonical” sin evidencia.

## TIER D — COMUNIDAD / SECUNDARIO

Blogs, redes, PDFs no autorales, videos comunitarios, etc.

Sirven para localizar fuentes o documentar una variante comunitaria. Nunca deben sobrescribir Tier A/B.

---

# 4. PREGUNTAS DE ADJUDICACIÓN — RESPUESTA OBLIGATORIA

## 4.1 Reference high / low

Determina exactamente:

- ¿es un máximo/mínimo de 20 días, 20 barras o “20-period” genérico?
- ¿se excluye la barra actual del lookback?
- ¿qué pasa con empates de máximos/mínimos?
- ¿se usa el extremo más reciente o existe una regla distinta?
- ¿el nivel de referencia debe ser anterior por un mínimo de barras/días?

## 4.2 Regla de antigüedad

El informe dice “al menos 4 días atrás”. Determina:

- redacción original;
- si son 4 trading days o 4 bars;
- si el día/bara del extremo cuenta o no;
- desigualdad exacta permitida;
- si aplica igual a LONG y SHORT.

## 4.3 Setup clásico LONG

Extrae la secuencia exacta:

- condición sobre low actual vs reference low;
- condición de recuperación/re-entry;
- tipo de entrada: market, stop, limit o close;
- nivel exacto de entrada;
- si debe ocurrir el mismo día/bar;
- cancelación/expiry de la señal.

Dar formalización OHLC/event-driven sin lookahead.

## 4.4 Setup clásico SHORT

Mismo nivel de detalle y simetría que LONG.

## 4.5 Turtle Soup Plus One

Separar formalmente de Turtle Soup clásico.

Determinar:

- qué significa “Plus One” en la fuente;
- cuál es la barra día 1 y cuál es la barra día 2;
- condición de activación;
- tipo y nivel de orden;
- invalidación;
- expiración;
- si Plus One reemplaza o complementa al setup clásico.

## 4.6 Stop loss

Adjudicar por variante:

- reference level;
- sweep extreme;
- setup-day extreme;
- ATR stop;
- stop monetario/volatility stop;
- cualquier buffer/tick.

No mezclar un stop de Tier C con una entrada Tier A salvo que se declare como experimento híbrido separado.

## 4.7 Exit / take profit

Recuperar la gestión original completa:

- profit target si existe;
- time exit si existe;
- trailing/stop adjustment;
- 5-period exit si existe y contexto;
- fixed R si existe y valor;
- qué ocurre si stop y target son tocados en la misma barra para backtesting OHLC.

## 4.8 “TBS / TWS”

Verificar si los términos:

- `Turtle Body Soup`;
- `Turtle Wick Soup`

son de Raschke/Connors, de otra fuente autoral, o de comunidad.

Si no son Tier A/B, marcarlo explícitamente como **NO CANONICAL TERMINOLOGY**.

## 4.9 Candle shape / pin bars

Verificar si la metodología original exige:

- long wick;
- pin bar;
- hammer;
- shooting star;
- engulfing pattern;
- body close constraints adicionales.

No inferir price-action moderno sobre el sistema original.

## 4.10 Sesión y hora

Determinar si Turtle Soup clásico prescribe sesión/horario.

Separar de:

- NY 06:00–08:59 range;
- 09:00–12:00 NY active window;
- 09:30–11:00 NY;
- NY PM;
- London/NY overlap;
- Asia range.

Para cualquier ventana intradía, registrar zona horaria y DST.

## 4.11 NY M5 Sweep

Encontrar la fuente exacta de esta variante y responder:

- autor;
- fecha;
- instrumentos demostrados;
- rango exacto;
- ventana exacta;
- definición exacta del sweep;
- confirmación exacta M5;
- entry;
- stop;
- target;
- daily trade cap;
- invalidación/expiry.

## 4.12 WH SelfInvest

Verificar:

- si existe Turtle Soup implementado por WH SelfInvest;
- reglas completas;
- qué significa exactamente 3×ATR(20) emergency stop;
- exit principal;
- horario 06:00–22:00 y timezone;
- cualquier diferencia respecto a Raschke.

## 4.13 CRT Turtle Soup

Identificar autor/fuente y formalizar por separado:

- H4/H1/M15 roles;
- range candle;
- sweep;
- entry;
- SL;
- TP1 midpoint;
- TP2 opposite extreme;
- session/timing;
- mercados.

## 4.14 FVG / OB / EMA / volume

Para cada filtro:

- ¿aparece en Tier A/B?
- si no, ¿de qué variante procede?
- ¿es requisito o confluencia opcional?
- ¿existe umbral cuantificable?

## 4.15 Risk management

Separar metodología de signal generation de account risk.

QORE no permitirá que VT-09 decida riesgo de cuenta en porcentaje. Aun así, documenta si la fuente menciona 1–2%, BE a 1R/1.5R, una operación diaria, etc., y clasifica su autoridad.

## 4.16 Mercados y transferibilidad

Registrar instrumentos/asset classes usados o demostrados en cada fuente.

Separar:

- **source-demonstrated market**;
- **source-authorized generalization**;
- **QORE transfer-research market**.

No afirmar universalidad sin fuente.

---

# 5. MATRIZ CLAIM-LEVEL OBLIGATORIA

Entregar una tabla con estas columnas exactas:

| Claim ID | Concepto | Claim | Variante | Tier | Fuente | Localizador | Evidencia | Confianza | Regla determinista | Ambigüedad residual | Automatizable | Notas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

Usar al menos estos conceptos:

- identity/origin;
- lookback;
- reference extreme;
- age constraint;
- sweep;
- re-entry / close-back-inside;
- classic entry;
- Plus One entry;
- long/short symmetry;
- stop;
- target;
- time exit;
- 5-period exit;
- cancellation/expiry;
- session;
- timeframe;
- market scope;
- TBS/TWS;
- candle shape;
- ATR;
- NY M5 range;
- FVG;
- OB;
- EMA;
- volume;
- BE;
- trade-frequency cap.

---

# 6. FORMALIZACIÓN EJECUTABLE OBLIGATORIA

Para cada regla Tier A/B suficientemente clara, devolver pseudocódigo o desigualdades exactas.

Ejemplo de formato — NO asumir que esta es la regla correcta:

```python
reference_low = min(low[t-N:t])
reference_index = ...
age_ok = ...
swept = low[t] < reference_low
recovered = close[t] > reference_low
setup = age_ok and swept and recovered
```

Debe especificarse:

- inclusividad/exclusividad de cada comparación;
- tratamiento de igualdad;
- orden temporal;
- dato conocido en cada instante;
- entry timestamp;
- expiry timestamp;
- stop price;
- target/exit rule;
- timezone si aplica.

Si la fuente no permite fijarlo, escribir `UNRESOLVED` y explicar qué dato falta.

---

# 7. TAXONOMÍA DE AMBIGÜEDAD

Usar estos reason codes cuando corresponda:

- `SOURCE_TEXT_UNAVAILABLE`
- `SOURCE_CONFLICT`
- `VARIANT_CONFLATION`
- `ENTRY_LEVEL_UNRESOLVED`
- `STOP_RULE_UNRESOLVED`
- `TARGET_RULE_UNRESOLVED`
- `TIMEFRAME_UNRESOLVED`
- `SESSION_UNRESOLVED`
- `REFERENCE_AGE_UNRESOLVED`
- `EQUALITY_SEMANTICS_UNRESOLVED`
- `EXPIRY_UNRESOLVED`
- `MANAGEMENT_UNRESOLVED`
- `MARKET_SCOPE_UNRESOLVED`
- `LATER_IMPLEMENTATION_ONLY`
- `COMMUNITY_ONLY`
- `SAFE_TO_AUTOMATE`

---

# 8. RESULTADO FINAL REQUERIDO

Tu entrega debe terminar con cinco bloques:

## A. Canonical Raschke Turtle Soup

Solo reglas justificadas por Tier A/B.

## B. Canonical Turtle Soup Plus One

Separada de A.

## C. Derived variants

NY M5, WH SelfInvest, CRT u otras; cada una separada.

## D. Claims rejected / downgraded

Todo claim del informe del Human Owner que no pueda sostenerse como se presentó.

## E. QORE engineering recommendation

No optimización. Debe indicar qué variante(s) están suficientemente especificadas para que Ingeniería construya candidatos R2 separados, y exactamente qué sigue bloqueado.

---

# 9. PROHIBICIONES

- No inventar reglas.
- No usar “smart money/liquidity institutions” como mecanismo causal si la fuente original no lo enseña.
- No convertir una confluencia comunitaria en requisito canonical.
- No declarar TBS/TWS original sin evidencia.
- No usar un 2R universal por comodidad.
- No asumir M15 porque QORE v1 lo usa.
- No asumir M5 porque una variante moderna lo usa.
- No mezclar stop de una variante con target de otra sin etiquetarlo como híbrido experimental.
- No entregar una tasa de acierto promocional como validación.
- No recomendar DEMO/LIVE; tu autoridad es investigación de fuente, no promoción.

---

# 10. ENTREGA PARA INGENIERÍA

La respuesta debe ser autosuficiente y lista para copy/paste a QORE.

Al final incluir:

- lista de fuentes primarias verificadas;
- claims que quedaron `UNRESOLVED`;
- reglas que pueden codificarse sin juicio humano;
- reglas que requieren Human Owner adjudication;
- fingerprints o hashes de archivos fuente si recibiste PDFs/videos/archivos locales;
- fecha exacta de acceso a material web cambiante.

**No cierres ambigüedades por criterio propio.** Si dos fuentes autorizadas discrepan, conserva ambas como versiones y explícalo.
