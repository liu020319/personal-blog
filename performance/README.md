# JMeter 分级压测

这份计划只测试公开 GET 路径，默认目标是 `/blog-api/analytics/summary`。不要一上来就在生产服务器执行 10000 线程，也不要使用 JMeter GUI 正式压测。

先在 GUI 中打开 `blog-read.jmx` 检查请求，然后在独立压测机使用 CLI：

```bash
jmeter -n -t blog-read.jmx \
  -Jusers=100 -Jramp=60 -Jduration=300 \
  -Jhost=xiaoliudev.com \
  -l result-100.jtl -e -o report-100
```

建议阶段：`100 → 300 → 500 → 1000`，每档至少 5 分钟。只有上一档错误率低于 1%、P95 满足目标，并且服务器 CPU、内存、连接数稳定，才进入下一档。10000 活跃线程通常需要多台 JMeter 施压机或分布式模式。

分别测清楚：

- `/`：Nginx 静态首页能力；
- `/blog-api/analytics/summary`：Redis 读取与博客 API 能力；
- `/blog-api/articles`：SQLite 只读能力；
- `/agent-api/chat`：不要做万人压测，受模型并发、费用和每日额度限制。

生产压测前先确认备份、报警和停止阈值。错误率超过 1%、P95 连续恶化、CPU 持续超过 85%、可用内存低于 200MB 或开始出现 502/503 时立即停止。
