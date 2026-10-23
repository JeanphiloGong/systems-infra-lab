# F04：惊群、同键合并与受限旧读

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

同一个商品键过期，20 个请求一起回源。本专题先测真实协程重叠，再逐步改变填充与等待的关系。只使用 Python 3.12 标准库；没有真实数据库或 HTTP 服务依赖。

- [v0](v0/tutorial.md)：同时过期产生 20 个在途加载。
- [v1](v1/tutorial.md)：同键共享一个 Task；不同键不串结果。
- [v2](v2/tutorial.md)：shield 隔离等待者取消，独立源期限限制悬挂，失败与取消传播可验证。
- [v3](v3/tutorial.md)：随机过期分散不同键；SWR 在有限窗口返回旧值并后台更新；真实子进程显示本地合并的边界。

每版有完整源码与 plan.md。测试提取正文全部依赖，在新的目录和解释器中执行并核对源码一致性：

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/traffic/herd -q
```

</details>

逻辑 TTL 时间与实际 asyncio 任务是不同层面：前者控制可重放调度，后者产生测得的在途数量。峰值不是吞吐量。单事件循环映射不提供多线程或跨节点协调；异步超时要求加载器协作取消。
