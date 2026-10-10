# Scalper A1 — verificación GitHub CI / scientific replay

Fecha: 2026-10-10. Rama `agent/scalper-architect-a-cognition-20261010`. Issue #756; PR DRAFT #758; PR padre #623. NO MERGE/NO VPS.

## Método de reproducibilidad

El workflow global `.github/workflows/ci.yml` se activa con `pull_request: [main]`, no con PR a rama de integración. Un ensayo de CI se obtuvo mediante el PR temporal #760 hacia `main` y se restauró su base a `agent/qore-capitalizer-cognitive-v1-001`. **Run `38042441033` FAIL Mypy V53**, run de contrato `38042441069` SUCCESS. Este método no promueve ni fusiona; repetir contra integración final. Esto no es autorización de integración.

El SHA concreto debe fijarse por cada run. No deducir PASS a partir de compilación estática, CI sin artefactos o resultados de otros commits.

## Preflight

- [x] GitHub-only; no VPS ni despliegue
- [x] Investigados cinco blockers Mypy/Ruff en runs corregidos de V50-R, V51, V53, V54-A y V54-B
- [x] Cambios de calidad aislados, sin retoque de estrategia, umbrales, riesgo, P&L
- [ ] CI global completo en PR/HEAD de este branch: Ruff, Mypy, pytest + cobertura
- [ ] V50-R calidad + 9/9 mercados + aggregate
- [ ] V51 calidad + 9/9 mercados + aggregate
- [ ] V53 calidad + 9/9 mercados + aggregate
- [ ] V54-A calidad + 9/9 mercados + aggregate
- [ ] V54-B calidad + 9/9 mercados + aggregate
- [ ] Corrected-core V50-G winner-preservation respecto de V49
- [ ] A2 reviewed method/FVG/CISD/re-arm con fuente textual exacta
- [ ] Congelar candidato (NO antes de cierre)

## Captura mínima de evidencia por ejecución

`workflow` / `run_id` / `head_sha` / `event` / `quality_status` / `market_jobs_success_over_total` / `aggregate_status` / `artifact_id` / `model_identity` / `data_fingerprint` / `whether_replayed`.

Cada replay económico debe informar la población de referencia, el denominador del winner-preservation, la línea causal, la unidad de riesgo R, costes, y las exclusiones por geometría/tesis. Nada de ello se infiere de QORE CI.

**Este documento es una checklist y protocolo, no un PASS ni certificación.**
