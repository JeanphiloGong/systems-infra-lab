# T03 v0 计划

先展示两个 autocommit 连接同时读取 10，随后各自写回 9；最终 9 证明一次扣减丢失。只保留两连接、单库存行和整数数量；下一版增加 version 条件。检查 `test_t03_locking.py` 使用真实数据库读取最终状态。


## Tutorial Increment

- **Pressure:** The two workers decrementing shared inventory scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 两个请求各自读10、计算9、写回，最后9而非期望8。我们压缩为两连接、一行库存和四条autocommit语句，保留应用层读取后覆盖的漏洞。 从仓库根目录执行（仅连接本实验的临时数据库）：
- **Change:** # T03 v0：复现丢失更新; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/locking -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T03 locking teaching model for two workers decrementing shared inventory; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of T03 locking, carrying forward the state and invariant rather than restarting from a disconnected example.

