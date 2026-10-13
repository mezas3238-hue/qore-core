# HANDOFF MAESTRO — QORE Research Accelerator Ultra-Fast (2026-10-13)

## Objetivo y estado real

Construir y mantener CINCO CAPAS de investigación de mercados en paralelo, SIN
modificar Trader Lab ni autorizar ejecución DEMO/LIVE. La rama
research/qore-accelerator-5layers-ultrafast-20261013 contiene un MVP
ejecutable y pruebas sintéticas; NO es certificación económica. No merge sin
orden del propietario. Ningún capital real. No out-of-sample ni holdout consumido.

## Código y componentes

1. Data Lake inmutable: src/qore/infrastructure/research_accelerator/core.py.
   Manifiestos obligatorios con SHA256 de bytes CSV, fuente, broker,
   proveedor, instrumento, symbol_id, versión, zona UTC, licencia y
   provenance; importación de solo escritura inicial, revalidación cada
   lectura, verificador para CI. Datos M1 BID y ticks BID/ASK OBSERVADOS;
   prohíbe MID sintético y CSV cruzados con ask menor que bid.
   Fuentes admitidas vía adaptador CSV normalizado; integración directa
   MT5/cTrader sin exportación todavía NO CONSTRUIDA.
2. Memoria científica: memory.py. Registro JSONL append-only en disco,
   cadena SHA256, digest de configuración, SHA artefacto y código. Rechaza
   duplicados y alteraciones. Git es raíz de auditoría externa.
3. Motor ultra fast: experiments.py y ultrafast.py.
   Config JSON con nombre, horizontes congelados, umbrales de features
   OB, FVG, displacement y breaker, placebo local_extreme, seed y
   bootstrap agrupado por día. Búsqueda por bisect en timestamps,
   etiquetado lineal y salida sellada por SHA. SOLO screening
   direccional bruto BID, no PnL económico. Las features deben provenir
   de detector causal externo, cuyo contrato todavía requiere testigos.
4. Regímenes: regimes.py. Etiquetas trailing-only tendencia/rango,
   volatilidad alta/baja, opening/continuation/reversal en horario NY.
   Análisis retrospectivo informativo, no gate para la estrategia.
5. Simulador: execution.py y comando execute. CE LIMIT:
   compra solo si ASK observado <= CE; venta solo si BID >= CE;
   stop C2 más margen de un tick, target DOL, cancelación por ventana,
   cierre stop/target/tiempo, comisión por lado en puntos de precio,
   slippage adverso. UNFILLED e INCOMPLETE son estados explícitos.
   Ledger en precio-puntos por unidad; no equivale a USD, cTrader ACK
   o fills certificados. El simulador exige identidad de broker/feed/símbolo
   exacta para impedir tratar NAS100 distinto de USTEC como homólogo.

Workflow independiente:
.github/workflows/qore-research-accelerator.yml

Pruebas sintéticas:
tests/infrastructure/research_accelerator/test_research_accelerator_contracts.py

## Decisión sobre fuente canónica — PROVISIONAL, NO DEFINITIVA

La evidencia más fuerte disponible para VT31 es IC Markets DEMO
cTrader Open API USTEC symbolId 10014, recopilada en PR #899 y PR #901.
PR #901 documenta 483103 observaciones BID/ASK de lado, 30 horas de
Silver Bullet en 10 días de development. NO son tres años continuos.
Son streams separados de BID y ASK: NO importarlos como pares observados
hasta construir unión as-of, contrato de latencia y quarantine.
Datos en artefacto de GitHub Actions #11801263502, SHA ZIP:
a0cb3e62f2c889b414e7283d7d426576468e753b34f60351d0c9aa1965fc1edf.
Según PR #901 esos artefactos expiran el 2027-01-11.
El original 3Y M1 NAS100 tiene SHA de archivo fuente:
0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa.
No hay homologación formal NAS100 versus USTEC; el cruce no autoriza
PnL ni calibración de spread automático. Fuente primaria propuesta:
IC Markets DEMO cTrader para investigación condicionada a su validación,
no MT5 supuesto. No guardar credenciales ni grandes datos licenciados en git.

## Uso local o en GitHub Actions

Python >=3.12,<3.13, pip install -e ".[dev]".

Manifiesto JSON exacto:
kind (m1_bid o tick_bidask), sha256, broker, provider, instrument,
symbol_id, feed_version, timezone=UTC, timeframe=M1/TICK, provenance, license.

