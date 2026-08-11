# xiaoliudev.com 发布说明

## 最终访问关系

- `https://xiaoliudev.com/`：个人博客；
- `https://xiaoliudev.com/kanglian-cloud/#/login`：康联云登录页；
- `https://xiaoliudev.com/api/`：继续转发到原 Spring Boot 服务。

博客是纯静态文件，不启动新进程、不增加数据库，也不会长期占用额外内存。

## 服务器目录

```text
/var/www/dsms/                       # 现有 Nginx 网站根目录，放博客首页
/var/www/dsms/assets/                # 保留：康联云原静态资源
/var/www/dsms/kanglian-cloud/        # 新增：康联云子目录入口
/var/www/dsms/blog-assets/           # 新增：博客独立静态资源
```

## 推荐发布方式

先把本地打包文件上传到服务器固定位置：

```text
/home/xiaoliu/personal-blog-site-20260811.zip
```

本地成品位于 `D:\CodexWorkFiles\output\personal-blog-site-20260811.zip`。上传完成前不要执行下面的部署命令。

仓库内的 `server-install.sh` 会自动执行以下操作：

1. 检查现有 `/var/www/dsms/index.html` 和 `/var/www/dsms/assets/`；
2. 优先读取 `/home/xiaoliu/personal-blog-site-20260811.zip`，不存在时才从 GitHub 下载；
3. 将当前网页完整备份到 `/home/xiaoliu/backups/`；
4. 把原康联云首页复制到 `/kanglian-cloud/index.html`；
5. 安装博客首页和 `/blog-assets/`；
6. 执行 `nginx -t`、重载 Nginx，并访问两个入口验证；
7. 任一步失败时恢复原首页。

登录服务器后执行：

```bash
curl -fsSL https://raw.githubusercontent.com/liu020319/personal-blog/main/deploy/server-install.sh | bash
```

脚本运行中会正常询问 `sudo` 密码。最后出现 `DEPLOY_OK` 才表示脚本完成。

## 手工发布顺序

### 1. 先备份当前网页

```bash
stamp=$(date +%Y%m%d-%H%M%S)
sudo cp -a /var/www/dsms "/var/www/dsms.backup-$stamp"
```

作用：保留当前可访问版本。复制命令成功后再继续；报错就停止。

### 2. 保存康联云入口并上传博客

先创建康联云子目录，并保存当前首页：

```bash
sudo mkdir -p /var/www/dsms/kanglian-cloud
sudo cp /var/www/dsms/index.html /var/www/dsms/kanglian-cloud/index.html
```

然后把博客文件上传到 `/var/www/dsms/`。成功标准是服务器存在：

```text
/var/www/dsms/index.html
/var/www/dsms/kanglian-cloud/index.html
/var/www/dsms/blog-assets/app.js
/var/www/dsms/blog-assets/data.js
/var/www/dsms/blog-assets/styles.css
```

这套布局沿用现有 Nginx 根目录，不修改 `/api/`、`/uploads/` 或 `/assets/` 配置。

### 3. 只检查配置，先不要重载

```bash
sudo nginx -t
```

出现 `syntax is ok` 和 `test is successful` 才能继续。否则不要重载，先修正配置。

### 4. 重载并验证

```bash
sudo systemctl reload nginx
curl -I http://127.0.0.1/ -H 'Host: xiaoliudev.com'
curl -I http://127.0.0.1/kanglian-cloud/ -H 'Host: xiaoliudev.com'
curl -I http://127.0.0.1/api/ -H 'Host: xiaoliudev.com'
```

前两个地址应返回 `200`，`/api/` 可能返回业务状态或 `404/405`，但不能是 Nginx 的 `502`。最后再用浏览器检查博客首页、康联云登录页和一次真实登录。

## 回滚

如果博客或康联云入口异常，恢复刚才备份的 Nginx 配置后执行：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

只有 `nginx -t` 成功才能重载。网页文件不必立刻删除，旧配置恢复后会重新指向原康联云目录。

## HTTPS

当前已验证 `https://xiaoliudev.com/` 返回 200，证书覆盖 `xiaoliudev.com` 与 `www.xiaoliudev.com`，有效期至 2026-11-06。修改 Nginx 时要同步调整现有的 443 `server` 块；如果 HTTP 与 HTTPS 分开配置，HTTP 块只保留跳转，以上 location 应放入 HTTPS 块。
