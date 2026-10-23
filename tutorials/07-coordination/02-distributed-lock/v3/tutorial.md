# D02 v3: renew and release require ownership

资源端拒绝旧 token 后，旧 worker 仍可能发送迟到的续租请求。若续租只按资源名称延长时间，`a` 的旧请求可能改变 `b` 已接管的租约。因此续租必须同时检查 owner、获取时的 token 和租约是否仍有效。

这个 checkpoint 实际实现 acquire 与 renew，标题中的 release 尚不在本围栏中。`acquire` 在有效租约存在时返回 `None`；到期后递增 `next_token`。`renew` 验证当前 `(owner, token)`，并拒绝已经到期的租约；成功续租保留 token，只改变 `expires_at`。即使 owner 名字被重用，旧 token 也不能代表新一次获取。

将下面的完整代码保存为 `checkpoint.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: checkpoint.py -->
```python
from dataclasses import dataclass
@dataclass
class Lease: owner: str; token: int; expires_at: float
class LockService:
    def __init__(self): self.lease=None; self.next_token=0
    def acquire(self, owner, now, ttl):
        if self.lease and self.lease.expires_at > now: return None
        self.next_token += 1; self.lease=Lease(owner,self.next_token,now+ttl); return self.lease
    def renew(self, owner, token, now, ttl):
        if not self.lease or (owner,token)!=(self.lease.owner,self.lease.token) or self.lease.expires_at <= now: raise ValueError('lease lost')
        self.lease=Lease(owner,token,now+ttl); return self.lease
service=LockService(); first=service.acquire('a',0,1); second=service.acquire('b',2,1)
try: service.renew('a',first.token,2,3)
except ValueError: stale_rejected=True
current=service.renew('b',second.token,2,3)
assert stale_rejected and current.token == second.token and current.expires_at == 5
print({'stale_renew_rejected':stale_rejected,'current_owner':'b','token':current.token,'expires_at':current.expires_at})
```

可选执行 [参考分支检查](../../../../docs/reference-checks.md)。`a` 在 0 获取，`b` 在 2 接管；`a` 的续租被拒绝，`b` 的续租保留 token 2，截止时间变为 `2 + 3 = 5`。输出需为 `stale_renew_rejected=True`、`current_owner='b'`、`token=2`、`expires_at=5`。

若实现释放，同样必须验证当前 owner/token，不能让旧持有者删除新租约；不要据此认为本围栏已验证释放。当前服务还是单进程顺序对象，没有并发原子性、持久化或 TTL 输入校验。下一章讨论无法联系锁服务时，调用方能作出的有限判断。

将本页的完整 `checkpoint.py` 保存到仓库根目录；上一版同名临时文件已保存进度后再替换。直接运行文件即可执行本页断言和打印结果，不需要 replay 脚本。

```bash
uv run python checkpoint.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/coordination/locks/replay_d02.py
```

</details>
