# VT31 · Puerta 2: régimen condicional PIT, preregistro bloqueado

**Fecha 2026-10-13. Este archivo se publica ANTES del código/ejecución Gate2 y NO se puede modificar en respuesta a resultados.**

**Hipótesis causal:** una ventaja de predicción a +15 minutos de las señales COG+OPS originales de VT31 puede quedar oculta al promediar periodos de tendencia/rango y volatilidad alta/baja. El régimen debe conocerse **antes de comenzar** la ventana ICT, no desde la evolución posterior a la señal.

## Universo congelado e indicadores as-of

- Mercado NAS100 CFD M1 original 2023-10-01 a 2026-10-01 exclusivo, **1.059.784** velas, sha256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, artifact **11459859004**.
- Fuente de primera FVG seleccionada COG+OPS original **2.140** candidatos de **2.286** ventanas completas, ledger artifact **11657461650**, SHA256 `e9683d87f0645b488968aeb3e207347649f4e9aea5c535202ab4f024c22e7646`. Comparador raw primer FVG por ventana de Gate1 PR #910; sin modificar cohortes ni OHLC.
- Tres horas ICT en reloj `America/New_York` DST: 03:00–04:00, 10:00–11:00, 14:00–15:00; cada ventana con exactamente 60 M1 dentro de la hora.
- Para **cada ventana**, régimen calculado al comienzo de la ventana (`t` 03/10/14:00 NY) con **exclusivamente las 60 M1 inmediatamente anteriores `[t−60min,t)`** y continuidad temporal comprobada.
- `R_t = sum(abs(close_i − close_(i−1)), i=1..59)` usando esas 60 M1; `E_t = abs(close_59 − close_0) / R_t`, si `R_t>0` (sino UNKNOWN). Clasificar **TREND si `E_t >=0.35`**, en otro caso **CHOP**. Umbral operativo QORE fijado sin optimización (no doctrina ICT).
- Clasificar **HIGH_VOL** si `R_t > median(R_prev_20)` de las **20 ventanas anteriores observadas de la MISMA sesión** (la propia `R_t` aún no se incluye); LOW_VOL en caso contrario. Solo se guarda R de referencia si sus 60 M1 fueron contiguas, y de la sesión que ya comenzó; para evitar futuro, la historia se actualiza **después de clasificar el instante `t`**. Menos de 20 observaciones previas válidas: `UNKNOWN_WARMUP`; 60 M1 incompletas: `UNKNOWN_PREWINDOW`; `R=0`: `UNKNOWN_FLAT`. Nunca asignar UNKNOWN al grupo ganador.
- **Cuatro celdas fijas**, no exploración de umbrales: `HIGH_VOL_TREND`, `HIGH_VOL_CHOP`, `LOW_VOL_TREND`, `LOW_VOL_CHOP`. Población y clasificaciones anteriores a COG/FVG; no usar retornos futuros para definir régimen.

## Métrica primaria y multiplicidad

- Dentro de cada celda, **misma ventana de calendario NY**, comparar COG+OPS primer FVG seleccionado vs primer FVG raw sin selección. Para ambos: `side*(OPEN[t_confirm+15m]−OPEN[t_confirm])`, con **16 M1 exactas y consecutivas**; son relojes/direcciones potencialmente diferentes como en Gate1. `delta=selected−raw` emparejado por ventana. No PnL ni coste broker.
- Cuatro estimaciones de mejora condicional primarias `mean(delta)`; cálculo IC **98,75 % bilateral por remuestreo de semanas ISO (2000, semilla 13102026)**: Bonferroni de cuatro celdas para controlar FWER ~5% (0,05/4).
- **Criterio positivo a nivel celda** solo si n de parejas >=100, >=20 semanas ISO, `mean(selected gross)>0`, `mean(delta)>0` y **límite inferior IC98.75% del delta >0**; incluso así se considera **indicio exploratorio conjunto**, NO edge neto, y exige OOS nuevo.
- Reportar IC95% individuales descriptivos, propios y raw por celda, n, cobertura UNKNOWN y faltantes, sesiones, direcciones y desfase de inicio. No combinar celdas para seleccionar retrospectivamente aquella con mejor PnL. **No cambiar horizonte, signo, costes ni utilizar otro régimen tras resultado.**
- **No aceptar conclusión de falta de edge** si n o potencia son insuficientes; `UNDERPOWERED`, `NO_SUPPORT`, `EXPLORATORY_POSITIVE` se distinguen. La pertenencia no asegura equivalencia de timing, dirección y entrada. Para aislar COG exclusivamente faltaría ablation al mismo as-of y candidato; esta es comparación **COG+OPS conjunta**.
- Macro calendario no mezclado en esta fase (Puerta 3 separada), tampoco target DOL/SL/C2/CE (Puerta 4). El desarrollo ya es investigado: **esto es análisis exploratorio**, no afirmación confirmatoria OOS, no seleccionar favorable para producción.
- Los resultados anteriores G3 code `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` y acta `a446afa17ed6e411b8f0b6fc182b103a78959a97` son inmutables, G3 `PENDING_DUAL_SIGNATURE`; **no merge, LIVE, VPS, holdout ni órdenes.**

**Salvaguarda adicional:** filtrar por completos del 3Y, no rellenar timestamps y comprobar el resultado Gate1 total [−0.954117 pts n2140] antes de segmentar, para detectar alteración del análisis fuente.
