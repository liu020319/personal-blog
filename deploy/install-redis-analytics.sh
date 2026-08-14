#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_ENV="/etc/personal-blog-resume.env"
REDIS_CONFIG="/etc/redis/xiaoliu-blog.conf"
REDIS_UNIT="/etc/systemd/system/xiaoliu-blog-redis.service"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/home/xiaoliu/backups/redis-analytics-${STAMP}"
PASSWORD_TEMP=""
HEALTH_TEMP=""

cleanup() {
  if [[ -n "${PASSWORD_TEMP}" && -f "${PASSWORD_TEMP}" ]]; then
    rm -f -- "${PASSWORD_TEMP}"
  fi
  if [[ -n "${HEALTH_TEMP}" && -f "${HEALTH_TEMP}" ]]; then
    rm -f -- "${HEALTH_TEMP}"
  fi
}
trap cleanup EXIT

echo "[1/6] 检查博客环境文件"
test -f "${SERVICE_ENV}"
command -v openssl >/dev/null
command -v curl >/dev/null

echo "[2/6] 安装 Redis 服务和 Python 客户端"
if ! command -v redis-server >/dev/null || ! /usr/bin/python3 -c 'import redis' >/dev/null 2>&1; then
  sudo apt-get update
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y redis-server python3-redis
fi
command -v redis-cli >/dev/null
/usr/bin/python3 -c 'import redis; print("PYTHON_REDIS_READY", redis.__version__)'

echo "[3/6] 备份已有 Redis 配置"
mkdir -p "${BACKUP_DIR}"
chmod 0700 "${BACKUP_DIR}"
if [[ -f "${REDIS_CONFIG}" ]]; then
  sudo cp -a -- "${REDIS_CONFIG}" "${BACKUP_DIR}/xiaoliu-blog.conf"
fi
if [[ -f "${REDIS_UNIT}" ]]; then
  sudo cp -a -- "${REDIS_UNIT}" "${BACKUP_DIR}/xiaoliu-blog-redis.service"
fi
sudo cp -a -- "${SERVICE_ENV}" "${BACKUP_DIR}/personal-blog-resume.env"

echo "[4/6] 配置仅本机可访问、最大使用 64MB 的 Redis"
PASSWORD_TEMP="$(mktemp)"
REDIS_PASSWORD="$(sudo sed -n 's/^requirepass //p' "${REDIS_CONFIG}" 2>/dev/null | tail -n 1 || true)"
if [[ "${#REDIS_PASSWORD}" -lt 32 ]]; then
  REDIS_PASSWORD="$(openssl rand -hex 32)"
fi
cat > "${PASSWORD_TEMP}" <<EOF
include /etc/redis/redis.conf
bind 127.0.0.1 ::1
protected-mode yes
port 6381
pidfile /run/xiaoliu-blog-redis/redis.pid
logfile ""
dbfilename xiaoliu-blog.rdb
requirepass ${REDIS_PASSWORD}
maxmemory 64mb
maxmemory-policy allkeys-lru
appendonly no
EOF
sudo install -o root -g redis -m 0640 "${PASSWORD_TEMP}" "${REDIS_CONFIG}"
cat > "${PASSWORD_TEMP}" <<'EOF'
[Unit]
Description=Xiaoliu Blog Redis Analytics
After=network.target

[Service]
Type=notify
User=redis
Group=redis
RuntimeDirectory=xiaoliu-blog-redis
RuntimeDirectoryMode=0750
ExecStart=/usr/bin/redis-server /etc/redis/xiaoliu-blog.conf --supervised systemd --daemonize no
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=full
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
LockPersonality=yes
MemoryDenyWriteExecute=yes
MemoryMax=96M
TasksMax=32

[Install]
WantedBy=multi-user.target
EOF
sudo install -o root -g root -m 0644 "${PASSWORD_TEMP}" "${REDIS_UNIT}"

sudo sed -i '/^BLOG_REDIS_URL=/d;/^BLOG_REDIS_PREFIX=/d;/^BLOG_REDIS_TIMEOUT=/d' "${SERVICE_ENV}"
printf 'BLOG_REDIS_URL=redis://:%s@127.0.0.1:6381/0\n' "${REDIS_PASSWORD}" | sudo tee -a "${SERVICE_ENV}" >/dev/null
printf '%s\n' 'BLOG_REDIS_PREFIX=xiaoliu:blog' 'BLOG_REDIS_TIMEOUT=0.35' | sudo tee -a "${SERVICE_ENV}" >/dev/null
sudo chmod 0600 "${SERVICE_ENV}"

echo "[5/6] 启动 Redis 并重启博客服务"
sudo systemctl daemon-reload
sudo systemctl enable xiaoliu-blog-redis
sudo systemctl restart xiaoliu-blog-redis
REDISCLI_AUTH="${REDIS_PASSWORD}" redis-cli -p 6381 ping | grep -Fxq PONG
sudo systemctl restart personal-blog-resume

echo "[6/6] 验证 Redis 与站点脉搏接口"
HEALTH_TEMP="$(mktemp)"
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS --connect-timeout 2 -o "${HEALTH_TEMP}" http://127.0.0.1:8091/health \
    && grep -Fq '"available": true' "${HEALTH_TEMP}"; then
    break
  fi
  if [[ "${attempt}" -eq 10 ]]; then
    echo "Redis 或博客服务启动失败，请检查 systemctl status 与 journalctl。" >&2
    exit 1
  fi
  sleep 1
done
curl -fsS http://127.0.0.1:8091/analytics/summary
echo
echo "REDIS_ANALYTICS_OK"
echo "Redis 备份目录：${BACKUP_DIR}"
unset REDIS_PASSWORD
