#!/usr/bin/env python3
"""Small authenticated resume repository service for xiaoliudev.com.

Public visitors can list and read published PDFs. Mutating operations require a
Bearer token supplied through RESUME_ADMIN_TOKEN. Files and metadata stay on the
server; the token is never embedded in the static site or returned by the API.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import shutil
import threading
import uuid
from datetime import date, datetime, timezone
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


HOST = os.environ.get("RESUME_HOST", "127.0.0.1")
PORT = int(os.environ.get("RESUME_PORT", "8091"))
DATA_DIR = Path(os.environ.get("RESUME_DATA_DIR", "/var/lib/personal-blog-resumes"))
FILES_DIR = DATA_DIR / "files"
TRASH_DIR = DATA_DIR / "trash"
INDEX_FILE = DATA_DIR / "resumes.json"
DELETED_INDEX_FILE = DATA_DIR / "deleted-resumes.json"
ADMIN_TOKEN = os.environ.get("RESUME_ADMIN_TOKEN", "")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 256 * 1024
LOCK = threading.RLock()

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9-]{12,80}$")
UNSAFE_METADATA_RE = re.compile(
    r"(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?<!\d)1[3-9]\d{9}(?!\d)|"
    r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)|密码|口令|secret|token|access[_-]?key)",
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
        "file": f"./resume-api/files/{resume_id}.pdf",
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

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        try:
            if path == "/health":
                self.json_response(HTTPStatus.OK, {"ok": True})
                return
            if path == "/admin/check":
                if self.require_admin():
                    self.json_response(HTTPStatus.OK, {"ok": True})
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
        except (OSError, ValueError, json.JSONDecodeError):
            self.error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "服务器读取失败，请检查服务日志")

    def do_POST(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
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
