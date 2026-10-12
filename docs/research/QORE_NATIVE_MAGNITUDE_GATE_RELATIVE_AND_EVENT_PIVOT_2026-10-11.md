# QORE NATIVE — GATE DE MAGNITUD ECONÓMICA Y REORIENTACIÓN A EVENTOS

**Fecha 2026-10-11 · DECISIÓN DE RESEARCH GOVERNANCE · PRE-RELATIVE, PRE-EVENT-OUTCOMES.** No se ejecuta ningún test nuevo de retornos. Este documento NO reabre los preregistros ni los resultados ya consumidos de RESET y DRIVE.

## 1. Diagnóstico conjunto, sin falsa independencia

| Experimento ya consumido | Estimando primario | IC95 % |
|---|---:|---:|
| RESET G1 EURUSD M5 (#802) | −0,691910 bps | [−1,935366;+0,547365] bps |
| RESET G2 EURUSD M1 (#804) | −0,520534 bps | [−1,382368;+0,375944] bps |
| DRIVE G1 NAS100 M1 (#805) | +0,586574 bps | [−2,051465;+3,251739] bps |

Los tres **no demostraron edge diferencial contra su control preregistrado**. RESET G1/G2 **no son ensayos independientes**, comparten casi todas sus fechas y mecanismo. DRIVE define otro estimando, control y mercado. **No meta-analizar D de cada experimento** como tres mediciones homogéneas ni convertir 3.5 millones de velas en 3.5 millones de ensayos independientes: muestras efectivas del orden de ~2450 a ~2550 fechas, con dependencia semanal. `CI95 includes 0` no significa `edge exactamente 0` ni prueba universal de imposibilidad, pero sí `NO PROMOTION`. Las señales netas no se han medido.

Hipótesis de trabajo actual: explorar diferencias económicas **materiales respecto de costes** (y no meras diferencias de signo) antes de autorizar nuevas familias. No asumir como coste verdadero un rango genérico 0,3–2 bps; se debe medir o declarar `COST_UNVERIFIED` para cada instrumento/cuenta/hora/leg.

## 2. Regla preregistrada de magnitud para RELATIVE (primaria y única)

> **RELATIVE solo puede pasar de evidencia descriptiva a candidato económicamente investigable si, en una cartera de dos piernas normalizada al nocional bruto y con costes completos verificados antes de los resultados, la mejora bruta media frente al control emparejado es al menos 3× el coste conservador de ida y vuelta de ambas piernas, el límite inferior de su IC95 % supera +2 bps y el límite inferior del retorno bruto absoluto supera el coste de ida y vuelta; de lo contrario STOP sin ajustar pares, betas, umbrales u horizontes.**

Formalización para eliminar unidades ambiguas, antes de resultados económicos:

- Retornos `r_A`, `r_B` en **bps del instrumento** sobre precios nativos y un hedge ratio `β_t` conocido estrictamente ANTES de la entrada. Retorno de la posición cash-neutral idealizada `G_t=(s_t*(r_A,t−β_t*r_B,t))/(1+abs(β_t))`; este denominador normaliza al **nocional bruto**. La fórmula es aproximación de retornos logarítmicos y no reemplaza PnL real de contratos, conversión ni margen. `s_t` debe conocerse as-of, no construir señal de cointegración ex post.
- `c_A,t`, `c_B,t` son bps del nocional de cada leg de **coste ROUND TRIP** completos (diferencial de spread de entrada/salida, comisión, deslizamiento, financiación/rollover si corresponde). `C_t=(c_A,t+abs(β_t)*c_B,t)/(1+abs(β_t))`; escenario conservador de los dos legs. Si costes por fecha son heterogéneos usar agregación especificada antes y test de estrés de costes a 1×/1,5×/2×. Una cotización actual no demuestra el spread histórico de 2015.
- `Δ_t=G_t−B_t`, donde `B_t` es benchmark preregistrado, **mismo reloj, riesgo y nocional bruto** y sin optimizar la elección posterior. No mezclar retorno del residual desnudo con retorno de estrategia. Se necesita estimador pareado con bootstrap de día/semana y corrección de multiplicidad si se inspeccionan varios pares.
- **GATE_RELATIVE_MAGNITUDE** exige simultáneamente:
  (i) `mean(Δ)>=3*C_RT_conservador`;
  (ii) `LCB95(Δ)>+2bps` (estrictamente, no solo IC que no cruza cero);
  (iii) `LCB95(G−C)>0bps` (coste observado modelado en cada trade; no `LCB(G)-C` si C varía sin concordancia);
  (iv) identidad de precios/contratos, ambas piernas y tiempo de información as-of verificados;
  (v) gate de potencia/muestra preregistrado y corrección de pruebas múltiples, además de futura verificación independiente OOS antes de certificación.
- **SIN EVIDENCIA DE COSTES DE AMBAS PIERNAS = `GATE_NOT_OPEN_COST_UNKNOWN`**, no usar C=0, no etiquetar NO-EDGE ni autorizar ensayo económico definitivo. Si la economía se ejecuta en M1 sin spread, solo `GROSS_EXPLORATORY` con fallo de puerta de promoción. Ninguna magnitud artificialmente fijada a una libra de contratos/FX delta diferente.
- Esta regla no da autoridad para abrir tres pares y escoger el mejor; pares EURUSD/GBPUSD, AUDUSD/GBPUSD y AUDJPY/GBPJPY de #794 continúan **censo de sincronía G0 únicamente** hasta fijar un único par/criterio pre-retornos.

La exigencia `3×cost` no se interpreta como garantía de rentabilidad. El **LCB de delta > +2bps** es una barrera de materialidad propuesta por el propietario; no es una constante universal del mercado ni un umbral de certificación suficiente. Si otra familia usa marcos de días/semanas, debe usar costes y bps coherentes con ese horizonte y retención.

## 3. Puerta previa: decidir si abrir RELATIVE o pivotar

**No ejecutar RELATIVE G1 por inercia.** Antes, el investigador debe producir exclusivamente un expediente `GO / BLOCKED_COST / BLOCKED_SOURCE / STOP_FAMILY` sin leer resultados de retornos, con:
1. Fuente y estimación defendible del **coste completo de las dos legs** para la cuenta cTrader/broker, horarios y tamaño; con timestamp de validez, distinción entre coste observado, tarifa y escenario de estrés.
2. Horizonte económico y escala esperada documentada **ex ante** (un mecanismo, una cartera, una unidad bps). El evento `r_A-r_B` que aparece por construcción no se confunde con beneficio capturable.
3. Auditoría de disponibilidad minuto común por año y contigüidad, hedge ratio rolling estimado solo en el pasado, posibilidad de no reversión por ruptura estructural, sesgos de calendarios, y un holdout temporal de verdad no examinado.
4. Evaluación de potencia para detectar **2bps por encima de cero con IC inferior positivo** o el mínimo `3*C`, sin preselección de pares por retornos realizados.
5. Si alguno falla, **NO backtest económico para forzar tres traders**. Estado antes de este gate: `RELATIVE_ON_HOLD_MAGNITUDE_AND_COST_SCREEN`.

## 4. Nuevas familias basadas en eventos (INVESTIGACIÓN DE FUENTES, no promesas de decenas de bps)

Se exploran, con prioridad según datos realmente disponibles y vínculos entre evento y subyacente, no según bps asumidos:

| Familia | Fuente verificable previa | Ventaja posible | Bloqueo fundamental |
|---|---|---|---|
| **Macro programado** (primera opción para un G0 nuevo) | Calendarios primarios BLS CPI y Fed/NY Fed; CIBO NAS100/USTEC, XAUUSD/FX M1 y M5 | Movimiento direccional a veces amplio tras sorpresa macro | El **calendario no predice el signo**; expectativas y sorpresa *as-of* se deben comprar/validar; publicación y latencia/spread violento; no entrar al print retrospectivo |
| **Fin de mes/trimestre** | Fecha calendario y reglas verificadas pre-evento; M1 y agregados H1/Daily de CIBO | Reasignaciones/hedging y horizontes de varios días | Rebalance real e intensidad no observados, drift, calendario y riesgo USD; controlar días normales idénticos |
| **Recomposición de índices** | Anuncios efectivos **as-of** de proveedor de índice y componentes | Tracking de indexación en constituyentes individuales | **NAS100/USTEC CFD agregado ≠ constituyente añadido/eliminado**; sin equity individuales ni anuncios históricos fechados no hay test honesto |
| **Vencimientos de opciones** | CME calendario oficial de contratos, strikes e interés abierto/posición neta historizada | Flujos de cobertura y liquidación | **Fecha de vencimiento sola no permite inferir gamma ni dirección**; cierres, trading hours, liquidación SOQ, OI desfasado y mapeo CFD/futuro |

Fuentes institucionales: [BLS CPI calendar](https://www.bls.gov/schedule/news_release/cpi.htm); [New York Fed economic calendar](https://www.newyorkfed.org/research/calendars/nationalecon_cal.html); [CME options expiry calendar](https://www.cmegroup.com/tools-information/quikstrike/options-calendar-equity-index.html); [CME Nasdaq-100 settlement](https://www.cmegroup.com/trading/equity-index/settlement.html); [S&P DJI index methodology](https://www.spglobal.com/spdji/en/methodology/article/dow-jones-bic-50-index-methodology/).

**Elección P0: EVENT-G0-MACRO-SOURCE**, inventario solo de **calendario histórico realmente conocido as-of, timestamps de publicación, expectativa disponible antes del evento, primera operación posible en CFD y coste del evento**, sin calcular ningún retorno. Incluso si el gap de precio es grande, la fracción capturable puede ser cero o negativa.

**Separación de hipótesis**: el primer candidato a investigar como fuente de datos sería **CPI estadounidense** programado 08:30 Nueva York y reacción de NAS100 (CFD `USTEC` de CIBO); es una **elección de familia y datos a investigar**, NO preregistro de entrada/dirección/ventana/target de un trader, porque aún no sabemos si existe consenso as-of y coste-evento. Elegir CPI desde una visión macro y fuente institucional y congelar que no se ampliará a NFP/FOMC sin contar multiplicidad. Los eventos de CPI son pocos (~12/año); si el objetivo de potencia es inalcanzable, declarar `EVENT_UNDERPOWERED` y no ajustar para rescatar.

**No se afirma que una recomposición, opción o publicación macro produzca siempre una ganancia de decenas de bps.** Los grandes movimientos pueden reflejar información incorporada antes de poder entrar o costes de choque. Requiere evidencia de sorpresa previa y simulación first-online, nunca OHLC con fill sintético en publicación.

## 5. Governance y continuación

- RESET G1/G2 y DRIVE G1 quedan **cerrados sin edges certificados**. Se archivan sus intervalos y source SHA; nunca retestear cambios de horario/stops/mercado por esta lectura conjunta.
- **RELATIVE** pasa a `ON_HOLD_PRE_ECONOMIC_COST_AND_MAGNITUDE_SCREEN`. No backtest sin cumplir puertas previas.
- **EVENT-MACRO G0** permitido como investigación documental/calendario/sourcing **sin PnL**. Solo tras sources, potencia y prereg específico podrá existir Event-G1.
- 3 plazas objetivo no son cuota: 0–3 sobrevivientes posibles. Ningún trader nativo, cognitiva, Shared, CIBO, QDLE, VPS, MT5, live o capital real se autoriza aquí.

**Esta PR/documento modifica exclusivamente la gobernanza científica del programa #789 y la prioridad de los expedientes #794/#792; no datos de mercado, código de traders ni procesos de producción.**
