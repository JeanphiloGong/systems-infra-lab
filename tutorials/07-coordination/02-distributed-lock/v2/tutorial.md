# D02 v2: fencing protects the resource

沿用上一章的时间线：`a` 持有 token 1 后暂停，`b` 接管拿到 token 2 并写入 `new`。现在 `a` 恢复，尝试写入 `old`。只在锁服务检查 owner 没有用，因为这次写请求已经到了资源端；资源必须自己记住已接受的最高 token。

下面先应用新持有者写入，再把旧 token 与资源保存的 2 比较。旧 token 更小就拒绝，拒绝分支不能修改 `value`。token 表示获取租约的先后，不是墙钟时间。本例允许相等 token 的后续写入，因此 fencing 本身也不是请求去重。

<!-- checkpoint: checkpoint.py -->
```python
resource={'token':0,'value':None}; old_token=1; new_token=2
resource.update(token=new_token,value='new')
try:
    if old_token < resource['token']: raise ValueError('stale fencing token')
    resource['value']='old'
except ValueError: pass
assert resource['value']=='new'; print({'stale_rejected':True,'token':resource['token']})
```

运行 `uv run python tests/coordination/locks/replay_d02.py`；本章必须打印 `stale_rejected=True`、`token=2`，并通过 `value == 'new'` 断言。去掉 token 检查后，迟到请求会覆盖为 `old`，这个断言就揭示了原先的缺口。

这只是资源端顺序模型。真实存储必须原子完成 token 比较和写入，并持久保存最高 token；单调 token 的生成也需要可靠的锁服务。下一章讨论 owner/token 如何约束续租，仍不实现分布式存储。
