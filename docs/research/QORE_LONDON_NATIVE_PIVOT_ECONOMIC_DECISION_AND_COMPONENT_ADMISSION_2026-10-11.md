# QORE LONDON NATIVE — DECISIÓN DE OWNER Y PUERTA DE EVIDENCIA ECONÓMICA

**Fecha de decisión:** 2026-10-11 · **Autoridad:** Owner de QORE · **Programa de investigación:** [QORE Native #789](https://github.com/mezas3238-hue/qore-core/issues/789) · **Estado:** `RESEARCH_ONLY / NO_CERTIFIED_TRADER / NO_LIVE`.

## 1. Decisión estratégica vinculante — CAMINO B, no réplica TTrades

**El objetivo de QORE Londres es descubrir una fuente de edge monetizable propia**, no seguir a TTrades de manera rígida. Los materiales TTrades/ICT pueden ser *fuentes de ideas* e inspiración para componentes, pero **ningún requisito del autor es criterio obligatorio** para el trader QORE, y ningún componente hereda autoridad por su autoría.

**Cese formal del track de fidelidad**: [Issue #785](https://github.com/mezas3238-hue/qore-core/issues/785) + [handoff PR #786](https://github.com/mezas3238-hue/qore-core/pull/786) + [investigación PR #788](https://github.com/mezas3238-hue/qore-core/pull/788) quedan como **archivo científico reutilizable** con resultados, bugs, código y advertencias; no se ejecutarán más rondas Gate A/B/C para probar si el trader replica exactamente el London Fractal Sep-2026. Es legítimo usar código de validación temporal SIN adoptar su lógica como estrategia. No fusionar código de réplica en producción.

**Separación estricta de tracks**:
- `QORE_NATIVE` / [Issue #789](https://github.com/mezas3238-hue/qore-core/issues/789): tres familias propias DRIVE/RESET/RELATIVE y posibles investigaciones de eventos, cada una con hipótesis económica y tests independientes. Londres **no se cuenta** como trader adicional por denominar una sesión.
- `QORE_ALPHA_V1_96` / [Issue #798](https://github.com/mezas3238-hue/qore-core/issues/798): familia VT08/M30→M3 de 96 variantes congeladas, otro prereg. **No se altera**, no se añade variante número 97, ni se importan sus PnL a este programa.
- `QORE_NATIVE_LONDON_REENTRY_G1` / [PR #801](https://github.com/mezas3238-hue/qore-core/pull/801): ensayo económico específico YA ejecutado. No repetirlo con nuevo nombre.

## 2. Contrato económico previo: responder '¿por qué pagaría el mercado?'

Una hipótesis nueva solo entra a G1 después de escribir **ANTES de consultar outcomes**:
1. **Contraparte y fuente de retorno plausible**: cuál es la fricción/exposición temporal que soporta el pago (por ejemplo flujos programados verificables, demandas de cobertura o inventario); distinguir mecanismo comprobable de cuento de 'smart money' inferido de OHLC.
2. **Predicción DIRECCIONAL y nula**: evento y estado conocidos causalmente; ventana de salida económica; variable de resultado; qué distribución debe observarse si no existe edge; cómo puede perder frente a un placebo.
3. **Contrato de precios ejecutables**: precio de entrada/salida BID/ASK, spreads, comisión, slippage, horarios de mercado, stops dobles y gaps. Sin testigos de costes, un resultado bruto es `GROSS_EXPLORATORY`, no rentabilidad validada.
4. **Magnitude gate ANTES de backtest**: estimación conservadora de roundtrip C con dos lados (o dos piernas), magnitud económicamente suficiente para cubrir el coste; como referencia de cribado de [PR #806](https://github.com/mezas3238-hue/qore-core/pull/806), `gross differential >= 3*C`. Si C no está medido, `C_UNKNOWN` y ninguna promoción económica. No importar el `+2bps` de RELATIVE a un producto con otra volatilidad sin prejustificación.
5. **Una sola instancia congelada por familia, baselines y límites**: fechas no consumidas donde sea posible, validación walk-forward con embargo si solapamiento, potencia/n efectivo por semana/día, bootstrap agrupado, IC de la esperanza neta vs control superior a 0, tests de sensibilidad y multiplicidad; **registrar TODOS los ensayos**. Un PF aislado >1.30 o `>=50 trades` NO es certificación estadística.
6. **Stop irrevocable para la instancia**: si no supera efecto bruto/control/potencia/costes, dictamen `NO_SUPPORT` o `UNDERPOWERED`; no cambiar post hoc horario, ATR, pair o stop para rescatarla.

**London 08:00–09:00 NO constituye por sí solo una hipótesis de edge**: es una etiqueta temporal. Prohibido promover un trader porque CISD/H4/POI 'se ve convincente' en gráficas.

## 3. Lo que QORE puede REUTILIZAR, sujeto a ablation

| Elemento | Fuente/origen | Uso permitido en QORE | Promoción permitida |
|---|---|---|---|
| `first_known_utc`, cierre causal y no rellenar precio retroactivo | Auditoría #788 | Infraestructura de no-lookahead / trazas por señal, independiente de la estrategia | Admisible como **seguridad**, nunca como edge por sí misma |
| Diagnóstico de rollover 17h NY y DST + calendario de minuto M1 | #788 / [CI #38173764426](https://github.com/mezas3238-hue/qore-core/actions/runs/38173764426) | Sensores de disponibilidad, censura y no-tick; no inferir Daily corrupta de 1440/1440 | Admisible para **datos**; no predictor de retorno sin experimento independiente |
| Apertura primera vela de secuencia CISD | Descripción TTrades; observador #788 | Feature descriptiva de transición, solo si secuencia se identifica as-of; jamás inferir swing por hindsight | **CONDICIONAL**: ablation baseline vs con-feature, neta costes, OOS |
| Swing protegido/POI | TTrades | Posibles candidatos de invalidación/estructura; evitar stop trasladado del autor sin economics | **CONDICIONAL**: stops y riesgo precongelados; selección no guiada por PnL |
| Dirección Daily/H4 wick/C2/C3 | TTrades | Opcionales solo cuando timing/ancla definidas por QORE y no contaminan decisiones | **EN CUARENTENA**: no bloquear desarrollo económico esperando 'fidelidad' |
| SMT/divergencia de pares | TTrades/QORE | Candidato de feature pero exige series sincronizadas y costes de varias piernas | **EN CUARENTENA**: correlación no es hedge ni predictibilidad |

**Regla de admisión:** una feature inspirada en un autor NO forma parte del motor por tradición. Solo (a) seguridad temporal/validación sin cambiar señales, o (b) ablation causal previamente registrada sobre una base que ya tiene razón económica, comparando mismo universo/días/costes para evitar sesgo de selección. Una feature que recorta muestra y mejora PF incidentalmente se rechaza si empeora expectativa neta ajustada y robustez.

## 4. Resultado económico londinense PREEXISTENTE: NO-GO, no reiniciar

La investigación nativa ya hizo la prueba recomendada, pero con *identidad exacta distinta de la réplica*:

- [PR #801](https://github.com/mezas3238-hue/qore-core/pull/801), prereg PRE-PnL commit `dfe4af6918e172843ad71c1f5a9d4d86481520be`, [GitHub Actions #38174719898](https://github.com/mezas3238-hue/qore-core/actions/runs/38174719898) **2/2 SUCCESS / 10 pytest PASS**, [reporte completo](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-london-reentry-g1-dev-20261011/docs/research/QORE_NATIVE_LONDON_REENTRY_G1_DEV_EXECUTED_NO_GO_2026-10-11.md).
- DEV 2020-09-24 a 2023-09-22, no OOS virgen, fuente cTrader DEMO archivada, **599 señales totales** en dos brazos/pares, no equivale a 599 trades Londres. Londres EURJPY **187 trades, PF bruto 0.880, mean -0.0604R**, USDCHF **216 trades, PF bruto 1.112, mean +0.05286R**.
- Media de Londres equiponderada por par `-0.00377R` **ANTES de costes**. Ventaja sobre placebo `+0.153R` con bootstrap de semanas IC95 `[-0.0068,+0.3068]`; IC95 media Londres `[-0.101,+0.090]`; ambos incluyen 0. Sensibilidad hipotética `0.10R` deja ambos mercados negativos; falta coste BID/ASK ejecutable.
- **Veredicto contractual `DEV_NO_SUPPORT`**; no escoger USDCHF ganador ni reoptimizar hora/ATR/SL/TP post hoc. Esta falsación vale para esta receta y datos; no demuestra que toda la sesión Londres carezca de oportunidades.

**Resultado estratégico:** el barrido/reentrada de primera hora NO entra a integración ni PAPER, y no renace bajo `QORE_LONDON_NATIVE` con otro nombre.

## 5. Próxima decisión de investigación: SIN abrir otro grid londinense

La cartera QORE Native #789 ya evaluó RESET G1/G2 y DRIVE G1 sin pruebas robustas de edge; [magnitude gate #806](https://github.com/mezas3238-hue/qore-core/pull/806) detuvo RELATIVE hasta conocer costes dos piernas. El G0 de [eventos CPI #807](https://github.com/mezas3238-hue/qore-core/pull/807) es fuente/calendario, todavía no señales. La misión siguiente es **confirmar primero un mecanismo económico grande** con una fuente as-of y costes identificables, no añadir un cuarto intento de sweep/ATR ni prolongar el ciclo del autor.

**Propuesta de trabajo económico abierta, SIN autorizar G1:** eventos macro verificables (CPI) en #808: recuperar consenso histórico realmente disponible antes del anuncio y testigos del coste NAS100/USTEC alrededor del release, después una sola tesis por sorpresa normalizada y horizonte preregistrados. Si no están disponibles as-of y sin evidencia de costes, `BLOCKED_SOURCE`, no inventar señales. Esta prioridad programática no convierte CPI en 'trader Londres' ni atribuye éxito antes de medirlo.

## 6. Estado final y autoridades

- `TTRADES_LONDON_AUTHOR_EXACT = CLOSED_AS_RESEARCH_PATH` **no es veredicto 'TTrades no funciona'**: solo que la réplica inequívoca no es formalizable con la evidencia actual al coste aceptable de investigación.
- `QORE_NATIVE_LONDON = ECONOMIC_RESEARCH_ONLY / REENTRY_G1_NO_GO / NO_ACTIVE_LONDON_EDGE`.
- `QORE_ALPHA_96 = SEPARATE_FROZEN_PROGRAM`; no modificar.
- `0_LONDON_TRADERS_CERTIFIED / NO_PAPER / NO_DEMO / NO_LIVE / NO_VPS / NO_MT5 / HOLDOUTS_UNTOUCHED`.
- No cambiar arquitectura CIBO/Shared/QDLE, ni utilizar holdout VT08 sellado. Ningún éxito de tests sintéticos autoriza mercado real.

**Este documento es una decisión de portfolio R&D y reutilización selectiva de componentes, NO un nuevo prereg de trading ni una autorización a ejecutar PnL.**