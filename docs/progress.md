# 教程状态与本轮验证

main 是学习者逐版创建代码的工作区，reference 保存历史答案。教程文件存在、旧实现测试通过和学习者自己完成，是三种不同状态；这里记录的是文档维护与检查范围。

2026-10-22 全目录审核的 12 个问题已逐项调整：修复恢复与查询语义，补齐真实服务入口和并发检查，重建选主/Raft/LSM 的连续版本，清理通用计划模板，并同步导航。没有恢复预生成的 labs/tests，也没有自动提交。

| 本轮范围 | 实际验证 |
| --- | --- |
| 全部 196 篇正文 | 完整 Python checkpoint 语法、计划配套、文档链接与显式本地 import 目标检查 |
| C02 v0–v4 | 每版独立运行，投票重启子进程、过期授权与故障组合 |
| C03 v0–v8 | 每版及早期行为回归；投票/追加/提交/快照的进程故障；真实 etcd 3.5.17 三进程 |
| S05 v6/v7 | 集成 WAL/Bloom/MANIFEST/删除，损坏拒绝与 flush 故障；同格式全量/两层合并与实际字节计数 |
| P03 v4、Q01 v0–v3、D04 v1/v4 | 恢复全部旧数据及覆盖/删除，拒绝非法订单，真实操作计数，新进程 Saga 与八线程竞争 |
| F01 v1/v3、A03 v1 | 独立 PostgreSQL/PgBouncer 的复用与会话边界；停止旧主后真实提升备库并读回两条记录 |
| A01 v0–v4 | 专用 PostgreSQL 的逻辑恢复/约束、损坏 dump、物理备份/归档、目标时间恢复与缺 WAL 失败 |
| T04 v0 | 实际执行两种串行顺序并验证各留一位医生 |

未改动专题的全部数据库、容器与网络实验没有在本轮重新运行；静态检查不等于它们已重新通过运行验收。本轮是同一作者的修订与复核，没有声称获得新的独立审核意见。

继续学习可从 [T01 v0](../tutorials/02-transactions-isolation/01-isolation/v0/tutorial.md) 开始，再按 [总路线](roadmap.md) 选择专题。当前正文里的直接命令与断言用于验证自己的实现；[reference 检查](reference-checks.md) 仅验证所检出的历史版本。

<details>
<summary>历史作者与审核证据（仅供追溯）</summary>

## 历史验收表（不代表本轮状态）

下表原样保留过去的验收记录。后续正文已改动；其中“已验收”“当前状态”和后续闭环叙述只属于当时输入，不能覆盖本页上方的新版本。

当前闭环证据包括 [计划质量闭环](../.agent-runs/wave-22-plan-quality-closure.md)、
[D03/T04 runtime 复核](../.agent-runs/wave-23-d03-t04-runtime-independent-review.md)
以及 [E01/A03 runtime 复核](../.agent-runs/wave-23-e01-a03-runtime-independent-review.md)。
它们分别证明 196 份版本计划的覆盖/语义审核，以及此前外部服务未验证边界的实际运行。

如果未来修改正文、代码或外部环境，必须重新打开受影响版本；已有证据不覆盖后续变化。

