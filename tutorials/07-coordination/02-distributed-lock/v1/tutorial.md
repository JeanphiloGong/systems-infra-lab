# D02 v1: lease expiry creates overlap risk

上一章不释放的锁会阻止接管。设 worker `a` 得到一秒租约，却因进程暂停停在工作中间；逻辑时间到 2 时，锁服务允许 `b` 接管。问题是 `a` 恢复后仍可能继续写订单，租约表里只有一个 owner 并不等于资源端只有一个写入者。

这个 checkpoint 只压缩上述时间线：`expires=1` 在 `now=2` 已到期，随后用 `b` 的租约替换它。没有真实等待，也没有主动终止旧进程；`old_owner_paused` 和 `overlap_risk` 是场景说明，代码尚未执行两个写入来证明覆盖结果。

<!-- checkpoint: checkpoint.py -->
```python
lease={'owner':'a','expires':1}; now=2
assert lease['expires'] <= now
lease={'owner':'b','expires':3}
print({'old_owner_paused':True,'new_owner':'b','overlap_risk':True})
```

在仓库根目录运行 `uv run python tests/coordination/locks/replay_d02.py`。本章打印 `new_owner='b'`、`overlap_risk=True`，到期断言必须通过。若把 `now` 改为 0，这条接管时间线就不满足前提，应在断言处失败。

租约解决的是允许后来者接管，未解决旧持有者恢复后的写入。下一章把判断移到真正接收写入的资源端，用单调 token 拒绝迟到请求。本例不实现时钟同步、租约存储或网络超时。
