# QORE-alpha v1 — PRERREGISTRO INMUTABLE DEL ESPACIO 96 Y CRITERIOS DE PARADA

**Congelado 2026-10-11 ANTES de visualizar un nuevo PnL o de seleccionar una variante. Rama independiente:** `research/qore-alpha-96-frozen-20261011` derivada de base VT08 sólo para reutilizar infraestructura; sin equivalencia/fidelidad obligatoria al autor. QORE-alpha es **investigación PROPIA**, patrones inspirados en TTrades, y no "VT08 reconstruido". VPS/LIVE y holdout de 7 años sellados. Referencia histórica: ensayo anterior QORE M30M3 PF bruto 0,964 / limit 0,895 (viejo universo 1095d) **no es un resultado de ninguna de estas 96 variantes** y prohíbe seleccionar opciones a posteriori basándose en él.

## 1. Espacio factorial cerrado: EXACTAMENTE 96 variantes únicas

Patrón **fijo**: M30 C2 único barrido (un lado de C1) y cierre de reversión dentro C1; confirmación M3 CISD y Protected Swing de serie de velas contrarias **confirmados antes de C3.open**. No modelos alternativos ni filtros ocultos.

| Dimensión | Opciones (sin otras) | Razón EX-ANTE |
|---|---|---|
| Entrada | `POSITIONAL_C3` / `CISD_RETEST` | Dos maneras de entrar a un mismo patrón confirmado (market posicional / limit predeclarada) |
| Sesión | `ASIA` / `LONDON` / `NEW_YORK` | Diferentes regímenes conocidos de liquidez; se fijan ventanas reloj NY abajo |
| Stop | `PS` / `EQ_M30` / `BREAKER` / `ATR_X1` | Cuatro nociones predefinidas de invalidación: extrema estructura, punto medio, breaker proxy y volatilidad |
| Target | `R1` / `R2` / `R3` / `EXTERNAL_LIQUIDITY` | Tres rewards de R definidos ex ante y una referencia estructural previa |

**Producto cartesiano 2×3×4×4 = 96, IDs deterministas por orden anterior. Ninguna variante extra.** `BREAKERS` son formalizaciones QORE C, nunca "authentic breaker author". EQ_M30 = (HIGH+LOW)/2 de C2 ya cerrado, sin regla condicional de relevante swing autor. La historia anterior PS-only no justifica eliminar su opción predefinida; se incluye en factorial sin prioridad.

### Semántica de ejecución PREDEFINIDA (no ajustar mirando PnL)

- Zona horaria IANA `America/New_York` (DST respetado); clasificación no solapada por apertura de C3: **ASIA 19:00–00:00 NY**, **LONDON 02:00–05:00 NY**, **NEW_YORK 08:00–11:00 NY** (extremo final excluido). Horarios QORE C explícitos, no ventanas universales del autor. Las horas fuera de esas tres bandas jamás entran al ensayo; cierres exactos 00:00, 05:00 y 11:00 no extienden la banda. Día de agrupación = fecha NY de C3.open. Los datos previos VT08 (01:00–13:00) NO cubren correctamente la nueva Asia; hay que reconstruir TODO desde fuente M3, NO reciclar listado `research_observations` filtrado.
- Barrido y reversión: bullish si C2.low < C1.low, C2.high <= C1.high y `C1.low < C2.close < C1.high`; bearish simétrico. Ambigüedad doble barrido C2 que toma HIGH y LOW de C1 **se rechaza uniformemente** en 96; sin optimizar la exclusión. M3 CISD+PS reconstruido con cierre y series, **un único PS**; si múltiples o cero, rechazo universal (no elegir el ganador ex post). Entry eligibility se determina en `C3.open`, nunca por retesteo posterior, futuro RR, futura volatilidad ni target finalmente tocado.
- Máximo **una señal madre pre-entrada por par y fecha NY por variante**, elegir la más temprana en esa sesión y que los parámetros de la variante sean **válidos en ese instante** (stop objetivo de reward positivo, fuentes completas). Si una madre no tiene stop/target válido para la variante se marca abstención, no se elige una posterior en función de PnL.
- `POSITIONAL_C3`: market al open del primer M3 de C3. `CISD_RETEST`: limit predeclarada exactamente al nivel CISD confirmado antes de C3.open; favorable respecto al posicional/stop; activa máximo 10 M3 cerrados de C3 (30 minutos); no touch ⇒ NO_FILL 0R en esa madre, nunca se elige después de saber que sí tocó. Ventana de seguimiento para ambas **10 velas M3 completas desde C3.open**, stop/tp o salida a C3.close. El stop-first si M3 toca simultáneamente ambos; si entrada limit+tp/sl en primera M3 se asigna -1R conservador (OHLC carece de orden intrabar). Cada variante separada, **nunca** 96 órdenes reales.
- `PS` = PS extremo confirmado M3 pre-C3; `EQ_M30` = (C2.high+C2.low)/2; `BREAKER` = low/high de **más reciente secuencia M3 no solapada** con low→high→lower low→higher high (o inversa short) completamente confirmada antes de C3, sin futuro; requiere fuente real del M3 y selección estable por timestamp. `ATR_X1` = stop `entry -/+ Wilder ATR(14)` de **14 M30 completos al abrir C3** (verdadero TR con close previo, prior 14 M30 y close anterior). Si no se puede construir stop con estos elementos exactos, abstenerse. Stop al nivel elegido menos/mas un tick de cotización broker únicamente en PS/EQ/BREAKER; `ATR_X1` usa diferencia exacta ATR1. Tick y broker source necesarios; no suponer 0.0001 universal FX.
- `R1/R2/R3` = entry ± 1, 2, 3 veces riesgo predeclarado. `EXTERNAL_LIQUIDITY` = high anterior **intacto** de la sesión NY día trading anterior para long, low anterior intacto para short; para no usar día parcial, computar con día anterior de mercado completo basado en OHLC M3, y comprobar ningún toque posterior al origen hasta C3.open. Si no existe high/low válido anterior, abstención. No elegir PDH/PWH alternativo posthoc. Target siempre lado favorable y nunca se recalcula al cambiar resultado.
- Simulación OHLC M3 produce solo **proxy de fills**; para gate económico realista exige **BID/ASK y fees verificables en cada evento**. Costes en R deben provenir del spread/commission/slippage documentado del broker y timestamp predefinido, no parámetro elegido para PF. Si no hay esos datos, estado `BLOCKED_COST_EVIDENCE`, no afirmar aprobación.
- Riesgo para reproducir drawdown **0,1% del equity anterior a la operación** (sin apalancar simultáneas; ordenar fills por timestamps y market, riesgo total abierto <=0,1%). Esta unidad de cuenta QORE C existe sólo para definir el DD<20% exigido; Sharpe/Sortino son secundarios y no reemplazan gate. La política real también fija 0,1% inicial si se aprueba paper.

