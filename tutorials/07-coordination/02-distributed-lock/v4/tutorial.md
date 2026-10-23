# D02 v4: failure is explicit, not silently safe

上一章只有收到服务响应才能确认续租成功。现在 worker 无法联系锁服务：它不知道请求未到达、响应丢失，还是自己的租约已经被别人接管。把 timeout 当作“我仍然拥有锁”会继续产生不确定写入。

下面将这种不确定性压缩为 `service_available=False`，把异常转成明确的调用方决定 `do not write`。资源已经保存 token 2 和 `new`，本次失败路径不触碰它。这里演示的是停止发出新写入的策略，不是网络故障检测器，也不证明旧的在途写入已经取消。

将下面的完整代码保存为 `checkpoint.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: checkpoint.py -->
```python
service_available=False; resource={'token':2,'value':'new'}
try:
    if not service_available: raise TimeoutError('lock service unavailable')
except TimeoutError: decision='do not write'
assert decision=='do not write'; print({'availability':'unknown','safety_action':decision,'resource':resource})
```

可选执行 [参考分支检查](../../../../docs/reference-checks.md)，本章输出必须保留 `resource={'token':2,'value':'new'}`，并显示 `availability='unknown'`、`safety_action='do not write'`。这个检查冻结了失败时不主动写入的调用方规则。

本章牺牲可用性来避免新的不确定操作，但不能替代 v2 的资源端 fencing。真实系统还需要锁服务共识、持久 token、原子资源更新和故障测试；本组五个小模型没有实现这些部署能力。

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
