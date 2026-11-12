# HANDOFF MAESTRO — NUEVO TRADER QORE CRT (SIETE FAMILIAS)
**Continuidad técnica / Owner | corte 11 de noviembre de 2026**
**Estado global: INVESTIGACIÓN QA, no trader certificado. NO LIVE / NO REAL CAPITAL / NO VPS POR ASISTENTE / NO MERGE SIN ORDEN.**

## 0. Misión irrevocable del siguiente arquitecto

CREAR **UN NUEVO TRADER BASADO EN EL INDICADOR QORE CRT RADAR PRO R4-A**, dentro del Trader Lab QORE en GitHub. El trader debe reconocer, administrar, backtestear y eventualmente simular entradas/salidas en **siete estrategias CRT independientes**, para los **34 instrumentos IC Markets**. El sistema tiene que registrar entradas, SL, TP, vencimientos, pérdidas, ganancias, costs, PF, drawdown, OOS y resultados **por familia y agregados**, con causalidad perfecta. No seguir trabajando indefinidamente en un indicador como objetivo final: el indicador es fuente científica de patrones; el objetivo nuevo es un trader completo, aún **NO CERTIFICADO**.

El **primer trabajo urgente** es resolver dos fallos de conciliación entre geometría H4 y MSS propio en USDCAD y AUDNZD; después completar los 33 feeds disponibles, incorporar BTCUSD con la fuente adecuada, homologar feeds y poner a prueba el motor económico de las siete estrategias.

## 1. Dónde continuar, sin reiniciar

