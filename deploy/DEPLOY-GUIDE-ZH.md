# xiaoliudev.com 博客 V2 发布说明

## 最终访问关系

- `https://xiaoliudev.com/`：个人博客静态主站；
- `https://xiaoliudev.com/kanglian-cloud/#/login`：康联云登录页；
- `https://xiaoliudev.com/resume-api/`：简历仓库轻量接口；
- `https://xiaoliudev.com/api/`：继续转发到原 Spring Boot 服务。

文章、项目、搜索和主题仍是静态功能。只有简历上传、删除和“设为当前版”使用一个 Python 标准库服务，不使用数据库，默认仅监听 `127.0.0.1:8091`。

## 发布包

本地成品：

```text
D:\CodexWorkFiles\output\personal-blog-release-20260811-v2.zip
```

上传到服务器：

```text
/home/xiaoliu/personal-blog-release-20260811-v2.zip
```

建议解压目录：

```text
/home/xiaoliu/personal-blog-release-20260811-v2
```

## 发布流程

### 1. 解压

```bash
mkdir -p /home/xiaoliu/personal-blog-release-20260811-v2
unzip -q /home/xiaoliu/personal-blog-release-20260811-v2.zip \
  -d /home/xiaoliu/personal-blog-release-20260811-v2
```

### 2. 安装静态页面与简历服务

```bash
bash /home/xiaoliu/personal-blog-release-20260811-v2/deploy/install-release.sh
```

脚本会：

1. 检查现有博客、康联云入口和 `/assets/`；
2. 把当前网页备份到 `/home/xiaoliu/backups/`；
3. 将旧的错误示例简历移出线上目录并保留在备份中；
4. 发布新的博客静态文件；
5. 安装并启动 `personal-blog-resume` 服务；
6. 首次部署时生成 64 位管理口令，保存到 `/etc/personal-blog-resume.env`；
7. 检查 Nginx 与两个已有网页入口。

出现 `STATIC_AND_SERVICE_OK` 表示页面和本机简历服务正常。

### 3. 把简历接口接入现有 HTTPS 站点

将 `deploy/nginx-resume-api-location.conf` 中的 `location /resume-api/` 放进现有 `xiaoliudev.com` HTTPS `server` 块。不要改动已有 `/api/` 和 `/assets/`。

修改后：

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -fsS https://xiaoliudev.com/resume-api/health
```

只有 `nginx -t` 成功才允许重载。健康接口应返回：

```json
{"ok": true}
```

## 管理口令

查看口令：

```bash
sudo sed -n 's/^RESUME_ADMIN_TOKEN=//p' /etc/personal-blog-resume.env
```

口令不要发给任何人，也不要写入 GitHub、博客配置或聊天截图。网页只把它放在当前浏览器的 `sessionStorage`；关闭页面后自动清除。

## 简历数据位置

```text
/var/lib/personal-blog-resumes/resumes.json          # 公开版本记录
/var/lib/personal-blog-resumes/files/                # 正在公开的 PDF
/var/lib/personal-blog-resumes/deleted-resumes.json  # 删除记录
/var/lib/personal-blog-resumes/trash/                # 删除后的服务器恢复副本
```

网页删除后会立即从公开列表消失，但服务器保留恢复副本，避免误删后完全找不回来。

## 服务检查

```bash
sudo systemctl status personal-blog-resume --no-pager
sudo journalctl -u personal-blog-resume -n 80 --no-pager
curl -fsS http://127.0.0.1:8091/health
```

## 备份重点

以后备份服务器时，除原来的业务系统外，还要备份：

```text
/var/lib/personal-blog-resumes
/etc/personal-blog-resume.env
```

前者是历史简历数据，后者是管理口令。两者都不要提交到 Git。