| 模块 | 版本范围 | 当前状态 | 已验收版本 |
| --- | --- | --- | --- |
| S01 页与局部性 | v0–v4 | 已验收 | v0–v4 |
| S02 B+Tree | v0–v7 | 已验收 | v0–v7 |
| S03 WAL | v0–v5 | 已验收 | v0–v5 |
| S04 Bloom Filter | v0–v3 | 已验收 | v0–v3 |
| S05 LSM | v0–v7 | 已验收 | v0–v7 |
| S06 列存 | v0–v4 | 已验收 | v0–v4 |
| S07 Vacuum | v0–v4 | 已验收 | v0–v4 |
| T01 事务隔离 | v0–v4 | 已验收 | v0–v4 |
| T02 MVCC | v0–v3 | 已验收 | v0–v3 |
| T03 锁 | v0–v4 | 已验收 | v0–v4 |
| T04 可串行化 | v0–v3 | 已验收 | v0–v3 |
| P01 分区 | v0–v3 | 已验收 | v0–v3 |
| P02 倾斜 | v0–v3 | 已验收 | v0–v3 |
| P03 迁移 | v0–v4 | 已验收 | v0–v4 |
| R01 主从 | v0–v4 | 已验收 | v0–v4 |
| R02 一致性 | v0–v4 | 已验收 | v0–v4 |
| R03 多主 | v0–v4 | 已验收 | v0–v4 |
| R04 复制机制 | v0–v3 | 已验收 | v0–v3 |
| C01 CAP/Quorum | v0–v3 | 已验收 | v0–v3 |
| C02 选主 | v0–v4 | 已验收 | v0–v4 |
| C03 Raft | v0–v8 | 已验收 | v0–v8 |
| D01 幂等 | v0–v4 | 已验收 | v0–v4 |
| D02 分布式锁 | v0–v4 | 已验收 | v0–v4 |
| D03 分布式提交 | v0–v4 | 已验收 | v0–v4 |
| D04 Saga | v0–v4 | 已验收 | v0–v4 |
| Q01 数据建模 | v0–v3 | 已验收 | v0–v3 |
| Q02 索引 | v0–v3 | 已验收 | v0–v3 |
| Q03 查询计划 | v0–v3 | 已验收 | v0–v3 |
| Q04 物化视图/缓存 | v0–v4 | 已验收 | v0–v4 |
| F01 连接 | v0–v3 | 已验收 | v0–v3 |
| F02 流量 | v0–v4 | 已验收 | v0–v4 |
| F03 重试 | v0–v4 | 已验收 | v0–v4 |
| F04 惊群 | v0–v3 | 已验收 | v0–v3 |
| A01 备份 | v0–v4 | 已验收 | v0–v4 |
| A02 检查点 | v0–v3 | 已验收 | v0–v3 |
| A03 HA | v0–v4 | 已验收 | v0–v4 |
| E01 CDC | v0–v4 | 已验收 | v0–v4 |
| E02 Schema | v0–v3 | 已验收 | v0–v3 |
| E03 Event Sourcing | v0–v4 | 已验收 | v0–v4 |
| E04 分析 | v0–v3 | 已验收 | v0–v3 |

## 第一批证据

R01/C01 的[计划复审](../.agent-runs/wave-07a-plan-review.md)证明九份计划与当前实现一致，
同时重新打开实现范围：R01 v0/v3/v4 尚缺双进程持久恢复、确认策略耗时和失败保留
测量等原要求；C01 v3 的 R+W>N 并发历史反例已由独立复审关闭，证据见
[C01 v3 修订复审](../.agent-runs/wave-09-c01-independent-review.md)。

E01 初审曾发现真实 PostgreSQL LSN 被丢弃，事件身份和消费游标尚未满足路线图要求；
原有六项测试通过不能作为验收。该历史发现已由最终复审关闭，保留作修订轨迹。
证据见 [E01 重开审核](../.agent-runs/wave-03/reviews/e01-v0-v4-reopened.md)。

E01 的中间修订曾以持久 SQLite 和新进程验证提交前后崩溃，但 UPDATE/DELETE
衔接探针又发现快照后的变更被忽略；该历史发现已由混合操作修订关闭，
见 [E01 衔接复审](../.agent-runs/wave-03/reviews/e01-handoff-revise.md)。
后续修订加入带锁的混合操作切点和持久化重放，八项隔离 PostgreSQL 测试通过；
最终复审见 [E01 v0–v4](../.agent-runs/wave-03/reviews/e01-final.md)。
A02 的[细化计划](../tutorials/09-recovery/02-checkpoint/plan.md)已明确四版代码与故障验收任务，
并已由对应正文和复审证据实现。
A02 v0 已通过独立复审：完整 WAL 段重放、实际读取量、临时文件忽略、缺段/截断/CRC
拒绝和正文隔离回放均已验证，证据见
[A02 v0 复审](../.agent-runs/wave-03/reviews/a02-v0-baseline-final.md)。
A02 v1–v3 的早期验收曾因快照读取、损坏处理和发布前验证缺口撤回；修订后已补齐
快照实际读取、损坏明确失败、发布前验证、保留代际和教程正文围栏。独立提取重放与
16 项检查通过，见 [A02 修订复审](../.agent-runs/wave-04-A02-repair-review.md)。
E02 v0–v3 曾通过独立复审：直接改名失败、可空兼容列、双写、真实进程中断后的
批量回填恢复、NULL 保护和最终约束清理均已在隔离 PostgreSQL 中重放，证据见
[E02 最终复审](../.agent-runs/wave-03/reviews/e02-final.md)。
后续[范围复核](../.agent-runs/wave-07-e02-scope-review.md)重新打开 E02：尚缺必填字段
导致旧写入失败的反例、事件 schema 实验和客户端兼容矩阵；旧写后新读存在陈旧值，
回填实验重复运行及最终约束失败写入也需补验。历史通过仅证明当时执行的实验。
上述缺口已由[原范围独立复审](../.agent-runs/wave-08-e02-independent-review.md)关闭：
六项隔离 PostgreSQL 与事件兼容测试通过，包含同一行交错更新、完整回填实验重复运行、
真实 worker 计数及最终约束拒写。旧写入方退出仍是最终切换的明确前提。
E03 v0–v4 已通过独立复审：事件顺序与非法状态、真实并发期望版本冲突、投影去重与
重建、版本倒退拒绝、旧事件 upcast 和副作用隔离均已从正文重放，证据见
[E03 最终复审](../.agent-runs/wave-04-E03-review-final.md)。

