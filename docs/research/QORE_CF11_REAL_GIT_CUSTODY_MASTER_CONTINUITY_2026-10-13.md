# QORE CORE — Continuidad de custodia Git real para CF-11 y QORE Research

**Checkpoint:** 13-OCT-2026. **Repositorio:** mezas3238-hue/qore-core. **Presupuesto:** USD0.
**PR hija:** [#919](https://github.com/mezas3238-hue/qore-core/pull/919) (OPEN/DRAFT, NO MERGE).
**Rama:** `research/qore-cf11-git-custody-readonly-20261013`.
**Cadena:** #895 → #913 → #914 → #915 → #916 → #918 → #919.
**Reglas:** NO LIVE/DEMO/órdenes/capital real/VPS/sizing de trader ni merge sin orden.

## 1. Trabajo realmente terminado

Se llevó el esquema prereg DRAFT de #918 a un **testigo de Git real**, validado en Actions, para evitar que simples flags de JSON sustituyan commits y blobs auténticos. La implementación **no abre, reevalúa ni promueve** ninguna hipótesis. **No son muestras nuevas del mercado**.

### Dos testigos diferentes — no confundir

**Testigo histórico 1: preregistro EIA real anterior a su resultado**
- Commit del preregistro original: `00065e6df7450cac707f983858ca39eed7b30c47`.
- Commit del runner del resultado original: `25b8d2fc18c02992ff1115bbb117cc42438de891`.
- Ruta fijada: `docs/research/QORE_FUTURES_A_EIA_WTI_NG_F1F2_PREDICTIVE_SCREEN_PREREG_2026-10-13.md`.
- Blob Git SHA-1 exacto: `cb73347a17d7d08292efce2a5843827b35a5e34d`.
- Validación: `git merge-base --is-ancestor`, `git rev-parse COMMIT:PATH`, `git show`, hash de objeto recalculado desde bytes, campos H1_WTI/H1_NG presentes. **El resultado sigue NO_SUPPORT**.

**Testigo de configuración 2: manifiesto de propuestas futuras sin hipótesis**
- Commit original del manifiesto DRAFT vacío: `19ed90def222f18591c5bb7b03c8928e8a597c77`.
- Ruta: `docs/research/QORE_RESEARCH_PREREG_DRAFTS_2026-10-13.json`.
- Blob Git SHA-1: `f23e2ef9995776d913848a24f7811cbd8fc392e5`.
- Validación: el commit original es ancestro del HEAD del workflow; tanto blob original como blob del HEAD deben ser **idénticos y válidos**, con `drafts: []`. Además verifica que `git status` no indique archivos sucios y que `git rev-parse HEAD` coincide con el `GITHUB_SHA` de Actions.
- **Esto NO es un preregistro sellado de nuevas hipótesis.** Es una prueba de que no se han agregado hipótesis ni modificado su manifest.

## 2. Entregables

- `src/qore/infrastructure/trader_lab/qore_research_git_custody_v1.py`: verificación pura y recibo determinista SHA256.
- `tests/infrastructure/trader_lab/test_qore_research_git_custody_v1.py`: **11** tests adversariales adicionales (SHA, commits iguales, falta de ancestro, cambios de blob, worktree dirty, manifest manipulado, errores git, hashes).
- `.github/scripts/qore_research_git_custody_readonly_v1.py`: wrapper ejecutable únicamente bajo contexto declarado GitHub Actions para la rama #919.
- `.github/workflows/qore-cf11-prereg-draft-causal-gate.yml`: hereda verificación de EIA original y construcción de ledger CF-11; incorpora pruebas y testigo Git real, emite dos artifacts sin precios de terceros.

## 3. Evidencia ejecutada verificada

**[Actions run #38482764242](https://github.com/mezas3238-hue/qore-core/actions/runs/38482764242)** en commit de código `98f96ec994eae141c45ab1bf92babc753628f630`: **SUCCESS**.
- **51/51 tests Python**, Ruff PASS y Mypy PASS.
- Fuente original EIA/run/digest/prereg ancestry verificados por el pipeline heredado.
- Prereg DRAFT count 0. No replay económico, ningún holdout abierto.
- Git custody original prereg/manifest histórico: **PASS real**, no fixture sintético.
- Receipt lógico `GIT_CUSTODY_RECEIPT_SHA256 = f6b3b1063550b2020588c006820425fe56a5ca3f22df855266a45b03e349dac9`.
- Artifact de custodia: [#11857396966](https://github.com/mezas3238-hue/qore-core/actions/runs/38482764242/artifacts/11857396966), ZIP digest `sha256:c5b90f2babc6db7c0dbb5ed14eb26f81bb6820b810b2f5f7d793f540adaefd77`.
- Artifact prereg DRAFT: [#11858945637](https://github.com/mezas3238-hue/qore-core/actions/runs/38482764242/artifacts/11858945637), ZIP digest `sha256:fd80946db69fcedfa7ecfb9e124f195b10ab0cd6e96590f4e40b56066aa8ec67`.

**Los 51 tests abarcan 24 previos de #916 + 16 de #918 + 11 nuevos de #919.** Las fallas intermedias correspondían a Ruff B023 (loop closure) y Mypy context managers, ambas corregidas antes de la CI SUCCESS; no reportar runs RED como verdes.

## 4. Alcance científico: qué NO demuestra

- Un commit ancestro no demuestra que el investigador no haya consultado previamente los precios o outcomes. Git demuestra historia de objetos, no ceguera de seres humanos ni publicación histórica del proveedor.
- La firma de `GITHUB_SHA`/GitHub Actions no demuestra licencia CME, bid/ask, PnL neto, ni primera publicación as-of.
- Este trabajo no registra ninguna hipótesis nueva. La reserva EIA 2022-01 a 2024-04 sigue sin evaluar, y el holdout FX Native desde 2024-09-17 no se toca.
- `research.eia.futures-a-f1f2-closure = CLOSED_NO_SUPPORT`; `research.futures-a.native-6roots-d1 = SOURCE_BLOCKED`. Mantener así hasta evidencia nueva.
- `new_prereg_scientifically_frozen=False`, `can_open_holdout=False`, `can_promote_trader=False`, presupuesto US$0.
- Esta tarea **NO crea** el Research Director autónomo 24/7. GitHub Actions no es daemon.

## 5. Pendientes y orden científico del siguiente arquitecto

**P0 datos:** comprobar una fuente CME contract-native seis raíces, dos expiries, 2012–2024, OHLCV/settlement/OI, bid/ask/costes, derechos US$0 y timestamps de primera publicación. En ausencia de esto no hay fuente negociable ni trader que certificar. No comprar datos sin orden.

**P0 edge:** ninguna rentabilidad evaluada con esta evidencia. No declarar PF/DD/Sharpe, no promover Trader Lab ni ejecutar fuera de pruebas sintéticas.

**P1 prereg futuro:** diseñar metodología de prereg verdadero sólo para hipótesis independientes científicamente, con commits previos a runs de resultados, source entitlement, as-of causal, versión y política de enmiendas; una hipótesis posterior no debe usar el testigo del manifest vacío como permiso. Un nuevo commit del manifest **romperá el testigo actual por diseño** hasta que un arquitecto lo reemplace bajo gobernanza.

**P1 investigación sustantiva:** priorizar hallazgo de fuente legal sin gasto o, con nueva instrucción expresa, mudar hipótesis a un universo con datos válidos existentes. Evitar más artefactos de «verde técnico» sin mover la evidencia económica.

**P1 autoridad/infra:** issuer de fuente y licencias, custodia de artifacts expirables y director de investigación idempotente son todavía pendientes; ninguna de estas piezas suplanta Risk/CIBO.

**P2:** con datos válidos: prereg → replay causal con costes → OOS fresco → stress/Monte Carlo → Risk/CIBO soberano → Trader Lab. Sin LIVE.

## 6. Reanudación

Abrir [PR #919](https://github.com/mezas3238-hue/qore-core/pull/919) y la CI anterior; verificar último HEAD porque el commit de este documento se suma después de la CI. PRs en DRAFT. Sin merge.

**Dictamen:** mejora comprobada de custodia científica a nivel Git, sin edge nuevo ni ejecutabilidad económica.
