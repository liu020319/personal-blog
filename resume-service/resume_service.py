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
import shutil
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


HOST = os.environ.get("RESUME_HOST", "127.0.0.1")
PORT = int(os.environ.get("RESUME_PORT", "8091"))
DATA_DIR = Path(os.environ.get("RESUME_DATA_DIR", "/var/lib/personal-blog-resumes"))
FILES_DIR = DATA_DIR / "files"
TRASH_DIR = DATA_DIR / "trash"
INDEX_FILE = DATA_DIR / "resumes.json"
DELETED_INDEX_FILE = DATA_DIR / "deleted-resumes.json"
DATABASE_FILE = DATA_DIR / "blog.db"
ADMIN_TOKEN = os.environ.get("RESUME_ADMIN_TOKEN", "")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 256 * 1024
LOCK = threading.RLock()
RATE_LOCK = threading.Lock()
RATE_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)

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


def check_rate(client: str, action: str, limit: int, window_seconds: int) -> bool:
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


class ResumeHandler(BaseHTTPRequestHandler):
    server_version = "XiaoliuResume/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        # Never log Authorization headers or request bodies.
        super().log_message(fmt, *args)

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
        return (self.headers.get("X-Real-IP") or self.client_address[0] or "unknown")[:80]

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
                self.json_response(HTTPStatus.OK, {"ok": True})
                return
            if path == "/admin/check":
                if self.require_admin():
                    self.json_response(HTTPStatus.OK, {"ok": True})
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
                with database() as connection:
                    connection.execute(
                        """INSERT INTO article_comments
                           (id, article_slug, nickname, content, status, created_at)
                           VALUES (?, ?, ?, ?, 'pending', ?)""",
                        (comment_id, slug, nickname, content, utc_now()),
                    )
                self.json_response(HTTPStatus.CREATED, {"ok": True, "message": "评论已提交，审核通过后公开显示"})
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
    server = ThreadingHTTPServer((HOST, PORT), ResumeHandler)
    print(f"resume service listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
