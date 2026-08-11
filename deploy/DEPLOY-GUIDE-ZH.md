# xiaoliudev.com 博客 V8 发布说明

## 最终访问关系

- `https://xiaoliudev.com/`：个人博客静态主站；
- `https://xiaoliudev.com/kanglian-cloud/#/login`：康联云登录页；
- `https://xiaoliudev.com/blog-api/`：文章发布、简历、点赞、评论和合作留言接口；
- `https://xiaoliudev.com/api/`：继续转发到原 Spring Boot 服务。

页面仍由 Nginx 直接提供。会产生数据的功能由一个 Python 标准库服务处理，默认仅监听 `127.0.0.1:8091`；发布文章、点赞、评论和合作留言保存在 SQLite 单文件数据库，不占用现有 MySQL。

## 发布包

本地成品：

```text
D:\CodexWorkFiles\output\personal-blog-release-20260811-v8.zip
```

上传位置：

```text
/home/xiaoliu/personal-blog-release-20260811-v8.zip
```

## 1. 解压

```bash
mkdir -p /home/xiaoliu/personal-blog-release-20260811-v8
unzip -q /home/xiaoliu/personal-blog-release-20260811-v8.zip \
  -d /home/xiaoliu/personal-blog-release-20260811-v8
```

## 2. 安装静态页面与博客服务

```bash
bash /home/xiaoliu/personal-blog-release-20260811-v8/deploy/install-release.sh
```

脚本会：

1. 检查博客、康联云入口和原 `/assets/`；
2. 把当前网页与旧服务备份到 `/home/xiaoliu/backups/`；
3. 移除旧的错误示例简历，但在备份目录保留恢复副本；
4. 发布新页面；
5. 安装并启动 `personal-blog-resume` 轻量服务；
6. 首次部署时生成管理口令，保存到 `/etc/personal-blog-resume.env`；
7. 验证服务、博客首页和康联云入口。

出现 `STATIC_AND_SERVICE_OK` 才表示本机安装完成。

## 3. 接入 Nginx

把 `deploy/nginx-blog-api-location.conf` 中的 `location /blog-api/` 放入现有 `xiaoliudev.com` HTTPS `server` 块。不要改动已有 `/api/` 和 `/assets/`。

修改后：

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -fsS https://xiaoliudev.com/blog-api/health
```

只有 `nginx -t` 成功才能重载。健康接口应返回：

```json
{"ok": true}
```

## 管理中心

访问：

```text
https://xiaoliudev.com/#/manage
```

管理中心可以：

- 在“文章”页面创建、发布或删除文章，发布时间由系统自动生成；
- 查看访客留下的微信、电话或邮箱；
- 标记合作留言为新留言、已联系或已结束；
- 审核评论，通过后才会公开；
- 删除不合适的评论或合作记录。

查看管理口令：

```bash
sudo sed -n 's/^RESUME_ADMIN_TOKEN=//p' /etc/personal-blog-resume.env
```

口令不得写入 GitHub、网页配置、截图或聊天记录。网页只将口令保存在当前浏览器会话中。

## 数据位置

```text
/var/lib/personal-blog-resumes/blog.db              # 发布文章、点赞、评论、合作联系方式
/var/lib/personal-blog-resumes/resumes.json         # 公开简历版本记录
/var/lib/personal-blog-resumes/files/               # 正在公开的 PDF
/var/lib/personal-blog-resumes/deleted-resumes.json # 删除的简历记录
/var/lib/personal-blog-resumes/trash/               # 简历恢复副本
```

数据库目录权限为 `0700`，服务文件默认使用 `0077` 权限掩码。合作联系方式不会通过公开接口返回。

## 服务检查

```bash
sudo systemctl status personal-blog-resume --no-pager
sudo journalctl -u personal-blog-resume -n 80 --no-pager
curl -fsS http://127.0.0.1:8091/health
```

## 备份重点

```text
/var/lib/personal-blog-resumes
/etc/personal-blog-resume.env
```

前者包含 SQLite 数据库与历史简历，后者是管理口令；两者都不能提交到 Git。
