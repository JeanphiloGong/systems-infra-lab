# D02 v0: atomic acquire has one winner

两个 worker 同时领取同一张订单。如果先读取“尚未领取”，再分别写入自己的名字，两者都可能认为自己获胜。需要把检查和占用合成一个不可分割的操作；先在一个进程中验证这个最小要求，再讨论网络中的锁服务。

下面的完整 checkpoint 用 `Barrier(2)` 让两个线程都到达竞争点。`acquire(False)` 是非阻塞原子尝试：成功者保留锁，失败者立即返回。这里故意不释放锁，否则后来的线程也可能合法获得它，实验就不再是在验证同一次领取只有一个赢家。`winners` 只记录成功者，不决定谁获胜。

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

在仓库根目录准备好 `uv sync` 环境后，运行 `uv run python tests/coordination/locks/replay_d02.py`。它从每章提取 `checkpoint.py` 到临时目录执行；本章输出的 `contenders` 必须是 2，`winner` 可以是 `a` 或 `b`，断言要求恰有一位赢家。不要把固定的线程获胜顺序当作测试条件。

现在只证明单进程内原子领取。`threading.Lock` 不跨主机，也没有过期和故障恢复；持有者不退出竞争区，其他人就不能接管。下一章给占用加期限，但期限到达并不会停止旧 worker。
