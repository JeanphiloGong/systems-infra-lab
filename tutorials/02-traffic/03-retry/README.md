# F03: Retry Storm and Circuit Breaker

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

This tutorial is one evolving Python project under `labs/traffic/resilience/`. Each version is a complete, independently runnable checkpoint:

- v0 measures immediate retry amplification.
- v1 classifies retryable and permanent failures and adds a total deadline.
- v2 adds exponential backoff and seeded jitter.
- v3 bounds recovery probes with a circuit breaker.
- v4 executes nested retries and consumes a shared leaf-attempt budget.

The first pass intentionally uses no side effects. Idempotency and reconciliation belong to the later D01 dependency, where retrying a side effect can be made safe. Extract the exact checkpoint fence in each tutorial version and run the focused tests with [参考分支检查](../../../docs/reference-checks.md).

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/traffic/retry -q
```

</details>
