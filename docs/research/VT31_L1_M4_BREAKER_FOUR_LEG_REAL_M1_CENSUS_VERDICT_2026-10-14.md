# VT31 — L1/M4 DICTAMEN REAL 3Y: four-leg BREAKER source witness vs single pivot

**2026-10-14 | SOURCE STRUCTURE ENGINEERING PASS / TTRADES BREAKER METHOD NOT CERTIFIED | PR #945 DRAFT**

## Fuente primaria y diferencia metodológica
- TTrades: https://ttrades.com/breaker-blocks-simplified/ (5-Jul-2025), bullish Low→High→Lower Low→Higher High, bearish High→Low→Higher High→Lower Low, con vela o secuencia de velas de zona y retest. El artículo no fija como algoritmo único del autor pivote de tres M1, desempate de primero o anclaje 09h.
- TTrades AM NQ 2025: https://ttrades.com/the-am-silver-bullet-strategy-on-nq/ (19-Jun-2025). Deben existir 09h H1 completo, barrido de un lado del H1 durante 10–11 NY, desplazamiento/confirmación hacia el extremo opuesto. No atribuir este filtro horario a ICT universal.
- PR #906, su detector BREAKER_RETEST en una rama anterior, utiliza un pivote 09h de 3 M1 y su retesteo como **QORE proxy**; la presencia de un pivote no demuestra las cuatro piernas ni una zona de bloque fallida. Su recuento exploratorio de 84 casos no es la cohorte de esta formalización: distintos algoritmos y criterios, no comparar rentabilidad, no reinterpretar 149 nuevos testigos como 149 breaker trades.

