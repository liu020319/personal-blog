#!/usr/bin/env python3
"""Small authenticated resume repository service for xiaoliudev.com.

Public visitors can list and read published PDFs. Mutating operations require a
Bearer token supplied through RESUME_ADMIN_TOKEN. Files and metadata stay on the
server; the token is never embedded in the static site or returned by the API.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import os
import re
import smtplib
import ssl
import shutil
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from email.parser import BytesParser
from email.policy import default as email_policy
from email.message import EmailMessage
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

try:
    import redis as redis_library
except ImportError:  # Redis analytics is optional; the rest of the blog stays available.
    redis_library = None


HOST = os.environ.get("RESUME_HOST", "127.0.0.1")
PORT = int(os.environ.get("RESUME_PORT", "8091"))
DATA_DIR = Path(os.environ.get("RESUME_DATA_DIR", "/var/lib/personal-blog-resumes"))
FILES_DIR = DATA_DIR / "files"
TRASH_DIR = DATA_DIR / "trash"
INDEX_FILE = DATA_DIR / "resumes.json"
DELETED_INDEX_FILE = DATA_DIR / "deleted-resumes.json"
DATABASE_FILE = DATA_DIR / "blog.db"
ADMIN_TOKEN = os.environ.get("RESUME_ADMIN_TOKEN", "")
NOTIFY_EMAIL = os.environ.get("BLOG_NOTIFY_EMAIL", "").strip()
SMTP_HOST = os.environ.get("BLOG_SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("BLOG_SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("BLOG_SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.environ.get("BLOG_SMTP_PASSWORD", "").replace(" ", "")
SMTP_STARTTLS = os.environ.get("BLOG_SMTP_STARTTLS", "true").lower() == "true"
SMTP_SSL = os.environ.get("BLOG_SMTP_SSL", "false").lower() == "true"
EMAIL_NOTIFICATIONS_ENABLED = os.environ.get("BLOG_EMAIL_NOTIFICATIONS", "false").lower() == "true"
REDIS_URL = os.environ.get("BLOG_REDIS_URL", "").strip()
REDIS_PREFIX = os.environ.get("BLOG_REDIS_PREFIX", "xiaoliu:blog").strip() or "xiaoliu:blog"
REDIS_TIMEOUT = max(0.1, min(2.0, float(os.environ.get("BLOG_REDIS_TIMEOUT", "0.35"))))
HTTP_WORKERS = max(2, min(32, int(os.environ.get("BLOG_HTTP_WORKERS", "16"))))
HTTP_QUEUE = max(8, min(256, int(os.environ.get("BLOG_HTTP_QUEUE", "64"))))
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 256 * 1024
LOCK = threading.RLock()
RATE_LOCK = threading.Lock()
RATE_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)
EMAIL_DELIVERY_SLOTS = threading.BoundedSemaphore(2)
REDIS_CLIENT_LOCK = threading.Lock()
REDIS_CLIENT = None
REDIS_WARNING_LOCK = threading.Lock()
REDIS_LAST_WARNING = 0.0

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9-]{12,80}$")
ARTICLE_SLUG_RE = re.compile(r"^[a-z0-9-]{2,100}$")
VISITOR_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
UNSAFE_METADATA_RE = re.compile(
    r"(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?<!\d)1[3-9]\d{9}(?!\d)|"
    r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)|密码|口令|secret|token|access[_-]?key)",
    re.IGNORECASE,
)
PUBLIC_PII_RE = re.compile(
    r"(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?<!\d)1[3-9]\d{9}(?!\d)|"
    r"https?://|(?:微信|手机号|电话|邮箱)\s*[:：])",
    re.IGNORECASE,
)
COMMENT_REVIEW_RE = re.compile(
    r"(?:加\s*[微薇vV]|私聊|代(?:写|做)|包过|刷单|返利|博彩|贷款|推广|广告|免费领取|点击领取|QQ群|群号)",
    re.IGNORECASE,
)
EXCESSIVE_REPEAT_RE = re.compile(r"(.)\1{7,}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_storage() -> None:
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        atomic_write_json([])
    if not DELETED_INDEX_FILE.exists():
        atomic_write_deleted_json([])
    initialize_database()


def database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_FILE, timeout=8)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 8000")
    return connection


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_FILE, timeout=8) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS article_likes (
              article_slug TEXT NOT NULL,
              visitor_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY (article_slug, visitor_hash)
            );
            CREATE TABLE IF NOT EXISTS article_comments (
              id TEXT PRIMARY KEY,
              article_slug TEXT NOT NULL,
              nickname TEXT NOT NULL,
              content TEXT NOT NULL,
              status TEXT NOT NULL CHECK (status IN ('pending', 'approved')),
              created_at TEXT NOT NULL,
              approved_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_comments_public
              ON article_comments(article_slug, status, created_at);
            CREATE TABLE IF NOT EXISTS cooperation_leads (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              contact_method TEXT NOT NULL,
              contact_value TEXT NOT NULL,
              requirement TEXT NOT NULL,
              status TEXT NOT NULL CHECK (status IN ('new', 'contacted', 'closed')),
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_leads_status
              ON cooperation_leads(status, created_at);
            CREATE TABLE IF NOT EXISTS published_articles (
              slug TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              excerpt TEXT NOT NULL,
              category TEXT NOT NULL,
              tags_json TEXT NOT NULL,
              content_text TEXT NOT NULL,
              published_date TEXT NOT NULL,
              reading_minutes INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_published_articles_date
              ON published_articles(published_date DESC, created_at DESC);
            CREATE TABLE IF NOT EXISTS hidden_articles (
              slug TEXT PRIMARY KEY,
              hidden_at TEXT NOT NULL
            );
            """
        )


