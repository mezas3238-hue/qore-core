# VT31 M3 — VEREDICTO REAL CISD AUTORAL: apertura de PRIMERA vela opuesta, NO última
**Corte 15-OCT-2026** · Owner: certificar **METODOLOGÍA Y COGNITIVA**; nunca otorgar esos Gates según PF/DD/Sharpe/Sortino/densidad/lotaje. PR #968 DRAFT child Ultra Fast #966. NO merge, LIVE/DEMO/VPS/FundedNext.

## Fuente primaria nueva que corrige un error doctrinal
- [TTrades, Understanding The Change in State of Delivery (CISD) — 29 Jun 2025](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/): para múltiples velas opuestas consecutivas, el nivel de cierre CISD es el **opening price de la PRIMERA vela en la secuencia**; no siempre apertura de la última.
- [TTrades, Market Structure Shifts vs CISD — 1 Jul 2025](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): CISD de aperturas de velas opositoras y MSS de desplazamiento+cierre más allá de swing son **distintos**. No convertir el componente CISD en MSS ni OB completo/entrada.
- [TTrades, Order Blocks Simplified — 4 Jul 2025](https://ttrades.com/order-blocks-simplified/): CISD+POI no es por sí solo el modelo Order Block completo, con serie, displacement, retest, 50%-body y riesgo estructural.
- PR #960 `source_ob_cisd()` usa con transparencia última vela contraria como **proxy QORE** y reportó 478/483; ese recuento NO representa exactamente la nueva regla multivela del autor ni comparte definiciones de simultaneidad con la prueba nueva. No comparar 478 y 441 como caída de rentabilidad o señal.

## Ensayo real, sin optimización, con el runner del Trader Lab
**[CI #38748169055 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38748169055)**, commit CÓDIGO `de1211cfab1c9ce7874bba88cec35ae361c9f109`, **Ruff PASS + 38/38 pruebas**: autor FIRST vs LAST open LONG/SHORT, serie 1 o 2 velas, empate cierre, doji, falta M1, reloj futuro/naive, sweep tardío y orden consecutivo. **1.059.784 M1 NAS100 fuente SHA `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`**, 775 días/483 retornos congelados, históricos de desarrollo ya vistos NO OOS.
 
[Evidence artifact #11980157368](https://github.com/mezas3238-hue/qore-core/actions/runs/38748169055/artifacts/11980157368), ZIP SHA256 `914afc584e7c940df5eb5cb25f399e641463eceb25258b298224eff5aad90aa4`, expone TODOS los 483 registros con timestamps y estado de fuente, ninguno es fill/trade; casebook JSON SHA256 completo `11d32d1fda356fdcad96093f0e0a30e7ae373d20f5c7069a24631f1b8949644b`.

| Clase por día (exhaustivas 483) | Contextos | Veredicto |
| --- | ---: | --- |
| `AUTHOR_FIRST_SERIES_CLOSE_COMPONENT` | **441** | En algún cierre M1 elegible se atravesó OPEN de PRIMERA vela opuesta consecutiva; solo **componente CISD source-compatible**, no completo/orden |
| `LEGACY_LAST_ONLY_FALSE_PROMOTION` | **22** | Nunca se confirmó apertura inicial bajo criterio conservador, sí hubo cierre contra APERTURA de última vela. **WAIT/NO PROMOVER** |
| `NO_SOURCE_FIRST_SERIES_CLOSE_OBSERVED` | **20** | No llegó testigo bajo reglas conservadoras de reloj y cierre; no implica imposibilidad de otros modelos/series con latencia distinta |
| **Total** | **483** | No operaciones, no PF/DD y sin sizing |

**388 días** tuvieron al menos un EVENTO `last_open crossed` mientras `first_open not crossed`; muchos de esos días más tarde registraron confirmación correcta y por eso 388 **no es subgrupo disjunto** de los 22. Separar nivel evento de nivel día.

Fuente V2 #954 conserva primer raid, sesgo H1 09, retorno, invalidez y la ventana NY 10–11; se requiere sesgo vigente; si el target contrario H1 ya fue alcanzado, no promocionar CISD nuevo. Nueva formalización QORE acota el testigo a la serie opuesta **contigua inmediatamente anterior** al cierre confirmador, y exige cuerpo de vela confirmadora en dirección del sesgo, además de cierre más allá del primer OPEN. El autor describe el **primer OPEN** inequívocamente, pero no dice que CISD sólo pueda ocurrir 1 M1 después del último candle: abstenciones aquí no niegan oportunidad de otra latencia temporal. Etiquetar `CONSERVATIVE_IMMEDIATE_QORE_TEMPORAL_INTERPRETATION`; no falsificar source-perfect.

## Paridad Ultra Fast comprobada
M1 original y censo NY cargados una vez 15,655694 segundos, censo scalar 10,986916 segundos vs ejecución 2×fork Ultra Fast 5,654691 segundos. **JSON completo de cada uno de 483 casos scalar==fork por SHA256**, incluyendo clase, first-open event y timestamps. Aceleración del COG de este gate ~1,94× sin carga inicial. Esta paridad es de implementación, no certificación del trader.

## Estado de los Gates
- **M3 componente FIRST_OPEN multi-CISD**: regla autoral documentada, implementada y validada en QORE research de solo lectura. **M3 método/cognición de VT31 NO certificado** hasta integrarlo al productor cognitivo real de perfil y resolver displacement/MSS/FVG/OB (no creer QORE latest proxy).
- **M4**: OB/Breaker con fuentes TTrades #960/#961, serie, POI, zona/retest, prioridad todavía requieren adjudicación causal independiente.
- **M5**: swing corto 3 velas autoral existe, pero relación **SWING QUE CAUSÓ displacement** aún no está identificada/sellada.
- **M0** selector pre-sesión #963 research, no runtime canónico integrado.
- **M6** [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) exige dos revisores COG/OPS auténticos y SHA exacto, no presentar una cuenta como dos firmas.
- **No se emiten** `CERTIFICADO_METODOLOGIA`, `CERTIFICADO_COGNITIVA` ni trader-ready. Ningún `CognitiveDecision` se manda a OPS, no fills, stop, lote, PnL, demo o live.

## Próxima acción técnica recomendada
Integrar el testigo FIRST_OPEN como **máquina de espera cognitiva V3 de investigación** vinculada al primer raid H1, confirmación causal y revocación explícita por raid contrario/target consumido; preservar fuente original G3 inmutable y comprobar invariantes `WAIT/UNKNOWN/INVALIDATED`. Después unir en perfil M0 y resolver M4/M5/M6 reales. **No sustituir trabajo por reportes, ni certificar por contadores.**
