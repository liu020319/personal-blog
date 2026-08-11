#!/usr/bin/env bash
set -Eeuo pipefail

SITE_ROOT="/var/www/dsms"
BLOG_ARCHIVE_URL="https://github.com/liu020319/personal-blog/archive/refs/heads/main.tar.gz"
LOCAL_BLOG_ZIP="/home/xiaoliu/personal-blog-site-20260811.zip"
STAMP="$(date +%Y%m%d-%H%M%S)"
WORK_DIR="$(mktemp -d)"
BACKUP_DIR="/home/xiaoliu/backups/personal-blog-${STAMP}"
ORIGINAL_INDEX="${WORK_DIR}/original-index.html"
INSTALL_STARTED=0

cleanup() {
  rm -rf -- "${WORK_DIR}"
}

rollback() {
  if [[ "${INSTALL_STARTED}" -eq 1 && -f "${ORIGINAL_INDEX}" ]]; then
    echo "验证失败，正在恢复原首页……" >&2
    sudo cp -- "${ORIGINAL_INDEX}" "${SITE_ROOT}/index.html"
    sudo nginx -t
    sudo systemctl reload nginx
  fi
}

trap cleanup EXIT
trap rollback ERR

echo "[1/7] 检查现有康联云网页目录"
test -d "${SITE_ROOT}"
test -f "${SITE_ROOT}/index.html"
test -d "${SITE_ROOT}/assets"

echo "[2/7] 准备博客文件"
mkdir -p "${WORK_DIR}/source"
if [[ -f "${LOCAL_BLOG_ZIP}" ]]; then
  command -v unzip >/dev/null
  unzip -q "${LOCAL_BLOG_ZIP}" -d "${WORK_DIR}/source"
else
  curl -fsSL --retry 3 --connect-timeout 15 "${BLOG_ARCHIVE_URL}" -o "${WORK_DIR}/blog.tar.gz"
  tar -xzf "${WORK_DIR}/blog.tar.gz" --strip-components=1 -C "${WORK_DIR}/source"
fi
test -f "${WORK_DIR}/source/index.html"
test -f "${WORK_DIR}/source/blog-assets/app.js"
test -f "${WORK_DIR}/source/blog-assets/data.js"
test -f "${WORK_DIR}/source/blog-assets/styles.css"
test -f "${WORK_DIR}/source/resumes/current/xiaoliu-java-resume-current.pdf"

echo "[3/7] 备份当前网页"
mkdir -p "$(dirname "${BACKUP_DIR}")"
sudo cp -a -- "${SITE_ROOT}" "${BACKUP_DIR}"
sudo cp -- "${SITE_ROOT}/index.html" "${ORIGINAL_INDEX}"

echo "[4/7] 保存康联云子目录入口"
sudo mkdir -p "${SITE_ROOT}/kanglian-cloud"
if ! grep -q '个人技术博客' "${SITE_ROOT}/index.html"; then
  sudo cp -- "${SITE_ROOT}/index.html" "${SITE_ROOT}/kanglian-cloud/index.html"
fi
test -f "${SITE_ROOT}/kanglian-cloud/index.html"

echo "[5/7] 安装博客静态文件"
INSTALL_STARTED=1
sudo mkdir -p "${SITE_ROOT}/blog-assets"
sudo cp -a -- "${WORK_DIR}/source/blog-assets/." "${SITE_ROOT}/blog-assets/"
sudo mkdir -p "${SITE_ROOT}/resumes"
sudo cp -a -- "${WORK_DIR}/source/resumes/." "${SITE_ROOT}/resumes/"
for file in index.html 404.html rss.xml sitemap.xml robots.txt .nojekyll; do
  sudo cp -- "${WORK_DIR}/source/${file}" "${SITE_ROOT}/${file}"
done

echo "[6/7] 检查并重载 Nginx"
sudo nginx -t
sudo systemctl reload nginx

echo "[7/7] 验证博客和康联云入口"
sleep 1
curl -fsSL --connect-timeout 15 https://xiaoliudev.com/ | grep -q '个人技术博客'
curl -fsSL --connect-timeout 15 https://xiaoliudev.com/kanglian-cloud/ | grep -Eq '家庭慢病|康联云'

INSTALL_STARTED=0
trap - ERR
echo "DEPLOY_OK"
echo "备份目录：${BACKUP_DIR}"
