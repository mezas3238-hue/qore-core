# VT31 — Puerta 1: prueba de mejora de selección COG+OPS frente a FVG bruto

**13 octubre 2026. Dictamen: `NO_SUPPORT_FOR_POSITIVE_JOINT_SELECTION_LIFT`** sobre el objetivo fijo de 15 minutos. **No es prueba económica ni prueba independiente de la cognitiva sola.**

## Test realmente ejecutado

- Preregistro **anterior al código y sus resultados**: `docs/research/VT31_GATE1_COGNITION_RAW_FIRST_PREREG_20261013.md` commit **`c7822542fd6d2d734cc511db25466d4d6bb604c4`**. No se modificó una definición para mejorar retornos.
- [**GitHub Actions #38427455928 SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38427455928), código+tests exactos **`c852684edbf55dcdc0454dd497c41e8b22e686a6`**, **8/8 pruebas adversariales** PASS, Ruff, compile, checksum original y SHA256 de outputs PASS, artifact **`11830195430`**.
- Fuente: **1.059.784** M1 NAS100 congeladas octubre 2023–octubre 2026, SHA256 **`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`**, artifact `11459859004`. Selecciones históricas ya aprobadas **2.140**, ledger source-only artifact `11657461650`, SHA256 `e9683d87f0645b488968aeb3e207347649f4e9aea5c535202ab4f024c22e7646`. Sesiones London 766/NY AM 721/NY PM 653.
- Control causal determinista: **primer FVG de tres M1 consecutivas en cada ventana completa**, independiente de COG y de su DOL/MSS. Se rechaza C3 que cierra al final de la ventana, igual que OPS. **2.286/2.286** ventanas tuvieron FVG bruto; **2.140** tuvieron candidato posterior COG+OPS, **146** no. Para ambas poblaciones retorno firmado direccional a 15 minutos de la apertura M1 siguiente a la confirmación, sin coste/fill ni acceso a información posterior. En parejas se exige **misma ventana y jornada**, no necesariamente mismo minuto o dirección. Todos los retornos tienen 16 M1 exactas: **0 missing**. Bootstrap por semanas ISO **2.000** muestras, semilla fija.

## Resultados

| Grupo | N | Media bruta 15m, pts | IC 95% semanal, pts |
|---|---:|---:|---|
| Primer FVG bruto en todas las ventanas | **2.286** | **−0,416234** | [−1,972777; +1,122173] |
| Primero bruto en ventanas luego admitidas | **2.140** | **−0,965547** | [−2,515128; +0,611294] |
| **COG+OPS primer FVG adecuado, mismo grupo de 2.140** | **2.140** | **−1,919664** | [−3,549534; −0,402129] |
| **Diferencia PAREADA COG+OPS menos primer FVG bruto, misma ventana** | **2.140** | **−0,954117** | **[−2,692464; +0,840541]** |
| Primer FVG bruto en ventanas NO admitidas | **146** | **+7,635342** | [+1,347727; +14,682823] |

**Interpretación:** no se demostró incremento predictivo positivo. La diferencia pareada media es negativa, pero su IC cruza cero: clasificar `NO_SUPPORT`, **no** una falsación causal de COG, ni prueba de ventaja de invertir su selección. El grupo no admitido es pequeño y su partición depende de la decisión durante esa hora; una media positiva de su señal bruta no implica que se pudiera ejecutar otra política rentable.

### Diagnóstico de comparabilidad obligatorio

- **1.169/2.140** tienen exactamente el mismo minuto de FVG como inicio de retornos. **971/2.140** difieren en el minuto; el evento seleccionado ocurre **en promedio 6,8252 minutos más tarde**, mediana 0, rango 0–54.
- **1.407/2.140** comparten dirección. **733** tienen dirección distinta. Por tanto esta **NO es ablation causal de la cognitiva únicamente**; la regla de primer FVG, target, MSS, desplazamiento y selección OPS influyen simultáneamente. El control bruto está fijado de modo causal pero no es una estrategia validada.
- Efecto pareado por ventana: Londres **+0,317441** pts IC [−0,866739;+1,647783] (766); NY AM **−2,321720** pts IC [−6,858909;+1,935216] (721); NY PM **−0,935697** IC [−3,266670;+1,489709] (653). **Ningún intervalo excluye cero**. No escoger retrospectivamente London por ser el único con media positiva.
- Efecto pareado por año en mismo método: 2023 **−1,194118** (n170), 2024 **−0,133783** (n711), 2025 **−2,496215** (n716), 2026 **+0,080295** (n543); todos intervalos semanales 95% incluyen cero. No optimizar rangos/años.
- La comparación más justa para COG pura necesitaría un **universo fijo de oportunidades y hora exacta** con decisiones `COG_APPROVE/REJECT` registradas **en cada FVG crudo** antes de resultado, y misma dirección de cada candidato para un placebo. El ledger disponible conserva principalmente `COG+OPS ADMITTED` y el raw contra primer FVG, por lo que **no podemos adjudicar contribución causal exclusiva de COG** con honestidad. No convertir la diferencia de fuente en certificación COG.

## Decisión de cuatro puertas y continuidad

- **Puerta 1 (selección cognitiva):** el primer control empírico, **COG+OPS conjunto**, = `NO_SUPPORT_FOR_POSITIVE_SELECTION_LIFT` a +15m; la versión exclusiva COG = `NOT_IDENTIFIABLE_WITH_CURRENT_LEDGER`. No tocar ni ajustar cognitiva para perseguir PF.
- **Puerta 2 (regímenes):** aún no evaluada; prereg obligatorio de regímenes medibles con información disponible al formar la señal, pequeño número de estados, contraste por semanas y corrección de multiplicidad. **Excluir IC de subgrupos elegidos por mejor retorno**.
- **Puerta 3 (eventos macro):** pendiente; calendario PIT verificable y tratamiento DST/hora real, política de noticia previamente fijada, nunca eventos etiquetados a posteriori a conveniencia.
- **Puerta 4 (salida asimétrica CE STOP C2 DOL):** pendiente de G3 firma válida, fuente BID/ASK cronológica del mismo símbolo y OMS; no inventar fill o costes con OHLC. No cerrar esta puerta por fracaso predictivo +15m.
- **Decisión económica actual: `EDGE_NETO_VT31_NOT_DEMONSTRATED`**. NO producción, NO certificación, NO seleccionar ganador, NO presupuesto para cambios paramétricos. El 3Y ya es desarrollo consumido; ningún resultado es validación OOS. El G3 viejo acta SHA `a446afa17ed6e411b8f0b6fc182b103a78959a97` + código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` permanece intacto, unsigned; holdout, main y VPS inalterados.

**Evidencia reproducible íntegra:** [CI #38427455928](https://github.com/mezas3238-hue/qore-core/actions/runs/38427455928), artifact `11830195430`, con `gate1-raw-control.json`, `gate1-summary.json`, SHA256 outputs y código fuente.
