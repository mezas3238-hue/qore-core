# VT31 · Mandato P0: CERTIFICACIÓN METODOLÓGICA Y COGNITIVA

Fecha 2026-10-14. **Se prioriza la metodología y el razonamiento COG, no la optimización cuantitativa ni nuevos retornos históricos.** Este acta se registra antes del desarrollo del testigo de certificación. No modifica ni sustituye el G3 r1.3 firmado-para-revisión, no crea una firma COG/OPS independiente y no declara rentable al trader.

## Principio rector: separar lo que es ICT, TTrades y QORE

- **ICT 2023 (metodología madre)**: fuentes [ICT Silver Bullet Time-Based Trading Model](https://www.youtube.com/watch?v=tRq1hyGGtl4), y acta de contraste existente `docs/research/VT31_2023_PRIMARY_VIDEO_DOCTRINE_DELTA_2026-10-12.md`. Tres ventanas NY 03–04, 10–11, 14–15; contexto DOL y FVG; no atribuir 9am H1 obligatorio a Londres/NY PM, ni afirmar que CE, C2 SL o MSS 1,25x mediana5 son reglas universales del autor.
- **TTrades AM 2025 (variante particular de fuente autoral)**: [The AM Silver Bullet Strategy on NQ](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/), 19 junio 2025. SOLO NY AM 10–11; alto/bajo completos del H1 anterior NY 09–10; barrido 10–11 high→SHORT o low→LONG; confirmación de **desplazamiento de regreso DENTRO** del rango después del barrido; objetivo **extremo H1 opuesto**; cuatro familias mencionadas (displacement, FVG estructural, OB, Breaker); SL más allá del swing que creó desplazamiento. No se proporciona definición computacional universal para OB/Breaker, ni se permite llamar a su proxy actual réplica fiel.
- **QORE actual**: PR #896 G3 doc `a446afa17ed6e411b8f0b6fc182b103a78959a97` y código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`. COG usa pivote de 3 M1 y cuerpo >=1,25× mediana5, DOL del NY previo/Asia/Londres, elige destino elegible más cercano; calcula M15/H1/H4 y requiere H1/M15 presentes y frescos, **pero no existe en este perfil un veto TTrades AM por sweep 09–10 ni un DOL opuesto fijo de ese H1**. Pasa controles de integridad causal ya diseñados, **no una certificación doctrinal completa**.

## Puertas de aceptación metodológica y cognitiva

| Gate | Objetivo | Testigos necesarios | Situación al iniciar |
|---|---|---|---|
| M0 IDENTIDAD | Dos perfiles inequívocos: `ICT_GENERAL_2023` y `TTRADES_NY_AM_2025`, sin tratar la restricción AM como universal | Fuente primaria + acta QORE + IDs separados | Parcial, alta prioridad |
| M1 TIEMPO | Todas las decisiones solo desde M1 cerradas, DST y 09AM H1 completo si TTrades | Reloj UTC/NY, M1 contiguas, sin datos futuros | Implementado parcialmente; reforzar test |
| M2 LIQUIDEZ | TTrades requiere barrido del 09–10 H1 antes de reversal, dirección inversa, target extremo opuesto | Nivel H1 as-of, barra y hora del sweep, veto 0/2 barridos, target correcto | **FALTA en COG general** |
| M3 CONFIRMACIÓN | COG MSS/shift después del barrido, reversión dentro del rango, hecho observado cerrado | Marca MSS, vela real, cuerpo/cierre as-of, no usar pivot futuro | **FALTA vínculo sweep↔MSS** |
| M4 ENTRADAS | Source family de displacement/FVG/OB/Breaker inequívoca, zona y cronología causal; testigos de OB/Breaker no solo proxy | Testigo por familia, setup conforme al autor o etiquetado formalización QORE, no cruces entre familias | **Proxies separados en PR #906**, no G3 integrado |
| M5 SALIDAS | SL swing por familia o política QORE declarada (G3 C2 propuesto), TP DOL y expiraciones sin hindsight | Forma stop/target causal y política de conflicto intrabar | **Sin OMS/fills**, no certificado |
| M6 DOBLE FRONTERA | COG decide, OPS valida datos/orden sin elegir dirección por PnL; protección falsificación de MSS y DOL | adversariales mutación MSS, nivel y timestamp; responsables COG/OPS | G3 unsigned |
| M7 CERTIFICACIÓN FINAL | evidencia metodológica + cognitiva + operacional + económica en gates independientes | actas válidas, OOS, BID/ASK+ACK, PF/DD/expectativa neta | **NO CERTIFICADO** |

## Trabajo P0 de esta rama: ejecutar un testigo independiente de M0–M3

Prototipo **RESEARCH ONLY** de verificador de contexto TTrades AM (no trading permission) que recibe una `CognitiveDecision` auténtica como contrato, 60 M1 del 09–10 y M1 cerradas posteriores a las 10 NY, distingue:
1. `CONTEXT_CONFORMANT_ONLY` si H1 09–10 completo, sweep de extremo anterior, dirección de MSS opuesta, MSS posterior que cierra **estrictamente dentro** de rango en dirección favorable, DOL idéntico a opuesto H1, timestamp de señal exacto y sin conflicto doble barrido; aún **NO metodología certificada** sin familia entrada y stop.
2. `REJECTED` y razones separadas para H1 incompleto, señal fuera de 10–11, sin sweep o ambos sweeps, dirección incorrecta, MSS anterior/no corroborado, desplazamiento no regresó al rango, target equivocado, datos futuros o gaps.
3. `ICT_GENERAL_2023` queda segregado, **NO** se invalida una señal de London/PM por ausencia de H1 09–10. COG general no podrá quedar `CERTIFIED_TTRADES` por sus tests de ingeniería.
4. Casos adversariales sintéticos reales del código consumidos en GitHub Actions, sin market PnL ni lectura del holdout.

**Reglas de gobernanza:** nunca renombrar `CONTEXT_CONFORMANT_ONLY` como `TRADER_CERTIFIED`. Nunca introducir el verificador de prueba dentro del trader o CIBO/QDLE sin otra aprobación. Nunca MERGE, live, paper con OMS ni VPS. No fingir revisión dual: #897 sigue abierta. Si una regla autoral carece de definición determinista, admitir `SOURCE_AMBIGUITY`, no inventar fidelidad.

**Criterio de aprobación P0:** pruebas adversariales pasan; el verificador DEMUESTRA explícitamente los bloqueadores doctrinales, documenta testimonios reproducibles y prepara la posterior revisión cognitiva específica. El trader seguirá NO CERTIFICADO hasta completar M4–M7.