def get_redis_client():
    global REDIS_CLIENT
    if not REDIS_URL or redis_library is None:
        return None
    if REDIS_CLIENT is not None:
        return REDIS_CLIENT
    with REDIS_CLIENT_LOCK:
        if REDIS_CLIENT is None:
            REDIS_CLIENT = redis_library.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=REDIS_TIMEOUT,
                socket_timeout=REDIS_TIMEOUT,
                health_check_interval=30,
            )
    return REDIS_CLIENT


def log_redis_warning(scope: str, exc: Exception) -> None:
    global REDIS_LAST_WARNING
    now = time.monotonic()
    with REDIS_WARNING_LOCK:
        if now - REDIS_LAST_WARNING < 30:
            return
        REDIS_LAST_WARNING = now
    print(f"redis {scope} unavailable: {type(exc).__name__}", flush=True)


def check_rate(client: str, action: str, limit: int, window_seconds: int) -> bool:
    redis_client = get_redis_client()
    if redis_client is not None:
        bucket = int(time.time()) // window_seconds
        key = f"{REDIS_PREFIX}:rate:{action}:{bucket}:{client}"
        try:
            pipeline = redis_client.pipeline(transaction=True)
            pipeline.incr(key)
            pipeline.expire(key, window_seconds + 5)
            current, _ = pipeline.execute()
            return int(current) <= limit
        except Exception as exc:  # Keep public forms available if Redis is temporarily down.
            log_redis_warning("rate limiter", exc)

    now = time.monotonic()
    key = (client, action)
    with RATE_LOCK:
        bucket = RATE_BUCKETS[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def clean_analytics_page(value: object) -> str:
    page = str(value or "home").strip().lower()
    allowed = {"home", "articles", "article", "archive", "projects", "services", "resume", "about", "pulse"}
    if page not in allowed:
        raise ValueError("页面标识不正确")
    return page


def analytics_visitor_hash(client_key: str, visitor_id: object) -> str:
    visitor = str(visitor_id or "")
    if not VISITOR_ID_RE.fullmatch(visitor):
        raise ValueError("访客标识不正确")
    return hashlib.sha256(f"{client_key}:{visitor}".encode("utf-8")).hexdigest()


def record_analytics_visit(client_key: str, payload: dict) -> dict:
    redis_client = get_redis_client()
    if redis_client is None:
        return {"ok": True, "available": False, "message": "实时统计服务暂未启用"}

    page = clean_analytics_page(payload.get("page"))
    slug = str(payload.get("articleSlug") or "").strip()
    if page == "article":
        slug = valid_article_slug(slug)
    elif slug:
        raise ValueError("文章标识与页面不匹配")

    visitor_hash = analytics_visitor_hash(client_key, payload.get("visitorId"))
    heartbeat = payload.get("heartbeat") is True
    today = date.today().strftime("%Y%m%d")
    now = int(time.time())
    page_key = hashlib.sha256(f"{page}:{slug}".encode("utf-8")).hexdigest()[:16]
    dedupe_key = f"{REDIS_PREFIX}:dedupe:{today}:{visitor_hash}:{page_key}"
    try:
        counted = False if heartbeat else bool(redis_client.set(dedupe_key, "1", nx=True, ex=60))
        pipeline = redis_client.pipeline(transaction=True)
        online_key = f"{REDIS_PREFIX}:online"
        pipeline.zadd(online_key, {visitor_hash: now})
        pipeline.zremrangebyscore(online_key, 0, now - 300)
        pipeline.expire(online_key, 900)
        if counted:
            pv_key = f"{REDIS_PREFIX}:pv:{today}"
            uv_key = f"{REDIS_PREFIX}:uv:{today}"
            pipeline.incr(pv_key)
            pipeline.expire(pv_key, 8 * 86400)
            pipeline.pfadd(uv_key, visitor_hash)
            pipeline.expire(uv_key, 8 * 86400)
            if slug:
                pipeline.zincrby(f"{REDIS_PREFIX}:article:hot", 1, slug)
        pipeline.execute()
        return {"ok": True, "available": True, "counted": counted}
    except Exception as exc:
        log_redis_warning("analytics write", exc)
        return {"ok": True, "available": False, "message": "实时统计服务暂时不可用"}


def analytics_summary() -> dict:
    redis_client = get_redis_client()
    if redis_client is None:
        return {"ok": True, "available": False, "online": 0, "todayPv": 0, "todayUv": 0, "topArticles": []}
    today = date.today().strftime("%Y%m%d")
    now = int(time.time())
    try:
        pipeline = redis_client.pipeline(transaction=True)
        online_key = f"{REDIS_PREFIX}:online"
        pipeline.zremrangebyscore(online_key, 0, now - 300)
        pipeline.zcard(online_key)
        pipeline.get(f"{REDIS_PREFIX}:pv:{today}")
        pipeline.pfcount(f"{REDIS_PREFIX}:uv:{today}")
        pipeline.zrevrange(f"{REDIS_PREFIX}:article:hot", 0, 4, withscores=True)
        _, online, pv, uv, ranking = pipeline.execute()
        return {
            "ok": True,
            "available": True,
            "online": int(online or 0),
            "todayPv": int(pv or 0),
            "todayUv": int(uv or 0),
            "topArticles": [{"slug": slug, "views": int(score)} for slug, score in ranking],
            "windowMinutes": 5,
            "uvApproximate": True,
        }
    except Exception as exc:
        log_redis_warning("analytics read", exc)
        return {"ok": True, "available": False, "online": 0, "todayPv": 0, "todayUv": 0, "topArticles": []}


def clean_public_text(value: str, field: str, minimum: int, maximum: int) -> str:
    cleaned = " ".join(value.replace("\x00", " ").split()).strip()
    if not minimum <= len(cleaned) <= maximum:
        raise ValueError(f"{field} 长度应为 {minimum}-{maximum} 个字符")
    if PUBLIC_PII_RE.search(cleaned):
        raise ValueError(f"{field} 中不能公开联系方式或外部链接")
    return cleaned


def clean_private_text(value: str, field: str, minimum: int, maximum: int) -> str:
    cleaned = " ".join(value.replace("\x00", " ").split()).strip()
    if not minimum <= len(cleaned) <= maximum:
        raise ValueError(f"{field} 长度应为 {minimum}-{maximum} 个字符")
    return cleaned


def clean_article_content(value: str) -> str:
    cleaned = value.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not 20 <= len(cleaned) <= 30000:
        raise ValueError("文章正文长度应为 20-30000 个字符")
    return cleaned


def comment_requires_review(nickname: str, content: str) -> bool:
    combined = f"{nickname} {content}"
    return bool(COMMENT_REVIEW_RE.search(combined) or EXCESSIVE_REPEAT_RE.search(combined))


def email_notifications_configured() -> bool:
    return bool(
        EMAIL_NOTIFICATIONS_ENABLED
        and NOTIFY_EMAIL
        and SMTP_HOST
        and SMTP_USERNAME
        and SMTP_PASSWORD
    )


def deliver_email(message: EmailMessage) -> None:
    context = ssl.create_default_context()
    if SMTP_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10, context=context) as client:
            client.login(SMTP_USERNAME, SMTP_PASSWORD)
            client.send_message(message)
        return
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as client:
        client.ehlo()
        if SMTP_STARTTLS:
            client.starttls(context=context)
            client.ehlo()
        client.login(SMTP_USERNAME, SMTP_PASSWORD)
        client.send_message(message)