## 2. Segmentación temporal EXACTA (sin cambiar fechas)

| Etapa | Inicio incluido | Fin excluido |
|---|---|---|
| TRAIN | 2022-01-01 00:00 NY | 2024-07-01 00:00 NY |
| VALIDATE | 2024-07-01 00:00 NY | 2025-07-01 00:00 NY |
| INTERNAL_TEST | 2025-07-01 00:00 NY | 2026-07-01 00:00 NY |
| HOLDOUT_7Y_SEALED | — | NO se lee |

M3 nativo consumido previamente en QORE #35941643396 proporciona `1095d` (aprox. desde 2023), **NO acredita desde 2022-01-01**. Requisito DATA-COVERAGE: market/cotizaciones completas en todos los splits, fechas verificadas antes de PnL; si incompletas, **BLOCKED_DATA_COVERAGE**, no reinterpreta ventanas ni gana datos por interpolación. "En dos semanas" es una meta del plan del usuario, no promesa de ejecución ni prueba sin datos.

## 3. Filtros económicos y selección EXACTOS, fijados antes del ensayo

Para cada variante, en la misma población, sin omitir pares perdedores:
- TRAIN `PF gross > 1.40`, `trades >= 50`.
- VALIDATE `PF gross > 1.30`, `trades >= 25`.
- `max_dd_pct < 20` por segmento TRAIN y VALIDATE sobre equity 0,1% por operación y 0,1% de riesgo abierto global;
- `abs(win_rate_train - win_rate_validate) <= 0.15` **15 puntos porcentuales** (la frase "±15%" aquí se fija como pp para evitar cambiar según PnL).
- Si 0 pasan, **STOP**: descartar este feature set, futura nueva hipótesis requiera su propio preregistro y evidencia nueva; no optimizar filtro de la misma familia.
- Si 1–2 pasan, escoger **una única ganadora por mayor VALIDATE PF bruto**; tie determinista por menor `variant_id`.
- Si 3+ pasan, `OVERFITTING_REVIEW_REQUIRED` sin autorizar test interno hasta auditar split/duplicados/correlación; tras revisión, **la selección permanece una sola variante por VALIDATE PF**, sin re-ranking usando el test.
- **Única ganadora** al INTERNAL_TEST: si `PF gross < 1.20`, REJECT. Si `PF gross >= 1.20`, pasar a paper (inmediatamente sin usar test para retocar el modelo). Trade minimum en test interno no especificado por el usuario; se reporta N, no se inventa gate alternativo.
- Paper prospectivo **3 meses ininterrumpidos, cotizaciones nuevas no vistas en splits**; PF net >1.20 con costes broker comprobados. No reiniciar ventana ni añadir filtro si falla; fracaso ⇒ CERRAR este candidato.
- Solo tras aprobar paper, programa REAL con riesgo inicial **0,1%/trade y riesgo máximo abierto 0,1%**, crecimiento progresivo condicionado a evidencia nueva y límites QORE autorizados, NO despliegue automático a VPS.
- **Corrección múltiple:** `PF 1.40` es un **gate heurístico del protocolo**, NO valor derivado matemáticamente del Bonferroni. Para una prueba estadística Bonferroni `alpha_family=0.05`, `alpha_each=0.05/96 ≈ 0.00052083`, necesitaría p-values con hipótesis y dependencia temporal predefinidas; NO declarar control FWER a partir de PF solo, ni cambiar PF umbral solicitado. Conteos 96 correlacionados, ningún "edge verificado" a partir de solo PF bruto.

## 4. Estado de ejecución de los gates (sin hacer backtest por presión)

La validación final solo puede ejecutarse si se verifica M3 original desde 2022, feeds M15/M30 cruzados, spreads/ticks, market timezone, commits, no duplicaciones y data availability real. En ausencia de requisito, el workflow CI debe producir **BLOCKED** con evidencia concreta, no `0 PF` ni certificar rendimiento.

El antiguo ensayo VT08 FINAL #1 autor-fiel (#787) queda **SUPERSEDIDO POR DECISIÓN DEL OWNER PARA QORE-alpha**, no se relaja ni ejecuta su holdout como sustituto; conservar su archivo y PR #765 como historial/auditoría, sin fusionar a producción.

**Sin mutación silenciosa** de este espacio; si falla, no 97.ª variante ni ajuste al período. Nunca activar LIVE, VPS ni abrir holdout sin autorización posterior.
