# T03 v1 计划

在 v0 丢失更新后保存同一 `(quantity, version)` 读取结果。第一次条件 UPDATE 成功并递增 version；第二次使用旧 version 得到 rowcount 0。测试必须检查最终 quantity=9、version=1 及冲突明确返回。下一版用行锁保护读取。


## Tutorial Increment

- **Pressure:** The two workers decrementing shared inventory scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v0两个请求都认为完成，实际只扣一次。需要让写入验证读取后的状态是否仍有效。version条件与quantity>0一起放进UPDATE，由数据库原子判断。 前置[v0](../v0/tutorial.md)，保留环境。本版两个请求持有同一个旧版本，第一条条件更新递增version，第二条旧版本条件更新零行。不引入自动重试。旧schema缺乏版本信息，现在完整替换schema.sql为：
- **Change:** # T03 v1：条件更新检测冲突; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/locking -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T03 locking teaching model for two workers decrementing shared inventory; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of T03 locking, carrying forward the state and invariant rather than restarting from a disconnected example.

