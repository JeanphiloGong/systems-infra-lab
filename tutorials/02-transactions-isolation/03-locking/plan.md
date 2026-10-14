# T03 计划

v0 读取后覆盖写入复现数量 9；v1 版本条件更新让竞争者得到 rowcount=0；v2 两连接 SELECT FOR UPDATE 并比较等待边界；v3 两行相反顺序锁定制造 40P01，再固定顺序避免；v4 纯内存教学模型展示锁升级收益与阻塞扩大，明确 PostgreSQL 不做 SQL Server 式自动升级。每版完整代码、真实 PG 验证和独立 review；不提交 Git。