M1 CSV: closed_at,open,high,low,close
Quotes CSV: at,bid,ask, **ambos del mismo instante homologado**
Signals CSV: event_id,anchor_at,available_at,side,anchor_price,ob,fvg
Con features opcionales breaker y displacement de valor entre 0 y 1.
Orders CSV: event_id,known_at,activated_at,expires_at,
forced_exit_at,side,limit_ce,stop_c2,target_dol

Spec JSON antes de mirar outcomes:
{
  "name": "OB_contra_FVG_prereg_001",
  "horizons_minutes": [5, 15, 30, 60],
  "feature_min": {"ob": 0.7, "fvg": 0.5},
  "controls": ["local_extreme"],
  "block_bootstrap_draws": 1000,
  "seed": 42
}

Comandos:
  python -m qore.infrastructure.research_accelerator.ultrafast ingest --source DATA.csv --manifest META.json --lake ./lake
  python -m qore.infrastructure.research_accelerator.ultrafast verify --lake ./lake
  python -m qore.infrastructure.research_accelerator.ultrafast screen --bars M1.csv --manifest M1.json --signals EVENTS.csv --spec SPEC.json --out OUT.json --registry ./research/experiments.jsonl --code-sha <40-hex-commit>
  python -m qore.infrastructure.research_accelerator.ultrafast execute --quotes TICKS.csv --quote-manifest TICKS.json --bar-manifest M1.json --orders ORDERS.csv --tick-size 0.1 --slippage-ticks 1 --commission-points 0 --out EXEC.json --registry ./research/experiments.jsonl --code-sha <40-hex-commit>

No se publican datos sintéticos como resultados financieros.
No hay benchmark real de factor ×10. Ultra Fast identifica diseño
indexado, no multiplicador validado. No mutar datasets históricos.

## Problemas y trabajo para siguiente arquitecto (PRIORIDAD)

P0: importar la fuente real de PR #901 en ámbito privado, inspeccionar
SHA y 97/97 hashes de archivos, expandirla de 30h a cobertura requerida
con autorización/licencia. Revisar expiry y vault #837; contrato #857.
P0: consolidar ticks BID y ASK de streams diferentes con unión
as-of y cota de staleness EXACTA; registrar crossed, gaps y DST;
verificar BID OHLC m1 vs ticks; emitir dataset homologado solo
con testigos; hasta entonces simulador neto NO evaluable.
P0: normalizar instrumentos NAS100/USTEC y contrato de punto,
tick, lote, hora, comisión, swap y ajuste; evitar homologación inferida.
P1: adaptar proveedores cTrader Open API read-only, MT5 export,
y fuentes externas mediante interfaces sin credenciales en el repo.
P1: controles placebo de matching causal por día, sesión, dirección,
volatilidad y rango de extrema; test de falsificación de OB/Breaker
contra simple reversión a la media; independencia de muestras.
P1: grupo de expertos debe congelar hipótesis, periodos DEV/OOS,
familias y multiplicidad; Holm o alternativas preregistradas,
poder estadístico y tests adversariales antes de decir EDGE.
P1: auditar disponibilidad exacta de features de terceros; una
marca available_at declarada no prueba que el detector no mire futuro.
P1: bench medido ultra-fast vs runner baseline cronológico, con
identidad de salidas bit a bit; investigar pooling y paralelismo.
P1: CI debe correr lint, mypy y suite total antes del merge.
P2: simular órdenes limit con timestamps reales, latencia/política
de fill, comisiones convertidas a USD y permisos broker, más
slippage calibrado; pasar gates del Trader Lab via evidencia independiente.
P2: auditar gobernanza del registro ante múltiples ramas y escritura
en paralelo; en GitHub mergear ledgers requiere orden y reconciliación.

## Fuentes (GitHub)

- https://github.com/mezas3238-hue/qore-core/pull/901
- https://github.com/mezas3238-hue/qore-core/pull/899
- https://github.com/mezas3238-hue/qore-core/issues/837
- https://github.com/mezas3238-hue/qore-core/issues/857

El siguiente arquitecto NO debe:
- afirmar edge, factor ×10, PF o drawdown con pruebas sintéticas;
- leer holdout para tuning;
- cambiar el Trader Lab, Risk, CIBO o entornos LIVE;
- inventar BID/ASK a partir de OHLC ni declarar fills sin tick/ASK;
- hacer merge sin orden.

## Actualización de implementación — as-of BID/ASK

