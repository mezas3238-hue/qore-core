# HANDOFF MAESTRO — QORE NATIVE — 12 OCTUBRE 2026

**ARQUITECTO ENTRANTE: LEER PRIMERO.**
**Repositorio:** https://github.com/mezas3238-hue/qore-core  
**Rama de continuidad:** `research/qore-native-master-handoff-20261012`  
**Misión inmediata:** issue https://github.com/mezas3238-hue/qore-core/issues/815  
**Proyecto principal:** issue https://github.com/mezas3238-hue/qore-core/issues/789

## A. Visión y límites

QORE Native investiga **hasta tres traders originales** basados en mecanismos de mercado propios y distintos; NO se exige llenar tres plazas, NO clones rígidos de TTrades/ICT, NO optimización indiscriminada hasta ver PnL positivo. Todos requieren ventaja económica real y causal, costes medidos, robustez, OOS genuino, potencia, gestión de riesgo/stop, y certificación posterior. La cognitiva de los traders, Shared y CIBO no crea edge económico de la nada.

**Instrucción última del propietario:** empezar AHORA con los **12 activos ya existentes** en los históricos cTrader IC Markets; existen **otros 21 en proceso de descarga**, que se incorporarán cuando terminen y pasen validación. Total **33 planeados, no 33 verificados**. **No esperar la descarga completa** para trabajar ni inventar los nombres de los 12 sin consultar manifiestos. Trabajos SOLAMENTE en GitHub investigación; prohibido modificar VPS, MT5, LIVE, cuentas, CIBO, Shared, QDLE, production, o autorizar trader LIVE.

**Política vigente de investigación:** QORE Native **NO desarrollará estrategia de ejecución durante noticias macro de alta volatilidad**, cierre por restricción de riesgo: `EVENT_MACRO_EXECUTION_CLOSED_BY_RISK_POLICY`. Esto NO significa que CPI carezca de edge demostrado. Documento y PR https://github.com/mezas3238-hue/qore-core/pull/814 . Puede utilizar calendarios de noticias para *evitar exposición* causalmente, sin asumir que todos los anuncios no programados pueden conocerse.

## B. Referencias y ejecución histórica — HECHOS VERIFICADOS

**Programa y fuentes:** https://github.com/mezas3238-hue/qore-core/issues/789 . Archivo CIBO provider-native NAS100/USTEC M1 **3.486.929 barras** UTC 2016-09-17→2026-09-17 excl., 11 particiones anuales SHA verificadas, Actions https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334 , artefacto 10618862813, productor `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. También EURUSD histórico 10y M1. Investigación G0 9 mercados 2025-09→2026-09 (NO equiparar con los 12 del usuario) https://github.com/mezas3238-hue/qore-core/pull/791 / run 38166675573. Reader del repo `src/qore/infrastructure/trader_lab/capitalizer_cibo_m1_reader_v1.py`.

**RESET Londres FX fixing EURUSD M5:** PR https://github.com/mezas3238-hue/qore-core/pull/802 / Actions https://github.com/mezas3238-hue/qore-core/actions/runs/38175711378 . Delta bruto vs placebo −0,691910 bps, IC95 [−1,935366;+0,547365]. NO_SUPPORT a esa regla.

**RESET EURUSD M1:** PR https://github.com/mezas3238-hue/qore-core/pull/804 / run https://github.com/mezas3238-hue/qore-core/actions/runs/38184186416 . Delta −0,5205344 bps IC95 [−1,3823683;+0,3759441]. **No independiente** del M5: mismo mecanismo y gran parte de fechas. Cotejo BID/ASK tick cTrader intentó autenticación pero `CH_ACCESS_TOKEN_INVALID`, PR https://github.com/mezas3238-hue/qore-core/pull/803 . No inventar comisiones/costes históricos.

**DRIVE NAS100 M1 NY:** PR https://github.com/mezas3238-hue/qore-core/pull/805 / run https://github.com/mezas3238-hue/qore-core/actions/runs/38185670105 artefacto 11719487773. Regla congelada signo 09:30–10:00 NY y medir continuación 10:01–11:00 frente al signo del día previo; **2.547 fechas, 522 semanas**, bruto +1,11956bps, control +0,53298bps, delta pareado +0,5865738bps, IC95 semana bootstrap [−2,051465;+3,251739]. NO_SUPPORT; 9/9 tests. Prereg anterior a outcomes commit `9ebcf60628196a52cbd476e584d4f554b60af035`. No ajustar horas/stops post hoc.

**RELATIVE está ON HOLD**: documento puerta de materialidad PR https://github.com/mezas3238-hue/qore-core/pull/806 / issue https://github.com/mezas3238-hue/qore-core/issues/794 . Portfolio bruto por nocional `G=s(r_A−βr_B)/(1+|β|)`, coste RT ambas piernas `C=(c_A+|β|c_B)/(1+|β|)`, β solo de pasado, control B equiexpuesto, delta G−B. Gate predefinido: ventaja >=3× coste RT conservador, IC95 límite inferior delta >2bps, IC95 límite inferior G−C >0bps, muestra/power adecuada y true OOS. **Coste desconocido = BLOQUEADO, no C=0**. Sin abrir múltiples pares y escoger ganador.

