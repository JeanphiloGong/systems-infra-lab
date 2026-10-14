# T04 计划

v0 枚举两医生串行结果；v1 SERIALIZABLE 并发中止一方；v2 重试整个事务并重新读取；v3 记录竞争负载下成功、失败、重试与吞吐，区分 serializability 和 strict serializability。所有破坏实验只使用 t04_ 临时 schema。
