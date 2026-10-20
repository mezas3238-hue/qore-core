# QORE CORE — VT08 CRT de TRES FUENTES: CRITERIO OWNER + PROTOCOLO V1 PRE-REGISTRADO

**Fecha:** 15-OCT-2026 · **PR #626 DRAFT** · **RESEARCH-ONLY**, sin merge / capital / sizing / demo/live.  
**Directiva Owner nueva:** **CRT NO debe ser idéntico a cada detalle de RomeoTPT**. El universo autorizado de documentación es **RomeoTPT, SpeculatorFL y TraderFlameseN**. La metodología se llamará **`VT08_CRT_THREE_SOURCE_QORE_V1`** para diferenciar *síntesis de QORE* de obra de un solo autor.

## Autoridades y lo que realmente puede afirmarse

- **RomeoTPT:** [video original](https://www.youtube.com/watch?v=UUq_wKQ61Wo) y [post old CRTH](https://t.me/s/officialRomeotpt/6615). Fuente origen. No exigir una norma Romeo de elección universal entre old-highs como bloqueo insalvable.
- **SpeculatorFL:** [CRT: Candle Ranges Theory, 28-APR-2024](https://threadreaderapp.com/thread/1784493604473618604.html), especialmente secciones «Every single candle is a range», «Inside Bars within CRT», «Trade Protocols», «CSD», «LTF CRT with HTF CRT». Su texto permite estudiar un side-sweep seguido de dirección al 50 %/opuesto y una confirmación inferior.
- **TraderFlameseN:** [Choose the best CRT candle, 13-MAY-2024](https://threadreaderapp.com/thread/1790141530461622525.html), rangos por vela, H4 padre/micro CRT, CSD confirmación y destino 50 %/opuesto. **El contenido es sustancialmente paralelo al texto SpeculatorFL y da crédito a Romeo; NO presentarlos como dos validaciones independientes de una ventaja económica.**

**La nueva regla de autoridad:**
1. Una regla específica puede tener como apoyo **una o más** de estas tres fuentes (sin exigir confirmación de Romeo para cada una).
2. Cualquier paso de implementación que **ninguna fuente explique con precisión** es **`QORE_ENGINEERING`**: describirlo como tal, explícitamente, y someterlo al proceso de aprobación/cognición; no atribuirlo a la fuente.
3. Una laguna o contradicción se resuelve mediante política causal **precongelada**, nunca mirando PnL/resultado posterior. Reglas inexistentes/no adjudicadas = WAIT, no PASS.
4. Los siete contratos obligatorios constan en `crt_pure_three_source_methodology.py`: referencia, selección múltiple, HTF/LTF, confirmación, invalidación/expiración, destino y conflicto/rearm.

## Propuesta de síntesis operacional v1 (investigación, no admitida para certificación)

**Decisión de diseño QORE, NO una cita literal de Romeo/Speculator/Flames.** La congelamos en esta acta **antes** de mirar su primer resumen de replay, para evitar una selección por resultados.

**Data:** dos H4 cerradas anteriores `H4_C1` y `H4_C2`, H4 C3 vigente, M15 C1 y M15 C2 cerradas (no futura C3), escala de precio relativa original por mercado, reloj UTC causal. Solo AUDUSD y USDJPY research; BTCUSD frozen.

**R1 parent range:** la H4 C1 cerrada determina `high1`, `low1`, midpoint exacto `(high1 + low1)/2`. Es una **política explícita QORE de antigüedad fija**, no supone que sean los únicos old CRTH/CRTL de los autores.

**R2 directional purge:** H4 C2 debe penetrar estrictamente **UN** lado del H4 C1 y cerrar DENTRO del rango C1: `H4_C2.low < low1 && H4_C2.high <= high1 && low1 < H4_C2.close < high1` → tesis **BULLISH**; simétrico `H4_C2.high > high1 && H4_C2.low >= low1 && low1 < H4_C2.close < high1` → **BEARISH**. Si ambos lados o ninguno son penetrados, si el close acepta fuera o si la geometría es falsa, **ABSTAIN**, nunca trade retrospectivo. Exigir `opened_C2 + 4h == opened_C3`.

**R3 micro-C2 confirmation:** M15 C1 y C2 consecutivas al comienzo del C3 H4. Como contrato QORE determinista de lower-timeframe «purge/reclaim», M15 C2 debe penetrar UN lado del M15 C1 en **MISMA dirección** que parent H4, cerrar dentro de M15 C1 y en lado favorable de su midpoint (**> midpoint M15_C1 para bullish**, **< midpoint para bearish**), sin dos-side sweep. Si está incompleto o contrario, **WAIT/ABSTAIN**, no entrada. **NO llamarlo «CSD original» sin prueba específica**: es un contrato QORE derivado de la idea de confirmación inferior.

**R4 clock:** evaluable **solo al cierre efectivo de M15 C2**, no durante M15 C2, no después de H4 C3. La caducidad de esta versión QORE es **el cierre de H4 C3**; no hay C3-open fallback. No reabrir idéntica hipótesis después de invalidez. Esta expiración es QORE engineering.

**R5 destination:** objetivo conceptual primario el **midpoint del H4 C1 original**, únicamente cuando todavía se encuentra ADELANTE del cierre M15 C2 (**BULLISH target > M15_C2.close; BEARISH target < M15_C2.close**). Si el midpoint ya se consumió, **ABSTAIN** porque DOL original no queda disponible; no mover target arbitrariamente. Distancia/thresholds/beneficio NO se optimizan ahora.

**R6 structural invalidation:** low del M15 C2 (bullish) / high (bearish) como nivel descriptivo de tesis, no stop broker, no sizing y no orden. Rechazar setup si invalidación ya cruzada al momento de decisión. Nunca calcular lotaje.

**R7 decision output:** `EXECUTE` es sólo **conceptual, source-engineering candidate**, bajo `research_only=True`, `source_authority_closed=False`, `GM1_PASS=False`, `G_M5=False`, `grants_execution_authority=False`, `grants_capital_authority=False`. Publicar **todas** las ramas WAIT/ABSTAIN, no solo positivos. Una señal positiva de esta rama no es trading ni certificación.

## Por qué esta estrategia aún NO es certificable / trabajos pendientes

- El **Owner sí aprobó el uso de tres fuentes** y la síntesis, pero **NO se ha aprobado ni revisado independientemente esta elección concreta C1→C2 y confirmación micro**; esto es **propuesta científica** del arquitecto, no contrato definitivo certificado.
- Los 48 casos de G-M2 se seleccionaron de datos ya explorados. El nuevo V1 sobre ellos será **desarrollo/diagnóstico solamente**, incluso aunque aparezca una señal; NO un holdout nuevo ni evidencia de rentabilidad.
- No existe continuidad original BID/ASK/fills + costes broker por decisión/mercado ni reglas económicas numéricas propias de CRT PURE aprobadas. PF/DD/Sharpe/Sortino permanecen **NOT_EVALUATED**. DD patrimonial únicamente bajo CIBO/Risk separado; ningún sizing en el Trader.
- Antes de medir desempeño: congelar versión exacta del candidato, ledger caso por caso y su code SHA; definir corpus OOS **realmente virgen**, potencia y política de umbrales por autoridad Owner/Risk. No aplicar ciegamente límites de otros traders #762 / #838. Pruebas fuera de muestra, bootstrap/stress, PF net y Risk/CIBO siguen obligatorias para GLOBAL.
- El contrato actualmente no incluye la totalidad de familias CRT del autor; no prometer que representa todo CRT. Si fracasa la hipótesis, dejar falsada V1 y proponer nueva versión con NUEVO holdout; no retunar sobre resultados.

**Estado de fuente:** `model1_source_ready()` Romeo-only permanece true/false según registro histórico, pero **ya no es la única condición del certificado de síntesis**. No alterar evidencia Romeo antigua, crear autoridad QORE separada con contratos nuevos verificables; mientras siete contratos fuente-ingeniería no estén adjudicados, G-M5/Global fallan cerrados.

**Prohibiciones permanentes:** no sizing propio del Trader ni simulado; CIBO único responsable volumen, capital y DD de cuenta. NO MERGE; NO LIVE/DEMO/PRODUCTION/VPS/MT5. Ningún resultado geométrico equivale a Profit Factor.


## Anexo de pre-registro ANTES de censo de cobertura H4 original completo

**La cohorte de 48 G-M2 es estratificada por C2 conocida después de la hora de decisión de V1 y NO permite estimar densidad, ni siquiera de señales.** Por eso, sin mirar su frecuencia, se decide un censo sobre **TODAS las ventanas H4 completas de reloj UTC** de los dos mercados del Atlas original, no sólo los dos triplets por día del antiguo runner R2-C. Horas H4: **00:00,04:00,08:00,12:00,16:00,20:00 UTC**; adyacencia H4 C1/C2 y primeras 2 M15 dentro de H4 C3, todas las barras con datos M5 exactos y continuos. Esta elección UTC es **ingeniería QORE de versión V1**, no se atribuye a hora 159/369 del autor; la compatibilidad con broker/NY DST y calidad de sesiones todavía debe estudiarse. Incluir todos los casos **NO H4 SWEEP**, **dos lados**, **target consumido**, **M15 falta**, **conflicto**, **candidato conceptual**, con año UTC, conteo y denominadores explícitos. NO mostrar ganancias ni trades ni PF.
**Fuente de datos:** exactos M5 Atlas original de [run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), íntegros y SHA antes del cálculo; BTCUSD congelado. Cualquier resultado de este censo será **DESARROLLO CONSUMIDO**, jamás nuevo OOS ni certificación.
**Objetivo del censo:** detectar si el borrador V1 tiene densidad conceptual suficiente para justificar más inversión en método, sin encerrar CRT en la muestra artificial de sólo 48 casos ni dos oportunidades fijas por día. Separar conteo H4 contextos de hipotéticas señales M15, jamás llamar los primeros «trades».
