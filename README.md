# 小刘的个人技术博客

以静态主站为核心的个人技术博客。站点包含首页、文章、归档、分类标签、全文搜索、项目空间、可管理简历仓库、关于页、深浅主题、RSS、站点地图和移动端适配。

## 本地预览

在本目录启动自带的零依赖预览服务：

```powershell
node scripts/serve.js
```

然后访问 `http://127.0.0.1:4173/`。

## 新增文章

打开 `blog-assets/data.js`，在 `BLOG_DATA.posts` 数组中复制一项，并修改：

- `slug`：文章唯一英文地址；
- `title`、`excerpt`：标题和摘要；
- `date`、`category`、`tags`：发布日期、分类和标签；
- `content`：文章正文 HTML。

## 新增项目

打开 `blog-assets/data.js`，在 `BLOG_DATA.projects` 数组中复制一项。`url` 填项目登录页，`source` 填公开源码地址。不要填写账号、密码、数据库地址或其他生产配置。

## 管理简历仓库

- 部署 `resume-service/` 中的轻量服务，并通过 Nginx 将 `/resume-api/` 转发到 `127.0.0.1:8091`；
- 在简历仓库页面点击“上传新简历”，输入服务器生成的管理口令；
- 每份 PDF 独立保存，可以设为当前版或从公开区删除；
- 删除后的文件进入服务器恢复区，不继续公开；
- 上传前必须检查真实姓名、私人联系方式、家庭地址、账号凭据、内部地址及公司保密内容。

## 发布到 GitHub Pages

仓库创建并推送后，在 GitHub 仓库的 `Settings → Pages` 中选择：

- Source：`Deploy from a branch`
- Branch：`main`
- Folder：`/ (root)`

GitHub Pages 可以作为备用预览地址；正式站点部署在 `https://xiaoliudev.com/`，服务器发布方法见 `deploy/DEPLOY-GUIDE-ZH.md`。

## 技术说明

- 文章与项目页面零运行时依赖，浏览器直接加载；
- Hash 路由，兼容 GitHub Pages 子目录；
- 搜索和主题切换均在浏览器本地完成；
- 简历服务只使用 Python 标准库，不使用数据库；
- 管理口令只保存在服务器环境文件和当前浏览器会话；
- 博客与康联云业务系统完全分离。
