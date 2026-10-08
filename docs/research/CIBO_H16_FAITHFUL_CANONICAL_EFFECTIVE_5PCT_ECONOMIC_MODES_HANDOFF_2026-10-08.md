# CIBO H16 — FIEL AL CÓDIGO CANÓNICO, 5% EFECTIVO, REPLAY 3.368 / ECONOMÍA POR MODO

**08-10-2026 · RESEARCH ONLY · NO CERTIFICADO**

## Directiva vinculante
Copiar de modo exacto CIBO **desde** `agent/cibo-causal-expectation-leakage-fix-001` (branch vigente de ingeniería). No cambiar metodología, razonamiento de la cognitiva, decisión de modos, entradas de Traders, salidas, stop/R, Capital Compound, Portfolio Compound, Sizing, Leverage ni condiciones de riesgo existentes. El único cambio autorizado es el **monto de riesgo efectivo por entrada**, objetivo 5% del capital corriente (USD3 nominales a USD60) sujeto a restricciones originales. Usar benchmark **USD60, 3368 entradas**, no mezclar con Stellar Instant USD2k o su comisión solicitada USD14/lote.

## Por qué H15 no era suficiente
H15 run [37776873181](https://github.com/mezas3238-hue/qore-core/actions/runs/37776873181) fue SUCCESS y mostró CIBO SOURCE EXACTO, pero el cambio de constante `MEDIUM_RECOMMEND_RISK_FRACTION` de .04 a .05 **no afectó el presupuesto efectivo** de muchas entradas MEDIUM: `historical_risk_fraction` lo sobrescribe al seleccionar capital a asignar. H15 net USD3120.25024, DD36.91054%, BANK $0 (0 trades), MEDIUM +$276.52115 (2519 trades), ATTACK +$2843.72910 (849 trades), soberano incumple $77.10360. Estos no son la ejecución autorizada **MEDIUM 5% efectivo**; la comparación es un ATTACK cap 5% con MEDIUM prior viejo. Marginal H15 Sizing +$159.095; Portfolio Compound +$2597.817, no sumables ni atribuibles directamente a dólares ganados.

## H16 corregido: fuente canónica 100% intacta
- Branch `agent/cibo-faithful-effective-fivepct-h16-001` copia en línea desde H15, cuyo base fue clonado del **CIBO CANÓNICO VIGENTE**. No modificar ningún fuente dentro de GitHub (verificar compare).
- Workflow `.github/workflows/cibo-trader-lab-faithful-effective-5pct-h16.yml`, commit `dd89b93e864d867b892a9463a2fb099aa91a9769`, ejecución [37777655782](https://github.com/mezas3238-hue/qore-core/actions/runs/37777655782).
- Paso 1 copia `src/` exactamente dos veces; contrasta igualdad bit a bit. Solo en **copia TEMPORAL** de la variante inserta una línea `medium_risk_fraction = Decimal("0.05")` **después** del selector original del prior histórico y **antes** del multiplicador monetario MEDIUM. Afirmar que el diff tenga exactamente una línea añadida y ninguna eliminada.
- ATTACK emplea flag original `--ceiling-attack-single-trade-risk-fraction 0.05` vs control `0.20`. No otra lógica tocada.
- Cada modo sigue la cognitiva/ruta postentrada y la administración completa CIBO actual; no se impone 5% siempre si stop 1x, funding, margen y protección restringen el volumen. Medir riesgo efectivamente consumido antes de reclamar exactamente USD3 por cada entrada.
- Cuatro replays de 3368: original, 5%-efectivo, 5%-efectivo sin Sizing incremental y 5%-efectivo sin Portfolio Compound. Las 2 ablations son **comparaciones causales aparte**, no copias de CIBO ni propuestas de cambiar metodología.
- Banco realiza **0 trades**, net PnL 0. BANK crea y recupera working-capital seed. MEDIUM+ATTACK net receipts suman el PnL final; el informe desglosa comisiones de provider original, ganancias y pérdidas brutas. Sizing/Portfolio `delta full minus no-engine` no son utilidades adicionales ni aditivas.
- Instrumentos provienen de manifest histórico pinned (2019-22), original provider costs. **FundedNext USD2k 6% trailing, $60/day y $14/lot es otra simulación que este benchmark no representa**.
- Sovereign bank negatives o piso incumplido INVALIDAN certificación de ganancias, incluso si el balance final es positivo.

**Criterio**: 3368/3368, fuente idéntica, diff exacto 1 línea monetaria, conciliación `initial+sum(mode net)==final`, DD, GL, PF, soberano; solo resultados observados en el run, no anticipados. H16 resultado debe adjuntarse al terminar verificación.
