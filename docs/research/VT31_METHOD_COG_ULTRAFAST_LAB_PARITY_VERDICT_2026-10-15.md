# VT31 — Ultra Fast metodológico/cognitivo: paridad total y aceleración REAL medida
**Corte:** 15-OCT-2026 · **Mandato Owner:** certificar metodología+cognitiva, no PF/DD/Sharpe/Sortino, densidad ni lotaje. PR #966 DRAFT child de #960 (fuentes primarias TTrades), no merge, no LIVE/DEMO/VPS/FundedNext.

## 1. Infraestructura identificada y empleo CORRECTO
- **[Trader Lab Ultra Fast PR #730](https://github.com/mezas3238-hue/qore-core/pull/730)**: el diseño `scripts/cibo_trader_lab_batch_runner.py` carga fuente verificada una vez y reutiliza M5 en Linux `fork` con una fuente compartida COW (copy-on-write), comparando resultado scalar. NO se invocó su motor de trading/riesgo ni se consideró economía.
- **[QORE Research Accelerator PR #908](https://github.com/mezas3238-hue/qore-core/pull/908)**: `research_accelerator/ultrafast.py` es motor independiente con memoria SHA e indexación, pero su `screen` está orientado a outcomes direccionales BID e `execute` a simulación de órdenes. Ninguno es juez de método/COG. Por eso se reutilizaron su disciplina de procedencia y el patrón Ultra Fast de Trader Lab, **no** se declararon operaciones ni estadísticas.
- **Nuevo motor de VT31** `scripts/vt31_method_cog_lab_batch_ultrafast_20261015.py`: fuente NAS100 M1 una carga, `run_census` 775 días una vez, 2 procesos `fork` acotados. Sustituye `run_census` solo EN MEMORIA del proceso hijo, sobre una COPIA del censo congelado, durante la auditoría; al finalizar restaura la función, sin modificar ningún testigo previo. El productor original G3, OPS, acta r1.3 y testigo TTrades #929 verifican SHA intacto por CI.
- **Prerregistro PRE-CODE** commit `c2473687ccdf0989cd721818bd2e61073ee3e583`. Dataset M1 **1.059.784** registros SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, 775 NY días, 483 `FIRST_RETURN_NO_QORE_MSS` contextualizados. Datos desarrollo ya observados, NO nuevo OOS, BID/ASK/trades/posición no usados.
 
## 2. Paridad fuerte real verificada (no sólo recuento)
**[GitHub Actions #38741884264 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38741884264)**, código HEAD ejecutado `6b718e961632092a4ad624dac681e6c4f2125f8c`, **Ruff PASS + 69/69 tests PASS**. Archivo [#11975564344](https://github.com/mezas3238-hue/qore-core/actions/runs/38741884264/artifacts/11975564344), ZIP SHA256 `274e267480cabb6e31b22983ebb799e3786f65bcc1cca7ccf674d5ac3c0e912a`.

Ejecuta la lógica ORIGINAL 4 veces en modo scalar (cada uno con su censo verdadero) y de nuevo mediante batch fork (censo compartido), comparando el **SHA256 del JSON CANÓNICO COMPLETO**, que incluye cada fecha, caso, marca temporal y decisión; cualquier discrepancia provoca FAIL:

| Gate / testigo fuente anterior, sin edición | Full JSON SHA256 scalar == Ultra Fast |
| --- | --- |
| M3 `WAIT_V2` | `96e33a8dd144a106c06f0367afad0253ab5d0737fcf44e26a86880119f93c5a6` |
| M4 `FAMILY` | `d0feeef4d4968ee756116f73e8ec2cbbb7b9924c3bb31d273dcec9bb3628ecf1` |
| M5 `CAUSATIVE_SWING` | `16cd5bf5f61ad382632aa980f2ed25d50397216e7bf21021dc8aec60654d6c02` |
| M4/M5 `AUTHOR_COMPONENTS` | `113d7ac78531ce7acce8cff600477cc1a633a075ea26d1ed3843fa82f4ba0100` |

**PARIDAD = 4/4 FULL CASEBOOKS**, sobre los 483 contextos en cada uno, no señales de mercado ni trades reales. Si un único timestamp o decisión cambia, el SHA fallaría. No falsifica certificado.

## 3. Aceleración, con tiempos de pared MEDIDOS y alcance explícito
Fuente/censo inicial pagados una vez: **15,847363 s**. Scalar para **4 auditorías** sin esa carga: **79,546636 s**. Lote Ultra Fast de dos procesos sin esa carga: **20,504293 s**. Por tanto aceleración de auditorías **3,8795×**, calculada como 79,546636/20,504293 (no prometer 10×). End-to-end aproximado incluyendo idéntica fuente inicial: **2,6242×** (95,394 s vs 36,352 s). No es “tres años de ticks” ni mejora económica.

## 4. Ejecución RÁPIDA real, sin scalar repetido
Se publicó **`.github/workflows/vt31-method-cog-ultrafast-fastonly-20261015.yml`**, con `workflow_dispatch` manual y GitHub Actions. El CI fija el SHA del código del batch y los cuatro SHA de decisión validados arriba; ejecuta sólo Ultra Fast, compara esos cuatro hashes con el baseline scalar ya sellado #38741884264. No acepta cambios silenciosos en productor o método.

**[GitHub Actions FAST ONLY #38742541313 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38742541313)** · Ruff+ **69/69 tests** · código `190f3d1dc8c98ed7080bb579edfed42979304403` (nuevo workflow; script Ultra Fast contenido inmutable). [Artifact #11975919720](https://github.com/mezas3238-hue/qore-core/actions/runs/38742541313/artifacts/11975919720), ZIP SHA256 `76daaa6831718178e09a3d24c3325353250b079838ac65b2894ab4abe7dcf758`. Fuente 15,941820 s y lote Ultra Fast 20,709538 s, **aprox. 36,65 s de procesamiento para los 4 Gates**, sin repetir scalar. **4/4 SHA coinciden exactamente** con baseline verificado anterior.

La propiedad `all_full_casebook_sha256_scalar_match` en la ejecución FAST-ONLY es false porque en ESA ejecución no corrió scalar; la validez se prueba por la igualdad exacta con los cuatro hashes ANTERIORMENTE comparados en #38741884264. No confundir un campo de modo de ejecución con resultado de validación.

### Uso futuro
- Vía Actions: ejecutar manualmente **VT31 Method Cognitive Ultra Fast Verified Replay No Scalar No PnL** en la rama `agent/vt31-method-cog-ultrafast-20261015` cuando se quiera repetir el paquete actual.
- Vía CLI en runner con importación original de source #933/censo #934: `PYTHONPATH=src:. python scripts/vt31_method_cog_lab_batch_ultrafast_20261015.py --market source/NAS100/market-evidence.json --workers 2 --out evidence/result.json`.
- Para **cualquier cambio** en la lógica de M3/M4/M5 o dataset, actualizar versión/prerregistro y volver a ejecutar `--parity` para generar **nuevos** hashes contra el scalar. El SHA viejo no se debe recalibrar por PnL ni aceptar como válido después de cambiar código. Sello del nuevo baseline en commit nuevo.
 
## 5. Gobernanza sin atajos
**M3/M4/M5 original sigue NO CERTIFIED como metodología/fidelidad TTrades**: la aceleración replica perfectamente las *decisiones del testigo*, no prueba que los cuatro modelos OB/Breaker/FVG/displacement estén completos ni que se identifique el swing CAUSANTE del stop. M0 perfil fuente research [#963](https://github.com/mezas3238-hue/qore-core/pull/963) 51/51, pero no runtime. **M6 issue [#897](https://github.com/mezas3238-hue/qore-core/issues/897)** exige dos firmas independientes COG+OPS no presentes; no se falsifican. `METHOD_CERTIFIED=false`, `COGNITION_CERTIFIED=false`, `TRADER_CERTIFIED=false`. No merge, LIVE, DEMO/VPS/FundedNext, lotaje VT31 ni PnL.

**Conclusión:** motor Ultra Fast para pruebas cognitivas entregado, medido, validado por paridad completa y listo para nuevas versiones de los testigos con nuevos preregistros; no es un atajo alrededor de metodología ni autorización.
