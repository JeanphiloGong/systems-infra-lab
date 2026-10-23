# Q01 v0 实施计划

前置 Python 字典读写。

1. 在 checkpoint.py 里保存两条属于客户 9 的订单副本，只改其中一条的 customer 字段。
2. 从两条记录实际计算姓名集合，断言集合含 Ada 与 A. Lovelace，展示同一事实出现矛盾。冻结反例，v1 把当前姓名转为唯一客户记录。

执行 `uv run python checkpoint.py`；完整文件及预期结果见 [正文](tutorial.md)。
