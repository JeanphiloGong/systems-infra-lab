# F01 v1：有界连接复用计划

依赖 v0 的直接 PostgreSQL 连接；目标把连接生命周期交给 psycopg_pool，同时保留 SQL 的真实执行。

1. pool.py 的 make_pool 验证 min/max、timeout 与 max_waiting，构造官方 ConnectionPool；使用 connection 上下文持有并归还，finally close 结束池。
2. 直接入口用 min_size=max_size=1，第一次借出查询 pg_backend_pid，退出后再借一次；断言同一 Python 对象和同一 backend PID，输出 sequential_borrows=2。
3. 执行 `uv run python pool.py`，需要 SYSTEMS_LAB_DATABASE_URL 指向专用数据库。复用是本次观测，连接失效后池可替换对象；v2 再制造耗尽与异常归还。

完整 checkpoint 见 [正文](tutorial.md)，参考分支测试不作为当前入口的替代。