**CPI EVENT MACRO G0 SOLO FUENTE:** PR https://github.com/mezas3238-hue/qore-core/pull/807 / Actions https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643 , calendario artifact 11720651765, presencia M1 artifact 11720822239. 11/11 calendarios BLS oficiales 2016–26, 119 fechas CPI en ventana CIBO, **113/119** con 71/71 minutos M1 de 08:20–09:30 Nueva York. 6 incompletos: 2017-01-18, 2017-03-15, 2017-04-14 (0/71), 2017-05-12, 2020-04-10 (0/71), 2022-12-13. Octubre **de referencia** 2025 no se publicó; septiembre referencia 2025 se comunicó 2025-10-24. No inventar fecha 12.

**CPI G0B ARCHIVO EFECTIVO:** PR https://github.com/mezas3238-hue/qore-core/pull/810 / exact-head run https://github.com/mezas3238-hue/qore-core/actions/runs/38191275999 / artifact 11721212991. **119/119 comunicados originales BLS archivados** cotejados por URL, fecha, referencia y embargo 08:30 ET. 11 tests, 2/2 jobs, sin datos económicos. Un calendario retrospectivo NO prueba fecha de aviso as-of.

**CPI pre-G1 potencia y viabilidad:** PR https://github.com/mezas3238-hue/qore-core/pull/813 / https://github.com/mezas3238-hue/qore-core/actions/runs/38192536589 / artifact 11722106398, 16/16 tests, 2/2 jobs. Comparación planificada de 24 fechas de consenso PIT (24/24 verificadas BLS, 23/24 con M1 completo; 2017-03-15 incompleto). **Ningún forecast real auditado, ningún spread broker histórico validado y ningún retorno económico consultado.** Trading Economics documenta PIT pero no se probó snapshot previo T−24h/T−5min en 2016–26, definición Forecast/TEForecast, revisión/LastUpdate, segundo proveedor o licencias. G1 era `BLOCKED_NOT_EVALUABLE_INFRASTRUCTURE`; después PR #814 lo cierra POR POLÍTICA, no por PnL. Ejercicio potencia puramente teórico n=113, alpha .05 bilateral 80%: MDE≈2,8016σ/√113, σ20→5,27bps, σ40→10,54bps; efecto verdadero 5bps poder ≈75,7% /26,4%. Sigma NO medida de mercado. Ventana 08:35–09:05 NY solo contrato prospectivo de sourcing de fricciones, NO señal de trading.

**Conclusión correcta:** RESET/DRIVE **no acreditaron** un edge bruto; NO está probado que existía edge y desapareció en costes. CPI solo acreditó calendario y cobertura, no edge ni imposibilidad universal de operar noticias. Todos los traders nativos **0/3 certificados**.

## C. Gobernanza más reciente y búsqueda alternativa

**PR #814** https://github.com/mezas3238-hue/qore-core/pull/814 fuente `docs/research/QORE_NATIVE_NO_NEWS_NORMAL_REGIME_PORTFOLIO_RESEARCH_POLICY_2026-10-11.md`: cerrar trading durante macro programada de alto impacto para nuevos Native por política, conservar fuentes CPI como calendario de riesgo. Candidatos de screening PRE-ECONÓMICO (NO reglas LIVE): blackout propuesto 30min antes y 60min después de eventos con horario realmente conocido as-of; ATR/volatilidad estimada solo con pasado, por ejemplo excluir >P90 pasado en misma sesión; coste completo <=10% del riesgo monetario del stop propuesto y comprobar que ampliación observada del spread no dispara stops mecánicamente; sin BID/ASK histórico o fills, clasificar UNKNOWN. Gestión de posiciones abiertas pre-evento requiere protocolo de salida y slippage causal: **no asumir stop gratis**. No aplicar a producción.

**Futuros vs CFD:** comparar MNQ/NQ/MES/ES como ruta de INFRAESTRUCTURA, no estrategia rentable probada. Tick != spread ejecutado, spread != comisión RT+slippage/roll, precio/tick bps depende índice, margen y compatibilidad broker. No asumir futures 5× más baratos ni adaptar cuentas actuales sin mandato.

**Nueva hipótesis** preferida: mecanismos económicos de regímenes normales con horizonte H4/D1 o multi-horas, que puedan producir magnitud plausible respecto a costes, con una sola configuración preregistrada y soporte de datos. No declarar que H4/D1 ya es rentable.

## D. LISTA OBLIGATORIA — PRÓXIMO ARQUITECTO

