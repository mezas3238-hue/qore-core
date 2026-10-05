# QORE SHARED LAB — Native Multiuser Bank 001

This layer makes QORE Shared Lab the primary validation bank for six architects
and three integrators. GitHub remains canonical code/history; Actions is only a
mirror and is not required by the native execution path.

## Native topology

```text
9+ clients
  -> qore-shared-lab submit
  -> Scheduler API
  -> priority/fairness/dedup/locks
  -> dynamic worker pool
  -> exact-SHA isolated worktrees
  -> suite DAG
  -> persistent Dataset Store
  -> causal Cache Store
  -> per-RUN Evidence Store
  -> PASS / FAIL / BLOCKED / CANCELLED / TIMEOUT
```

Initial contract:

- at least 9 concurrent clients;
- at least 32 queued jobs;
- 4 workers initially, resizable up to 20 without interface changes;
- exact commit SHA binding;
- content-addressed persistent datasets;
- causal cache key includes code/component/dependency/dataset/config/lab version;
- identical active jobs attach to one run;
- granular exclusive locks;
- cooperative cancellation and fail-closed timeouts;
- status for all jobs or one job;
- replay and reproduce without workflow_dispatch;
- optional post-run GitHub status publication.

## Commands

```bash
qore-shared-lab serve --workers 4 --max-workers 20
qore-shared-lab submit --sha <SHA> --submitted-by Architect-1 --role ARCHITECT \
  --scope mc18 --mode quick --priority QUICK
qore-shared-lab status
qore-shared-lab status <JOB_ID>
qore-shared-lab cancel <JOB_ID>
qore-shared-lab workers --capacity 8
qore-shared-lab validate --sha <SHA> --scope sensor --mode component
qore-shared-lab replay --sha <SHA> --scenario global-exam
qore-shared-lab reproduce <RUN_ID>
qore-shared-lab publish <RUN_ID>
```

## Absolute acceptance

The laboratory cannot be declared finished merely because these interfaces
exist. `scripts/shared_lab_multiuser_native_acceptance.py` must pass a real
HTTP scheduler exam with nine simultaneous clients, a 32-job queue, dedup,
causal cache, granular locks, cancellation, failure isolation, run ownership,
persistent dataset identity, exact SHA and native replay while the GITHUB_*
environment is removed.