A01 的历史独立 PostgreSQL 重放证明连续 WAL archive、第二恢复实例、目标时间恢复和
归档损坏识别；原范围复核另发现 v0 独立恢复/约束、v2 连续归档区间和 v4 窗口测量
仍需修订，见 [A01 范围复核](../.agent-runs/wave-08-a01-scope-review.md)。
A01 的上述缺口已由 WAL 区间格式回归测试、完整物理恢复重放、缺段失败和窗口测量
独立关闭；证据见 [A01 独立复核](../.agent-runs/wave-12-a01-independent-review.md)。
A03 已通过独立 Patroni live 重放和逐版教程复审；网络隔离 fencing、rejoin/cutover
及限制说明均已验证，证据见 [A03 最终复审](../.agent-runs/wave-04-A03-review-final.md)。

E04 已通过独立 PostgreSQL FDW 重放：双源 provenance、选择性传输测量、独立漂移、
源故障和 warehouse 可用性均已验证，证据见 [E04 最终复审](../.agent-runs/wave-04-E04-review-final.md)。

F04 v0–v3 已通过独立复审：真实 asyncio 并发、同键合并、取消/超时隔离、失败清理、
随机过期、SWR 与跨进程边界均已从正文提取并重放。证据见
[F04 独立复审](../.agent-runs/wave-04-F04-review.md)。

C03 原范围复核曾撤回 v1 验收，并发现 v3–v8 的确认、快照和多进程实验不足；
这些历史发现已由最终修订复审关闭，当前状态以上表为准；
证据见 [C03 修订意见](../.agent-runs/wave-03/reviews/c03-v3-v8-revise.md)。

C03 修订已关闭上述问题：固定成员节点使用真实持久化 ACK、当前任期多数提交、
选举计时、崩溃边界、消息故障、绝对索引快照与安装；v8 通过三进程 etcd 故障转移、
多数写入、重启追平和少数节点拒写。31 项测试及正文逐版重放通过，
最终复审见 [C03 修订复审](../.agent-runs/wave-03/reviews/c03-v3-v8-repair-final.md)。

R03 v0–v4 已通过[独立审核](../.agent-runs/wave-03/reviews/r03-v0-v4-final.md)：事件队列延迟、
分区并发冲突、时钟偏移下 LWW 丢写、重复乱序下计数器收敛及同负载对比均已重放。
时间指标仅为固定双节点模拟时间，不代表网络实测或生产耐久性。
R04 v0–v3 已通过[独立复审](../.agent-runs/wave-03/reviews/r04-v0-v3-final.md)：真实 PostgreSQL
物理/逻辑复制、DDL/序列与 replica identity 边界、暂停订阅 WAL 保留及追平均已验证。
复制实验使用同一主机上的专用容器，不宣称自动故障切换或跨主机耐久性。
D04 v0–v4 已通过[独立复审](../.agent-runs/wave-03/reviews/d04-v0-v4-final.md)：部分效果、
SQLite 恢复、幂等补偿、manual 状态及按订单隔离的并发效果键均已重放；外部系统没有
幂等键时的崩溃重复边界已明确。
C03 v0–v8 已通过独立复审；v0–v2 的基础证据见
[C03 基础复审](../.agent-runs/wave-03/reviews/c03-v0-v2-final.md)，v3–v8 的最终证据见
[C03 修订复审](../.agent-runs/wave-03/reviews/c03-v3-v8-repair-final.md)。
后续 source fence 修订已使 v1–v8 与版本化 checkpoint 一致；v8 已使用 etcd 3.5.17
完成三节点故障恢复与少数派拒绝写入的独立重放，证据见
[C03 v8 live 独立复核](../.agent-runs/wave-20-c03-v8-live-independent-review.md)。