def send_comment_notification(article_slug: str, nickname: str, content: str, status: str, created_at: str) -> None:
    if not email_notifications_configured():
        return
    message = EmailMessage()
    message["Subject"] = "[小刘博客] 收到一条新评论"
    message["From"] = SMTP_USERNAME
    message["To"] = NOTIFY_EMAIL
    review_text = "已自动公开" if status == "approved" else "等待人工审核"
    message.set_content(
        "小刘的博客收到一条新评论。\n\n"
        f"文章：{article_slug}\n"
        f"称呼：{nickname}\n"
        f"状态：{review_text}\n"
        f"时间：{created_at}\n\n"
        f"评论内容：\n{content}\n\n"
        "管理中心：https://xiaoliudev.com/#/manage\n"
    )
    deliver_email(message)


def send_lead_notification(
    name: str,
    contact_method: str,
    contact_value: str,
    requirement: str,
    created_at: str,
) -> None:
    if not email_notifications_configured():
        return
    message = EmailMessage()
    message["Subject"] = "[小刘博客] 收到一条新合作需求"
    message["From"] = SMTP_USERNAME
    message["To"] = NOTIFY_EMAIL
    message.set_content(
        "小刘的博客收到一条新合作需求。\n\n"
        f"称呼：{name}\n"
        f"联系方式类型：{contact_method}\n"
        f"联系方式：{contact_value}\n"
        f"时间：{created_at}\n\n"
        f"需求说明：\n{requirement}\n\n"
        "管理中心：https://xiaoliudev.com/#/manage\n"
    )
    deliver_email(message)


def send_test_notification() -> None:
    if not email_notifications_configured():
        raise ValueError("邮件提醒尚未配置完整")
    message = EmailMessage()
    message["Subject"] = "[小刘博客] 邮件提醒测试成功"
    message["From"] = SMTP_USERNAME
    message["To"] = NOTIFY_EMAIL
    message.set_content(
        "这是一封来自小刘博客管理中心的测试邮件。\n\n"
        "收到这封邮件说明：评论提醒和合作需求提醒已经可以正常发送。\n"
    )
    deliver_email(message)


def notify_comment_async(article_slug: str, nickname: str, content: str, status: str, created_at: str) -> None:
    if not email_notifications_configured():
        return
    if not EMAIL_DELIVERY_SLOTS.acquire(blocking=False):
        print("comment notification email skipped because delivery slots are busy", flush=True)
        return

    def deliver() -> None:
        try:
            send_comment_notification(article_slug, nickname, content, status, created_at)
        except (OSError, smtplib.SMTPException):
            print("comment notification email failed", flush=True)
        finally:
            EMAIL_DELIVERY_SLOTS.release()

    threading.Thread(target=deliver, name="comment-email", daemon=True).start()


