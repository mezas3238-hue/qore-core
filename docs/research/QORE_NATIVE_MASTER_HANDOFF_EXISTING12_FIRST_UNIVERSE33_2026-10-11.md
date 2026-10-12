# HANDOFF MAESTRO — QORE NATIVE / TRES TRADERS PROPIETARIOS / 12 ACTIVOS AHORA + 21 DESPUÉS

**Handoff para el siguiente arquitecto — 11 de octubre de 2026, America/Asuncion (algunas Actions se registran en GitHub el 12/oct UTC).**  
**Repositorio:** `mezas3238-hue/qore-core` — área de trabajo **GitHub RESEARCH**, sin cambios a `main`, VPS, MT5, cTrader operativo, CIBO, Shared, QDLE o trading real.  
**Documento vivo solo mediante nuevos commits y trazabilidad; preservar PR e informes originales sin reescribir sus resultados.**  
**Instrucción más reciente del propietario:** **«Comenzar con los 12 activos existentes; incorporar los otros 21 cuando se hayan descargado y validado»**. Esto reemplaza la tentación de esperar todo el universo de 33. La captura de los 21 corre en paralelo y es responsabilidad de otra rama; **NO duplicar ni interrumpir trabajos de otros arquitectos**.

## 0. Resumen ejecutivo: qué está probado y cuál es la misión ahora

