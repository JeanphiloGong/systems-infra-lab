# Q01 v1 实施计划

依赖 v0 的 checkpoint.py。

1. 把当前客户名与产品名移入各自 ID 字典，订单只保留两种 ID 与当时价格；join_order 读取当前描述但保留历史价格。
2. create_order 在修改 orders 前验证客户/产品存在和订单 ID 未占用。插入无效客户 9 时捕获 ValueError 并断言 orders==before；正常关联结果客户改名生效、价格仍为 12。

执行 `uv run python checkpoint.py`；完整文件及预期结果见 [正文](tutorial.md)。
