# D03: Distributed Transactions, 2PC and 3PC

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

Transfer 30 units between accounts in two independent PostgreSQL databases. Both begin at 100. v0 deliberately loses 30; v1 prepares both resources; v2 survives coordinator process failure; v3 models an extra pre-commit phase; v4 breaks a timeout shortcut under a partition.

The invariant is agreement on the final transaction outcome. Atomic commitment is not an instantaneous consistent snapshot across databases. During phase-two delivery readers can observe one participant committed while another remains prepared.

## Disposable PostgreSQL setup

Use an isolated server because prepared transactions keep locks after client disconnects. These commands use the repository's pinned PostgreSQL image and a dedicated port; use another free port if 55434 is occupied. The role must own the databases it creates and have CREATEDB.

```bash
docker run -d --name systems-d03-postgres \
  -e POSTGRES_PASSWORD=d03_local_only -e POSTGRES_USER=d03 -e POSTGRES_DB=d03 \
  -p 127.0.0.1:55434:5432 \
  postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b \
  postgres -c max_prepared_transactions=20
docker exec systems-d03-postgres pg_isready -U d03 -d d03
export D03_DATABASE_URL='postgresql://d03:d03_local_only@127.0.0.1:55434/d03'
uv sync
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/coordination/commit -q
```

</details>

Wait until pg_isready reports accepting connections before testing. This server deliberately has no persistent Docker volume. Stop it only after resolving any prepared transactions you still want to inspect. The experiment helper creates uniquely named temporary databases and cleans up their own remaining prepared transactions before dropping them. Its cleanup is teardown, not the coordinator recovery algorithm.

```bash
docker exec systems-d03-postgres psql -U d03 -d d03 -c 'SELECT gid, database FROM pg_prepared_xacts;'
docker rm -f systems-d03-postgres
```

The supplied endpoint uses a local-only tutorial password. Never point D03_DATABASE_URL at production. Existing shared lab PostgreSQL configuration is not modified. Two databases on one server demonstrate real independent transactions and prepared locking, not independent host crashes.

## Checkpoints

- [v0](v0/tutorial.md): `[70,100]` after the second local transaction fails.
- [v1](v1/tutorial.md): two PostgreSQL prepared transactions, then `[70,130]`.
- [v2](v2/tutorial.md): actual child-process crash, durable decision, row-lock observation, repeated recovery and unknown-decision blocking.
- [v3](v3/tutorial.md): explicit 3PC states, legal transitions and communication cost.
- [v4](v4/tutorial.md): partition counterexample to a local timeout shortcut.

Each guide prints all its source dependencies. Replay writes those exact fences into a new directory, runs them against the disposable server, compares semantic results, and checks source/fence equality. The version modules run as scripts, with adjacent helper imports; they are not a package facade.

The coordinator journal survives a process exit on local disk. Host loss, replicated journal availability, production membership management, complete 3PC termination, consensus and automatic failover are outside this lesson. A missing decision is never silently turned into commit or abort.
