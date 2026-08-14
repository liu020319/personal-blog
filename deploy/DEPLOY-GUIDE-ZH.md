# xiaoliudev.com 博客 V17 发布说明

## 最终访问关系

- `https://xiaoliudev.com/`：个人博客静态主站；
- `https://xiaoliudev.com/kanglian-cloud/#/login`：康联云登录页；
- `https://xiaoliudev.com/blog-api/`：文章发布、简历、点赞、评论和合作留言接口；
- `https://xiaoliudev.com/#/pulse`：Redis 实时访问、今日 UV/PV 与文章热榜；
- `https://xiaoliudev.com/agent-api/`：小刘技术与项目助理接口；
- `https://xiaoliudev.com/api/`：继续转发到原 Spring Boot 服务。

页面仍由 Nginx 直接提供。会产生数据的功能由轻量 Python 服务处理，默认仅监听 `127.0.0.1:8091`；文章、点赞、评论、合作留言以及经访客同意的 30 天访问明细保存在 SQLite，Redis 只负责高频访问计数、UV、在线窗口、热榜与限流，不占用现有 MySQL。

## 发布包

本地成品：

```text
D:\CodexWorkFiles\output\personal-blog-release-20260815-v17.zip
```

上传位置：

```text
/home/xiaoliu/personal-blog-release-20260815-v17.zip
```

## 1. 解压

```bash
mkdir -p /home/xiaoliu/personal-blog-release-20260815-v17
unzip -q -o /home/xiaoliu/personal-blog-release-20260815-v17.zip \
  -d /home/xiaoliu/personal-blog-release-20260815-v17
sed -i 's/\r$//' \
  /home/xiaoliu/personal-blog-release-20260815-v17/deploy/install-release.sh \
  /home/xiaoliu/personal-blog-release-20260815-v17/deploy/install-redis-analytics.sh
```

## 2. 安装静态页面与博客服务

```bash
bash /home/xiaoliu/personal-blog-release-20260815-v17/deploy/install-release.sh
```

脚本会：

1. 检查博客、康联云入口和原 `/assets/`；
2. 只把本次会覆盖的博客文件、旧服务和私密配置备份到 `/home/xiaoliu/backups/`，不重复复制康联云与原系统资源；备份目录权限为 `0700`；
3. 移除旧的错误示例简历，但在备份目录保留恢复副本；
4. 发布新页面；
5. 安装并启动 `personal-blog-resume` 轻量服务；
6. 首次部署时生成管理口令；若旧口令少于 32 个字符会自动修复，并同步给已安装的 Agent；
7. 配置博客 API 为 16 个固定工作线程、64 个排队位置，过载时返回 503；
8. 验证服务、博客首页和康联云入口。

出现 `STATIC_AND_SERVICE_OK` 才表示本机安装完成。

## 3. 安装 Redis 站点脉搏

第一次启用 Redis 时执行：

```bash
bash /home/xiaoliu/personal-blog-release-20260815-v17/deploy/install-redis-analytics.sh
```

脚本会通过 Ubuntu 软件源安装 `redis-server` 与 `python3-redis`，创建独立的 `xiaoliu-blog-redis` 服务，生成随机密码，只监听本机 `127.0.0.1:6381`，并把 Redis 数据内存限制为 64MB。它不修改默认 6379 服务，避免影响康联云以后使用 Redis。密码只写入权限为 `0600` 的博客环境文件，不会进入网页或 GitHub。

看到 `REDIS_ANALYTICS_OK` 才表示 Redis 模块完成。Redis 临时不可用时，站点会降级为不显示统计，文章、评论、简历和合作需求不受影响。

## 4. 接入 Nginx

把 `deploy/nginx-blog-api-location.conf` 中的 `location /blog-api/` 放入现有 `xiaoliudev.com` HTTPS `server` 块。不要改动已有 `/api/` 和 `/assets/`。

