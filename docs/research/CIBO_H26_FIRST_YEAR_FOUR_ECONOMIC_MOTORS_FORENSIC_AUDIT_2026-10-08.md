# CIBO H26 — AUDITORÍA ECONÓMICA DEL PRIMER AÑO / CUATRO MOTORES

**Fecha 2026-10-08. Estado: datos forenses confirmados; replays ablativos H26 en ejecución. RESEARCH ONLY.**

## Pregunta del propietario
¿Por qué USD60 generan solamente USD408,14 netos dentro del primer año del replay original? ¿Están funcionando o limitando el rendimiento los cuatro motores `SIZING`, `CIBO_COMPOUND`, `COMPOUND_PORTFOLIO`, `ADAPTIVE_LEVERAGE`?

La copia auténtica del CIBO canónico se hereda de H25 y el estudio focaliza el período **2019-07-01 a 2020-07-01, UTC**, contabilizando cierre de trades ya descontados costos de provider original. No reemplazar el CIBO ni inventar resultados. Todos los motores son parte de la misma cuenta, **no cuatro ganancias separadas**.

## Evidencia inequívoca H25 (ejecución GH 37785232285)

- Cuenta inicial USD60, resultado neto del primer año **USD408.141848879**, saldo liquidado USD468.141848879, 1,109 operaciones cerradas.
- Ganancia neta de MEDIUM: **USD209.184183226**, 954 operaciones; 891 de ellas con multiplicador **1x**, 47 a 2x, 16 a 3x (93.3962% de MEDIUM a 1x).
- Ganancia neta de ATTACK: **USD198.957665653**, 155 operaciones; primera actividad en **septiembre de 2019**, sin ATTACK ni julio ni agosto. Leverage de ATTACK año 1: **mediana 3x, media 3.974x, máximo 19x**, por mucho inferior al máximo nominal 10,000x. ATTACK perdió ~USD1.73 acumulados durante el primer semestre.
- Primer mes, 83/83 entradas MEDIUM, ninguna ATTACK. Stop-risk mediano **USD0.69**, solo 2/83 operaciones con stop-risk ≥USD3 (objetivo monetario 5% sobre capital inicial USD60). El costo de provider (comisiones modelo original) del primer mes fue ~USD7.4086.
- En los 12 meses, mediana stop-risk por trade USD0.96112, y USD125.65940 de costo provider; no equivale a USD14/lot FundedNext.
- Sizing está activo: total tres años 2,520 llamadas, 1,922 intensidades 1x registradas en distribución de sizing nativo, 585 binds MEDIUM al límite de intensidad cuando DD >=5%. El año primero estuvo mucho más concentrado en 1x.
- CIBO Compound, activo: 2,520 liquidaciones MEDIUM en todo el replay; en H21 distribución de ganancias netas distribuibles **50% Banco soberano y 50% portafolio**. La distribución cumple el piso soberano; no puede retirarse sin una nueva prueba de solvencia.
- Portfolio Compound: 3,305 llamadas, colchón ATTACK disponible en 860 epochs; banco de financiación y márgenes internos restringen repetidamente actividad; no inventar que restricciones = error.
- Adaptive Leverage: 862 evaluaciones en 3 años, 848 entradas ATTACK; leverage seleccionado media **7.345x**, máximo **299x** en 3 años, mientras año primero media ~3.974x y máximo19x. Los límites económicos se aplican.
- Los cuatro motores son funcionales/ejecutados según sensores. La incapacidad de llegar a 5% efectivo de stop por operación en todas las señales es una **brecha entre target nominal y riesgo aplicado**, no prueba de que la cognitiva esté apagada.
- El crecimiento del primer año se aceleró en **marzo 2020 +USD192.67**; antes experimentó meses negativos y casi no activó ATTACK.

## Experimento científico H26 iniciado

Workflow: `.github/workflows/cibo-trader-lab-h26-four-economic-motors-first-year.yml`; script `scripts/cibo_h26_first_year_four_motor_attribution.py`. GitHub Actions [run 37790775732](https://github.com/mezas3238-hue/qore-core/actions/runs/37790775732).

Se ejecutan **5 replays completos independientes de 3,368 entradas** cada uno:
1. `FULL` H21 clon canónico: risk 5% nominal, bootstrap cushion 50%, adverse loss-cut −0.20R.
2. `WITHOUT_SIZING` motor Sizing incremental desactivado.
3. `WITHOUT_CIBO_COMPOUND` redistribución/reinversión MEDIUM desactivada.
4. `WITHOUT_PORTFOLIO_COMPOUND` disponibilidad incremental del colchón ATTACK desactivada.
5. `WITHOUT_ADAPTIVE_LEVERAGE` motor de asignación ATTACK de leverage incremental desactivado.

Solo los casos 2–5 son contrafactuales de investigación. **Nunca** despliegan una nueva estrategia ni cambian CIBO original. Exactamente 3,368 decisiones, mismas entradas y datos; se agrupan **recibos de salida liquidada en primer año** y se auditan DD completo 3 años y banco. No sumar deltas `FULL - WITHOUT_X` como ingresos independientes ni afirmar causalidad separable sin interacciones.

**Estatus de los cuatro contrafactuales: espera de resultados validados antes de interpretar**. Prohibido suponer que eliminar restricción = multiplicar capital; puede romper DD y banco.

## Barreras de certificación

- H21 DD máximo **34.3537%**, límite dueño máximo **25%, ideal20%**, y 3,368 señales; banco interno sin infracción (margen real de bróker no probado).
- Se deben realizar tests de sensibilidad de margen y lote mínimo reales, spread/slippage y fechas OOS cerradas antes de certificar retorno financiero real; CIBO original USD60 y fee modelo original no es el funded FundedNext Stellar Instant USD2k ni USD14/lot.
- La cuenta no produce «ganancia mensual fija»: los primeros 6 meses neto USD32.393 y 12 meses USD408.142, fruto de secuencia concreta de resultados 2019–2020.

**Acción obligatoria**: extraer resultados del run H26 y actualizar este documento; diagnosticar la principal presión económica del primer año con los resultados ablation verificados y luego formular experimentos sobre RISK BUDGET eficaz que preserven piso soberano y 25% DD. No modificar producción ni ramas de otros arquitectos.
