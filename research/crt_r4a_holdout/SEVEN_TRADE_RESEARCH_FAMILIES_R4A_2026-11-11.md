# QORE CRT R4-A — siete familias de trading de investigación

Corte: 2026-11-11. QA solamente. NO LIVE, NO VPS, NO MERGE.

**Orden Owner:** el Trader debe investigar y, cuando se certifique, estar preparado para simular cada una de siete estrategias CRT independientes. Ningún detector QA autoriza broker.

## El catálogo de siete CATEGORÍAS no equivale a siete entradas

R4-A original: Git blob 693e3f49719e86e2ea0702f7b355af33bd0c4c7c.
En Pine L2268–2288, qaCatalogMask tiene siete roles (1,2,4,8,16,32,64):

| Bit | Categoría literal Pine | Estado |
|---:|---|---|
| 1 | TRUE 3C | Estructura QA; MSS M5 propio obligatorio |
| 2 | 2C Pending | **Provisional: NO ENTRY** |
| 4 | CRT 2C Expansion | **Rechazada: NO ENTRY** |
| 8 | Inside Return | Solo geometría QA y MSS propio |
| 16 | Inside Continuation | **Rechazada: NO ENTRY** |
| 32 | Multi-Candle | Contiene Multi4 y Multi-N independientes |
| 64 | Retest MSS M15 | Solo si es propio del mismo CRT y pivote M15 |

El **2C RETURN ratificado** es otra lógica base identificada por entryFamily Pine L2113–2120; no tiene bit en ese catálogo de siete. No transformar provisional/rejected en operable.

## Siete modelos legítimos como hipótesis de estrategia

Para cumplir los siete caminos de investigación sin usar las tres categorías no operables del catálogo, el Trader Lab separa 2C por momento del MSS, y separa Multi4 de Multi-N:

| # | Modelo de estrategia | Identidad y disparador | Estado actual |
|---:|---|---|---|
| 1 | 2C RETURN + MSS M15 en C2 | H4 de C2 ratificada, MSS15 propio dentro C2, nunca entrar antes de C2 cerrar | Detector integrado QA |
| 2 | 2C RETURN + MSS M15 en C3 | C2 ratificada, MSS15 propio dentro C3, nunca entrar antes del MSS cerrar | Detector integrado QA |
| 3 | TRUE 3C + MSS M5 | C2 interior, C3 barrida C1 unilateral y regreso a C1, MSS5 propio, C3 H4 ratificada | Detector integrado QA |
| 4 | Inside Return | C2 estrictamente interior C1; H4 posterior barre solo un extremo C2 y cierra dentro de C2; MSS propio | Geometría implementada; FSM MSS pendiente |
| 5 | Multi4 | C1/C2a/C2b/C3 completos; barrida en C2a, retorno distribuido; MSS M5/M15 del propio candidato | Geometría implementada; FSM MSS pendiente |
| 6 | Multi-N | C1 + 2 a 5 H4 estrictamente interiores + terminal barra C1 y cierra dentro; MSS propio | Geometría implementada; FSM MSS pendiente |
| 7 | Retest M15 del CRT | M15 posterior al MSS15 propio toca su mismo pivote y cierra recuperándolo, máximo 4h; CRT original ratificado | Geometría implementada; FSM/ciclo MSS pendiente |

**No se debe confundir siete hipótesis propuestas con las siete categorías diagnósticas originales.** Se conserva el catálogo íntegro y también los diagnósticos no operables.

## Entradas/SL/TP en fase de diseño científico

El indicador es solo DETECTOR y no define estrategia de broker, entradas, SL ni TP. Las siguientes son plantillas **propuestas, no certificadas**:

- Familias 1–3: límites de prueba en el 50% del cuerpo de H4 C2/C3, SL detrás de la barrida unilateral propia más colchón ATR, TP en extremo opuesto de C1. Todo debe ser calculado DESPUÉS de que cierre su confirmación MSS y H4 ratificadora.
- Familias 4–6: la H4 terminal y C1 son propios del patrón, sin pedir prestados niveles ni MSS de otro ciclo. Primer test propuesto 50% cuerpo terminal, SL detrás de su extremo manipulado, TP contra el otro extremo C1.
- Familia 7: primer test propuesto al cierre de la M15 de retest, SL detrás del extremo de ESA M15 y TP de C1 propio. No entrar antes de que C2 H4 esté ratificada.
- Por cada modelo: identidad única, evento de barrida, pivote confirmado anterior, MSS propio con cierre real, timestamp de disponibilidad, bid/ask, spread, swap, comisión, slippage, expiración, riesgo agregado y resolución conservadora cuando TP y SL se tocan dentro de una M5.
- Para que una familia pueda simular como CERTIFICADA, sus parámetros y su lógica deben quedar congelados ANTES de una nueva ventana de 24 meses no usada. Nunca optimizar por PnL del 2024–2025 ya explorado.

## Código y evidencia

- seven_family_contract.py: siete FamilySpec explícitas con fuente Pine, estado, MSS propio y barreras; mapa de siete bits y 3 estados prohibidos; no contiene API de órdenes.
- secondary_family_geometry.py: geometría pura de cuatro familias pendientes, respetando 48 M5/H4 cerradas, barrida unilateral, continuidad y ciclo de retest del MSS.
- tests/test_seven_family_contract.py: 17 pruebas sintéticas.
- tests/test_secondary_family_geometry.py: 22 pruebas sintéticas.
- causal_crt_m5_engine.py: dos familias base A/B; el split de A en C2 y C3 forma 3 hipótesis con detector QA.

**Estado: los 7 modelos tienen contrato; 3 detectores causales preliminares y 4 detectores de geometría. Ninguno está certificado para trading económico. Sin broker order authority, sin merge y sin LIVE.**