修改后：

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -fsS https://xiaoliudev.com/blog-api/health
```

只有 `nginx -t` 成功才能重载。健康接口应返回：

```json
{"ok": true, "redis": {"configured": true, "available": true}}
```

把 `deploy/nginx-site-security-headers.conf` 安装为
`/etc/nginx/snippets/xiaoliu-site-security-headers.conf`，并在 HTTPS `server` 块中加入：

```nginx
include /etc/nginx/snippets/xiaoliu-site-security-headers.conf;
```

它会补齐 HSTS、防 MIME 猜测、防嵌套页面、来源策略和浏览器权限限制。现有页面已经通过 HTML meta 使用严格 CSP，暂不在 Nginx 重复设置 CSP，避免影响康联云页面。

## 评论自动审核与邮件提醒

正常评论通过长度、隐私、频率、机器人和广告特征检查后会立即公开；可疑评论仍进入管理中心人工审核。配置邮件后，每次收到评论或合作需求都会尝试发送提醒，邮件失败不会影响数据保存。

Gmail 账号必须启用两步验证，并创建单独的“应用专用密码”。不要填写 Gmail 登录密码。编辑：

```bash
sudoedit /etc/personal-blog-resume.env
```

填写或修改以下配置：

```text
BLOG_EMAIL_NOTIFICATIONS=true
BLOG_NOTIFY_EMAIL=你的收件邮箱
BLOG_SMTP_HOST=smtp.gmail.com
BLOG_SMTP_PORT=587
BLOG_SMTP_USERNAME=你的 Gmail 地址
BLOG_SMTP_PASSWORD=你的 Gmail 应用专用密码
BLOG_SMTP_STARTTLS=true
BLOG_SMTP_SSL=false
```

保存后重启并查看日志：

```bash
sudo systemctl restart personal-blog-resume
sudo systemctl status personal-blog-resume --no-pager
sudo journalctl -u personal-blog-resume -n 50 --no-pager
```

不要填写 Gmail 登录密码。应用专用密码是 Google 在开启两步验证后单独生成的 16 位凭据，只放在服务器这个权限为 `0600` 的环境文件里，不要发到聊天、截图或 GitHub。

重启后进入 `https://xiaoliudev.com/#/manage`，管理中心会显示邮件是否已配置；点击“发送测试邮件”，收到测试邮件后才算配置完成。

## 管理中心

访问：

```text
https://xiaoliudev.com/#/manage
```

管理中心可以：

- 在“文章”页面创建、发布或删除文章，发布时间由系统自动生成；
- 查看访客留下的微信、电话或邮箱；
- 标记合作留言为新留言、已联系或已结束；
- 查看自动公开的普通评论，并人工处理可疑待审核评论；
- 查看邮件提醒配置并发送测试邮件；
- 查看 Agent 当日模型调用、缓存、限流和并发状态；
- 查看近 1、7 或 30 天 PV、UV、IP、页面、设备、系统和浏览器分布；
- 查看最近访问明细并按需清空；明细默认 30 天自动删除；
- 删除不合适的评论或合作记录。

查看管理口令：

```bash
sudo sed -n 's/^RESUME_ADMIN_TOKEN=//p' /etc/personal-blog-resume.env
```

口令不得写入 GitHub、网页配置、截图或聊天记录。网页只将口令保存在当前浏览器会话中。

## 数据位置

```text
/var/lib/personal-blog-resumes/blog.db              # 文章、互动、合作联系方式、访问统计明细
/var/lib/personal-blog-resumes/resumes.json         # 公开简历版本记录
/var/lib/personal-blog-resumes/files/               # 正在公开的 PDF
/var/lib/personal-blog-resumes/deleted-resumes.json # 删除的简历记录
/var/lib/personal-blog-resumes/trash/               # 简历恢复副本
/etc/redis/xiaoliu-blog.conf                         # 博客专用 Redis 限制和认证配置
```

数据库目录权限为 `0700`，服务文件默认使用 `0077` 权限掩码。合作联系方式不会通过公开接口返回。

## 服务检查

```bash
sudo systemctl status personal-blog-resume --no-pager
sudo journalctl -u personal-blog-resume -n 80 --no-pager
curl -fsS http://127.0.0.1:8091/health
curl -fsS http://127.0.0.1:8091/analytics/summary
REDISCLI_AUTH="$(sudo sed -n 's#^BLOG_REDIS_URL=redis://:\([^@]*\)@.*#\1#p' /etc/personal-blog-resume.env)" redis-cli -p 6381 ping
```

## 备份重点

```text
/var/lib/personal-blog-resumes
/etc/personal-blog-resume.env
```

前者包含 SQLite 数据库与历史简历，后者是管理口令；两者都不能提交到 Git。
