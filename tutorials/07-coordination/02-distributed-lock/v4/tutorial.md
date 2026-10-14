# D02 v4: failure is explicit, not silently safe

上一章只有收到服务响应才能确认续租成功。现在 worker 无法联系锁服务：它不知道请求未到达、响应丢失，还是自己的租约已经被别人接管。把 timeout 当作“我仍然拥有锁”会继续产生不确定写入。

下面将这种不确定性压缩为 `service_available=False`，把异常转成明确的调用方决定 `do not write`。资源已经保存 token 2 和 `new`，本次失败路径不触碰它。这里演示的是停止发出新写入的策略，不是网络故障检测器，也不证明旧的在途写入已经取消。

<!-- checkpoint: checkpoint.py -->
```python
service_available=False; resource={'token':2,'value':'new'}
try:
    if not service_available: raise TimeoutError('lock service unavailable')
except TimeoutError: decision='do not write'
assert decision=='do not write'; print({'availability':'unknown','safety_action':decision,'resource':resource})
```

运行 `uv run python tests/coordination/locks/replay_d02.py`，本章输出必须保留 `resource={'token':2,'value':'new'}`，并显示 `availability='unknown'`、`safety_action='do not write'`。这个检查冻结了失败时不主动写入的调用方规则。

本章牺牲可用性来避免新的不确定操作，但不能替代 v2 的资源端 fencing。真实系统还需要锁服务共识、持久 token、原子资源更新和故障测试；本组五个小模型没有实现这些部署能力。
