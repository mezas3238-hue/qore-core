# VT08 CRT PURE — N3: pre-registro del reloj CRT M15-C2→M5-C3

**Congelado ANTES de leer resultados N3, 14 OCT 2026.** Rama `agent/vt08-crt-pure-source-identity-001`; PR #626 DRAFT. Solo investigación, NO son trades.

## Discrepancia documental a investigar

- Fuente primaria RomeoTPT Model #1 (propia): [cierre interno QORE](VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md): H4 CRT→M15 Model #1; old-high/low y confirmación corporal, no prueba que N1 sea tal modelo. NO alterar.
- SpeculatorFL fuente B [25-MAY-2024](https://threadreaderapp.com/scrolly/1794311615535518154): `Conformational CRT` espera confirmación al cierre **C2**, luego busca trading en **C3 o posteriores**, y micro CRT LTF dentro de HTF refinado en timeframe adicional inferior. La regla exacta de confirmación, entrada y destino queda por fuente/imagen sin adjudicación. No extraer números ni promesas de precisión.
- TraderFlameseN fuente B [13-MAY-2024](https://threadreaderapp.com/thread/1790141530461622525.html): CRT anidados, dependencia con SpeculatorFL; no confirmación independiente.

**N1 QORE anterior** exigía `M15-C3.close` superando midpoint de `M15-C1` y miraba `M15-C4.open`, no representa confirmación fuente B antes de M15-C3. El experimento N3 diagnostica esa diferencia temporal sin inventar una entrada M5.

## Pregunta, universo y diseño congelado

**Universo:** AUDUSD y USDJPY, **los mismos 287/265 parent H4 TS** (2 triplas NY ingeniería), velas M5 SHA originales QORE Atlas hasta 2026-09-16. No añadir mercados o H4 clocks. C3 H4 debe tener las 16 M15 contiguas completas.

**Micro-evento N3 C2:** Dentro de H4-C3, evaluar cada par de M15 consecutivos con *otra M15 completa después*: micro-C1 = referencia H/L positiva; micro-C2 = barre estrictamente solo el high o solo el low de micro-C1 y su **cierre vuelve dentro inclusive del rango**. Es la forma QORE de reconocer la condición `C2_CLOSED_PURGE_RETURN`. Conocerlo en `microC2.closed_at`, **sin consultar microC3**. Se cuenta TODA observación, incluso contraria a H4 y aun si C3 luego falla. Micro dirección = low sweep/bullish, high sweep/bearish.
 
**Reloj M5 dentro de la micro-C3 siguiente:** 3 velas M5 contiguas `t0,t+5,t+10` con cierres `t+5,t+10,t+15`. Estas se observan **solo como desenlace temporal**, no se incorporan al gate de micro-C2. Guardar primer cierre M5 que supera el midpoint de micro-C1 en la dirección esperada y primera vela M5 que toque con wick el extremo *far* del mismo micro-C1. Si el C2 ya cerró del lado pertinente del midpoint, conservar flag `MIDPOINT_ALREADY_CROSSED_ON_C2_CLOSE`. No declarar que tal cierre M5 equivale a original Romeo Model #1 ni que es fill. Dentro de la misma vela M5, el orden entre wick y cierre es indeterminado.

**Denominadores/reconciliación obligatoria:** todos los pares con C3 completo, los C2 causalmente calificados, conteo por activo/período, dirección coincidente/opuesta H4, C2 con objetivo H4 ya tocado antes de su cierre, C2 midpoint ya superado, C3 M5 midpoint first-cross slot 1/2/3/no, first-far-touch slot 1/2/3/no, cruce M5 temprano por slot1/2, y parent H4 únicos. Para comparabilidad EXACTA con N1: `N1_confirmed_on_M15_C3_close` debe sumar **521 AUDUSD / 418 USDJPY**, ya que N1 restringe los eventos C2 con cierre de M15-C3 sobre su midpoint. N3 incluye también los C2 cuyos C3 no confirmaron, evitando sesgo de solo ganadores.

**Prohibiciones analíticas:** No usar precio futuro de M5 para seleccionar C2 candidato. No añadir M5 entry signal ni SL/TP, ni simular R, PnL, PF o WR. No convertir el 50% micro ya atravesado en objetivo futuro ni extrapolar far boundary como un DOL certificado. No comparar números de C2 «tradeable» sin invalidación/HTF PD arrays/timezone documentados. Eventos M15 repetidos pueden compartir M5/parent; reportar parent únicos y solapamiento sin atribuir independencia.

**Admisión doctrinal:** `QORE_N3_C2_CLOCK_OBSERVATION_ONLY`; fuente B apoya secuencia temporal general, detector `sweep_one_side+return` es ingeniería QORE, puente M5 es instrumentación PIT, no regla de entrada original. Si no se resuelve propiedad del nivel, macro contradicción, DOL y M5 trigger desde fuente, G-M1/3/4 = OPEN.

**Seguridad:** NO MERGE, NO LIVE/DEMO orders, NO VPS, NO MT5, NO FundedNext LIVE, BTCUSD congelado, no sizing Trader, CIBO autoridad.
