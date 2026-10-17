# QORE CRT tres fuentes — V2: ampliación TEMPORAL causal pre-registrada

**Registro antes de ejecutar V2:** 15-OCT-2026. PR #626 DRAFT, sin merge, sin sizing, broker orders, PnL o datos prospectivos. Identidad NUEVA: **`VT08_CRT_THREE_SOURCE_QORE_V2`**, no reemplazar ni reescribir V1.

## V1, resultado visto que motivó el nuevo experimento

Censo original V1 [#38710923324](https://github.com/mezas3238-hue/qore-core/actions/runs/38710923324): 296.372 M5, **5.524 contextos H4 completos C1/C2**, **54 candidatos conceptuales** (31 AUDUSD/23 USDJPY). Sin PF, sin cuentas, sin trades. Las 48 fichas G-M2 eran sesgadas por review a otro C2; no sirven para estimar densidad. V1 fue innecesariamente estricto al exigir el primer par M15 del H4 C3, y encima cerrar favorable al midpoint M15 C1; **no se demostró que estas dos limitaciones procedan de las tres fuentes**.

## Hipótesis de V2 congelada ANTES de ver su resultado

**Principio:** no usar fidelidad exclusiva a Romeo. Con apoyo conceptual de [SpeculatorFL CRT](https://threadreaderapp.com/thread/1784493604473618604.html) y [TraderFlameseN CRT](https://threadreaderapp.com/thread/1790141530461622525.html), CRT HTF puede contener un evento CRT LTF y una confirmación inferior; el rango tiene destino 50 %/opuesto. Ambos textos son muy similares, por lo cual eso no es corroboración económica independiente. La semántica EXACTA V2 sigue siendo **QORE_ENGINEERING**, no palabras del autor.

1. **Parent H4:** política V1 intacta: UTC 00/04/08/12/16/20, H4 C1 completo y H4 C2 inmediato completamente cerrado, `_direction(C1,C2)` de un lado barrido y cierre interno. Excluir ambas caras, cierres fuera, datos faltantes, H4 no contiguo.
2. **Exploración M15:** recorrer **TODOS los pares adyacentes de velas M15 cerradas** que existan durante las cuatro horas H4 C3: `(C1,C2)` índices 0–1, 1–2, ... 14–15. La inspección de cada par ocurre **AL CIERRE DE SU SEGUNDA VELA**, nunca antes. Prohibido requerir/suponer que C3 H4 futura ya cerró antes de decidir.
3. **Micro-setup:** M15 segunda vela barre estrictamente UN lado de la primera, cierra estrictamente dentro del rango de la primera y la dirección coincide con `HTF parent`. A diferencia de V1, NO requiere posición favorable respecto al midpoint M15 C1, pues eso era confluencia QORE excesiva sin evidencia de necesidad; el intento de ampliación es declarado y queda en identidad nueva.
4. **Destino:** midpoint H4 C1 debe estar delante del **close M15 causal** y no haber sido tocado por mechas M15 anteriores o de la confirmación dentro de H4 C3. Si se tocó, esa hipótesis terminó para este padre; **NO rearmar** el mismo target por «reaparecer» luego.
5. **Competiciones y rearm:** **máximo un candidato conceptual por parent H4 C3**, el primero cronológicamente válido; no decidir por éxito ex post ni rescatar source tras STOP/target. Otros eventos tardíos se registran como conflictos/observaciones, no nuevas entradas si usan mismo H4.
6. **Horizon:** caducidad fin de H4 C3. Sin cierre H4 C3 previo como requisito para evaluar un par M15 anterior. Si faltan barras, no inventar; cada oportunidad requiere M5 continuas 3+3 (15+15 min) y H4 padres íntegros.
7. **Salida:** conteo por mercado/año/primer-candidate clock, número de padres y pares M15 examinados, buckets first-fail, IDs únicos; nunca sizing, PnL, entradas bróker o «rentabilidad». Cualquier señal es **CONCEPTUAL_CANDIDATE_QORE_ENGINEERING_NOT_CERTIFIED**.

**Data:** Atlas original AUDUSD 148.171 M5 y USDJPY 148.201 M5, ya consumidos, sin fresh holdout. Fuente GitHub Actions #35166210458. Esta V2 sólo puede decidir si la **densidad de hipótesis** mejora; no permite certificar edge o promoverla a producción.

**Control:** Si V2 mejora densidad, sigue siendo resultado DEV in-sample y resultado del cambio elegido tras ver V1. Necesita preregistro y ensayo en holdout genuinamente no consultado, además de fuente/ejecución/economía y Gates PF/DD/Sharpe/Sortino/stress/MC/CIBO. No retunar V2 sobre mismo resultado. DD patrimonial CIBO/Risk, NO sizing por VT08.

**Gobernanza:** no Romeo-only, pero tampoco fingir tres acuerdos universales; cada regla es autor/fuente o QORE. G-M1..G-M4 todavía PARTIAL, G-M5/Global sin emitir.
