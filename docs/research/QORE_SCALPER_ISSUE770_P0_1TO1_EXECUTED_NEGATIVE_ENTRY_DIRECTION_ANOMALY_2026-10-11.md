# QORE Scalper — Issue #770 P0 — Auditoría REAL de entradas V49 con barreras simétricas ±1R

**Fecha:** 2026-10-11. **Estado:** REPLAY COMPLETO / ENTRADAS SIN VENTAJA DEMOSTRADA / NO PROMOVER / NO CERTIFICAR. **Origen:** [Issue #770](https://github.com/mezas3238-hue/qore-core/issues/770). Rama propia `research/scalper-p0-entry-quality-1to1-20261011`; [PR DRAFT #771](https://github.com/mezas3238-hue/qore-core/pull/771).

**Trazabilidad temporal:** preregistro previo a primer ensayo, commit `6fec1be603f4c2670a91a8120f1144a818ca345c`; source V49 run `38053946695` SHA `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`, M1 provider native run `35548099334` SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`; código de replay auditado SHA `0a7125ffaad66b4262b0f0ede58a3ced3564b1f7`. GitHub Actions [#38109948508](https://github.com/mezas3238-hue/qore-core/actions/runs/38109948508) **11/11 SUCCESS**, [artefacto consolidado #11690988906](https://github.com/mezas3238-hue/qore-core/actions/runs/38109948508/artifacts/11690988906) y nueve artefactos por mercado (cada uno registra todas las identidades fuente y ambos escenarios).

## GATE CERO — reconstrucción baseline antes del 1:1

**2876/2876** oportunidades y libros económicos inmutables reproducidos completamente desde source V49 y provider-native M1 en nueve mercados. MAX3 global de sesión/fecha seleccionó exactamente **2020**, 1167 ganadoras, 852 perdedoras, **1 flat**, gross profit +461.9427618322R, gross loss -695.2120889086R, PF 0.66446307422, DD 236.1342843563R, total -233.2693270764R, esperanza -0.1154798649R.

Censo de salidas fuente seleccionadas: **TARGET estructural 1030, STOP 609, SESSION_EXIT 381** (suman 2020); dual-touch ambiguos STOP_FIRST **3**. Beneficio medio por ganadora **0.3958378422R**; pérdida media por perdedora 695.2120889/852 = **0.8159766302R**. El 0.53R anterior era una interpretación incorrecta de target-planificado versus payoff efectivo. Solo tiene sentido la regla 51.25% break-even bruto+0.025R para ejecuciones **exactamente +1/-1** sin time stop ni censura.

## Resultados empíricos P0 — mismo 2020 A congelado, solo target cambiado a ±1R

### PURE_FIRST_BARRIER (SIN time stop; no alimentar resultados censurados)

- Intenciones **2020/2020**; resolved **1735** (TARGET **768**, STOP **967**), **285 RIGHT_CENSORED_PRICE_GAP**. No hay FIN DE FEED censor en esta muestra, pero el código lo contempla; el proveedor tiene interrupciones antes del primer contacto en 285 casos.
- STOP_FIRST dual touch **8** casos.
- Tasa target entre resolved **44.26513%**. Entre TODO el censo 2020, límite teórico inferior 768/2020 = **38.02%**, superior si los 285 censurados fuesen ganadores = **52.13%**; estas cotas NO prueban WR real, pues gaps no resueltos y capital ocupado.
- A coste **SUPUESTO** 0R: PF **0.79421**, expectancy por RESOLVED **-0.11470R**, DD salidas resueltas **201.00R**.
- A coste **SUPUESTO** 0.025R: PF **0.75547**, expectancy por RESOLVED **-0.13970R**, DD salidas resueltas **244.325R**, total RESUELTO **-242.375R**, wins 768 / losses 967.
- A coste **SUPUESTO** 0.05R: PF 0.71857, exp -0.16470R. A 0.10R: PF 0.64981, exp -0.21470R.
- Sensibilidad TARGET_FIRST para las 8 barras dual touch (NO test principal): PF hipotético 0.76970 / esperanza -0.13048R. Conclusión bruta negativa no se invierte al resolver ambigüedad favorable.
- Intervalo bootstrap de 1000 bloques de 5 jornadas para esperanza resolved con coste 0.025R: **[-0.18888R,-0.08718R]**; historial consumido, dependencias de censura, NO IC confirmatorio/OOS.

### SESSION_CAPPED_1TO1 (time stop original V49 al cierre de sesión)

- Intenciones **2020/2020**, resolved **2010**: TARGET **559**, STOP **718**, SESSION_EXIT **733**, censurados por huecos M1 dentro de sesión **10**. Same-bar STOP_FIRST **8**. La proporción TARGET 559/2010 **27.81%** NO es el win rate global, porque 733 salidas de sesión aportan beneficios/pérdidas parciales y hay 10 censurados.
- Con coste 0R: PF **0.76495**, expectancy -0.10035R/trade RESOLVED, DD **203.753R**.
- Con coste **SUPUESTO** 0.025R: PF **0.71580**, expectancy **-0.12535R/resolved**, DD **253.903R**, total **-251.94465R**, 863 ganadoras NETAS (incluye cierres de sesión positivos), 1147 perdedoras NETAS.
- Coste supuesto 0.05R: PF 0.66985, exp -0.15035R; 0.10R: PF 0.58671, exp -0.20035R.
- TARGET_FIRST 8 ambiguos costo 0.025: PF 0.73136 y exp -0.11739R (sigue negativo).
- Bootstrap 1000 × 5 jornadas: intervalo esperanza resolved a costo supuesto 0.025R **[-0.16564R,-0.08170R]**, no OOS.

**Los drawdowns de PURE y CAPPED son sobre PnL de posiciones resueltas ordenadas por exit y suponen 1R de riesgo unitario; no son un DD operable con capital finito, solapamientos de posiciones, leverage, slippage o inmovilización PURE.**

## Hallazgo adicional extraordinario: TEST DE DIRECCIÓN INVERSA — NO EQUIVALE A AUTORIZACIÓN PARA INVERTIR TRADES

Control preregistrado **same-time DIRECTION_FLIP**: para cada una de las MISMAS 2020 entradas, misma fecha/símbolo/precio/riesgo absoluto, intercambiar barreras stop 1R ↔ target 1R y LONG ↔ SHORT. **El stop nuevo no corresponde a un swing TTrades válido para la posición opuesta**; es una prueba adversarial del valor de la dirección original, NO una estrategia contrapuesta certificada.

| Comparación costo SUPUESTO 0.025R/trade resolved | Dirección original | Dirección opuesta espejo |
|---|---:|---:|
| PURE PF | **0.75547** | **1.17554** |
| PURE esperanza resolved | **-0.13970R** | **+0.08048R** |
| CAPPED PF | **0.71580** | **1.19719** |
| CAPPED esperanza resolved | **-0.12535R** | **+0.06739R** |

**2000 direcciones aleatorias** por entrada para placebo del signo del trigger, con tiempo/mercado/riesgo fijos, y misma regla STOP_FIRST: PURE mean esperanza neta aleatoria **-0.02975R**, intervalo percentiles [−0.07630,+0.01592]R; CAPPED mean **-0.02862R**, intervalo [−0.06602,+0.00667]R. La dirección original es peor que TODAS las 2000 aleatorizaciones en ambos escenarios (p unilateral de **superioridad** de la dirección original = **1.000**). Es un hallazgo grave de **posible anti-señal direccional** en V49, condicionado al replay 1:1.

**Advertencias antes de atribuir causa:** el mirror es matemáticamente complementario al bracket 1:1 con asimetría STOP_FIRST, NO demuestra que reversar en MT5 ganaría dinero ni que la dirección del autor esté mal. Comprueba solo el signo contra estos dos mismos niveles a distancias simétricas. Deben examinarse causalidad y sentido H1 bias, sweep, CISD y swing protegido, spreads físicos, cronología de simultáneas y confirmación genuinamente OOS. No ejecutar dirección inversa ni usar el resultado para ajustar reglas.

## Dictamen por algoritmo y protocolos STOP/GO

1. **La entrada H1→M15→M1 V49 NO demuestra capacidad predictiva direccional bajo barreras ±1R**: en PURE PF bruto 0.79421, en CAPPED 0.76495, ambos expectativa bruta/net supuesta negativa.
2. El signo contrario mismo momento supera favorablemente al signo V49 en datos consultados. Esto abre una **anomalía metodológica diagnóstica**, no permiso de inversión.
3. **PURE censura 285/2020 (14.11%)** por gaps y ninguna winrate incondicional debe excluirlos silenciosamente. CAPPED censura 10/2020.
4. Sin un placebo genuino de **horas de entrada aleatorias y comparables**, no puede separarse la calidad del timing frente al simple signo. El sign-flip ya revela defecto/posible sesgo direccional, pero no explica causalmente la fuente.
5. El stop swing M15 original y fuente H1 son testimonios históricos de V49; **no** están independientemente certificados al autor. M30→M3 TTrades autoral en #768 sigue línea distinta, no afectada.
6. No hay BID/ASK broker real, slippage, capital operable ni holdout independiente. Ninguna prueba autoriza entrar a LIVE/VPS/producción.

**CIERRE del test 1:1 sobre V49 con veredicto NEGATIVE_EXPLORATORY / DIRECTION_SIGN_ANOMALY**. Solicitar auditoría independiente de la política direccional y faithful first-online antes de cualquier optimización económica. Si falta potencia o censura afecta afirmaciones universales, el estado de edge de Scalper es `NOT_CONFIRMED`, no `UNIVERSALLY_REFUTED`. No abrir tuning de stop/TP basado en esta cohorte. Preservar todos los negativos. Prioridad #768 M30→M3 autoral independiente, seguida #769 esperanza condicional en nueva hipótesis y datos.

## Fuente/repositorio/artefactos

- [Run completo 11/11](https://github.com/mezas3238-hue/qore-core/actions/runs/38109948508)
- [Artefacto A=2020, dos escenarios 1:1, curvas y statistical report](https://github.com/mezas3238-hue/qore-core/actions/runs/38109948508/artifacts/11690988906)
- [PR DRAFT #771](https://github.com/mezas3238-hue/qore-core/pull/771)
- [Issue #770](https://github.com/mezas3238-hue/qore-core/issues/770)

**NO VPS / NO MERGE / NO LIVE / NO CERTIFICACIÓN.**
