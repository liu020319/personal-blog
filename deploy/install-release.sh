#!/usr/bin/env bash
set -Eeuo pipefail

RELEASE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_ROOT="/var/www/dsms"
SERVICE_ROOT="/opt/personal-blog-resume"
SERVICE_UNIT="/etc/systemd/system/personal-blog-resume.service"
SERVICE_ENV="/etc/personal-blog-resume.env"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/home/xiaoliu/backups/personal-blog-v6-${STAMP}"
TOKEN_TEMP=""

cleanup() {
  if [[ -n "${TOKEN_TEMP}" && -f "${TOKEN_TEMP}" ]]; then
    rm -f -- "${TOKEN_TEMP}"
  fi
}
trap cleanup EXIT

echo "[1/8] 检查发布包和现有站点"
test -f "${RELEASE_ROOT}/index.html"
test -f "${RELEASE_ROOT}/blog-assets/app.js"
test -f "${RELEASE_ROOT}/blog-assets/resume-repository.js"
test -f "${RELEASE_ROOT}/resume-service/resume_service.py"
test -f "${SITE_ROOT}/index.html"
test -d "${SITE_ROOT}/assets"
test -f "${SITE_ROOT}/kanglian-cloud/index.html"
command -v python3 >/dev/null
command -v openssl >/dev/null
command -v curl >/dev/null

echo "[2/8] 备份当前网页和简历服务"
mkdir -p "${BACKUP_DIR}"
sudo cp -a -- "${SITE_ROOT}" "${BACKUP_DIR}/webroot"
if [[ -d "${SERVICE_ROOT}" ]]; then
  sudo cp -a -- "${SERVICE_ROOT}" "${BACKUP_DIR}/service"
fi
if [[ -f "${SERVICE_UNIT}" ]]; then
  sudo cp -a -- "${SERVICE_UNIT}" "${BACKUP_DIR}/personal-blog-resume.service"
fi

echo "[3/8] 移除错误的静态示例简历"
if [[ -d "${SITE_ROOT}/resumes" ]]; then
  sudo mv -- "${SITE_ROOT}/resumes" "${BACKUP_DIR}/removed-static-resumes"
fi

echo "[4/8] 安装博客静态页面"
sudo install -d -m 0755 "${SITE_ROOT}/blog-assets"
sudo cp -a -- "${RELEASE_ROOT}/blog-assets/." "${SITE_ROOT}/blog-assets/"
for file in index.html 404.html rss.xml sitemap.xml robots.txt .nojekyll; do
  sudo install -m 0644 "${RELEASE_ROOT}/${file}" "${SITE_ROOT}/${file}"
done

echo "[5/8] 安装轻量博客数据服务"
sudo install -d -m 0755 "${SERVICE_ROOT}"
sudo install -m 0755 "${RELEASE_ROOT}/resume-service/resume_service.py" "${SERVICE_ROOT}/resume_service.py"
sudo install -m 0644 "${RELEASE_ROOT}/resume-service/personal-blog-resume.service" "${SERVICE_UNIT}"

if [[ ! -f "${SERVICE_ENV}" ]]; then
  TOKEN_TEMP="$(mktemp)"
  RESUME_TOKEN="$(openssl rand -hex 32)"
  printf 'RESUME_ADMIN_TOKEN=%s\n' "${RESUME_TOKEN}" > "${TOKEN_TEMP}"
  sudo install -o root -g root -m 0600 "${TOKEN_TEMP}" "${SERVICE_ENV}"
  unset RESUME_TOKEN
fi

sudo systemctl daemon-reload
sudo systemctl enable --now personal-blog-resume

echo "[6/8] 验证博客数据服务本机接口"
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS --connect-timeout 2 http://127.0.0.1:8091/health >/dev/null; then
    break
  fi
  if [[ "${attempt}" -eq 10 ]]; then
    echo "博客数据服务启动失败，请检查：sudo journalctl -u personal-blog-resume -n 80 --no-pager" >&2
    exit 1
  fi
  sleep 1
done
curl -fsS http://127.0.0.1:8091/resumes

echo "[7/8] 检查并重载 Nginx"
sudo nginx -t
sudo systemctl reload nginx

echo "[8/8] 验证博客与康联云入口"
curl -fsSL --connect-timeout 15 https://xiaoliudev.com/ | grep -q '个人技术博客'
curl -fsSL --connect-timeout 15 https://xiaoliudev.com/kanglian-cloud/ | grep -Eq '家庭慢病|康联云'

echo "STATIC_AND_SERVICE_OK"
echo "备份目录：${BACKUP_DIR}"
if sudo nginx -T 2>&1 | grep -q 'location /blog-api/'; then
  curl -fsS --connect-timeout 15 https://xiaoliudev.com/blog-api/health >/dev/null
  echo "BLOG_API_PUBLIC_OK"
else
  echo "NEXT_STEP_REQUIRED：现有 HTTPS server 块还需要加入 deploy/nginx-blog-api-location.conf"
fi
echo "管理口令查看命令：sudo sed -n 's/^RESUME_ADMIN_TOKEN=//p' ${SERVICE_ENV}"
