# QORE Native LONDON-REENTRY G1 — experimento DEV congelado antes de leer retornos

Fecha preregistro: **2026-10-11**. Línea propietaria exploratoria `QORE_NATIVE_LONDON_REENTRY_V1`; hipótesis **participantes/flujo recurrente**, sin atribuir stops u órdenes institucionales a velas OHLC. No se trata de TTrades, ICT, VT08 ni de RESET fixing WMR 16:00.

## 1. Por qué podría existir edge y qué lo refutaría

La primera hora negociada de Londres puede incorporar flujo de cobertura o reposicionamiento: una excursión fuera del intervalo 00:00–08:00 que regresa a su interior antes de 09:00 podría tener continuación contraria neta en 09:00–11:00. **Esto es especulativo.** La prueba mide si una estructura de **reentrada** supera al mismo patrón en una hora placebo previa, y si el resultado bruto puede cubrir costes. No se observa el flujo de órdenes ni se afirma manipulación de stops. Hipótesis nula: `mean_R_London - mean_R_placebo <= 0` o `mean_R_London <= 0`.

## 2. Datos e invariantes duros

- Fuente: [cTrader DEMO original run #36079229139](https://github.com/mezas3238-hue/qore-core/actions/runs/36079229139), commit `6958ea0c4f183020b5248b413af998065c6662da`, artifacts EURJPY `10840979795`, USDCHF `10840849959`. JSON `raw-7y-base.json` con barras M5 y M15 native. SHA256 original **EURJPY** `2a3afd8075b70fd7791ffbdefb15214e7174e7be7e0367cfa49037aa6b7af3e5`, **USDCHF** `6afd148635907ba936a52c25817cacac7397de4da224a1b2581e75fa95e50edf`.
- **Franja de investigación fijada:** fechas locales `2020-09-24` inclusive a `2023-09-23` exclusiva, aprox. 3 años, `Europe/London` IANA. Nunca acceder a `opened_at>=2023-09-24T23:45:00Z` (corte reservado VT08). Aunque es DEV no virgen y no OOS nuevo, **NO reclamar G1 científico definitivo ni certificar trader**.
- Se leerán barras M5 y M15 solamente del tramo permitido; no se tocará M1, M3, H4, otros mercados ni datos sellados. **Los UTC timestamps son fuente de orden**, los horarios London se convierten correctamente a BST/GMT. Una vela `opened_at` es un intervalo [open,open+period) y solo se conoce `close` cuando acaba.
- Los archivos originales no se modificarán; solo lectura desde artifacts usando `GITHUB_TOKEN` sin cTrader OAuth. Si SHA, metadatos demo, cutoff, timezone, OHLC o monotonicidad fallan, **FAIL_CLOSED**. No ffill/interpolación.
- No establecer relación de precios EURJPY y USDCHF entre sí (mercados independientes). Los dos resultados se reportan sin seleccionar mejor par.

## 3. Reglas únicas, fijas, sin tuning ni selección posterior

Aplicar la misma receta a cada par por cada fecha laboral London. Máximo una señal por sesión por activo y rama. Sin entradas en días no laborables.

### London real (familia principal)
1. **Rango de referencia:** 96 velas M5 con aperturas locales `00:00,00:05,...,07:55`; alto `H_ref=max(high)`, bajo `L_ref=min(low)`.
2. **ATR M15 nativa y causal:** 15 velas M15 completas terminadas a las **08:00 local**, equiespaciadas 15 minutos; `ATR14=mean(max(high-low,abs(high-prev_close),abs(low-prev_close)))` de las últimas **14** M15, sin smoothing, disponible a 08:00. No usar M15 que toca 08:00 o posterior.
3. **Ventana de exploración:** 12 velas M5 con aperturas London 08:00..08:55. Exigir completitud y cerrar la vela 08:55 antes de decidir a 09:00.
4. **Señal SHORT** si `max(high_08_09)>H_ref+0.10*ATR14`, ninguna vela 08–09 rompe `L_ref-0.10*ATR14`, y `L_ref<=close_08:55<=H_ref`. **LONG** simétrico si mínimo `<L_ref-0.10*ATR14`, sin ruptura superior y close 08:55 dentro. **Si dos lados superados, cero señal: AMBIGUOUS_BOTH_SIDES.** Ningún requisito de wick arbitrario adicional ni selector por resultado.
5. **Entrada proxy:** open M5 **09:00**. **SL distancia = 1.5 * ATR14 en precio**; TP distancia = 1R desde entrada; SL y TP simétricos por dirección. `SL=` entry + 1.5ATR SHORT / -1.5ATR LONG. `TP=` entry -1.5ATR SHORT / +1.5ATR LONG. No se afirma que TP sea precio apertura de sesión. Tiempo máximo 120 minutos hasta **11:00 open** (salida por tiempo).
6. Resolver cada M5 09:00..10:55 con OHLC, **STOP-FIRST** cuando SL y TP ambos son tocados en la misma vela, y `NO FILL` no se inventa. Si un gap atraviesa SL se asume fill al stop (optimista, no ejecutable) y se explicita. Al no tocar niveles, exit 11:00 M5 open. Si falta vela del periodo o 11:00, **censurar motivo MISSING_EXIT_WITNESS** (no rellenar).

### Placebo único — MISMAS duraciones, desplazamiento -2 horas
- Referencia `22:00` del **día local anterior** hasta `05:55` (96 M5). Ventana exploratoria `06:00` a `06:55` London, decisión al cerrar 06:55; entrar **07:00**; salir por tiempo **09:00 open**. ATR14 M15 terminado 06:00; umbral .10 ATR; 1.5ATR de stop; 1R target; mismas reglas para ambos lados y same-bar-stop-first. Mismo día local que London para remuestreo, no copiar su señal ni escoger el placebo más débil. Festivos/proveedor: censura de evidencia y motivo, nunca excluir por PnL.
- Ventana placebo y Londres pueden superponerse económicamente en holding pero sus **señales son decisiones separadas, no cartera ejecutable**; comparación descriptiva causal horaria, no R neto de portafolio.

## 4. Métrica económica primaria y decisión falsable

- Unidad cada operación = retorno en `R` con riesgo teórico exacto `1.5*ATR14`, **sin comisiones ni spread por desconocer BID/ASK transaccional**. Stop `-1R`, target `+1R`; por tiempo retorno firmado `(exit-open)/distance`, no truncar salvo límites OHLC. Contar señales, fills proxy, salidas stop/target/tiempo, censura y muestras.
- **Endpoint confirmatorio DEV único**: `D = mean(R_London) - mean(R_placebo)`, con los **dos mercados** incluidos de forma equiponderada por mercado (no mejor PF). `mean(R_London)` igualmente equiponderada por mercado. Si uno carece de muestra suficiente, marcar INSUFFICIENT y no salvar con el otro.
- Bootstrap 2000 muestras de **semanas ISO** (remuestreo conjunto de días, ambos símbolos y horarios para proteger correlación), semilla `941102`, percentil CI95 para D y meanR. No reoptimizar parámetros, no restar costes del placebo para elegir ganador.
- Umbral mínimo antes de evaluar: >=50 operaciones **en cada activo en la ventana Londres** y >=50 **en cada activo placebo**; en otro caso **UNDERPOWERED / NO GO**, aunque PF parezca alto.
- Veredicto `DEV_GROSS_POTENTIAL` SOLO si número suficiente, `CI95(D).lower>0`, `CI95(meanR_London).lower>0`, y `meanR_London` **positiva para CADA mercado**. Cualquier otra cosa `DEV_NO_SUPPORT` o `DEV_UNDERPOWERED`. Este umbral NO compensa la exploración previa en otras estrategias: **no es p-valor de familia libre de sesgo**.
- Sensibilidad fija no ejecutable: `R_London` menos `0.05R`, `0.10R`, `0.20R`, `0.30R` de coste **ilustrativo por trade**, no afirmar coste real. Si bruto potencial y 0.1R ya anula, `COST_FRAGILE`. Calcular PF descriptivo bruto y a 0.1R, muestra, drawdown secuencial R **solo de simulación de señales individuales**, y conteos de semanas/por año. El PF no es mecanismo causal ni certificado.
- Diagnósticos secundarios: no interpretar `H_ref` como stop orders, comparar long/short descriptivos, conteos de faltantes y DST, trades por año, distribución del rango/ATR; **prohibido cambiar SL/TP o escoger hora ganadora**.

## 5. Contrato de parada y autoridad

Una sola prueba principal 2020-09-24..2023-09-22 y dos instrumentos fijos. Si falla, **NO barrer 96 variantes, no pivotar a otra hora a partir de P&L, NO optimizar.** Mantener tanto resultados malos como buenos en issue #789. Si pasa en bruto, falta: costes transaccionales auténticos IC Markets bid/ask y slippage, test estrés, datos fuera de muestra realmente nuevos y ejecución real sin supuesto de fill. **0 traders certificados, sin VPS, sin live, sin modificar CIBO ni otros traders.**

Orden: `PREREG_COMMIT` → tests y motor causal → workflow GH Actions offline → artefactos por símbolo + agregado con SHA → dictamen vinculante. Este documento no debe editarse para acomodar resultados.
