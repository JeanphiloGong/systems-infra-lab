# D02 v0: atomic acquire has one winner

两个 worker 同时领取同一张订单。如果先读取“尚未领取”，再分别写入自己的名字，两者都可能认为自己获胜。需要把检查和占用合成一个不可分割的操作；先在一个进程中验证这个最小要求，再讨论网络中的锁服务。

下面的完整 checkpoint 用 `Barrier(2)` 让两个线程都到达竞争点。`acquire(False)` 是非阻塞原子尝试：成功者保留锁，失败者立即返回。这里故意不释放锁，否则后来的线程也可能合法获得它，实验就不再是在验证同一次领取只有一个赢家。`winners` 只记录成功者，不决定谁获胜。

将下面的完整代码保存为 `checkpoint.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: checkpoint.py -->
```python
from threading import Barrier,Lock,Thread
state=Lock(); barrier=Barrier(2); winners=[]
def attempt(owner):
    barrier.wait()
    if state.acquire(False): winners.append(owner)
threads=[Thread(target=attempt,args=(x,)) for x in ('a','b')]
[t.start() for t in threads]; [t.join() for t in threads]
assert len(winners)==1; print({'winner':winners[0],'contenders':2})
```

准备好 `uv sync --locked` 环境后，可选执行 [参考分支检查](../../../../docs/reference-checks.md)。它从每章提取 `checkpoint.py` 到临时目录执行；本章输出的 `contenders` 必须是 2，`winner` 可以是 `a` 或 `b`，断言要求恰有一位赢家。不要把固定的线程获胜顺序当作测试条件。

现在只证明单进程内原子领取。`threading.Lock` 不跨主机，也没有过期和故障恢复；持有者不退出竞争区，其他人就不能接管。下一章给占用加期限，但期限到达并不会停止旧 worker。

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
