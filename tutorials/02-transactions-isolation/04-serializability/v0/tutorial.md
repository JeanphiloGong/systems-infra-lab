# T04 v0：先定义串行参考

两位医生都在岗。串行执行医生1下班后医生2看到只剩一人并拒绝，或反过来；合法最终状态是恰好一人值班。

业务规则是至少留一人值班：只有读到在岗人数大于 1，当前医生才允许下班。这里把初始状态固定为 `(True, True)`，并假设两位医生各提交一次下班请求且按顺序执行完。先执行者离开，后执行者重新读取只剩一人，于是拒绝。这两个串行顺序分别得到 `(False, True)` 和 `(True, False)`。

这比直接要求“至少一人”更具体：`(True, True)` 也满足业务安全条件，但不是上述两次完整串行请求的结果。下面的集合是这项固定工作负载的参考答案，`sum` 把布尔值视为 0/1，验证集合中的每个结果都留下一人；代码尚未模拟请求的读取和更新。

```python
serial_results = {(False, True), (True, False)}
assert all(sum(state) == 1 for state in serial_results)
```

在仓库根目录运行 `uv run python -c "serial_results = {(False, True), (True, False)}; assert all(sum(state) == 1 for state in serial_results); print(sorted(serial_results))"`，应输出 `[(False, True), (True, False)]`。此章只用 Python，无需 PostgreSQL；把 `(False, False)` 加进集合后，断言应失败，因为没有医生值班。

如果两个事务并发读到人数都是 2，再分别更新自己的行，就可能得到 `(False, False)`。不同记录没有写写冲突，仍不代表历史可串行化。本章仅冻结参考结果，不证明某个数据库隔离级别；最终状态匹配也不能单独证明任意事务历史可串行化。下一版连接 PostgreSQL，让两个事务同时读并观察 SERIALIZABLE 如何拒绝冲突历史；那时才需要相应数据库环境。