1. La visión es **descubrir hasta tres traders de QORE realmente propios**, cada uno con un mecanismo económico distinto, edges demostrables, razonamiento causal, gestión inteligente de posición y certificación progresiva. **No fabricar tres por cuota**, ni reproducir TTrades/ICT rígidamente, ni transplantar supuestos positivos entre metodologías. Los componentes de autores externos sirven solo si se justifican y prueban por sí mismos. La cognitiva/Shared/CIBO futura **no convierte una señal sin edge en edge**.
2. **Ninguno de esos tres traders Native está certificado (0/3)**, ninguna operación Live/PAPER autorizada por estos estudios. Las pruebas fuente/calendario **no** son backtests ni evidencia de ganancias.
3. Los primeros **12 activos cTrader DEMO M5 de ~10 años ya PASARON G0 de integridad, 12/12**, [PR #816](https://github.com/mezas3238-hue/qore-core/pull/816), [Actions #38196127168](https://github.com/mezas3238-hue/qore-core/actions/runs/38196127168), **14/14 jobs GREEN**, **8.726.985 barras M5 originales**, 132/132 particiones anuales RAW y sus SHA de calidad/manifiestos verificados, errores de orden/duplicado/hash = 0. **Lo próximo NO es repetir G0**: es adjudicar sesiones reales del broker, huecos frente a cierres de mercado, costes y operabilidad en regímenes normales; luego preregistrar UNA hipótesis causal H4/D1 antes de mirar retornos.
4. **21 símbolos para completar 33 están pendientes de adquisición/validación 10Y M5** en rama distinta [PR #811](https://github.com/mezas3238-hue/qore-core/pull/811). Tras fallos OAuth anteriores, último informe de esa rama declaró IC Markets DEMO + catálogo verificados y adaptador histórico read-only para scope VIEW. Su corrida [#38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541) fue vista **QUEUED**, no con 21 capturas certificadas. **No afirmar 33/33**. M1 diez años existente para **9 de los 12**, faltan 24 M1 para el cupo de 33; 21 M5 faltantes y 24 M1 faltantes son **brechas diferentes**.
5. Resultado económico: **RESET** fixing EURUSD G1 M5 y sensibilidad M1 = **NO SUPPORT**, no falsaciones independientes; **DRIVE** NAS100 single-clock = **NO SUPPORT**; **RELATIVE sigue ON_HOLD** hasta dos-leg costs+materialidad/potencia. **EVENT CPI** concluyó G0/G0B excelente pero se cerró como **candidato a ejecución durante noticias por política de riesgo**, no por `NO_EDGE`.
6. Cambio de rumbo aprobado para *investigación Native*: **no exposición nueva a noticias programadas de gran impacto**; investigar causalmente **regímenes normales de varias horas/días** con costes medidos, stops supervivientes, potencia estadística y OOS. La ventana blackout 30m antes/60m después, coste RT<=10% stop-risk y P90 ATR son **candidatos de screening no certificados**, no instrucciones de Live ni cambios automáticos de Core.

### Enlaces prioritarios de arranque

- [Issue maestro Native #789](https://github.com/mezas3238-hue/qore-core/issues/789) — visión y certificación / prohibición producción.
- [PR política NO-NEWS #814](https://github.com/mezas3238-hue/qore-core/pull/814) — cambio de régimen de investigación, no inferencias exageradas de edge.
- [Issue #815](https://github.com/mezas3238-hue/qore-core/issues/815) — primera prioridad G0→pre-G1 **12 ahora / 21 después**.
- [PR #816](https://github.com/mezas3238-hue/qore-core/pull/816) — G0 M5 12/12 completado, datos fuente y informe.
- [PR #811](https://github.com/mezas3238-hue/qore-core/pull/811) — adquisición pendiente IC Markets DEMO: rama **separada, no fusionada**.
- [PR magnitud #806](https://github.com/mezas3238-hue/qore-core/pull/806) — gobernanza de coste, potencia, controles y RELATIVE.
- [PR Londres pivot #809](https://github.com/mezas3238-hue/qore-core/pull/809) — adoptar componentes útiles, no reproducir rígidamente TTrades.

## 1. Misión, fronteras y errores que NO deben repetirse

**Meta real:** descubrir 3 fuentes de ventaja económicamente explotable —no obligatoriamente DRIVE/RESET/RELATIVE, que son etiquetas de **familias candidatas** sujetas a falsación— y después diseñar traders cognitivos independientes para QORE Core. La certificación exige inputs causalmente conocidos, motor FIRST-ONLINE (sin lookahead), señales/fills auditables, benchmark justo, coste completo, tamaño de muestra/potencia, estabilidad temporal, drawdown, cola de pérdidas, múltiples símbolos/periodos sin elegir ganadores, WFO/OOS, stress y portafolio. **La cognitiva es una capa de decisión y veto; no una excusa para probar parámetros infinitos**.

**Prohibiciones absolutas sin autorización explícita del propietario:** no MT5/VPS/live, no enviar órdenes, no conectar CAPITAL real, no mutar el runtime de Traders/Shared/CIBO/QDLE, no elevar ramas research a main sin revisión, no usar slots secretos de cuenta para reautorizar OAuth a ciegas, no divulgar credenciales en chat/issues/logs, no desprecintar holdout pre-2016 o cualquier OOS reservado. Las fuentes cTrader DEMO antiguas **no garantizan que el broker origen fuera la cuenta IC Markets exacta**; los nuevos 21 deben tener identidad IC Markets DEMO probada desde su catálogo. No mezclar fuentes de broker sin marcarlo.

**Uso de auditor externo DeepSeek:** consultar al auditor ante ambigüedades de regla, causalidad, sobreajuste y potencia; su opinión es apoyo y **no sustituye evidencia o código**. Registrar pregunta, supuesto, respuesta y adjudicación en GitHub; discrepancias con fuentes primarias deben resolverse antes de convertir sugerencias en reglas.

## 2. Inventario exacto del universo: 12 existentes, 21 esperados

**Cupo de 33 inicial congelado en [issue #574](https://github.com/mezas3238-hue/qore-core/issues/574):** 3 índices + 2 metales + 7 FX mayores + 21 FX cruces/minores. Este roster **NO** afirma ser el catálogo completo de índices/metales de IC Markets; expandirlo requiere nueva versión ex ante (nunca elegir después de PnL).

### Cohorte A: los **12** con M5 10 años recuperado y G0 de integridad PASS

| Familia | Instrumento canónico (alias en archivo cuando procede) | Barras M5 source | H4 UTC completos (48 M5) | D1 UTC completos (288 M5) |
|---|---|---:|---:|---:|
| FX minor | AUDJPY | 745.468 | 14.881 | 1.945 |
| FX major | AUDUSD | 745.283 | 14.760 | 1.835 |
| FX major | EURUSD | 745.458 | 14.867 | 1.932 |
| FX minor | GBPJPY | 745.478 | 14.916 | 1.979 |
| FX major | GBPUSD | 745.274 | 14.804 | 1.871 |
| Índice | NAS100 / **USTEC** | 701.457 | 12.681 | **0** |
| Índice | SP500 / **US500** | 693.064 | 11.431 | **0** |
| Índice | US30 | 700.856 | 12.592 | **0** |
| FX major | USDCAD | 745.088 | 14.722 | 1.797 |
| FX major | USDJPY | 745.327 | 14.832 | 1.899 |
| Metal | XAGUSD | 706.516 | 12.417 | **0** |
| Metal | XAUUSD | 707.716 | 12.762 | **0** |
| **Total** | **12 / 12** | **8.726.985** | — | — |

**Interpretación indispensable:** H4 y D1 aquí son **bitmaps de slots UTC de disponibilidad M5, no velas broker-native H4/D1**. Que NAS100, SP500, US30, XAUUSD y XAGUSD muestren **0 D1 UTC completas** es consecuencia probable de sus **pausas de sesión**, y **NO prueba un feed inservible**. Deben adjudicarse cierres/rollover por sesión del broker antes de reconstruir barras multihora/diarias; no rellenar horas inoperables. Un intervalo activo H4 sin 48 velas no equivale automáticamente a dato corrupto. No declarar barras completas 24/7 de índices/metales.

**Fuentes verificadas:**
- Productor M5 [Actions **#35166210458**](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), SHA `ab782b8e9f890f86a2b6500070f0556b4b685e3d`, aggregate [artifact **#10476615509**](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458/artifacts/10476615509), manifest hash `47f5763d7ea2c10dd32fa40a84d7480c8124f1a512b623c1299ef2ba7b8c51c2`, período objetivo **2016-09-17T00:00Z → 2026-09-17T00:00Z excl.**
- Auditor independiente G0 [Actions **#38196127168**](https://github.com/mezas3238-hue/qore-core/actions/runs/38196127168), exact exec SHA `1336a86ff4d9ef1a076fc7cfc1803590580de159`, **14/14 jobs SUCCESS**, **132/132 SHA RAW y 132 SHA calidad**, conteo **8.726.985/8.726.985**. Aggregate [artifact **#11723327973**](https://github.com/mezas3238-hue/qore-core/actions/runs/38196127168/artifacts/11723327973), SHA256 final `b701075c24fa899e05e833f0940b034c70a70d6d91790f8622448a9c34281050`.
- Contrato prereg **ANTES de análisis** commit `7309ac368e2ba306bda311d73a1b13692872d825`: [prereg original 12](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-existing12-m5-g0-normal-regimes-20261011/docs/research/QORE_NATIVE_EXISTING12_M5_G0_PREREG_SOURCE_ONLY_2026-10-11.md).
- [Informe G0 12 ejecutado](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-existing12-m5-g0-normal-regimes-20261011/docs/research/QORE_NATIVE_EXISTING12_M5_G0_EXECUTED_SOURCE_12_OF_12_2026-10-11.md); código `src/qore/infrastructure/trader_lab/qore_native_existing12_m5_g0_v1.py`, tests `tests/infrastructure/trader_lab/test_qore_native_existing12_m5_g0_v1.py`, workflow `.github/workflows/qore-native-existing12-m5-g0.yml`.

### M1 de diez años disponible en **9 de los 12**

`AUDJPY AUDUSD EURUSD GBPJPY GBPUSD NAS100 USDCAD USDJPY XAUUSD` — originales provider-native, no reconstruidos de M5, [Actions **#35548099334**](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), productor `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. La auditoría reciente G0 fuente M1 de nueve mercados está en [PR #791](https://github.com/mezas3238-hue/qore-core/pull/791), [Actions **#38166675573**](https://github.com/mezas3238-hue/qore-core/actions/runs/38166675573), agregado [#11712187623](https://github.com/mezas3238-hue/qore-core/actions/runs/38166675573/artifacts/11712187623) (allí se auditó una ventana 2025–26, no diez años completos en cada celda). Ejemplo NAS100 10Y = **3.486.929 M1** verificados por SHA; EURUSD 10Y = **3.693.521 M1**. **No hay archivo M1 10Y acreditado en estos orígenes para SP500/US30/XAGUSD**, aunque sí hay M5 10Y: prohibido sintetizar M1 desde M5.

### Cohorte B: los **21** que FALTAN para el cupo M5 10Y (captura en otra rama)

`NZDUSD USDCHF EURGBP EURJPY EURCHF EURCAD EURAUD EURNZD GBPCHF GBPCAD GBPAUD GBPNZD AUDCAD AUDCHF AUDNZD CADJPY CADCHF CHFJPY NZDJPY NZDCAD NZDCHF`.

- `USDCHF` y `EURJPY` cuentan con **archivos M5 parciales ~7 años** en [Actions **#36079229139**](https://github.com/mezas3238-hue/qore-core/actions/runs/36079229139), USDCHF artifact `#10840849959`, EURJPY artifact `#10840979795`, 2019–2026. No equivalen a M5 10Y ni deben reutilizarse como holdout virgen; había reserva VT08. Los otros **19** no figuran en los tres orígenes inventariados, lo que no equivale a «nunca existieron en Core».
- **Brecha M5 10Y = 21**, segunda fase **brecha M1 10Y = 24** (incluye `SP500 US30 XAGUSD` y los 21 faltantes M5). No confundir descargas.
- [PR **#811**](https://github.com/mezas3238-hue/qore-core/pull/811), [inventario 33](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-universe-33-icmarkets-ctrader-capture-20261011/docs/research/QORE_NATIVE_ICMARKETS_CTRADER_UNIVERSE33_INVENTORY_AND_MISSING_CAPTURE_2026-10-11.md), workflow `.github/workflows/qore-native-icmarkets-33-universe-m5-missing-capture.yml`, registry `src/qore/infrastructure/trader_lab/qore_native_universe_33_source_registry_v1.py`, preflight `qore_native_icmarkets_catalog_preflight_v1.py`, captura `qore_native_icmarkets_missing_m5_capture_v1.py`.
- **Incidencia real (no repetir)**: OAuth antiguo `CTRADER_ACCESS_TOKEN_INVALID_NO_REFRESH_ATTEMPTED`; otro reintento dio `brokerTitleShort` opcional ausente, corregido con `ProtoOATraderReq.trader.brokerName`, y el cliente de producción CIBO requería TRADE incluso para lectura histórica. Se implementó adaptador **_ReadOnlyIcMarketsHistoryClient** separado, aceptando scope VIEW/TRADE para IC Markets **DEMO** y negando refresh/órdenes. No modificar SDK de producción. El informe PR #811 documenta IC Markets DEMO/catálogo **verificado posteriormente**; el run de captura [**#38193802541**](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541), commit `e0ca5a13c866a19d8505c68cffc473598984b340`, seguía **QUEUED en última consulta de GitHub**. Cuenta exacta/alias deben cotejarse con manifiestos de salida, no por nombre supuesto.
- **STOP**: no declarar `21/21 CAPTURED` por matriz ejecutada, workflow verde parcial, catálogo correcto o intención del dueño. Solicitar comprobación de job por símbolo, barras originales, rangos, 11 RAW SHA/año, duplicados y artefactos no expirados, y luego G0 independiente ANTES de añadir cualquiera al pool. No duplicar corridas mientras otro arquitecto procesa capturas.

## 3. Investigación ejecutada: tesis, ensayos económicos y resultados negativos/no soportados

### QORE Native: origen de visión y frontera con otras líneas

- [Programa 3 traders #789](https://github.com/mezas3238-hue/qore-core/issues/789): origen de DRIVE (persistencia), RESET (reversión de flujo), RELATIVE (residual relativo), *todos hipótesis y no identidades comercializadas*.
- [PR Londres pivot #809](https://github.com/mezas3238-hue/qore-core/pull/809): propietario decidió usar features que sirvan (CISD, liquidity/sweep, protected swing, causal clocks) **sin fidelidad obligatoria** a TTrades. Los archivos de reconstrucción fiel Londres #785/#786/#788 y programa `QORE-alpha 96` PR #797 son **TRACKS DISTINTOS**; no mezclarlos con resultados Native ni asumir que 96 pruebas son las aprobadas para G1 Native.
- Londres reentry [PR #801](https://github.com/mezas3238-hue/qore-core/pull/801), [CI #38174719898](https://github.com/mezas3238-hue/qore-core/actions/runs/38174719898): `DEV_NO_SUPPORT`. EURJPY Londres 187 trades **PF gross 0,880, mean −0,0604R**; USDCHF Londres 216 **PF gross 1,112, mean +0,05286R**, conjunto ~`−0,00377R` antes de costes y ventaja sobre placebo CI incluye 0. **No seleccionar USDCHF a posteriori**, ni retunear para salvar Londres. Global 599 señales, no 599 trades Londres.
- **RESET fixing London EURUSD**, prereg y G1 [PR **#802**](https://github.com/mezas3238-hue/qore-core/pull/802), [Actions **#38175711378**](https://github.com/mezas3238-hue/qore-core/actions/runs/38175711378): DIFF-in-DIFF de fix tail vs franja control, presión 15:30–15:55 London y reversión 16:05–16:30, efecto pareado **−0,691910 bps**, CI95 **[−1,935366,+0,547365]**, no soportado. Conclusión **del estimando específico**, no de todos los flujos FX.
- Sensibilidad RESET **M1 EURUSD** [PR **#804**](https://github.com/mezas3238-hue/qore-core/pull/804), [Actions **#38184186416**](https://github.com/mezas3238-hue/qore-core/actions/runs/38184186416): 2446 días, efecto **−0,520534 bps**, IC95 **[−1,382368,+0,375944]**, no soportado. **NO segunda falsación independiente** del RESET M5: mismo evento/fechas subyacentes.
- Coste BID/ASK para RESET: [PR #803](https://github.com/mezas3238-hue/qore-core/pull/803), [Actions #38183622754](https://github.com/mezas3238-hue/qore-core/actions/runs/38183622754) cTrader histórico tick dio `CH_ACCESS_TOKEN_INVALID` en su contexto. No usar este fallo antiguo como prueba universal de que OAuth actual no funciona, ni suponer spreads 0 porque el gross no soportó hipótesis.
- **DRIVE G1 NAS100/USTEC M1**, [PR **#805**](https://github.com/mezas3238-hue/qore-core/pull/805), [Actions **#38185670105**](https://github.com/mezas3238-hue/qore-core/actions/runs/38185670105): formación direccional **09:30–10:00 NY**, continuación **10:01–11:00**, baseline dirección día elegible anterior; **2547 días** y 522 semanas; gross señal **+1,11956 bps**, gross baseline **+0,53298 bps**, **ventaja bruta Δ +0,586574 bps** (bootstrap weekly 95% **[−2,051465,+3,251739]**). Sin ventaja robusta ni prueba neta. Prereg `9ebcf60628196a52cbd476e584d4f554b60af035`, output [artifact #11719487773](https://github.com/mezas3238-hue/qore-core/actions/runs/38185670105/artifacts/11719487773). No buscar «variante mejor» en los mismos resultados.
- **Lectura correcta:** los efectos pequeños/no soportados **NO prueban que hubiera edge positivo eliminado por spread**. No se midieron costes transaccionales completos para afirmar eso. Prueban insuficiente evidencia para ESAS reglas y controles.

### RELATIVE: puertas congeladas, NINGÚN G1 autorizado

- [PR **#806**](https://github.com/mezas3238-hue/qore-core/pull/806), prereg `docs/research/QORE_NATIVE_MAGNITUDE_GATE_RELATIVE_AND_EVENT_PIVOT_2026-10-11.md`: exige cartera de dos piernas con nocional bruto normalizado; beta hedge y signo **conocidos antes** de cada decisión. Gross `G=s(r_A−β*r_B)/(1+|β|)`; coste RT de ambas piernas `C=(c_A+|β|c_B)/(1+|β|)` con spread, comisión, slippage y financiación; baseline mismo reloj/riesgo; **Δ bruto >=3× coste conservador verificado, lower CI95(Δ)>+2bps y lower CI95(G−C)>0**; power, múltiple testing y OOS antes de promover.
- La puerta económica triple fue congelada **ANTES de retornos RELATIVE**; costo desconocido = `GATE_NOT_OPEN_COST_UNKNOWN`, nunca cero. M1 synchrony disponible de pares candidatos fue solo calidad (no edge), p.ej. EURUSD/GBPUSD 368.289 minutos y AUDJPY/GBPJPY 370.858 en ventana 2025–26.
- Políticas adicionales propuestas en [PR #814](https://github.com/mezas3238-hue/qore-core/pull/814): costes RT conservadores <=10% riesgo(stop), stop basado en BID/ASK y no solo mid, spread P99 por horario, ATR histórico P90 causal, calendario conocido as-of. Son **screens por verificar**, NO condiciones inherentes probadas del mercado ni modelo live.

## 4. Investigación EVENT CPI: completa documentalmente, CERRADA como ejecución por política

Separar cuatro niveles:
- **G0 calendario+timestamp**, [PR **#807**](https://github.com/mezas3238-hue/qore-core/pull/807), [CI **#38189483643**](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643): 11/11 calendarios oficiales BLS 2016–2026, 131 filas de calendarios totales (algunas fuera ventana); **119 CPI fechados dentro ventana cTrader 2016-09-17→2026-09-17** y **113/119** con 71/71 minutos NAS100/USTEC M1 originales en 08:20–09:30 NY. [Source artifact #11720651765](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643/artifacts/11720651765) y [presence artifact #11720822239](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643/artifacts/11720822239), 9 tests PASS, NO precios/outcomes. Seis fechas incompletas: **2017-01-18; 2017-03-15; 2017-04-14 (0); 2017-05-12; 2020-04-10 (0); 2022-12-13**. No inferir feriados/causa broker sin fuente.
- **G0B publicación efectiva**, [PR **#810**](https://github.com/mezas3238-hue/qore-core/pull/810), [CI exact head **#38191275999**](https://github.com/mezas3238-hue/qore-core/actions/runs/38191275999): cotejo con índice BLS de comunicados originales y **119/119 cabeceras** embargo 08:30 ET, fecha de release y mes/año referencia; **11 tests y Ruff PASS**, artifact [#11721212991](https://github.com/mezas3238-hue/qore-core/actions/runs/38191275999/artifacts/11721212991). Fechas originales de anuncio **sí**, pero calendarios *conocidos de antemano* aún no demostrados. CPI de referencia **octubre 2025 NO publicado** por shutdown, CPI referencia septiembre 2025 salió **2025-10-24**, nunca agregar un mes sintético.
- **G0C/G0D + potencia, sin abrir retornos**, [PR **#813**](https://github.com/mezas3238-hue/qore-core/pull/813), [CI **#38192536589**](https://github.com/mezas3238-hue/qore-core/actions/runs/38192536589): **16 tests + 2 jobs PASS**, 24 fechas congeladas de comparación punto en tiempo, **24/24 comunicados reales, 23/24 M1 completas** (2017-03-15 parcial), artifact [#11722106398](https://github.com/mezas3238-hue/qore-core/actions/runs/38192536589/artifacts/11722106398). **Consenso CPI PIT anterior (T−24h/T−5min) no verificado, ni doble proveedor independiente, ni spreads/fills CPI del broker**; Trading Economics PIT existe documentalmente, pero endpoint histórico y `LastUpdate` no prueban vintage pre-release y licencias/demos no comprobadas. Ventana **08:35→09:05 NY** fijada solo para *sourcing de costes*, NO señal probada.
- **Power teórica** con 113 eventos nominales independientes y alfa bilateral 5%, meta 80%: `MDE≈2,8016σ/√n`. σ hipotética 20bps ⇒ MDE **5,27bps**; σ 40bps ⇒ **10,54bps**. Si efecto verdadero 5bps: potencia teórica **75,7% vs 26,4%** respectivamente. No se midió σ real del estimando neto. Un `CI` cruzando 0 si la muestra no alcanza potencia debe clasificarse **INCONCLUSIVE_UNDERPOWERED**, NO `NO_EDGE`. Con efecto 3bps la potencia no es <15% *en ambos casos*: ~36% σ20 y ~13% σ40.
- **DECISIÓN ACTUAL** [PR **#814**](https://github.com/mezas3238-hue/qore-core/pull/814): `EVENT_MACRO_EXECUTION_CLOSED_BY_RISK_POLICY` para nuevas estrategias QORE Native. Es **política de no operar shocks macro programados**, **NO falsación del mercado, NO prueba empírica de spread 20–50 puntos ni inevitabilidad de stops**. G0/G0B permanecen auditables para proteger posiciones usando calendario as-of; **no seguir gastando rondas en compra de consenso CPI/spreads para abrir G1** salvo cambio explícito de política. `G0C`/`G0D` quedan archivados/diferidos. **No aplicar el veto automáticamente a traders no Native ya en producción**.
- Fuente oficial [BLS CPI releases](https://www.bls.gov/bls/news-release/cpi.htm). Datos de calendario histórica son conocidos ex post, no prueba de calendario publicado un día antes. Para reglas no-news backtest habría que recuperar fuente/timestamp histórica del calendario antes del anuncio, o tratar blackout retrospectivo como sensibilidad marcada.

## 5. Problemas técnicos encontrados y resueltos (evitar perder semanas)

1. **BLS index ≠ comunicado efectivo.** G0 verificaba calendarios; se creó G0B que lee archivo original y encabezado. Primera versión del parser rechazó HTML CPI **largo** al intentar leer todo el release, daba falsos `NO_MATCH`; se cambió a leer **prefijo de cabecera**. Archivos antiguos tenían **Windows-1252 con en-dash** en título CPI; parser UTF-8 descartaba injustamente. Formato de 2022 a veces no incluía día de semana en frase de embargo. Correcciones técnicas documentadas y tests: 119/119 finales, sin cambiar evento ni PnL.
2. **cTrader OAuth DEMO / broker identity.** Token anterior inválido, refresh en RAM invalidaba posibilidad de recuperar estado seguro. La rama nueva IC Markets no rota tokens; al inicio brokerTitleShort ausente y permisos VIEW rechazados por cliente CIBO que asumía TRADE. Se añadió **adaptador de histórico aislado** sin órdenes. Validar nuevo run antes de anunciar descargas.
3. **H4/D1 mal interpretado a partir de M5.** El criterio 48/48, 288/288 UTC cuenta minutos continuos pero índices/metales tienen pausas de sesión; cero D1 completos no significa feed defectuoso. Necesario calendario de sesión/broker antes de evaluar tendencias H4/D1.
4. **Gran muestra de barras ≠ N efectivo de trades.** DRIVE ~2547 días con datos M1 10Y; eventos CPI 119 releases, no millones de muestras. RESET M1/M5 mismo mecanismo y fechas, no experimentos independientes. Corrección por ventanas, símbolos y pares; no escoger mejor posterior.
5. **Costes desconocidos.** La fuente OHLC provider M5 o M1 no demuestra BID/ASK de entrada ni profundidad/slippage. No codificar `cost=0`; ni asumir «futuros 5× más baratos» a partir del tick. Una comparación CFD NAS100 vs futuros NQ/MNQ requiere proveedor/broker futuros, BID/ASK, comisiones, roll, márgenes, valor de tick, acceso operativo y ejecución comprobada. Es **proyecto nuevo de infraestructura**, no atajo al edge.
6. **Repos múltiples de investigación / PRs DRAFT.** PR #811 (captura) está basada en rama `research/qore-native-ctrader-demo-eurjpy-usdchf-m5-20261011`, mientras PR #816 (12 G0) deriva de #814 (política Native). **Son ramas hermanas/no integradas**: una PR separada no queda mágicamente disponible en otra. Usar rutas completas con ref; nunca asumir que `main` tiene estos archivos.
7. **Conocimiento temporal**: NY, London, UTC y broker son zonas diferentes, DST histórico importante. Identidad de candle abierta y última confirmación causal deben registrarse; no construir indicadores de swing, régimen o forecast con velas futuras, revisiones publicadas más tarde o `LastUpdate` post-release.

## 6. Próxima misión del arquitecto — secuencia concreta y puerta de salida

### P0 — Empalme, trazabilidad e integridad ya lograda (NO rehacer)

- [ ] Leer este handoff y los PR #814/#816/#811, Issue #815, y auditar que la rama correcta sigue válida sin afectar otras líneas.
- [ ] Verificar en GitHub la ejecución **#38193802541** y sus **21 jobs por símbolo**. Estado visto en la entrega: **QUEUED**; si tiene nuevos artefactos, registrar lista de símbolos y validarlos G0 por separado; si aún no, **trabajar exclusivamente los 12** y no intentar renovar OAuth o lanzar duplicados. Criterio **21 completados** = 21/21 artifacts provider-native M5 10Y + 11 hashes/raw anuales cada uno, 0 duplicados, timestamps/rangos, catálogo IC Markets DEMO acreditado, no solamente matriz verde. Después anunciar cohorte B.
- [ ] Registrar manifiesto de cohorte A (12) en issue #815 con el artifact G0 #11723327973. No mover originales ni abrir OHLC económico para inventario.

### P1 — Cerrar SEMÁNTICA de sesiones y costos de los 12

- [ ] Por mercado, recuperar **calendario comercial del proveedor histórico** (si fuente cTrader DEMO original no es IC Markets confirmado, distinguirlo); horarios semanal/feriados/interrupciones/rollover, DST NY/broker, zonas de pausa. Separar `EXPECTED_MARKET_CLOSED` vs `UNEXPECTED_FEED_GAP` sin rellenar artificialmente.
- [ ] Construir barras H4/D1 **únicamente de velas M5 confirmadas** y reglas de sesión/rollover preregistradas; diferenciar barra diaria broker de UTC calendario. Si una barra H4 no tiene cobertura esperada, `PARTIAL` con causa. Conservar sesiones efectivamente negociables para metales/índices; exigir suficientes H4/D1 confirmadas por símbolo. **Esto sigue siendo G0 de fuente**, sin PnL.
- [ ] Investigar acceso a costes **en el mismo instrumento, broker, hora y lote**: spread BID/ASK histórico, comisiones RT, slip, tick/lot/notional/currency, latencia, swap para multiday y política de gaps. Emitir estados `EXEC_COST_VERIFIED/LOWER_BOUND_ONLY/MODEL_NOT_VALIDATED/COST_UNKNOWN`; datos median/mid-OHLC no sustituyen BID/ASK. Si ningún histórico de spread es accesible, pedir al propietario decisión de financiación/dato o **limitarse a GROSS_EXPLORATORY**; NO atribuir rentabilidad certificable.
- [ ] Proponer contrato causal de **abstención NEWS** en Native: calendario programado conocido as-of (no fecha reconstruida hoy), riesgo de posiciones abiertas, 30 min antes/60 min después **hipótesis de exclusión** pre-registrada que todavía debe simularse/validarse; un evento imprevisto necesita gobernador de riesgo independiente. No escribir filtros en producción.

### P2 — Una hipótesis H4/D1 nueva, desde mecánica económica

- [ ] **Elegir UNA clase/símbolo por mecanismo antes de mirar PnL** dentro de los 12 actuales; justificar horizonte **varias horas/días** (p. ej. persistencia de tendencia por riesgo/regímenes en FX líquido) mediante fuente económica primaria; comparar con baseline idéntico en tiempo/capital/riesgo, no con precio 0.
- [ ] Pre-registrar: régimen pre-decision basado solo en velas cerradas y ATR rolling pasado, entrada/salida FIRST-ONLINE, dirección, invalidación/stop, target/time-exit, no-news, prioridad de conflictos, riesgo, costo y slippage, N efectivo y umbral de beneficio neto, calendario vs data splits y embargo. Declarar **qué variable depende del modelo** antes de resultados; no permitir «pruebo 12 símbolos × 5 horarios × 3 stops» sin corrección familywise/FDR/holdout.
- [ ] Power primero: detectar edge **neto económicamente suficiente** contra desviación σ del **estimando** (no volatilidad de vela). Fuente de σ desde desarrollo o literatura externa, no validación sellada; bajo muestreo semanal/por régimen y clases correlacionadas. Si n efectivo impide demostrar ventaja mínima, `NOT_WORTH_G1_UNDERPOWERED` — no quemar holdout.
- [ ] Ejecutar G1 gross/NET **solo si** fuente/broker/sesión/costos/Power gate pasan y prereg congelado con SHA anterior al output. Usar diseño cronológico development→validation→OOS virgen con tratamiento de independencia entre activos y noticias. Documentar falsaciones, resultados negativos, CI, PF, Sharpe/Sortino, DD/R, skew/tail, margen-coste, frecuencia y capacidad en condiciones reales.
- [ ] Si una prueba falla `DEV_NO_SUPPORT`, NO optimizar el mismo ensayo después de observarlo; nueva hipótesis = nueva razón económica, nueva familia de ensayos documentada y OOS preservado.

### P3 — Cuando los 21 nuevos se descarguen

- [ ] Cambiar registro `DOWNLOAD_PENDING` a `SOURCE_CANDIDATE` por cada símbolo con archivo real y SHA verificable. Correr **G0 de captura separado por símbolo** con las mismas invariantes de 12 y adjuntar índices/años/alias proveedor, broker y diferencias de sesión; no usar otra cuenta para fusionar retazos históricamente incompatibles.
- [ ] Detectar problemas de disponibilidad diferencial por clase de activos, session clock, gaps de feriados, cobertura aparente «10Y» incompleta (primera/última barra) y densidad; no calificar `INVALID` por sesiones cerradas.
- [ ] Fijar nuevo universo y dividir en clases / exposiciones USD/JPY, correlación de índices/FX, metal vs dollar antes de cualquier ampliación económica. Los nuevos 21 no deben funcionar como «segunda oportunidad» para buscar el mejor resultado de una regla fallida sin control de multiplicidad.
- [ ] M1 de **24** instrumentos continua pendiente como segunda fase: nunca declarar que 33 símbolos ya tienen M1 porque los 21 nuevos recibieron M5.

### P4 — Certificación progresiva del sistema Native

- [ ] Si hay edge demostrado: convertirlo en identidad Trader separada, con cognitiva market/session/execution y veto causal, riesgo soberano QORE/CIBO, gestión de entradas/salidas/posición verificable, auditoría de latencia y fricción, simulación de fill realista y engine FIRST-ONLINE.
- [ ] WFO/holdout aún no usado, bootstrap/Monte Carlo/stress, Drawdown, PF, Sharpe, Sortino, densidad, continuidad régimen, fallos de liquidez, supervivencia a stop, escenarios adversos, portfolio factor concentration, paper supervisado y capacity antes de *cualquier* ascenso.
- [ ] CIBO y Shared podrán integrarse **solo después** de congelar traders certificados y con autorización específica. No reclamar tres si uno no se certifica. Toda ampliación tiene que ser autónoma económicamente.
- [ ] Informar al Owner resultados en lenguaje de certeza: **datos probados, barreras reales, edge soportado/no soportado, insuficiencia de potencia, bloqueo de infraestructura, candidatos pendientes**; nunca mezclar GREEN G0 con victoria económica.

## 7. STOP/GO del siguiente arquitecto en una tabla

| Etapa | Condición mínima GO | Si falla |
|---|---|---|
| Usar 12 originales para *sesiones/costes* G0 | 12/12 SHA + UTC originales verificados ✅ | Reproducción sólo si difiere SHA |
| Calificar H4/D1 como *broker bars* | Calendario sesión/DST/rollover verificado ❌ | PENDING / no D1 inventado |
| Calificar coste neto | BID/ASK + comisión + slip fuente trazable ❌ | `COST_UNKNOWN`, sólo gross |
| Ejecutar primer G1 normal | UNA hipótesis prereg + control + N/power + reglas causales y costes ❌ | `NOT_AUTHORIZED` |
| Integrar 21 M5 | 21 artifacts, años, hashes/identidades broker validas ❌ | `DOWNLOAD_PENDING` |
| Integrar M1 33 | Faltan 24 M1 10Y ❌ | `M1_PARTIAL_UNIVERSE` |
| Operar macro CPI | CERRADO por política Native ❌ | No abrir G1 CPI |
| Certificar trader | Edge neto/OOS robusto + DD/capacity/riesgo + autorización ❌ | `ZERO_CERTIFIED` |

**Importante:** `❌` en esta tabla significa «no demostrado a la fecha del handoff», no «demostrado imposible».

## 8. Mapa GitHub y commands/artefactos de continuación

**Ramas independientes actuales al handoff**:
- `research/qore-native-no-news-normal-regimes-policy-20261011` → [#814](https://github.com/mezas3238-hue/qore-core/pull/814) política risk Native;
- `research/qore-native-existing12-m5-g0-normal-regimes-20261011` → [#816](https://github.com/mezas3238-hue/qore-core/pull/816), **SOURCE_G0_PASS 12/12**, base de **ESTE handoff**;
- `research/qore-native-universe-33-icmarkets-ctrader-capture-20261011` → [#811](https://github.com/mezas3238-hue/qore-core/pull/811), adquisición de 21 **no embebida en esta rama**; usar workflow/sha y artefactos desde ese ref;
- `research/qore-native-magnitude-gate-event-families-20261011` → [#806](https://github.com/mezas3238-hue/qore-core/pull/806), magnitude y RELATIVE;
- `research/qore-native-drive-nas100-open-continuation-g1-20261011` → [#805](https://github.com/mezas3238-hue/qore-core/pull/805) DRIVE no support;
- `research/qore-native-reset-fix-g1-execution-20261011` → [#802](https://github.com/mezas3238-hue/qore-core/pull/802); `research/qore-native-reset-fix-g2-m1-exploratory-20261011` → [#804](https://github.com/mezas3238-hue/qore-core/pull/804);
- `research/qore-native-event-macro-cpi-g0-source-20261011` → [#807](https://github.com/mezas3238-hue/qore-core/pull/807); `research/qore-native-event-cpi-g0b-archive-release-check-20261011` → [#810](https://github.com/mezas3238-hue/qore-core/pull/810); `research/qore-event-cpi-pre-g1-feasibility-power-20261011` → [#813](https://github.com/mezas3238-hue/qore-core/pull/813).
- `research/qore-native-london-economic-pivot-20261011` → [#809](https://github.com/mezas3238-hue/qore-core/pull/809), Londres propios componentes.
- **ESTE handoff:** `research/qore-native-master-handoff-12-first-33-roadmap-20261011` deriva del HEAD de #816 y conserva todo el G0 12. Los PR paralelos no quedan fusionados.

**Comprobación inicial cada sesión:** consultar en GitHub `/repos/mezas3238-hue/qore-core/actions/runs/38193802541`, `/pulls/811`, `/pulls/816`, `/issues/815` antes de dar por terminado un download; obtener `actions/runs/{run_id}/artifacts` y verificar SHA de los resultados. Los archivos GH Actions están sujetos a **retención**, no asumir permanencia ilimitada: para evitar pérdida de testigos preservar hashes/manifiestos y considerar depósito de investigación inmutable/permitido sin publicar credenciales o cotizaciones licenciadas. La evidencia científica debe ser reproducible por SHA, período y fuente, no solo screenshot.

**No se requiere nuevo backtest, no se requiere pedir al Owner repetir los 12 símbolos.** El siguiente arquitecto arranca en P1 con el G0 original ya GREEN; la captura de 21 continúa paralelamente.

## 9. Comunicación obligatoria del siguiente arquitecto

Al empezar, anunciar:
1. «He leído el handoff y contrastado #814, #816, #811 y #815; **12 M5 G0 verificados**».
2. «La descarga de los 21 está [estado REAL revisado en Actions], no asumida».
3. «Mi primera ejecución será cerrar fuentes de sesiones/costes/no-news as-of y **preregistrar UNA hipótesis H4/D1** solo cuando haya suficiente evidencia de capturabilidad/potencia».
4. «No he modificado producción ni usado PnL/holdouts no autorizados».
5. «DeepSeek puede revisar supuestos, pero la verdad primaria es código/manifest/artefacto con SHA».

**Handoff preparado para continuidad de QORE Core en GitHub.** FIN.