Nuevo src/qore/infrastructure/research_accelerator/asof.py admite DOS
exportaciones independientes normalizadas con at,price, manifiestos
SHA256 y SIDE bid/ask. El comando python -m
qore.infrastructure.research_accelerator.asof exige rutas BID, ASK,
manifiestos --bid-manifest y --ask-manifest, --max-staleness-ms,
--output, --output-manifest, --receipt. Hace join causal de último
precio observado por lado, nunca mira hacia adelante, rechaza
cotizaciones cruzadas y descarta estados stale sin asumir cotización.
Produce nuevo CSV quote-state y manifiesto verificables por el data lake.
Esto NO equivale a ticks simultáneos ni broker ACK. Los raws cTrader
PR #901 aún deben normalizarse, auditarse y persistirse privadamente.


## Verificación adicional cerrada con datos REALES — 13-Oct-2026

- 30 horas fuente histórica real IC Markets cTrader DEMO USTEC, 10 días
  de desarrollo, sin holdout. Fuente pilot6/wave24 recuperada desde
  Actions y cotejada contra ZIP-SHA256 y SHA256SUMS por archivo.
- src/qore/infrastructure/research_accelerator/real_source.py
  ya funciona sobre ambos ZIPs sin API externa, con paridad native
  integer x1e5, UTC, DST, recuentos source, normalización causal as-of
  y cuarentena 250ms. Reingesta/verifica 30 manifests en un Data Lake
  temporal. Elimina fuente cruda del workspace y sube solo un reporte
  agregado SHA firmado.
- GitHub Actions SUCCESS:
  https://github.com/mezas3238-hue/qore-core/actions/runs/38425782083
- Valores reproducibles: BID=241538, ASK=241565,
  origen total=483103, estados as-of aceptados=240550,
  stale descartados=2004, crossed aceptados=0.
- Comparación independiente de 1500 ticks por lado: paridad exacta PASS;
  aceleración medida ~32.26x en join de cotizaciones solamente,
  no sobre 3 años ni sobre backtest completo del Trader.
- Resultado completo y runbook:
  docs/research/QORE_ACCELERATOR_REAL_CTRADER_30H_AUDIT_RESULT_2026-10-13.md.
- Corrección adicional: el simulador LIMIT nunca paga más del límite
  de compra ni recibe menos del límite de venta cuando slippage
  adverso excede el margen. Incluye pruebas de ambos lados.

### Pendientes NO resueltos, no confundir con implementación base

P0: homologar USTEC cTrader versus NAS100 fuente M1 del Trader,
licencia de datos y almacenamiento durable privado antes de expirar
artefactos, y cobertura BID/ASK multianual representativa.
P1: validar reproducibilidad científica end-to-end de runners de
hipótesis reales frente a un baseline lento (benchmark actual solo
mide as-of). Probar edge neto, spread/commission/slippage y controles
condicionales únicamente tras preregistro, holdout intacto, permisos
de autoridad y especificación completa.

Estos límites no invalidan que las cinco capas del Research
Accelerator son código ejecutable y que la fuente real parcial está
validada; impiden afirmar que el trader tiene edge o que la adquisición
histórica completa ha finalizado.


## Actualización P1: oráculo completo y prueba de screening (13-Oct-2026)

- Se amplió la auditoría de muestra a TODOS los 240550 estados as-of
  BID/ASK de las 30 horas de cTrader, contra segundo algoritmo
  independiente con búsqueda binaria. Paridad exacta 30/30 = PASS.
  Workflow SUCCESS: https://github.com/mezas3238-hue/qore-core/actions/runs/38448953480
  Artefacto agregado firmado: 11839407769. No contiene ticks crudos.
- Tests específicos de adversarial crossed, stale, missing y 30
  secuencias aleatorias desfasadas BID/ASK. Tests del screening
  comparan cálculo indexado versus recorrido cronológico independiente
  sobre barras sintéticas (4 horizontes, censura, filtros, placebo).
  CI aislada PASS:
  https://github.com/mezas3238-hue/qore-core/actions/runs/38448961410
- Informe fuente/mercado con partición por London, NY_AM y NY_PM:
  docs/research/QORE_ACCELERATOR_REAL_CTRADER_30H_AUDIT_RESULT_2026-10-13.md.
  Muestras DEV discontinuas: no estimar edge ni anualizar esas horas.
- El test cronológico comparte las funciones de bootstrap y
  clasificación de regímenes; NO se trata de una validación
  científica independiente de dichos estimadores.
- PENDIENTE fuente BID/ASK multianual, homologación NAS100/USTEC,
  custodia privada de fuente, auditoría de licencia, fills con
  acuses reales, economic gate OOS y prueba de eficiencia
  del runner end-to-end. No merge ni LIVE.