## Preregistro, ejecución y hashes
- Prereg escrito ANTES de ejecutar nuevo código y lectura del corpus: commit SHA 833fd1746659c6034cfcd49c816fb5c4804dedb1, archivo docs/research/VT31_L1_M4_TTRADES_FOUR_LEG_BREAKER_SOURCE_PREREG_2026-10-14.md.
- Código nuevo scripts/vt31_l1_breaker_four_leg_source_20261014.py, adversarial tests tests/infrastructure/test_vt31_l1_breaker_four_leg_source_20261014.py, workflow .github/workflows/vt31-l1-four-leg-breaker-source.yml.
- [CI GitHub Actions #38650665516 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38650665516), commit probado **12f4375b530f2b18e80bddd92b60515fe53ea647**, **228/228 pytest PASS**, Ruff PASS, py_compile PASS, tres blobs G3 originales intactos, fuente datos hash igual; primer intento #38650598847 falló **solo fixture sintético bearish sin candle bajista de zona**, corregido en tests, no alteró reglas del experimento.
- [Artifact #11934562358](https://github.com/mezas3238-hue/qore-core/actions/runs/38650665516/artifacts/11934562358), ZIP sha256 **4b8d485761e2cd93f194dff5824966f3e9c776fe2e58f54c1f1a4d23aa798dd5**: JSON de los 775 días, categorías, test JUnit, logs y SHA256SUMS.
- Fuente: artifact NAS100 #11459859004, 1.059.784 cierres M1, SHA256 **0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa**. Investigación DEVELOPMENT ya examinada, NO OOS.

## Resultado exacto de 775 jornadas NY
| Estado first-failure del diagnostic QORE estricto | Días |
|---|---:|
| FOUR_LEG_RESEARCH_WITNESS_NOT_AUTHOR_CERTIFIED | **149** |
| NO_10AM_CONFIRMATION_SWING | **514** |
| NO_10AM_FIRST_FAILURE_SWING | **3** |
| NO_BLOCK_CANDLE_ZONE | **5** |
| NO_FIRST_RAID | **65** |
| OPPOSITE_RAID_BEFORE_CONTEXT | **33** |
| INCOMPLETE_09_10 | **6** |
| Total | **775** |

**Interpretación exacta:** 149 jornadas presentan dentro de esta formalización un primer par de pivotes confirmados 09h, un primer raid de H1 en 10h, tercera pierna (LOW más bajo o HIGH más alto), cuarta pierna opuesta con nuevo high/low y una o más velas de zona direccionales visibles antes del raid. El pivote de tres velas sólo se declara tras cerrar su vecino derecho. Cuando hay un patrón así se cierra su testigo en ese instante; no se permite que una futura vela lo genere retrospectivamente. Esta selección 09h/10h es una **formalización QORE estrecha** y puede tanto omitir verdaderos breaker del autor como etiquetar estructuras que el autor rechazaría sin más contexto. Los 149 no son una prueba de 149 oportunidades ICT/TTrades, entradas ni fills.

**La mayor parte del bloqueo de la regla strict ocurre en ausencia de cuarta pierna confirmada:** 514 NO_10AM_CONFIRMATION_SWING; no es validación de que el autor descarta esas sesiones. No imputar un trade cero ni concluir que 149/775 representa frecuencia oficial.

## Evidencia adversarial de ingeniería
- LONG y SHORT, NY DST verano/invierno, 09h FIRST pair y secuencia de cuatro piernas completadas, zona de velas direccionales, sellos de disponibilidad en cierre derecho de pivote, y reloj de primera aceptación.
- Rechazo: tener sólo un pivote sin tercera/cuarta pierna, umbrales de pivote iguales, dos raids opuestos en la misma M1, raid contrario antes del testigo, falta de vela de zona, hora M1 faltante, modificación de velas posteriores a confirmación que no debe contaminar el testigo, muestra sintética no válida como 775 días reales.
- 228/228 comprenden las regresiones M1, cognitiva, FVG, stop, Trader Lab L1 research binding, L3 preparatorio y G3; **no** equivale a calidad general repo-wide ni certificación de negocio.

## Gates oficiales que NO cambiaron
| Gate | Estado vigente | Razón |
|---|---|---|
| M0–M3 | source-only, no autor íntegro | COG proxy first return, MSS 1.25x no autor verificado |
| **M4 breaker** | **RESEARCH STRUCTURAL WITNESS ONLY** | estructura 4-leg reproducible, pero pivote/pareo/serie/zone/retest todavía no testigo audiovisual autoral |
| M4 OB/FVG/direct | **INCOMPLETE** | otros detectores PR #906 aún proxy separado, selector y prioridad sin firma |
| M5 swing stop | **INCOMPLETE** | PR #943: C2 difería del proxy pre-MSS 116/119, sin identificar swing autor |
| M6 G3 | **PENDING_DUAL_SIGNATURE** | Issue #897 requiere dos firmantes independientes reales COG+OPS |
| L1 Trader Lab | **DRAFT** | PR #939 identity fingerprint no ResearchEvaluationFreezeEvidence de método completo |
| L2/L3 oficial | **NOT_QUALIFIED** | no replay de órdenes/fills + versión final |
| L4–L7 | **NOT_QUALIFIED** | OOS intocado, stress neto, Monte Carlo, PF/DD/Sharpe no identificados |
| L8–L10 | **NOT_QUALIFIED** | Risk, CIBO y validación independiente requieren atestaciones auténticas de candidato exacto |

## Próximo trabajo técnicamente necesario
1. **Auditoría audiovisual de Breaker/OB**: obtener al menos dos ejemplos primarios + un contraejemplo de TTrades, con pivote, formación y confirmación temporal de las cuatro piernas, delimitación de zona de bloque y vela/s secuencia, invalidación por cierre y retest. Si no se puede decidir una única interpretación, METHOD_SOURCE_UNDERDETERMINED es dictamen honesto, no permiso de inventar una definición.
2. **Congelar perfil + selector M4 completo**: un único objeto estrategia con reglas de prioridad entre displacement/FVG/OB/Breaker, incluyendo stop distinto TTrades swing versus QORE G3 C2, sin observar resultados anteriores como selector; cualquier cambio tras este screening requiere nuevo preregistro, version y fresh OOS.
3. **Governance M6**: dos revisores COG/OPS auténticos sobre SHA exacto #897. Sin firmas, no reclamar congelación oficial G3.
4. **L2/L7**: homologar NAS100↔USTEC exact broker symbol/contract/tick/origen/fees, BID/ASK en toda vida hasta salida 15:55 y evidencia OMS/ACK o explicit PAPER. No imputar compras a contactos OHLC CE. CIBO/CMA/QDLE exclusivamente lotaje y riesgo.
5. **L4–L10**: holdout nuevo realmente no consumido, stress, MC, cuantitativas netas y revisiones externas. El archivo 3Y consumido no admite OOS confirmatorio.

**NO MERGE A MAIN, NO LIVE/PRODUCTION/FUNDEDNEXT, NO VPS, NO ORDERS, NO LOTS FROM TRADER, NO FALSE CERTIFICATION.** Documento posterior a CI, el SHA aprobado de código sigue siendo 12f4375b530f2b18e80bddd92b60515fe53ea647.