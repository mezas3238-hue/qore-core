# QORE Native G1 — dictamen de reconciliación nativa Protobuf original, 2026-10-12

## Datos de origen, SHA y éxito real
Prerregistro congelado ANTES del source [PR #859](https://github.com/mezas3238-hue/qore-core/pull/859), commit `8d72803ce988c800286b7ac19c4aa2ed47301ba1`:
- Cinco instrumentos: EURUSD, GBPUSD, USDJPY (dirigidos por anomalías conocidas del lote original) y controles XAGUSD, SP500→US500. **Selección dirigida, NO muestra aleatoria.**
- Ventanas UTC NUEVAS: 2021-03-16 13:00–13:30 y 2023-03-21 13:00–13:30. No solapan las 3×10min anteriores. No se utilizaron rendimientos para seleccionar símbolos o ventanas.
- [Github Actions #38288411671](https://github.com/mezas3238-hue/qore-core/actions/runs/38288411671) SOURCE 5/5 SUCCESS, code `8dfae03e8212566d7d334c2598931e57c7b55d64`, [artifact original #11764163362](https://github.com/mezas3238-hue/qore-core/actions/runs/38288411671/artifacts/11764163362), digest ZIP SHA256 `b4eb9e66d76bcd439d4db8f2b8707afa06fe2d211a275c8af8b8605714b58684`. Almacenamiento temporal: GitHub Actions, expira ~2027-01-10; NO backup permanente.
- Se guardaron **campos originales serializados** de mensajes `ProtoOATickData` exclusivamente (sin envolvente `ctidTraderAccountId`), segmentados y con SHA por byte, frontera de consulta y testigo `hasMore`. Esta representación conserva wire-fields tras parsing SDK, **NO** envolvente TLS ni full protobuf original con account ID. No fuente raw en Git commits.

## Segunda decodificación, realmente independiente
[PR #860](https://github.com/mezas3238-hue/qore-core/pull/860) y [Actions #38288815999](https://github.com/mezas3238-hue/qore-core/actions/runs/38288815999), **SUCCESS**:
- SHA256 del artefacto original y de todos los ficheros market/side;
- Decodificación independiente desde `ProtoOATickData` de reloj y precio int 1e5, primer absoluto más diferencias firmadas posteriores;
- Conservación exacta de páginas `hasMore` descartadas y validación de cobertura de todos los leaf-ranges sin solapamientos;
- Igualdad del tick nativo al entero y al decimal almacenados por el productor, orden causal y relojes;
- Auditor as-of máximo 5s para analizar source BID=ASK, no ejecución de órdenes. [Artefacto de informe #11764626981](https://github.com/mezas3238-hue/qore-core/actions/runs/38288815999/artifacts/11764626981), ZIP SHA256 `83ae0ae936631af362481a126dde3ef4b6d70ef9cdefdb785821130040494fc4`.

| Instrumento | BID | ASK | as-of BID=ASK | Zero mismo ms | Positivos | Stale |
|---|---:|---:|---:|---:|---:|---:|
| EURUSD | 3541 | 3454 | **3194** | 2740 | 766 | 28 |
| GBPUSD | 4568 | 4140 | **1814** | 1465 | 3791 | 76 |
| USDJPY | 4470 | 4532 | **1632** | 1166 | 4210 | 52 |
| XAGUSD | 3848 | 3943 | **0** | 0 | 5154 | 112 |
| SP500→US500 | 1157 | 1108 | **0** | 0 | 1434 | 114 |
| **Total** | **17584** | **17177** | **6640** | **5371** | **15355** | **382** |

**3 missing-side**, **0 crossed spread** adicionales. Estos recuentos se refieren a instantes `last-known BID+ASK` con antigüedad máxima 5 segundos; el número de snapshots no equivale al número de ticks ni de trades. Source segundo decoder reproduce los ceros en los tres FX incluso en ventanas independientes **de las ventanas originales de 2020/2023/2026**. Del conjunto de cero-spreads **80,9%** coinciden ambos últimos timestamps en el mismo milisegundo del registro histórico.

## Interpretación estricta, problema P0 no resuelto

Las tres divisas exhibieron ceros históricos y los controles metal/índice no en los intervalos nuevos, pero la selección es **dirigida y corta**, por tanto esta comparación NO es una conclusión poblacional ni prueba causa. Descarta que el bug de acumulación de timestamps/precios del primer lector explique por sí solo los ceros, porque se repiten en redecodificación independiente de los campos originales. Aún faltan semántica del proveedor IC Markets/cTrader, evidencia contemporánea forward de bid/ask y protección contra el uso de cero como coste gratis. El mismo milisegundo de marca de tiempo NO es garantía de llegada simultánea a la plataforma, ni de ejecutabilidad real.

**Gate NET = BLOQUEADO; certificados 0/3; 231 tests Holm/FDR/E3 originales sin ventaja positiva replicada.** Para avanzar: resolver [issue #856](https://github.com/mezas3238-hue/qore-core/issues/856), homologar contratos y commissions [#857](https://github.com/mezas3238-hue/qore-core/issues/857), preservar temporal raw broker data en vault privado autorizado [#837](https://github.com/mezas3238-hue/qore-core/issues/837), planificar nueva cobertura histórica con presupuesto/licencia y matching causal de entradas y salidas. No LIVE/MT5/VPS/CIBO/Shared/QDLE.
