# VT08 CRT PURE — REESTUDIO ORDENADO POR OWNER: LA DENSIDAD R2-C NO ES LA DENSIDAD CRT

**Fecha:** 14-OCT-2026  
**Misión:** OWNER REJECTED la conclusión simplista de ~3 trades/mes/mercado. Reestudiar fuente y arquitectura sin forzar operaciones.  
**Repositorio:** `mezas3238-hue/qore-core` · PR `#626` DRAFT, sin merge.  
**Prueba de censo:** [GitHub Actions #38548265594](https://github.com/mezas3238-hue/qore-core/actions/runs/38548265594), código probado `d8add8ac878422cfecd68aae1cd89060f4b301d7`, **3/3 jobs SUCCESS**, AUDUSD y USDJPY sobre M5 originales QORE con SHA anual. La comprobación de lint y tipos pasó, y el replay/censo completo de ambos activos pasó. Pruebas unitarias adicionales del censo se vinculan por su run posterior a este documento y no se confunden con las pruebas originales.

## Dictamen rectificado

**RECHAZADO:** «VT08 tiene 32–35 operaciones al año por mercado porque CRT no produce más», «hay que quitar filtros para conseguir densidad» y «inside bars de fuente B soluciona densidad».

**CORRECTO:** R2-C es **una operacionalización engineering-only** de una familia CRT. No enumera todas las configuraciones CRT ni todas las posibles fuentes válidas. Los 69 AUDUSD y 64 USDJPY en casi 2 años son solo sus **entradas simuladas**, no la frecuencia total de la metodología. El diagnóstico anterior omitía el denominador de ventanas, descartes estructurales anteriores a la fuente, alternativas de source y otras familias de setup.

## Reestudio documental: tres fuentes (sin equivalencia falsa)

1. **RomeoTPT — autoridad A**: CRT es rango contextual; Model #1/OTE no representan una única entrada universal. El autor habla de reacción en un [old CRTH](https://t.me/s/officialRomeotpt/6615). Sigue pendiente una adjudicación primaria específica de `OLD_LEVEL_OWNERSHIP`, orden de candidatas y expiración. **No se puede atribuir una política `FIRST_SOURCE_ONLY`, `strength=1`, 2 triplets NY por día o filtro inside-bar al autor sin evidencia.**
2. **SpeculatorFL — explicación secundaria B**, [thread original de abril 2024](https://threadreaderapp.com/thread/1784493604473618604.html): expone «Every single candle is a range», protocolos *CRT inferior dentro de CRT superior*, unión de múltiples CRT, inside bars, selección por contextos y cronología; diferencia contexto de patrón y no equivale a decir «operar todas las velas». [Thread selección avanzada/confirmacional](https://threadreaderapp.com/scrolly/1794311615535518154) permite investigar familias **separadas**; no es permiso para alterar un setup existente silenciosamente.
3. **TraderFlameseN — explicación secundaria B**, [thread original de mayo 2024](https://threadreaderapp.com/thread/1790141530461622525.html): coincide extensamente en estructura, jerarquía temporal, inside bars, CRT anidados y modelos de TSQ. Es metodológicamente dependiente/cercano a SpeculatorFL, **no otra confirmación estadística independiente**.

**Conclusión doctrinal:** el universo de **hipótesis** CRT es más amplio que `H4 scheduled one-sided C2 Turtle Soup + old M15 pivot strength=1 + FIRST aligned source + body confirmation in C3 + first valid 50% target`. Pero NO hemos probado que cada hipótesis produzca edge. No elegir temporalidad o fuente por PF.

## Evidencia de fuente: jamás abrir otro proveedor por ausencia ficticia de datos

- GitHub [run fuente Atlas #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458): `AUDUSD` artifact `10475697610`, `USDJPY` artifact `10475389415`, 2016→2026 M5 original con `RAW_M5_LEDGER/2024–2026.jsonl`, `PARTITION_MANIFEST`, SHA anual y `SYMBOL_SHA256SUMS`. Al cierre ambos no expirados. Dataset original acaba **2026-09-17**; faltan los últimos 4 días de ventana R2-C solicitada.
- [QORE Native final33 G0](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-final33-tail-ready-g0-20261012/docs/research/QORE_NATIVE_FULL_33_MARKETS_G0_EXECUTED_FINAL_2026-10-12.md): 33 mercados, **24.377.420 barras M5** custodiadas en artifacts. No confundir artifacts con commits de código.
- Lectura efectivamente auditada en esta ronda: **148.171 AUDUSD + 148.201 USDJPY = 296.372 M5**. No hay órdenes ni cálculo de sizing.

## I. Embudo H4, con denominador que faltaba

| Conteo por mercado, 2024-09-21 a 2026-09-17 | AUDUSD | USDJPY |
|---|---:|---:|
| Ventanas C3 programadas en los 2 triplets NY engineering | **1.460** | **1.460** |
| Sin C1/C2/C3 completos a M5 | 606 | 583 |
| Secuencias con 3 H4 completas a M5 | **854** | **877** |
| C2 no satisface la definición estrecha `ONE-SIDED TURTLE SOUP` | 567 | 612 |
| Parent C2 sí satisface esa definición R2-C | **287** | **265** |
| R2-C termina produciendo trade simulado | **69** | **64** |

**Atención:** 606/583 ventanas sin completitud de tres H4 **NO son necesariamente velas defectuosas**: el calendario incluye fines de semana, cierre del mercado, límites temporales, DST/NY y vacaciones. Nunca llamar a todos esos casos «feed corrupto» ni inferir un problema de datos sin desglosarlos. El software exige los tres bloques completos (48 M5 por H4). La ventana cronológica usa una interpretación NY/DST de la notación `159159` que es ingeniería QORE, no timezone demostrada por Romeo.

**El problema central ya es visible:** ~2/3 de las secuencias H4 completas no pasan **la particular definición C2** de R2-C; y de las que pasan, alrededor de 3/4 no llegan a una operación. Esto NO equivale a «CRT inválido» en los descartes: pueden ser otras familias, setups fallidos o situaciones fuera del mandato actual. No promoverlos sin una fuente.

## II. Censo M15: penalidad de descartar todo después de primera fuente

| Etapa de los 287 / 265 parents elegidos | AUDUSD | USDJPY |
|---|---:|---:|
| Eventos M15 alineados con dirección y old pivot QORE | **563** | **527** |
| Parent CRT con alguna fuente alineada | 238 | 222 |
| Parent CRT con al menos **2** fuentes M15 diferentes | **156** | **144** |
| Parent CRT con al menos una fuente M15 confirmable por cierre | 156 | 138 |
| Parent CRT con alguna fuente que además ofrece geometría válida | **116** | **105** |
| Entradas simuladas por política **FIRST_SOURCE_ONLY** | **69** | **64** |
| Parent rechazados que contienen alternativa M15 posterior con confirmación+geometría local | **47** | **41** |

**Aritmética formal:** `69+47=116` AUDUSD y `64+41=105` USDJPY; de ahí **221 situaciones geométricamente elegibles dentro de los parents actuales** frente a las 133 entradas R2-C. No se fabrican 88 trades: **no** existe autorización metodológica/adversarial para aceptar una fuente tras fallo anterior, ni análisis de trayectorias de esos 88 episodios. Algunos eventos secundarios pueden corresponder a hipótesis conflictivas que exigen ABSTAIN. La mera distinción por velas no asegura unicidad causal, selección de nivel o permiso CIBO. `221` es un universo **investigable, no ejecutable**.

**Evidencia negativa también preservada:**

| Razón final que codifica el replay | AUDUSD | USDJPY |
|---|---:|---:|
| Sin fuente M15 alineada | 49 | 43 |
| **Primera fuente** sin confirmación M15 | 128 | 121 |
| Primera fuente confirmada con stop/target inválidos | 41 | 37 |
| Primera fuente aceptada y simulada | 69 | 64 |

**Casos para auditoría manual con fuente temporal original** (registrados en `density-root-cause.json` de Actions; NO trades):  
- AUDUSD 2024-10-03T01:00:00Z, bullish; primera fuente sin confirmar, 3 fuentes M15 alineadas, 1 alternativa posterior con geometría.  
- AUDUSD 2024-11-12T14:00:00Z, bullish; primera fuente sin confirmar, 5 fuentes alineadas, 2 alternativas posteriores.  
- USDJPY 2024-12-19T02:00:00Z, bullish; primera fuente sin confirmar, 5 fuentes alineadas, 1 alternativa posterior.  
- USDJPY 2025-03-20T13:00:00Z, bearish; primera fuente sin confirmar, 4 fuentes alineadas, 3 alternativas posteriores.

Estos ejemplos han sido identificados por cálculo causal de barras originales, sin demostrar todavía que son Model #1 originales auténticos de Romeo.

## III. Causas raíz — distinción de alcance, no propuesta de aumentar riesgo

| Restricción implementada en R2-C | Autoridad verificable | Consecuencia / problema |
|---|---|---|
| `159159` interpretado como **dos tríos de H4 por día** hora NY | QORE ingeniería de timezone y partición | No explora CRT anidados, horarios alternativos de fuentes B ni otras combinaciones consecutivas; ningún test actual justifica que sea catálogo CRT completo. |
| C2 tiene que ser **un solo lado barrido y recuperado dentro de C1** | Familia Turtle Soup de base; definición estrecha congelada R2-C | No abarca continuaciones, KOD, otras formas de CRT, confirmación avanzada vs C2. No asumir que lo rechazado es señal operable. |
| M15 old pivot con `strength=1` | Política engineering sin prioridad source-adjudicated | Un swing M15 no equivale automáticamente a un **old CRTH** del contexto original. Faltan ownership y adjudicación contra fuente A. |
| Se consume y evalúa **solo primera vela fuente** en C3, aunque fracase | `first_r2c_trade()` ingeniería de R2-C, sin fuente A que demuestre veto universal | Se identifican **88 parents con otra fuente posterior hipotética**; urge examinar invalidación/independencia antes de contarla como trade. |
| Un trade máximo por parent C3 | Contrato R2-C, no regla universal de todas familias | Impide múltiples candidatos, pero no debe relajarse para duplicar riesgos/identidades del mismo evento. |
| Confirmación cuerpo M15 y entrada próximo M15 open | Consonante con Model #1 particular; fuente documental Model1 previa | Otras familias OTE/conformational avanzadas quedan fuera; NO se pueden mezclar en control R2-C sin preregistro independiente. |
| Destino C1 50%; stop fuente; C3 close | Combinación de modelo parcial y políticas QORE | Rechazos de geometría pueden ser legítimos por destino conocido (no se deben «arreglar» moviendo TP/SL para ganar). |

## IV. Decisión cognitiva para QORE — no usar PnL como definición de verdad

1. **Gate metodología M1**: identificar exactamente qué entiende Romeo por `old CRTH/CRTL` y si una fuente independiente posterior al fallo de la primera constituye hipótesis nueva válida. Buscar minutaje/fuente, registrar incertidumbre en `WAIT/ABSTAIN`. Sin evidencia, no rearm automático de la misma fuente.
2. **Gate familias**: representar CRT TS, CRT anidado, Model #1, OTE, CSD y continuation como **familias separadas**, con evidencia principal o secundarias etiquetadas y temporalidad/contexto explícitos. Ninguna familia secundaria es una orden ejecutable por sí sola.
3. **Gate densidad causal**: examinar un conjunto predeclarado de casos reales, tanto primera fuente fallida como múltiples fuentes, contextos contradictorios y días sin trade; congelar los ejemplos **antes** de mirar beneficios. La cognitiva debe explicar diferencias entre **otra fuente independiente**, **duplicado del mismo nivel** y **tesis muerta que no puede rearmarse**.
4. **Gate de integridad**: explorar múltiples parent H4 **solo tras decidir qué ventanas son originales y cuál es política QORE**. No asumir que 2 ventanas son mandato universal; tampoco promover 6 al día para triplicar densidad sin fuente.
5. **Replay económico siguiente**: únicamente cuando las reglas de fuente estén preregistradas, comparar baseline **sin tocar sizing/capital**, nuevos eventos diferentes y ocupación/no-overlap. Reportar mercados, n, PF bruto y sensibilidad temporal; no confundir PF >1 en una muestra ya consumida con certificación.
6. **Autorización económica:** ninguna certificación global mientras falten datos de costes/fill BID/ASK, OOS independiente y gobernanza final. QORE Risk/CIBO soberanos de volume.

### Entregables verificables de la ronda

- Censo causal no operativo: `src/qore/infrastructure/trader_lab/vt08_crt_pure_density_root_cause_audit.py`; no emite nuevas operaciones ni R de alternativas.
- Tests semánticos adicionales: `tests/infrastructure/trader_lab/test_vt08_crt_pure_density_root_cause_audit.py`.
- GitHub Actions [run #38548265594](https://github.com/mezas3238-hue/qore-core/actions/runs/38548265594), resultados por mercado `density-root-cause.json` en artifacts y `density-stdout.log`, SHA archivados con reporte de inside bars original.
- **No merge, no LIVE/DEMO, no VPS/producción, BTCUSD freeze, no posicionamiento del trader; CIBO exclusivo de sizing.**

**ESTADO FINAL:** `DENSITY_DIAGNOSIS_CORRECTED; METHOD_AMBIGUITIES_OPEN; VT08_NOT_CERTIFIED; NO_NEW_TRADES_ADMITTED`.