## 最近闭环

wave-20/21 补齐了 D02、D04、T04 v0 的正文教学说明，并关闭 D04、P03、E03 的
五个计划语义 finding；正文围栏未被改动，证据见
[教学深度复核](../.agent-runs/wave-21-teaching-depth-independent-review.md) 和
[计划语义修订复核](../.agent-runs/wave-21-plan-semantic-fixes-independent-review.md)。
wave-23 又在专用环境中独立重放 D03、T04、E01、A03，保留 PostgreSQL、logical
decoding 和 Patroni 只代表本地实验边界，不扩展为生产 SLA 或跨主机保证。
裸环境直接执行 `uv run pytest -q` 不会自动启动这些专用服务，最近结果为
`360 passed, 25 skipped, 58 failed, 21 errors`；失败/错误集中在未设置的 DSN 和
未启动的数据库 fixtures。它不是对 wave-23 专用重放的替代，运行这些测试应按各模块
README 的 compose 与环境变量命令执行。

F03 v2/v4 的原范围复核撤回验收：v2 忽略操作耗时且默认不执行等待；v4 只计算乘法上界，
未执行多层调用及共享预算消耗。可复现证据见
[F03 重开审核](../.agent-runs/wave-03/reviews/f03-v2-v4-original-scope-reopened.md)。
这些缺陷现已通过[修订复审](../.agent-runs/wave-03/reviews/f03-v2-v4-repair-final.md)：
真实退避与多层预算均已执行。v4 恢复验收；v2 仍需实际 I/O 超时实验来证明端到端耗时边界，
不能把调用返回后的 deadline 检查当作对阻塞同步调用的中断保证。
F03 的 I/O 边界修订已通过[最终复审](../.agent-runs/wave-03/reviews/f03-native-io-closure-final.md)：
真实 stalled socket 使用同一 monotonic deadline 和 native connect/recv timeout，单次尝试后
超时并完成清理。通用同步 callable 仍不可抢占，OS 调度误差已明确记录。

Q02 的真实 PostgreSQL 实验已通过[独立重放](../.agent-runs/wave-03/reviews/q02-postgres-original-scope-final.md)，
选择性对照与版本边界也已通过[最终复审](../.agent-runs/wave-03/reviews/q02-final-residuals.md)：
相同投影与排序只改变过滤值；四版正文各自独立重放。
Q03 也已通过[真实数据库复审](../.agent-runs/wave-03/reviews/q03-postgres-original-scope-final.md)：
实际 ANALYZE、扩展统计信息、join 与 sort 溢出均有完整执行计划和隔离重放。
CPU 部分分析操作量和成本参数，不宣称测得独立 CPU 时间。Q02/Q03 均恢复验收。

D03 v0–v4 的原范围审核已通过：真实 PostgreSQL prepared transactions、协调者子进程
退出、锁观察、持久决定和部分提交恢复均已重放；3PC 使用明确限定的状态模型。
证据见 [D03 最终复审](../.agent-runs/wave-03/reviews/d03-v0-v4-final.md)。

C02 v0–v4 的独立审核验证了持久化投票、子进程退出后恢复、分区与长暂停、资源端
任期和租约校验。该顺序模拟器不提供复制日志共识或资源重启保证。
证据见 [C02 最终复审](../.agent-runs/wave-03/reviews/c02-v0-v4-final.md)。

作者记录与独立审核记录保存在 `.agent-runs/wave-01/`。该目录中的文件只报告实际完成的
检查和发现，不将未执行命令记录为成功。读者入口随各模块通过审核后添加。

