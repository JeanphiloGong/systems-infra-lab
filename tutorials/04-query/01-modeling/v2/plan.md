# Q01 v2 实施计划

依赖 v1 的 checkpoint.py。

1. 保留 v1.create_order/join_order，新增 view 与 rebuild_view，把两笔订单的查询结果保存为副本。直接改产品名先暴露副本陈旧，再调用维护入口。
2. rename_product 修改产品并逐笔更新涉及该产品的副本，返回实际更新数；断言两份副本与 join_order 一致且历史价格分别为 12/13。冻结维护边界，v3 量化读写次数。

执行 `uv run python checkpoint.py`；完整文件及预期结果见 [正文](tutorial.md)。
