# Wave 05 Version Plan Coverage

Snapshot: 2026-10-14. Added only previously missing `tutorials/**/vN/plan.md` files for R01–R04, C01–C03, D01, D02, D04, Q01–Q04, F01–F04, E01, E02, E04, A01 and A02. Existing plans, including the current A03 and E04 module plans, were left untouched. No source code, tutorial body, module README, `docs/progress.md`, or `tutorials/README.md` was changed.

Each added plan names its module scenario, compressed model, invariant, previous-version dependency, version-specific pressure, naive failure, deterministic break, one mechanism change, checks, freeze artifact, remaining limits, next pressure, and a repository replay command. The text is module-specific for the real scenario and invariant; it does not claim the corresponding implementation or independent review is complete.

Verification from repository root:

```bash
node - <<'JS'
const fs = require('fs');
const path = require('path');
const expected = {
  R01:['05-replication/01-leader-follower',5], R02:['05-replication/02-consistency',5], R03:['05-replication/03-multi-leader',5], R04:['05-replication/04-postgres',4],
  C01:['06-consensus/01-cap-quorum',4], C02:['06-consensus/02-leader-election',5], C03:['06-consensus/03-raft',9],
  D01:['07-coordination/01-idempotency',5], D02:['07-coordination/02-distributed-lock',5], D04:['07-coordination/04-saga',5],
  Q01:['04-query/01-modeling',4], Q02:['04-query/02-indexes',4], Q03:['04-query/03-planner',4], Q04:['04-query/04-derived',5],
  F01:['01-storage-engines/07-connections',4], F02:['02-traffic/02-admission',5], F03:['02-traffic/03-retry',5], F04:['02-traffic/04-herd',4],
  E01:['08-dataflows/01-cdc',5], E02:['08-dataflows/02-schema-evolution',4], E04:['08-dataflows/04-analytics',4],
  A01:['09-recovery/01-backup',5], A02:['09-recovery/02-checkpoint',4]
};
let missing=[]; for (const [id,[dir,n]] of Object.entries(expected)) for(let v=0;v<n;v++){const f=`tutorials/${dir}/v${v}/plan.md`;if(!fs.existsSync(f)||!fs.readFileSync(f,'utf8').includes('Pressure'))missing.push(f)}
if(missing.length) throw Error(missing.join('\n')); console.log(`PASS: ${Object.values(expected).reduce((n,[,v])=>n+v,0)} added/verified plans`);
JS
```

Result: **109 missing version plans added and path-checked**. This is documentation coverage only; no tutorial execution, acceptance, or progress count was changed. Existing missing plans outside the requested module set remain an explicit audit item.