- S01 v0–v4 已验收：[模块入口](../tutorials/01-storage-engines/01-pages-and-locality/README.md)，
  [v0 审核](../.agent-runs/wave-01/reviews/s01-v0.md)、[v1–v4 审核](../.agent-runs/wave-01/reviews/s01-v1-v4.md)。
- T01 v0–v4 已验收：[模块入口](../tutorials/02-transactions-isolation/01-isolation/README.md)，
  [v0 审核](../.agent-runs/wave-01/reviews/t01-v0.md)、[v1–v4 审核](../.agent-runs/wave-01/reviews/t01-v1-v4.md)。
- S03 v0、P01 v0–v1 已验收：[审核记录](../.agent-runs/wave-01/reviews/s03-v0-p01-v0-v1.md)。
- P01 v2–v3 已验收：[模块入口](../tutorials/03-partitioning-scaling/01-routing/README.md)，
  [审核记录](../.agent-runs/wave-01/reviews/p01-v2-v3.md)。
- S03 v1–v2、T02 v0 已验收：[审核记录](../.agent-runs/wave-01/reviews/s03-v1-v2-t02-v0.md)。

## 已执行的修订闭环

- T01：补充非法隔离级别不修改数据，以及事务结束后实际已提交余额的断言，复审通过。
- T02：明确替换中间实验时同时移除旧断言，并补齐 guard 表初始化位置；独立重放后复审通过。
- S03：补充不完整日志尾部截断后的真实进程崩溃边界；独立重放后复审通过。

第一批最终验收为 24 个版本，证据见 [最终审核](../.agent-runs/wave-01/reviews/final-audit.md)。

后续模块仍按总路线及各模块前置条件推进，不删除或缩减。

## Wave 02

版本只有在作者验证、审核、修订和复审全部完成后才写入“已验收版本”。Wave 01 的 24 个版本
仍由 `.agent-runs/wave-01/reviews/final-audit.md` 独立证明，不因 Wave 02 修改而变化。

S02 v2–v4 已修复为分阶段代码并通过作者侧重放；v5–v7 已补齐固定页编码、页 ID、根元数据、叶链、CRC、删除重平衡和边界实验，
并通过独立重放。T03 v0–v4 已补齐完整检查点、
schema 与确定性并发实验并通过独立审核。
早期阻塞证据仍见 [Wave 02 初审](../.agent-runs/wave-02/reviews/initial-findings.md)。

Wave 02 复审证据：[S02/T03 审核记录](../.agent-runs/wave-02/reviews/review-s02-t03.md)。
S02 v6/v7 已补齐完整树、页文件和实验 checkpoint；严格 v0–v7 临时目录重放、访问计数、截断页文件拒绝和存储测试通过，最终审核见
[S02/T04 早期复审](../.agent-runs/wave-02/reviews/final-followup-2.md)。

T04 v2/v3 的原范围复审已经关闭：真实 PostgreSQL 的首次读取屏障制造序列化冲突，
重试重新读取人数并拒绝最后一人下班；`max_retries=0` 验证异常传播。v3 的十轮竞争
报告操作数、提交数、中止尝试数、重试数、业务拒绝和吞吐。六个测试包含从教程代码
与 SQL 提取后使用 `python -I` 执行的隔离重放。证据见
[T04 原范围最终审核](../.agent-runs/wave-02/reviews/t04-original-scope-final.md)。