def notify_lead_async(
    name: str,
    contact_method: str,
    contact_value: str,
    requirement: str,
    created_at: str,
) -> None:
    if not email_notifications_configured():
        return
    if not EMAIL_DELIVERY_SLOTS.acquire(blocking=False):
        print("lead notification email skipped because delivery slots are busy", flush=True)
        return

    def deliver() -> None:
        try:
            send_lead_notification(name, contact_method, contact_value, requirement, created_at)
        except (OSError, smtplib.SMTPException):
            print("lead notification email failed", flush=True)
        finally:
            EMAIL_DELIVERY_SLOTS.release()

    threading.Thread(target=deliver, name="lead-email", daemon=True).start()


def masked_email(value: str) -> str:
    if "@" not in value:
        return ""
    local, domain = value.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def valid_article_slug(value: str) -> str:
    if not ARTICLE_SLUG_RE.fullmatch(value):
        raise ValueError("文章标识不正确")
    return value


def public_article(row: sqlite3.Row) -> dict:
    tags = json.loads(row["tags_json"])
    return {
        "slug": row["slug"],
        "title": row["title"],
        "excerpt": row["excerpt"],
        "category": row["category"],
        "tags": tags if isinstance(tags, list) else [],
        "contentText": row["content_text"],
        "date": row["published_date"],
        "readingMinutes": row["reading_minutes"],
        "createdAt": row["created_at"],
    }


def clean_article_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("文章标签格式不正确")
    tags: list[str] = []
    for item in value:
        tag = clean_private_text(str(item), "文章标签", 1, 20)
        if tag not in tags:
            tags.append(tag)
    if not 1 <= len(tags) <= 8:
        raise ValueError("文章标签需要填写 1-8 个")
    return tags


def atomic_write_json(items: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = INDEX_FILE.with_suffix(f".tmp-{uuid.uuid4().hex}")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(items, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, INDEX_FILE)


def atomic_write_deleted_json(items: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = DELETED_INDEX_FILE.with_suffix(f".tmp-{uuid.uuid4().hex}")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(items, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, DELETED_INDEX_FILE)


def load_items() -> list[dict]:
    ensure_storage()
    with INDEX_FILE.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, list):
        raise ValueError("resume index must be a JSON array")
    return value


def public_item(item: dict) -> dict:
    resume_id = item["id"]
    return {
        "id": resume_id,
        "version": item["version"],
        "stage": item["stage"],
        "date": item["date"],
        "change": item["change"],
        "current": bool(item.get("current")),
        "file": f"./blog-api/files/{resume_id}.pdf",
        "createdAt": item["createdAt"],
    }


def clean_text(value: str, field: str, minimum: int, maximum: int) -> str:
    cleaned = " ".join(value.replace("\x00", " ").split()).strip()
    if not minimum <= len(cleaned) <= maximum:
        raise ValueError(f"{field} 长度应为 {minimum}-{maximum} 个字符")
    if UNSAFE_METADATA_RE.search(cleaned):
        raise ValueError(f"{field} 中疑似包含联系方式、地址或凭据，请先脱敏")
    return cleaned


def parse_date(value: str) -> str:
    if not DATE_RE.fullmatch(value):
        raise ValueError("日期格式必须为 YYYY-MM-DD")
    date.fromisoformat(value)
    return value


def parse_multipart(content_type: str, body: bytes) -> tuple[dict[str, str], bytes, str]:
    message = BytesParser(policy=email_policy).parsebytes(
        b"Content-Type: " + content_type.encode("ascii", "strict") + b"\r\n"
        b"MIME-Version: 1.0\r\n\r\n" + body
    )
    if not message.is_multipart():
        raise ValueError("上传请求格式不正确")

    fields: dict[str, str] = {}
    pdf_bytes: bytes | None = None
    original_name = ""
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if name == "file" and filename:
            pdf_bytes = payload
            original_name = filename
        else:
            fields[name] = payload.decode(part.get_content_charset() or "utf-8", "strict")

    if pdf_bytes is None:
        raise ValueError("请选择 PDF 简历文件")
    return fields, pdf_bytes, original_name


def validate_pdf(content: bytes, original_name: str) -> None:
    if not original_name.lower().endswith(".pdf"):
        raise ValueError("只允许上传 PDF 文件")
    if not content.startswith(b"%PDF-"):
        raise ValueError("文件不是有效的 PDF")
    if not 100 <= len(content) <= MAX_UPLOAD_BYTES:
        raise ValueError("PDF 大小必须在 100 字节到 10 MB 之间")
    lowered = content.lower()
    for marker in (b"/javascript", b"/launch", b"/embeddedfile"):
        if marker in lowered:
            raise ValueError("PDF 包含脚本、启动动作或嵌入文件，不能公开上传")


class BoundedThreadPoolHTTPServer(HTTPServer):
    """A small fixed worker pool that rejects overload instead of spawning unlimited threads."""

    allow_reuse_address = True
    request_queue_size = 128

    def __init__(self, server_address: tuple[str, int], handler_class, workers: int, pending: int):
        super().__init__(server_address, handler_class)
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="blog-api")
        self.capacity = threading.BoundedSemaphore(workers + pending)

    def process_request(self, request, client_address) -> None:
        if not self.capacity.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Length: 0\r\nConnection: close\r\nRetry-After: 2\r\n\r\n"
                )
            finally:
                self.shutdown_request(request)
            return
        try:
            self.executor.submit(self._process_request, request, client_address)
        except Exception:
            self.capacity.release()
            self.shutdown_request(request)
            raise

    def _process_request(self, request, client_address) -> None:
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)
            self.capacity.release()

    def server_close(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=True)
        super().server_close()


