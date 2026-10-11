# QORE LON-A — CISD M15 como observación, Gate B M1 histórico y bloqueos

**Fecha:** 2026-10-11. **Issue:** [#785](https://github.com/mezas3238-hue/qore-core/issues/785). **PR de investigación:** [#788](https://github.com/mezas3238-hue/qore-core/pull/788).  
**Veredicto:** `AUTHOR_EXACT_UNDERDETERMINED`, `DATA_GATE_B_PENDING_EVIDENCE`, `NO_ECONOMIC_REPLAY`, `NO_VPS_LIVE`.

## 1. Hallazgo de fuente primaria sobre el CISD

1. Fuente principal Londres 12-sep-2026: [How to Trade London Using TTrades Fractal Model](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/), sección **Confirm The Swing On The 15 Minute**: el CISD ocurre cuando el cierre cruza la serie de velas que produjo el high/low; después el high/low puede ser swing protegido. Se requiere alineación Daily/H4.
2. Fuente específica 29-jun-2025: [Understanding Change in State of Delivery](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/), sección **What is...**: transición bearish→bullish es cierre por encima de apertura de serie de down-close; bullish→bearish cierre bajo apertura de serie de up-close; con varias velas, usar la **apertura de la PRIMERA vela** de la secuencia.
3. Fuente específica 10-ene-2026: [How CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/), secciones **How I Use CISD With Swing Points / Without HTF Closure**: no valida CISD aislado sin C2/C3 HTF, exige buscarlo DENTRO de la HTF; el swing por sí solo no habilita trade.

**Adjudicación:** es posible programar el **cálculo de primer open de una serie ya identificada**, pero NO se ha resuelto autoralmente qué barras forman de manera única la 'serie que produjo el swing' entre dojis, retrocesos, secuencias cruzadas y extremos extendidos. Tampoco hay un pivote confirmado first-online con contrato de extremo inalterable. No seleccionar retrospectivamente la serie más rentable.

## 2. Investigación publicada — observador M15, no modelo operativo

- [Código](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/src/qore/infrastructure/trader_lab/qore_london_lona_m15_cisd_sequence_observer_v1.py).
- [Tests con velas sintéticas](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/tests/infrastructure/trader_lab/test_qore_london_lona_m15_cisd_sequence_observer_v1.py).

La interpretación QORE provisional es **racha máxima de velas consecutivas que cierran en contra**, seguida de primer cierre por encima (alcista) o por debajo (bajista) de la apertura de la primera de la racha. En vez de elegir el mejor evento, enumera TODOS los cruces esquemáticos y señala si varias rachas se cruzan en la misma vela. Se registra extremo original, si hubo nuevo extremo adverso antes del cruce, hora exacta y proveedor. En igualdad exacta al open **no hay cruce**.

**Limitación epistemológica:** esto NO establece que el autor equipare racha consecutiva = 'series that made the swing' en todo escenario; **NO es CISD certificado**, ni protected swing, ni entry; no reconstruye POI/sweep/displacement, ni el estado Daily/H4. Campos explícitos `author_exact=false`, `protected_swing_certified=false`, `entry_authorized=false`, `economic_replay_authorized=false`, `fill_price=null`. Gaps, timestamps locales, proveedor mixto, OHLC imposible y velas M15 no completas bloquean el análisis. Pruebas incluyen invariancia de prefijos.

**Crítica a futuro:** la enumeración es investigación offline en ventanas pequeñas, no un motor incremental eficiente para años de M15; antes de escalar, implementar estado incremental first-online, censurar las rachas competidoras y preregistrar el criterio de selección solo si se consigue evidencia autoral.

## 3. Gate B — artefactos HISTÓRICOS realmente disponibles, no datos futuros

El repositorio tiene un lector neutral previo de CIBO, `capitalizer_cibo_m1_reader_v1.py`. Su reutilización se limita a **decodificar y validar M1 originales** del artefacto, no a importar la lógica/trades/indicadores del trader. El origen está identificado como cTrader native M1, sin sintético/interpolación. Fuente histórica ya consumida en investigación Londres, **NO un holdout virgen**.

Fuente [Actions run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334); SHA de fuente `18c338aedd5013ce65a6cb6408ffbc2e904a6217`.
Artefactos remotos verificados (retención activa según la API al inspeccionar):
- EURUSD: ID `10618547852` / `qore-capitalizer-cibo-10y-native-m1-EURUSD-18c338aedd5013ce65a6cb6408ffbc2e904a6217`.
- GBPUSD: ID `10618811910` / `qore-capitalizer-cibo-10y-native-m1-GBPUSD-18c338aedd5013ce65a6cb6408ffbc2e904a6217`.

**No se vuelven a generar datos conectando a broker**; GitHub Actions descarga únicamente el artefacto inmutable. El censo comprueba `m1-clone-manifest.json`, el SHA-256 de las particiones 2025/2026 originales y las banderas de origen nativo. Restringe estudio a `2025-09-17T00:00Z` → `2026-09-17T00:00Z`, periodo ya consultado, y reconstruye solamente **conteos** por bins UTC:
- M15 = 15/15 M1;
- H4 UTC = 240/240 M1;
- Daily UTC = 1.440/1.440 M1.

No genera precios O/H/L/C artificiales, no rellena gaps, no elimina automáticamente cierres/feriados: distingue bins completos/parciales y contabiliza discontinuidades de calendario que incluyen **cierres normales**. La fracción se calcula **entre bins con ≥1 M1**, nunca en todos los bins de calendario, y **no certifica** que el feed sea completo los días sin ninguna barra. El H4 UTC no se declara H4 correcto del autor (podría diferir del broker, de NY y del DST).

- [Script Gate B](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/src/qore/infrastructure/trader_lab/qore_london_lona_data_census_gate_b_v1.py).
- [12 tests de calendario sintético](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/tests/infrastructure/trader_lab/test_qore_london_lona_data_census_gate_b_v1.py).
- [Workflow de auditoría fuente (2 símbolos)](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/.github/workflows/qore-london-lona-gate-b-source-coverage-no-replay.yml).

**Alcance Gate B:** es un diagnóstico inicial del reloj **UTC**, NO certificación causal de D1/H4/M15; aún exige alinear timezone del autor, perfil NY, DST, market closures, barras parciales y disponibilidad `available_at`. Incluso con 100% de completitud UTC, el gate B permanecerá NO certificado hasta contrastar relojes y trazas reales.

## 4. Próximos bloqueos P0 sin atajos

1. Investigar origen exacto de 'serie que hizo el extremo': selección entre rachas solapadas y dojis, qué cierre invalida, retrocesos y extension del low/high. **No convertir los 21 tests sintéticos en certificación autoral**.
2. Obtener ejemplos TTrades fechados/video con tiempo real y ejemplos negativos. El video L0 sigue sin transcripción verificada.
3. Auditar el calendario H4 real del artículo Londres, horario NY versus UTC y ancla broker. No usar H4-Capitalizer V48 como autorización del otro método.
4. Revisar salida/SL, Daily Bias y mecha first-online con casos discrepantes, no parámetros por PF. Contrastar D1/H4/M15 nativas si proveedor accesible.
5. Reservar OOS realmente no examinado antes de economic test. El source 10Y existente en GitHub fue usado por otros análisis: no presumir virginidad por edad.

## 5. Cierre provisional

Lo obtenido es **instrumentación de auditoría**, no trader funcional. CIBO, Shared, Master Frame, VPS, MT5 y producción intocados. No hay cifras de PF, EV, DD, win-rate, fills ni promesa de rentabilidad. **El estado no se puede promocionar por éxito de CI sintética ni por cobertura completa UTC**.