**P0 (inmediato, los 12 que ya tenemos)**
1. Leer issue **#815** https://github.com/mezas3238-hue/qore-core/issues/815, PR #814, árbol de repo, manifests/artifacts/workflows recientes de adquisición cTrader IC Markets. Encontrar **nombres exactos de 12 símbolos existentes**, y estado de los 21 en progreso; no extrapolar de PR #791 (solo 9 mercados históricos).
2. Publicar **12-ASSET G0 MANIFEST** con por cada ticker nombre canónico/broker/symbol id, familia índice/metales/FX, fuente GitHub Actions run/artifact, hash original y particiones, timeframe disponible M1/M5/M15/H1/H4/D1, inicio-fin UTC, número barras, cobertura sesiones/DST, raw vs synthetic/interpolated, huecos, duplicados, años sin archivo, calendario/cierre, status VALID/PARTIAL/MISSING/IN_PROGRESS.
3. Implementar auditor automático READ ONLY con pruebas y workflow GitHub Actions que descargue solo artefactos existentes (no operaciones ni datos nuevos intrusivos); verificar originales/manifest SHA y calidad, producir JSON/CSV/report por símbolo + artefactos y commit. Si 8 o 9 en lugar de 12 son utilizables, declararlo sin suponer otros 3.
4. No esperar a 21 activos: con los 12 identificar subuniverso apto real, periodo de desarrollo y fechas ya consumidas; documentar filtros de noticias as-of y exposición multi-mercado. NO PnL antes de prereg.

**P1 (fuentes, fricción y potencia)**
5. Inventario BID/ASK/coste del MISMO broker por símbolo y sesión, spreads con percentiles reales, comisión, slippage, swaps/roll overnight, valor tick/lot/contrato, asimetría de stop y magnitud de movimiento esperada. Se puede completar G0 de calidad sin spread, pero NO declarar sistema NET certificado con costes ausentes. No pedir ni publicar credenciales.
6. Elegir UNA hipótesis económicamente motivada de regímenes normales H4/D1 con mecanismo causal y muestras suficientes ANTES de mirar resultados. Prerregistrar símbolo representativo, long/short, trigger as-of, entrada/salida, stop, baseline horario equiexpuesto, riesgo, exposición, no-news blackout, fechas OOS congeladas, coste y potencia (MDE n efectivo) y criterio de parada. NO grid de cientos variantes.
7. Comprobar potencial de magnitud económica conservador vs costes. Símbolos nuevos no se eligen por retorno visto. Si no se puede medir con infraestructura: `NOT_EVALUABLE`, no `NO_EDGE`.

**P2 (solo después de G0, costes y prereg)**
8. Crear implementación first-online de estrategia con ledger trade-by-trade, timestamps decisión, salida y stop ejecutable, net PnL en R y bps, baseline control, PF, Sharpe, Sortino, DD, pérdida bruta, densidad, muestras cronológicas, bootstrap por bloques, multiple-testing y sensibilidad spread/slippage/ATR/regímenes. CI neta y potencia realistas. Sellar SHA/config previo.
9. Resultado NO_SUPPORT, UNDERPOWERED, SOURCE_BLOCKED o CANDIDATE según evidencia, sin mover umbral para salvar efecto. No pasar a PAPER/CIBO/Shared/LIVE antes de certificación formal y consentimiento dueño.

**P3 (cuando terminen 21)**
10. Sin duplicar descargas ni mutar otros proyectos, confirmar runs completados, manifest+SHA, calidad de cada activo nuevo y crear **33-ASSET FINAL G0**, con las mismas reglas. La cohorte 21 nueva puede ser RÉPLICA externa si estaba sellada y no optimizada; si se usan para escoger estrategia se convierten en development y requieren otro OOS. No dar por hecho 33/33 hasta verificar.

## E. Fallos críticos a no repetir

- M1 millones ≠ millones de observaciones independientes; n=trades/eventos/fechas/cluster.
- No aceptar RETEST independiente si mismo universo/periodo; RESET M5/M1 son sensibilidades de una línea.
- No usar outputs CPI del futuro o consenso retrospectivo.
- No asumir que `spread=0`, `spread normal` o OHLC mid constituye precio ejecutable.
- No inventar 12 nombres o dar por terminada la descarga de 21.
- No abrir HOLDOUT 2014–16 sellado, ni denominar OOS a 2016–26 ya inspeccionado para DRIVE/RESET.
- No optimizar a posteriori ventana, símbolo o stop para «rescatar» estrategias negativas.
- No confundir prohibición por RISK POLICY con falsación del mercado o CPI.
- No introducir cambios a otros traders/CIBO/Shared o VPS; no fusionar a main sin aprobación.
- Si el propietario dispone de DeepSeek, usarlo como auditor externo adversarial para ambigüedades, NO como fuente primaria de PnL/datos.

## F. Entregables sucesor y CIERRE

A. PR auditoría `QORE Native 12 Asset G0` con report por símbolo, SHA, cobertura, CI, gaps, validaciones y estado. Enlazar issue #815.  
B. Contrato `Broker Cost / Safe Regime / Power` por mercado antes de PnL.  
C. ÚNICO `Normal Regime H4-D1 G1 Prereg`, baseline y potencia.  
D. Solo si pasa A–C, ejecución científica en GitHub Actions y dictamen honesto con evidencias.  
E. Al completar los 21, ampliar a manifiesto 33 tras G0 exacto; no elegir winners por resultados.

**Resultado actual: 0/3 traders Native certificados, NO operación de noticias, 12 declarados como existentes aún por censar formalmente, 21 en descarga. El siguiente arquitecto debe comenzar por P0 inmediatamente.**