- Repositorio soberano de trading y Trader Lab: **mezas3238-hue/qore-core**.
- PR existente: **#1007** — https://github.com/mezas3238-hue/qore-core/pull/1007 ; **DRAFT, no merge**.
- Rama de investigación: **research/crt-r4a-34-holdout-2y-20261111**.
- Último HEAD comprobado: **5452e271cc6f5bd4a1f53f694cfa1998a080ccac**.
- Carpeta de desarrollo del nuevo trader: **research/crt_r4a_holdout/**.
- El Pine original NO está en ese archivo Python: repositorio **mezas3238-hue/qore-deepseek-reviewer**; rama **qa/crt-34-v34-12x-integration-ci-20261109**; ruta **crt-radar-pro/qa-integrated-34/QORE_CRT_34_R4_AB_400_M5_AUTO_BUFFER_QA.pine**; blob SHA exacto **693e3f49719e86e2ea0702f7b355af33bd0c4c7c**.
- URL Pine: https://github.com/mezas3238-hue/qore-deepseek-reviewer/blob/qa/crt-34-v34-12x-integration-ci-20261109/crt-radar-pro/qa-integrated-34/QORE_CRT_34_R4_AB_400_M5_AUTO_BUFFER_QA.pine
- No sustituir silenciosamente R4-A por V34.12X u otra versión. Si se estudia otra versión, verificar diffs y congelar nuevo hash/versión.

**Importante:** el Pine tiene una ventana snapshot limitada de 400 M5/símbolo y entrega la UDT en barstate.islast; **no** es un backtester histórico de 24 meses. El motor de replay M5→H4 se construyó en Python y no ha demostrado paridad 100 % con el Pine original.

## 2. Siete categorías Pine vs. siete ESTRATEGIAS del nuevo trader

El Pine original tiene el mapa diagnóstico de 7 bits qaCatalogMask (aprox. L2268–2288):
- bit 1: TRUE 3C.
- bit 2: 2C Pending (**PROVISIONAL, jamás entrada**).
- bit 4: 2C Expansion (**RECHAZADO, jamás entrada**).
- bit 8: Inside Return.
- bit 16: Inside Continuation (**RECHAZADO, jamás entrada**).
- bit 32: Multi-Candle (tiene dos subfamilias: Multi4 y Multi-N).
- bit 64: Retest MSS M15.

Estos **siete diagnósticos NO son siete estrategias rentables ni siete entradas autorizadas**. El CRT 2C RETURN ratificado está fuera de esos bits y el Pine distingue MSS M15 de C2 versus C3 (L2113–2120). Para cumplir el mandato del Owner sin operar patrones inválidos, las **siete hipótesis de trading** son:

| ID | Familia del nuevo trader | Ratificación y confirmación | Estado actual |
|---|---|---|---|
| F1 | CRT 2C RETURN + MSS M15 propio **en C2** | C2 H4 completo, barrida unilateral + retorno; MSS15 en C2, señal no antes del cierre C2 H4 | Detector de eventos QA |
| F2 | CRT 2C RETURN + MSS M15 propio **en C3** | CRT de C2 ratificado; MSS15 en C3 del mismo ciclo, no antes del cierre MSS15 | Detector de eventos QA |
| F3 | **TRUE 3C + MSS M5 propio** | C2 sin barrer C1, C3 barre unilateralmente C1 y cierra dentro; confirmación solo al cierre H4 de C3 | Detector de eventos QA |
| F4 | **Inside Return + MSS propio** | C2 estrictamente dentro de C1; H4 terminal barre exactamente un extremo de C2 y cierra dentro; pivote/MSS propio | Detector experimental QA |
| F5 | **Multi4 + MSS propio** | C1/C2a/C2b/C3, primera barrida en C2a, retorno distribuido y cierre terminal; pivote/MSS de esa familia | Detector experimental QA |
| F6 | **Multi-N + MSS propio** | C1 + 2 a 5 H4 interiores + H4 terminal con barrida unilateral C1 y retorno; pivote/MSS de su terminal | Detector experimental QA |
| F7 | **Retest M15 del CRT fuente** | 2C/MSS15 ratificado del mismo ciclo; M15 posterior toca mismo pivote y cierra recuperándolo en ≤4 horas | Detector experimental QA, ligado a MSS15 padre |

**Nunca copiar el MSS o C1 de un ciclo distinto.** Una misma secuencia puede producir observaciones superpuestas; siete rutas no implican siete órdenes independientes en simultáneo. La estrategia F7 no constituye nueva confirmación MSS independiente, sino patrón derivado con referencia explícita al MSS original.

## 3. Código ya implementado — NO volver a escribir desde cero

En research/crt_r4a_holdout/:

**Motor/estructura**
- causal_crt_m5_engine.py: motor causal de M5, H4, CRT base y MSS, recolección de F1/F2/F3 y enlace con secundarios. readout dispone seven_family_research_event_counts.
- pine_h4_geometry.py: H4 de Nueva York y geometría.
- pine_swing_primitives.py: pivotes y cruces M5/M15 propios, congelación pre-barrida.
- secondary_family_geometry.py: geometría cerrada H4 Inside Return / Multi4 / Multi-N y retest M15.
- secondary_family_observer.py: observación independiente de F4–F7, conserva procedencia y vinculaciones.
- secondary_family_mss.py: candidatos y MSS15 propios de Inside/Multi4/Multi-N, pivotes congelados antes de sweep, descarte de barrida contraria, publicación solo tras H4 final.
- seven_family_contract.py: contrato de **siete familias** distinto del catálogo QA original; estados fail-closed y prohibición de ejecución broker.
- seven_family_paper_plan.py: **plantillas de hipótesis** para entrada, stop y take profit de las siete rutas, no fills ni órdenes broker.
- archived_integrated_engine_probe.py: lector de OHLC original y replay sobre fuente con hash validado.
- aggregate_seven_family_events.py: agregación fail-closed por mercado y por familia de los resultados de los 33 feeds; no PnL.
- aggregate_integrated_detector.py: agregación anterior A/B, ya certificada a nivel de resultado experimental, NO trading.

**QA**
- tests/test_causal_crt_m5_engine.py
- tests/test_secondary_family_geometry.py
- tests/test_secondary_family_observer.py
- tests/test_secondary_family_mss.py
- tests/test_seven_family_contract.py
- tests/test_seven_family_paper_plan.py
- tests/test_aggregate_seven_family_events.py
- Y resto de tests de la carpeta.

**Documentación**
- SEVEN_TRADE_RESEARCH_FAMILIES_R4A_2026-11-11.md
- RESULTADOS_CRT_MSS_CAUSAL_INTEGRADO_33_2024_2025.md

## 4. Evidencia real: NO confundir tests o eventos con rentabilidad

**Último HEAD verificado 5452e271:**
- [QA holdout research #43117571448](https://github.com/mezas3238-hue/qore-core/actions/runs/43117571448): PASS, **250/250 pruebas**.
- [QORE CI #43117571455](https://github.com/mezas3238-hue/qore-core/actions/runs/43117571455): PASS, **6.782 tests, 8 warnings**.
- [USDCHF piloto #43117571454](https://github.com/mezas3238-hue/qore-core/actions/runs/43117571454): SUCCESS. Ver log/artifact de versión para comprobar los contadores después de cualquier nueva modificación.

**Resultados históricos ANTERIORES (modelo base A/B):**
- [33 fuentes originales, agregación corregida #43110266221](https://github.com/mezas3238-hue/qore-core/actions/runs/43110266221): **4.890.804 M5, 33 de 34 instrumentos**, **12.232 observaciones A 2C MSS15** y **1.748 observaciones B TRUE3C MSS5** = 13.980 eventos A/B. **0 órdenes ejecutadas**.
- Fuentes: **21 IC Markets DEMO**, **12 Atlas DEMO NO HOMOLOGADAS contra IC**. BTCUSD aún no tiene fuente histórica IC verificable equivalente.
- Esas cifras son para la versión previa del motor A/B, **no son el total agregado de las siete estrategias**, no son trades, PF ni resultados económicos.

**Piloto real USDCHF de siete familias (evidencia [#43116336603](https://github.com/mezas3238-hue/qore-core/actions/runs/43116336603)):**
F1=114, F2=244, F3=57, F4=13, F5=28, F6=11, F7=264 observaciones. La suma nominal es **731** eventos de familia que **pueden superponerse**, no 731 fills ni 731 oportunidades económicas independientes. El motor registra 0 órdenes de broker, sin spreads ni swaps ni PnL. El estudio 2024–2025 está **BURNED / YA INVESTIGADO**.

**CRÍTICO — MATRIZ COMPLETA DE SIETE FAMILIAS FALLÓ:**
- [GitHub Actions #43117258279](https://github.com/mezas3238-hue/qore-core/actions/runs/43117258279): **31 de 33 jobs de fuente SUCCESS; 2 FAIL**: **USDCAD (Atlas)** y **AUDNZD (IC DEMO)**; etapa aggregate-seven-family **SKIPPED**.
- **No existe aún informe consolidado válido de siete familias / 33 mercados**.
- Ambos fallos son un gate lógico seguro activado en causal_crt_m5_engine.py readout: **ValueError: "owned MSS signal has no independently matched H4 geometry"**. El secondary_family_mss emitió una observación que no encuentra en secondary_family_observer la misma tupla (family, c1_at, ratified_at).
- Investigar por qué: ciclos de H4 incompletas / discontinuidades / DST, selección de C1 candidata MultiN, expiración, identidad terminal, rama de multi4, discrepancia en criterios de validez. **NO quitar el gate, NO forzar match, NO descartar eventos a escondidas; identificar el primer evento discordante y corregir la semántica y test de regresión.** Después rerun USDCAD/AUDNZD y los 33, obtener agregación de 7 familias.
- La última corrida PASS 250 tests **no elimina** esta falla que requiere escenarios históricos concretos.

## 5. Ventana y fuentes históricas

Universo 34:
AUDJPY, GBPUSD, GBPJPY, XAUUSD, USTEC, US500, US30, BTCUSD, AUDUSD, USDCAD, USDJPY, EURUSD, USDCHF, NZDUSD, NZDJPY, NZDCHF, XAGUSD, AUDCAD, AUDCHF, AUDNZD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY, EURNZD, GBPAUD, GBPCAD, GBPCHF, GBPNZD, NZDCAD.

Conservar la identidad de proveedor, símbolo (NASDAQ aliases NAS100↔USTEC y SP500↔US500 solo para etiquetado, NO paridad de precios), tick size, lot size, horarios, spread y costos. M5 48 continuas por H4, fases M5 0..4 por proveedor, DST NY y seis ventanas H4 según el Pine para ese tipo de instrumento. Distinguir calendario 24/7 cripto de índices con sesiones.

El histórico **2024-01-01 a 2025-12-31** fue inspeccionado varias veces, y ya no puede etiquetarse **holdout virgen** tras los cambios hechos. Sirve como dataset de desarrollo/diagnóstico. Para certificación científica final se necesita **otro intervalo consecutivo de 24 meses NUNCA CONSULTADO**, con evidencia anterior de su no-exposición; o una evaluación prospectiva de 24 meses. Hash notarizado no basta por sí solo para demostrar que los datos nunca fueron vistos.

## 6. Diseño completo del trader, aún PENDIENTE

**A. Detector y clasificación:** portar/testar estado exacto Pine (C1/C2/C3, Inside/Multi, 7 modelos, M5, M15, H4, FVG/PDH-PDL solo donde corresponde) y ledger histórico por evento con identidad, familia, dirección, C1, sweep, pivote congelado, MSS y ratificación.

**B. Señal vs orden:** definir un contrato "opportunity" libre de volumen para el trader; la señal debe ratificarse antes de habilitar la orden. Separar 2C C2 y 2C C3 sin mezclar. Gestionar simultaneidad y prioridad si varias familias se superponen en mismo símbolo/ciclo; no asumir 7 posiciones.

**C. Entrada, stop, TP:** en seven_family_paper_plan.py hay hipótesis iniciales (no reglas de Pine): 50 % cuerpo H4; SL detrás del extremo barrido propio con buffer ATR; TP estructural opuesto C1; retest con alternativa de entrada M15. Hay que congelar por familia sus variantes y verificar coherencia:
- F7 **requiere guardar retest_close propio** y usarlo para planear entrada; el módulo actual usa setup_close en ese caso: **revisar/corregir ese fallo de fidelidad antes de simular fills**.
- Separar la cotización BID/ASK por sentido y spread dinámico, buffer independiente, redondeo a tick y valor por punto.
- Expiración 3 H4 como hipótesis; cancelar límites si se invalida, no reintentar con datos futuros.
- En una M5 donde SL y TP aparecen ambos dentro de high/low, aplicar orden conservador o datos tick: no declarar TP favorable por suposición.
- Todas las entradas y salidas deben tener TCA y registrar comisión/swap/slippage y spread.
- Riesgo per-trade, diario y agregado; preservar separación de cartera y correlación.
- **No implementar conexiones LIVE o envío a cTrader/MT5 de esta rama**.

**D. Backtester económico:** convertir eventos a órdenes simuladas de verdad (señales→colocación límites→fill→SL/TP/timeout→costos→R), calendario de sesiones y múltiples instrumentos, trades ledger con traza completa y reproducibilidad. No reutilizar el conteo de 13.980/731 como cantidad de operaciones.

**E. Paridad Pine/replay:** exportación por barra desde Pine original o versión instrumentada con la **misma semántica**, no snapshot barstate.islast; comparación 100 % por family/event_id/fecha/horario y niveles sobre el **mismo feed**. Crear y hacer pasar el gate 0 ausentes/0 extras/0 anticipados/0 discrepancias de precio antes de certificación.

**F. Test y certificación:** regresiones sintéticas y reales, datos source-verified por 34, splits desarrollo/validación/holdout nunca vistos, freeze hashes SHA de código, parámetros y datasets, ejecución de **24 meses consecutivos** después del freeze; informes separados F1..F7 y cartera.

**G. Reporte exigido**: para cada familia y global: oportunidades, órdenes colocadas, límites expirados, fills, operaciones cerradas, WR, PF bruto/neto, expectativa/R, retorno, DD max, DD MC, Sharpe/Sortino (si aplican), spreads/slippage, sensibilidad, años/meses, mercado, largas/cortas, desgloses de pérdida, costos y breaches; exposición y correlación; no excluir perdedores. Publicar logs/artifacts completos.

## 7. Secuencia ejecutiva obligatoria para el siguiente arquitecto

P0. **Revalidar HEAD PR #1007, último CI, archivos y 33-job workflow**. No asumir que este corte sigue actual. Revisar últimos runs primero.
P1. **REPRODUCIR USDCAD/AUDNZD** desde los artefactos originales con SHA; registrar primera discordancia entre observable de geometría y propio MSS (family/C1/H4/fuente/fases), formular fix causal; añadir tests y aprobar ambos; mantener gate fail-closed.
P2. Correr **workflow 33 fuentes para siete familias** de nuevo, obtener 33/33 job SUCCESS y summary.json/summary.md con 7 columnas por instrumento; verificar 21/12 cohort y missing BTC.
P3. Resolver homologación de datos IC en 12 Atlas; incorporar **BTCUSD del proveedor IC verificado**; certificar 34/34.
P4. Desarrollar **ledger histórico original Pine y suite de paridad** para 7 estrategias; 0 diferencia.
P5. Congelar **siete especificaciones de órdenes** con modelo de costos, retest_close y gestión de señales simultáneas.
P6. Implementar y ejecutar backtester multi-activo con 7 familias, costos/sesiones/slippage y defensas anti-lookahead, sin broker.
P7. Seleccionar/fijar un intervalo genuinamente no visto de 24 meses. Si no existe hoy, declarar NO DISPONIBLE y realizar forward prospectivo; **no** usar 2024–2025 como virginal.
P8. Certificar gates, revisar performance por familia y en agregado. Una familia sin edge puede permanecer detector sin capital; NO forzar operabilidad a cambio de exponer dinero.
P9. Solo tras resultados, el Owner decide si se integra al flujo de riesgo CIBO/QORE, siempre separado del modo LIVE.

## 8. Reglas de trabajo del Owner

- GitHub es fuente de verdad. Usar rama y PR existentes, no crear repo/trader paralelo sin causa.
- **No merge** hasta autorización Owner.
- **No VPS** ni activar servidores remotamente.
- **No LIVE / no dinero real / no broker autotrading**. QA y pruebas de laboratorio.
- Mantener **34 instrumentos** como objetivo universal; 33/34 es avance parcial, BTC pendiente.
- Ninguna familia CRT debe heredar confirmación de otra ni usar pivotes futuros.
- El objetivo es **un nuevo trader real a nivel de software**, no solo gráficos/indicadores; rentabilidad solo se determinará con test económico neto y holdout auténtico.
- Owner recibe informes en **español**, porcentajes y métricas con fuentes/URLs exactas, sin exageración.

## 9. Primer mandato para el nuevo chat

**"Actúa como arquitecto soberano de Trader Lab QORE. Revalida HEAD de PR #1007 y las ejecuciones GitHub. Estamos construyendo el NUEVO TRADER QORE CRT de SIETE FAMILIAS a partir del Pine R4-A; no me entregues solo otro indicador. Empieza reproduciendo y resolviendo la discordancia causal USDCAD/AUDNZD de la matriz #43117258279, sin borrar el gate. Después ejecuta 33/33 y homologa las 34 fuentes, obtén paridad completa del Pine, completa la simulación entrada/SL/TP y costos, y prepara holdout genuinamente no visto de 24 meses. Deja todo trazado en PR #1007. QA solamente; no merge, no VPS, no LIVE."**

**Estado final de este corte: arquitectura/suite siete familias QA y piloto USDCHF logrados; siete familias / 33-mercados agregadas — BLOQUEADO por 2 discordancias; trader netamente rentable/24m holdout virgen — NO CERTIFICADO.**