S04 v0–v3 已通过原范围复审：八组参数实测、真实 S05 v1 SSTable 集成、假阳性回退、
空值/Unicode/重开和实际文件打开计数均有证据。见 [S04 v0–v2 审核](../.agent-runs/wave-02/reviews/s04-v0-v2-revised.md)
与 [S04 v3 集成审核](../.agent-runs/wave-02/reviews/s04-v3-original-integration.md)。
S05 v0–v1 已通过独立审核，见 [S05 审核](../.agent-runs/wave-02/reviews/s05-v0-v1.md)。
S05 v2–v3 已通过独立复审：明确文件新旧顺序、结构化删除标记、新进程读取、任意
字符串保留，以及省略删除记录会复活旧值的反例均已验证。修复旧字节码导致的
重放不稳定后，21 项测试连续三次通过，另有 6 项打印检查点重放。
见 [S05 v2/v3 审核](../.agent-runs/wave-02/reviews/s05-v2-v3.md)。
S05 v4 已通过审核：部分合并保留仍可能被更旧文件需要的删除标记，覆盖最老文件时才
安全丢弃；合并前的旧值复活反例、文件保留和新进程读取均已重放。见
[S05 v4 审核](../.agent-runs/wave-02/reviews/s05-v4.md)。
S05 v5、F01 v0–v3、F02 v0–v4 已通过最终独立复审：S05 使用真实子进程退出并在发布前后
 重启读取；F01 使用官方连接池和 PgBouncer 事务池代理；F02 覆盖失败 worker 恢复、在途
 计数、异构 worker 调度和背压。见 [最终复审](../.agent-runs/wave-02/reviews/s05-v5-f01-f02-final.md)。
F01/F02 后续围栏与源文件边界修订也已独立复核：F01 的 PostgreSQL/PgBouncer 集成和
四版重放、F02 的五版重放及行为测试均通过，证据见
[F01/F02 修订复核](../.agent-runs/wave-12-f01-f02-independent-review.md)。
S05 v6–v7 已通过最终独立复审：v6 展示 WAL 撕裂尾部的精确截断、Bloom definite miss
 与自然假阳性；v7 用三份文件比较 full 与 leveled 合并策略。见
 [S05 v6–v7 最终复审](../.agent-runs/wave-02/reviews/s05-v6-v7-final.md)。
P02 v0–v3 已通过最终独立复审：教程围栏独立重放，并在正文中断言热点键、盐析、容量、
 p99 与共享调度器瓶颈的关系。见 [P02 最终复审](../.agent-runs/wave-02/reviews/p02-v0-v3-final.md)。
P03 v0–v4 已通过最终独立复审：包含增量更新/删除去重、切换屏障、持久化迁移阶段、
 fresh process 恢复以及真实 stale-owner 写入拒绝。见
 [P03 最终复审](../.agent-runs/wave-03/reviews/p03-v0-v4-final.md)。
R01 v0–v4 已通过最终独立复审：顺序日志、延迟 apply、读取屏障、确认模式边界和中断后
 去重恢复均从正文围栏重放；明确这是内存教学模型，不冒充 PostgreSQL 流复制。见
 [R01 最终复审](../.agent-runs/wave-02/reviews/r01-v0-v4-final.md)。
此前范围复核重新打开的进程恢复缺口已由独立 writer/reader 进程重放、完整测试和五个
版本围栏一致性检查关闭；当前收尾证据见 [R01 作者收尾](../.agent-runs/wave-10-r01-author-closeout.md)
与 [R01 独立复核](../.agent-runs/wave-10-r01-independent-review.md)。
Q01 v0–v3 已通过最终独立复审：规范化更新异常、反规范化读模型滞后、读写成本以及独立
 历史订单快照均由正文重放验证。见 [Q01 最终复审](../.agent-runs/wave-03/reviews/q01-v0-v3-final.md)。
R02 的历史最终复审曾遗漏 v2/v4 语义；修订后独立复审验证历史区间、快照保留版本、
缺副本/陈旧副本 session 拒绝，证据见 [R02 修订复审](../.agent-runs/wave-09-r02-independent-review.md)。
Q02/Q03 原范围复核曾重新打开验收：以下历史审核只证明 Python 教学模型，不能证明路线图
要求的真实 PostgreSQL EXPLAIN、Index-Only Scan、VACUUM、ANALYZE 和执行计划变化。
Q02/Q03 后续均已补齐真实数据库正文并通过复审，见本页当前状态表与数据库审核证据。
Q04 v0–v4 已通过[独立复审](../.agent-runs/wave-03/reviews/q04-v0-v4-final.md)：真实聚合、
物化视图旧读与刷新、并发刷新锁、TTL 以及 epoch cache race 均已重放。成功刷新耗时未单独
基准化，作为明确限制保留。
Q02 v0–v3 曾通过模型复审：复合索引 range/order 对比，以及 visibility map 更新、
 heap fallback 和 VACUUM-like 恢复均从正文围栏重放。见
 [Q02 最终复审](../.agent-runs/wave-03/reviews/q02-v0-v3-final.md)。