class ResumeHandler(BaseHTTPRequestHandler):
    server_version = "XiaoliuResume/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        # Do not retain visitor IP addresses, tokens or request bodies in service logs.
        return

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def json_response(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def error_response(self, status: HTTPStatus, message: str) -> None:
        self.json_response(status, {"ok": False, "message": message})

    def require_admin(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {ADMIN_TOKEN}"
        if not ADMIN_TOKEN or not hmac.compare_digest(supplied, expected):
            self.error_response(HTTPStatus.UNAUTHORIZED, "管理口令不正确或已经失效")
            return False
        return True

    def request_body(self) -> bytes:
        length_text = self.headers.get("Content-Length", "")
        if not length_text.isdigit():
            raise ValueError("缺少有效的请求长度")
        length = int(length_text)
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("上传请求超过 10 MB 限制")
        return self.rfile.read(length)

    def json_body(self, maximum: int = 64 * 1024) -> dict:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("请求必须使用 JSON 格式")
        length_text = self.headers.get("Content-Length", "")
        if not length_text.isdigit():
            raise ValueError("缺少有效的请求长度")
        length = int(length_text)
        if length <= 0 or length > maximum:
            raise ValueError("请求内容过大或为空")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("请求内容必须是对象")
        return payload

    def client_key(self) -> str:
        address = str(self.headers.get("X-Real-IP") or self.client_address[0] or "unknown")[:80]
        return hashlib.sha256(address.encode("utf-8")).hexdigest()[:24]

    def require_human_form(self, payload: dict) -> None:
        if payload.get("website"):
            raise ValueError("提交未通过校验")
        started_at = payload.get("startedAt")
        if not isinstance(started_at, (int, float)):
            raise ValueError("表单校验信息缺失，请刷新页面后重试")
        elapsed = time.time() * 1000 - float(started_at)
        if elapsed < 2500 or elapsed > 2 * 60 * 60 * 1000:
            raise ValueError("提交过快或页面停留时间过长，请刷新后重试")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/health":
                redis_client = get_redis_client()
                redis_ready = False
                if redis_client is not None:
                    try:
                        redis_ready = bool(redis_client.ping())
                    except Exception:
                        redis_ready = False
                self.json_response(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "redis": {"configured": bool(REDIS_URL), "available": redis_ready},
                        "http": {"workers": HTTP_WORKERS, "queue": HTTP_QUEUE},
                    },
                )
                return
            if path == "/analytics/summary":
                self.json_response(HTTPStatus.OK, analytics_summary())
                return
            if path == "/admin/check":
                if self.require_admin():
                    self.json_response(HTTPStatus.OK, {"ok": True})
                return
            if path == "/admin/email-status":
                if not self.require_admin():
                    return
                self.json_response(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "configured": email_notifications_configured(),
                        "enabled": EMAIL_NOTIFICATIONS_ENABLED,
                        "recipient": masked_email(NOTIFY_EMAIL),
                        "smtpHost": SMTP_HOST if SMTP_HOST else "",
                    },
                )
                return
            if path == "/articles":
                with database() as connection:
                    rows = connection.execute(
                        """SELECT slug, title, excerpt, category, tags_json, content_text,
                                  published_date, reading_minutes, created_at
                           FROM published_articles
                           ORDER BY published_date DESC, created_at DESC
                           LIMIT 500"""
                    ).fetchall()
                    hidden_rows = connection.execute("SELECT slug FROM hidden_articles").fetchall()
                self.json_response(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "items": [public_article(row) for row in rows],
                        "hiddenSlugs": [row["slug"] for row in hidden_rows],
                    },
                )
                return
            interaction_match = re.fullmatch(r"/articles/([a-z0-9-]{2,100})/interaction", path)
            if interaction_match:
                slug = valid_article_slug(interaction_match.group(1))
                with database() as connection:
                    like_count = connection.execute(
                        "SELECT COUNT(*) FROM article_likes WHERE article_slug = ?", (slug,)
                    ).fetchone()[0]
                    rows = connection.execute(
                        """SELECT id, nickname, content, created_at
                           FROM article_comments
                           WHERE article_slug = ? AND status = 'approved'
                           ORDER BY created_at ASC LIMIT 100""",
                        (slug,),
                    ).fetchall()
                comments = [
                    {"id": row["id"], "nickname": row["nickname"], "content": row["content"], "createdAt": row["created_at"]}
                    for row in rows
                ]
                self.json_response(HTTPStatus.OK, {"ok": True, "likeCount": like_count, "comments": comments})
                return
            if path == "/admin/comments":
                if not self.require_admin():
                    return
                status = parse_qs(parsed.query).get("status", ["pending"])[0]
                if status not in {"pending", "approved", "all"}:
                    raise ValueError("评论状态不正确")
                sql = "SELECT id, article_slug, nickname, content, status, created_at, approved_at FROM article_comments"
                params: tuple = ()
                if status != "all":
                    sql += " WHERE status = ?"
                    params = (status,)
                sql += " ORDER BY created_at DESC LIMIT 300"
                with database() as connection:
                    rows = connection.execute(sql, params).fetchall()
                self.json_response(HTTPStatus.OK, {"ok": True, "items": [dict(row) for row in rows]})
                return
            if path == "/admin/leads":
                if not self.require_admin():
                    return
                status = parse_qs(parsed.query).get("status", ["all"])[0]
                if status not in {"new", "contacted", "closed", "all"}:
                    raise ValueError("合作状态不正确")
                sql = "SELECT id, name, contact_method, contact_value, requirement, status, created_at, updated_at FROM cooperation_leads"
                params = ()
                if status != "all":
                    sql += " WHERE status = ?"
                    params = (status,)
                sql += " ORDER BY created_at DESC LIMIT 300"
                with database() as connection:
                    rows = connection.execute(sql, params).fetchall()
                self.json_response(HTTPStatus.OK, {"ok": True, "items": [dict(row) for row in rows]})
                return
            if path == "/resumes":
                with LOCK:
                    items = sorted(load_items(), key=lambda item: item["date"], reverse=True)
                    items.sort(key=lambda item: not item.get("current", False))
                self.json_response(HTTPStatus.OK, {"ok": True, "items": [public_item(item) for item in items]})
                return
            if path.startswith("/files/") and path.endswith(".pdf"):
                resume_id = path.removeprefix("/files/").removesuffix(".pdf")
                if not ID_RE.fullmatch(resume_id):
                    self.error_response(HTTPStatus.NOT_FOUND, "简历不存在")
                    return
                with LOCK:
                    known_ids = {item["id"] for item in load_items()}
                if resume_id not in known_ids:
                    self.error_response(HTTPStatus.NOT_FOUND, "简历不存在")
                    return
                file_path = FILES_DIR / f"{resume_id}.pdf"
                if not file_path.is_file():
                    self.error_response(HTTPStatus.NOT_FOUND, "简历文件不存在")
                    return
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f'inline; filename="xiaoliu-resume-{resume_id}.pdf"')
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.send_header("Cache-Control", "private, max-age=300")
                self.end_headers()
                with file_path.open("rb") as stream:
                    shutil.copyfileobj(stream, self.wfile)
                return
            self.error_response(HTTPStatus.NOT_FOUND, "接口不存在")
        except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error):
            self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "服务器读取失败，请检查服务日志")

    def do_POST(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path == "/analytics/visit":
            try:
                if not check_rate(self.client_key(), "analytics", 180, 60):
                    self.error_response(HTTPStatus.TOO_MANY_REQUESTS, "访问统计请求过于频繁")
                    return
                payload = self.json_body(maximum=8 * 1024)
                self.json_response(HTTPStatus.OK, record_analytics_visit(self.client_key(), payload))
            except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.error_response(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if path == "/admin/email/test":
            if not self.require_admin():
                return
            try:
                send_test_notification()
                self.json_response(HTTPStatus.OK, {"ok": True, "message": "测试邮件已发送，请检查收件箱和垃圾邮件"})
            except ValueError as exc:
                self.error_response(HTTPStatus.BAD_REQUEST, str(exc))
            except (OSError, smtplib.SMTPException) as exc:
                print(f"test notification email failed: {type(exc).__name__}", flush=True)
                self.error_response(HTTPStatus.BAD_GATEWAY, "测试邮件发送失败，请检查 Gmail 地址、应用专用密码和服务日志")
            return
        if path == "/admin/articles":
            if not self.require_admin():
                return
            try:
                payload = self.json_body(maximum=40 * 1024)
                title = clean_private_text(str(payload.get("title", "")), "文章标题", 2, 100)
                excerpt = clean_private_text(str(payload.get("excerpt", "")), "文章摘要", 10, 300)
                category = clean_private_text(str(payload.get("category", "")), "文章分类", 2, 30)
                tags = clean_article_tags(payload.get("tags"))
                content = clean_article_content(str(payload.get("content", "")))
                published_date = date.today().isoformat()
                slug = f"article-{published_date.replace('-', '')}-{uuid.uuid4().hex[:12]}"
                reading_minutes = max(1, min(60, (len(content) + 499) // 500))
                created_at = utc_now()
                with database() as connection:
                    connection.execute(
                        """INSERT INTO published_articles
                           (slug, title, excerpt, category, tags_json, content_text,
                            published_date, reading_minutes, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            slug,
                            title,
                            excerpt,
                            category,
                            json.dumps(tags, ensure_ascii=False),
                            content,
                            published_date,
                            reading_minutes,
                            created_at,
                        ),
                    )
                    row = connection.execute(
                        """SELECT slug, title, excerpt, category, tags_json, content_text,
                                  published_date, reading_minutes, created_at
                           FROM published_articles WHERE slug = ?""",
                        (slug,),
                    ).fetchone()
                self.json_response(HTTPStatus.CREATED, {"ok": True, "item": public_article(row)})
            except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.error_response(HTTPStatus.BAD_REQUEST, str(exc))
            except sqlite3.Error:
                self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "文章保存失败，请检查服务日志")
            return
        interaction_match = re.fullmatch(r"/articles/([a-z0-9-]{2,100})/(likes|comments)", path)
        if interaction_match:
            slug = interaction_match.group(1)
            action = interaction_match.group(2)
            try:
                valid_article_slug(slug)
                payload = self.json_body()
                if action == "likes":
                    if not check_rate(self.client_key(), "like", 80, 3600):
                        self.error_response(HTTPStatus.TOO_MANY_REQUESTS, "操作过于频繁，请稍后重试")
                        return
                    visitor_id = str(payload.get("visitorId", ""))
                    if not VISITOR_ID_RE.fullmatch(visitor_id):
                        raise ValueError("访客标识不正确，请刷新页面后重试")
                    visitor_hash = hashlib.sha256(visitor_id.encode("utf-8")).hexdigest()
                    with database() as connection:
                        cursor = connection.execute(
                            "INSERT OR IGNORE INTO article_likes(article_slug, visitor_hash, created_at) VALUES (?, ?, ?)",
                            (slug, visitor_hash, utc_now()),
                        )
                        like_count = connection.execute(
                            "SELECT COUNT(*) FROM article_likes WHERE article_slug = ?", (slug,)
                        ).fetchone()[0]
                    self.json_response(HTTPStatus.OK, {"ok": True, "liked": True, "added": cursor.rowcount == 1, "likeCount": like_count})
                    return

                if not check_rate(self.client_key(), "comment", 5, 600):
                    self.error_response(HTTPStatus.TOO_MANY_REQUESTS, "评论提交过于频繁，请稍后重试")
                    return
                self.require_human_form(payload)
                nickname = clean_public_text(str(payload.get("nickname", "")), "称呼", 1, 30)
                content = clean_public_text(str(payload.get("content", "")), "评论内容", 4, 800)
                comment_id = f"comment-{uuid.uuid4().hex}"
                created_at = utc_now()
                status = "pending" if comment_requires_review(nickname, content) else "approved"
                approved_at = created_at if status == "approved" else None
                with database() as connection:
                    connection.execute(
                        """INSERT INTO article_comments
                           (id, article_slug, nickname, content, status, created_at, approved_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (comment_id, slug, nickname, content, status, created_at, approved_at),
                    )
                notify_comment_async(slug, nickname, content, status, created_at)
                published = status == "approved"
                response_message = "评论发布成功，已经公开显示" if published else "评论已提交，将由小刘人工复核后显示"
                self.json_response(
                    HTTPStatus.CREATED,
                    {"ok": True, "published": published, "message": response_message},
                )
                return
            except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.error_response(HTTPStatus.BAD_REQUEST, str(exc))
                return
            except sqlite3.Error:
                self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "互动数据保存失败，请稍后重试")
                return

        if path == "/contact":
            try:
                if not check_rate(self.client_key(), "contact", 3, 3600):
                    self.error_response(HTTPStatus.TOO_MANY_REQUESTS, "提交过于频繁，请稍后再试")
                    return
                payload = self.json_body()
                self.require_human_form(payload)
                if payload.get("privacyConfirmed") is not True:
                    raise ValueError("请确认同意将联系方式用于本次合作沟通")
                name = clean_private_text(str(payload.get("name", "")), "称呼", 1, 30)
                method = str(payload.get("contactMethod", ""))
                if method not in {"微信", "电话", "邮箱", "其他"}:
                    raise ValueError("请选择联系方式类型")
                contact_value = clean_private_text(str(payload.get("contactValue", "")), "联系方式", 3, 100)
                requirement = clean_private_text(str(payload.get("requirement", "")), "需求说明", 10, 1500)
                lead_id = f"lead-{uuid.uuid4().hex}"
                now = utc_now()
                with database() as connection:
                    connection.execute(
                        """INSERT INTO cooperation_leads
                           (id, name, contact_method, contact_value, requirement, status, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, 'new', ?, ?)""",
                        (lead_id, name, method, contact_value, requirement, now, now),
                    )
                notify_lead_async(name, method, contact_value, requirement, now)
                self.json_response(HTTPStatus.CREATED, {"ok": True, "message": "合作需求已提交，小刘会在看到后与你联系"})
                return
            except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.error_response(HTTPStatus.BAD_REQUEST, str(exc))
                return
            except sqlite3.Error:
                self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "合作需求保存失败，请稍后重试")
                return

        if path != "/admin/resumes":
            self.error_response(HTTPStatus.NOT_FOUND, "接口不存在")
            return
        if not self.require_admin():
            return
        try:
            content_type = self.headers.get("Content-Type", "")
            if not content_type.lower().startswith("multipart/form-data;"):
                raise ValueError("请使用表单上传 PDF")
            fields, pdf_bytes, original_name = parse_multipart(content_type, self.request_body())
            if fields.get("privacyConfirmed") != "true":
                raise ValueError("请先确认上传文件已经完成隐私和保密检查")
            validate_pdf(pdf_bytes, original_name)
            item = {
                "id": f"{parse_date(fields.get('date', ''))}-{uuid.uuid4().hex[:12]}",
                "version": clean_text(fields.get("version", ""), "版本名称", 2, 40),
                "stage": clean_text(fields.get("stage", ""), "阶段名称", 2, 60),
                "date": fields["date"],
                "change": clean_text(fields.get("change", ""), "变化说明", 4, 300),
                "current": fields.get("current") == "true",
                "createdAt": utc_now(),
            }
            file_path = FILES_DIR / f"{item['id']}.pdf"
            temporary = file_path.with_suffix(".tmp")
            with LOCK:
                ensure_storage()
                with temporary.open("xb") as stream:
                    stream.write(pdf_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, file_path)
                try:
                    items = load_items()
                    if item["current"]:
                        for existing in items:
                            existing["current"] = False
                    items.append(item)
                    atomic_write_json(items)
                except Exception:
                    file_path.unlink(missing_ok=True)
                    raise
            self.json_response(HTTPStatus.CREATED, {"ok": True, "item": public_item(item)})
        except (KeyError, UnicodeError, ValueError) as exc:
            self.error_response(HTTPStatus.BAD_REQUEST, str(exc))
        except (OSError, json.JSONDecodeError):
            self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "保存失败，请检查服务日志")

    def do_DELETE(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        article_match = re.fullmatch(r"/admin/articles/([a-z0-9-]{2,100})", path)
        if article_match:
            if not self.require_admin():
                return
            try:
                slug = valid_article_slug(article_match.group(1))
                with database() as connection:
                    connection.execute("DELETE FROM published_articles WHERE slug = ?", (slug,))
                    connection.execute(
                        "INSERT OR REPLACE INTO hidden_articles (slug, hidden_at) VALUES (?, ?)",
                        (slug, utc_now()),
                    )
                self.json_response(HTTPStatus.OK, {"ok": True})
            except (ValueError, sqlite3.Error):
                self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "文章删除失败，请检查服务日志")
            return
        interaction_match = re.fullmatch(r"/admin/(comments|leads)/((?:comment|lead)-[a-f0-9]{32})", path)
        if interaction_match:
            if not self.require_admin():
                return
            kind, item_id = interaction_match.groups()
            table = "article_comments" if kind == "comments" else "cooperation_leads"
            try:
                with database() as connection:
                    cursor = connection.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
                if cursor.rowcount != 1:
                    self.error_response(HTTPStatus.NOT_FOUND, "记录不存在")
                    return
                self.json_response(HTTPStatus.OK, {"ok": True})
            except sqlite3.Error:
                self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "删除失败，请检查服务日志")
            return
        match = re.fullmatch(r"/admin/resumes/([a-z0-9-]{12,80})", path)
        if not match:
            self.error_response(HTTPStatus.NOT_FOUND, "接口不存在")
            return
        if not self.require_admin():
            return
        resume_id = match.group(1)
        try:
            with LOCK:
                items = load_items()
                deleted_item = next((item for item in items if item["id"] == resume_id), None)
                remaining = [item for item in items if item["id"] != resume_id]
                if len(remaining) == len(items):
                    self.error_response(HTTPStatus.NOT_FOUND, "简历不存在")
                    return
                atomic_write_json(remaining)
                file_path = FILES_DIR / f"{resume_id}.pdf"
                deleted_at = utc_now()
                if file_path.exists():
                    trash_name = f"{resume_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.pdf"
                    os.replace(file_path, TRASH_DIR / trash_name)
                with DELETED_INDEX_FILE.open("r", encoding="utf-8") as stream:
                    deleted_items = json.load(stream)
                deleted_items.append({**deleted_item, "deletedAt": deleted_at})
                atomic_write_deleted_json(deleted_items)
            self.json_response(HTTPStatus.OK, {"ok": True})
        except (OSError, ValueError, json.JSONDecodeError):
            self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "删除失败，请检查服务日志")

    def do_PUT(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        comment_match = re.fullmatch(r"/admin/comments/(comment-[a-f0-9]{32})/approve", path)
        if comment_match:
            if not self.require_admin():
                return
            try:
                with database() as connection:
                    cursor = connection.execute(
                        "UPDATE article_comments SET status = 'approved', approved_at = ? WHERE id = ?",
                        (utc_now(), comment_match.group(1)),
                    )
                if cursor.rowcount != 1:
                    self.error_response(HTTPStatus.NOT_FOUND, "评论不存在")
                    return
                self.json_response(HTTPStatus.OK, {"ok": True})
            except sqlite3.Error:
                self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "审核失败，请检查服务日志")
            return
        lead_match = re.fullmatch(r"/admin/leads/(lead-[a-f0-9]{32})/status", path)
        if lead_match:
            if not self.require_admin():
                return
            try:
                payload = self.json_body()
                status = str(payload.get("status", ""))
                if status not in {"new", "contacted", "closed"}:
                    raise ValueError("合作状态不正确")
                with database() as connection:
                    cursor = connection.execute(
                        "UPDATE cooperation_leads SET status = ?, updated_at = ? WHERE id = ?",
                        (status, utc_now(), lead_match.group(1)),
                    )
                if cursor.rowcount != 1:
                    self.error_response(HTTPStatus.NOT_FOUND, "合作记录不存在")
                    return
                self.json_response(HTTPStatus.OK, {"ok": True})
            except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.error_response(HTTPStatus.BAD_REQUEST, str(exc))
            except sqlite3.Error:
                self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "更新失败，请检查服务日志")
            return
        match = re.fullmatch(r"/admin/resumes/([a-z0-9-]{12,80})/current", path)
        if not match:
            self.error_response(HTTPStatus.NOT_FOUND, "接口不存在")
            return
        if not self.require_admin():
            return
        resume_id = match.group(1)
        try:
            with LOCK:
                items = load_items()
                if resume_id not in {item["id"] for item in items}:
                    self.error_response(HTTPStatus.NOT_FOUND, "简历不存在")
                    return
                for item in items:
                    item["current"] = item["id"] == resume_id
                atomic_write_json(items)
            self.json_response(HTTPStatus.OK, {"ok": True})
        except (OSError, ValueError, json.JSONDecodeError):
            self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "更新失败，请检查服务日志")


def main() -> None:
    if len(ADMIN_TOKEN) < 32:
        raise SystemExit("RESUME_ADMIN_TOKEN must contain at least 32 characters")
    ensure_storage()
    server = BoundedThreadPoolHTTPServer((HOST, PORT), ResumeHandler, HTTP_WORKERS, HTTP_QUEUE)
    print(
        f"resume service listening on http://{HOST}:{PORT}, workers={HTTP_WORKERS}, queue={HTTP_QUEUE}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
