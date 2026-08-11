# 小刘的个人技术博客

一个不需要数据库和常驻后端的个人技术博客。站点包含首页、文章、归档、分类标签、全文搜索、项目空间、简历仓库、关于页、深浅主题、RSS、站点地图和移动端适配。

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

## 更新简历仓库

- 当前版放在 `resumes/current/`；
- 历史版按日期放在 `resumes/archive/`，旧文件不覆盖；
- 在 `blog-assets/data.js` 的 `resume.history` 中增加版本、阶段和变化说明；
- 公开 PDF 统一使用“小刘”，发布前检查电话、私人邮箱、项目账号密码和 PDF 元数据。

## 发布到 GitHub Pages

仓库创建并推送后，在 GitHub 仓库的 `Settings → Pages` 中选择：

- Source：`Deploy from a branch`
- Branch：`main`
- Folder：`/ (root)`

GitHub Pages 可以作为备用预览地址；正式站点部署在 `https://xiaoliudev.com/`，服务器发布方法见 `deploy/DEPLOY-GUIDE-ZH.md`。

## 技术说明

- 零运行时依赖，浏览器直接加载；
- Hash 路由，兼容 GitHub Pages 子目录；
- 搜索和主题切换均在浏览器本地完成；
- 博客与康联云业务系统完全分离。