Q02 后续已补齐 v0–v3 版本化 checkpoint、v3 的 `VACUUM FULL` 可见性边界和 live
 replay；版本化 fence parity、PostgreSQL 测试和完整重放均通过，证据见
 [Q02 fidelity 独立复核](../.agent-runs/wave-15-q02-fidelity-independent-review.md)。
Q03 v0–v3 曾通过模型复审：计划选择、统计信息、相关字段估计，以及 nested-loop/
 hash join 和两种 sort 策略的时间、读取、比较和 spill 指标均已重放。见
 [Q03 最终复审](../.agent-runs/wave-03/reviews/q03-v0-v3-final.md)。
D01 v0–v4 已通过最终独立复审：覆盖响应丢失、并发 request-key 原子领取、事务崩溃边界、
 参数冲突、processing/retention 状态和外部接收方幂等限制。见
 [D01 最终复审](../.agent-runs/wave-02/reviews/d01-v0-v4-final.md)。
C01 v0–v3 已通过最终独立复审：分区超时未知结果、Two Generals 丢失确认、CAP 策略、
 quorum 交集和版本化读取边界均由正文重放验证。见
 [C01 审核](../.agent-runs/wave-03/reviews/d02-c01-review.md)。
D02 v0–v4 已通过最终独立复审：竞争、租约重叠、fencing、真实 renew ownership 以及锁服务
 不可用时的安全处理均已从正文重放。见 [D02 最终复审](../.agent-runs/wave-03/reviews/d02-v0-v4-final.md)。
F03 v0–v4 曾通过以下审核；v2/v4 已因本页记录的实际行为缺陷重新打开。早期覆盖立即重试、错误分类与截止时间、指数退避和 jitter、
 closed/open/half-open 断路器，以及多层有界 retry budget。见
 [F03 最终复审](../.agent-runs/wave-02/reviews/f03-final.md)。
F03 v1 的后续 deadline 修订也已独立复审通过：注入 monotonic clock，并重放跨越截止时间
 的 TimeoutError。见 [F03 v1 修订复审](../.agent-runs/wave-02/reviews/f03-v1-update.md)。
S06 v0–v4 已通过审核：行/列结果一致、字典缺失值、批次边界跳过和点查/更新读取
计数均有实测，并从正文代码在临时目录重放。见
[S06 v0–v4 审核](../.agent-runs/wave-02/reviews/s06-v0-v4.md)。
F01 v0–v2 使用官方 `psycopg_pool`，并对真实 PostgreSQL 验证直连、
复用、耗尽超时、异常归还和会话生命周期。v3 明确记录当前安装版本中
`application_name` 会跨归还保留，不能把连接池的事务重置泛化为所有会话参数都清除。
早期证据见 [F01 审核](../.agent-runs/wave-02/reviews/f01-final.md)。
以下为已关闭的历史发现，当前验收以本页上方的最终复审为准。
原路线图复核曾重新打开 v3：本地池不能替代事务池代理的多个客户端复用后端连接实验。
目前的会话状态结果仍有效，但不能支持 v3 验收。进一步复核也发现 v0 未分解建连
耗时与连接数、v1 未设置 `max_waiting`；在完成原路线图指标和等待队列上限前，
F01 全模块撤回早期验收状态，保留测试证据而不缩减目标。
F02 早期初稿的任务异常会使 worker 退出、在途计数语义不正确，且串行调度不能
证明并发负载策略；这些问题及缺失实验已修复并独立重放，见上方最终复审。
S07 v0–v4 已通过真实 PostgreSQL 复审：普通 VACUUM 的可复用空间、长快照、
VACUUM FULL 锁与重写，以及有界 autovacuum 观察均由正文代码隔离重放。见
[F01/S07 最终审核](../.agent-runs/wave-02/reviews/f01-s07-final.md)。

S02 v7 后续补正为同一逻辑页单位的二分数组/树比较，以及 Linux 文件大小限制
终止真实 `save()` 调用的故障实验，替代比较次数和事后复制截断。
见 [S02 v7 原范围实验审核](../.agent-runs/wave-02/reviews/s02-v7-original-experiments.md)。

</details>
