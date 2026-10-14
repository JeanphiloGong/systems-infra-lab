# R03：多主与地理复制

前置：R01 的复制进度、R02 的读取契约、C01 的分区含义。我们让 A/B 两地区用户修改一个展示名称，先测单主写入路径，再允许双主，在分区后正面处理冲突。最后用只增计数器说明哪些业务可以采用无重复合并。

## 运行

不需要数据库、Docker 或模型 API。Python 3.12+，使用仓库 uv 环境：

```bash
uv sync
uv run python labs/replication/multi_leader/v0.py
uv run python labs/replication/multi_leader/v1.py
uv run python labs/replication/multi_leader/v2.py
uv run python labs/replication/multi_leader/v3.py
uv run python labs/replication/multi_leader/v4.py
uv run python -m pytest tests/replication/multi_leader -q
```

每章完整打印本版源码和依赖，随后给出可执行检查围栏。测试从正文提取到空目录，同时执行入口与检查；不会从仓库导入遗漏依赖。源码与正文也逐字核对。脚本使用相邻文件导入，请按上面的路径直接运行。

## 学习顺序

- [v0](v0/tutorial.md)：离散事件产生单主 A/B 写入成本；改变单程延迟验证测量来源，并演示超时后的迟到效果。
- [v1](v1/tutorial.md)：双主本地确认；向量版本区分因果覆盖和真正并发，重连后保留冲突候选。
- [v2](v2/tutorial.md)：确定性 LWW；快钟较早写覆盖真实较晚写，成功确认不保证最终保留。
- [v3](v3/tutorial.md)：G-Counter 逐作者 max 再求和；穷举顺序、重复传播、旧快照及非法输入。
- [v4](v4/tutorial.md)：相同请求与等待节奏下，对比连接正常和分区时的成功率、延迟及冲突损失。

这是有界确定性模拟，时间是模拟毫秒，不是现实网络测速。40ms 单程和 2ms 本地处理是输入假设；所有报告延迟来自事件时间差。没有进程故障、磁盘持久化、负载队列、生产吞吐基准或全球线性一致保证。多地区单主也有远端副本，多地区不等于多主。
