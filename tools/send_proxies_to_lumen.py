#!/usr/bin/env python3
"""Upload proxy.txt beside this script to a Lumen V32.2+ service.

Uses only Python's standard library. Credentials are requested interactively and
are never written to disk. The Lumen owner account is required for TXT import.
"""

from __future__ import annotations

import argparse
import getpass
import http.cookiejar
import json
import re
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPSHandler,
    Request,
    build_opener,
)

MAX_FILE_BYTES = 2_000_000
PROXY_RE = re.compile(r"(?:https?|socks5)://[^\s\])]+", re.IGNORECASE)


class LumenError(RuntimeError):
    pass


def normalized_base_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise LumenError("آدرس سرویس خالی است.")
    if "://" not in value:
        value = "https://" + value
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LumenError("آدرس سرویس معتبر نیست.")
    # Only preserve a deployment sub-path when explicitly provided.
    clean_path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, clean_path, "", ""))


def read_proxy_file() -> tuple[Path, str, int]:
    path = Path(__file__).resolve().with_name("proxy.txt")
    if not path.is_file():
        raise LumenError(f"فایل proxy.txt کنار اسکریپت پیدا نشد:\n{path}")
    size = path.stat().st_size
    if size <= 0:
        raise LumenError("فایل proxy.txt خالی است.")
    if size > MAX_FILE_BYTES:
        raise LumenError("حجم proxy.txt بیشتر از ۲ مگابایت است.")
    text = path.read_text(encoding="utf-8-sig")
    endpoints: set[str] = set()
    for line in text.splitlines():
        match = PROXY_RE.search(line)
        if not match:
            continue
        try:
            parsed = urlsplit(match.group(0).rstrip(".,;"))
            if not parsed.hostname or parsed.port is None:
                continue
            endpoint = urlunsplit(
                (parsed.scheme.lower(), parsed.netloc, parsed.path.rstrip("/"), parsed.query, "")
            )
            endpoints.add(endpoint)
        except (ValueError, UnicodeError):
            continue
    if not endpoints:
        raise LumenError("هیچ پروکسی معتبری در proxy.txt پیدا نشد.")
    return path, text, len(endpoints)


def make_opener(insecure: bool):
    context = ssl.create_default_context()
    if insecure:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    cookies = http.cookiejar.CookieJar()
    return build_opener(HTTPCookieProcessor(cookies), HTTPSHandler(context=context))


def call_json(opener, base_url: str, route: str, method: str = "GET", body: Any = None) -> Any:
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "Lumen-Proxy-Uploader/1.0"}
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = Request(base_url + route, data=payload, method=method, headers=headers)
    try:
        with opener.open(request, timeout=45) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw).get("error", raw)
        except json.JSONDecodeError:
            detail = raw or exc.reason
        raise LumenError(f"خطای HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise LumenError(f"اتصال به سرویس انجام نشد: {exc.reason}") from exc


def prompt_credentials() -> tuple[str, str]:
    username = input("نام کاربری مالک پنل: ").strip()
    if not username:
        raise LumenError("نام کاربری خالی است.")
    password = getpass.getpass("رمز عبور مالک پنل: ")
    if not password:
        raise LumenError("رمز عبور خالی است.")
    return username, password


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ارسال فایل proxy.txt به سرویس Lumen V32.2+"
    )
    parser.add_argument("--url", help="آدرس سرویس؛ در صورت حذف، پرسیده می‌شود")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="غیرفعال‌کردن بررسی گواهی TLS (فقط برای تست محلی)",
    )
    args = parser.parse_args()

    path, proxy_text, proxy_count = read_proxy_file()
    print(f"فایل پیدا شد: {path}")
    print(f"تعداد endpoint یکتا: {proxy_count}")
    print("درصدهای انتهای خطوط توسط پنل نادیده گرفته می‌شوند.")

    entered_url = args.url or input("آدرس سرویس Lumen: ")
    base_url = normalized_base_url(entered_url)
    username, password = prompt_credentials()
    opener = make_opener(args.insecure)

    status = call_json(opener, base_url, "/api/status")
    if status.get("setup") is False:
        answer = input("پنل هنوز راه‌اندازی نشده است. همین حساب به‌عنوان مالک ساخته شود؟ [y/N]: ")
        if answer.strip().lower() not in {"y", "yes"}:
            raise LumenError("راه‌اندازی پنل لغو شد.")
        call_json(
            opener,
            base_url,
            "/api/setup",
            "POST",
            {"username": username, "password": password},
        )
        print("حساب مالک ساخته شد.")
    else:
        call_json(
            opener,
            base_url,
            "/api/login",
            "POST",
            {"username": username, "password": password},
        )
        print("ورود موفق بود.")

    result = call_json(
        opener,
        base_url,
        "/api/proxies/import",
        "PUT",
        {"text": proxy_text},
    )
    imported = int(result.get("imported", 0))
    server_items = result.get("proxies") or []
    print(f"ارسال موفق: {imported} پروکسی وارد پنل شد.")
    print(f"تعداد رکوردهای برگشتی پنل: {len(server_items)}")
    if imported != proxy_count:
        print(
            "توجه: تفاوت تعداد معمولاً به‌دلیل خطوط نامعتبر یا endpointهای تکراری است.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nعملیات لغو شد.", file=sys.stderr)
        raise SystemExit(130)
    except LumenError as exc:
        print(f"خطا: {exc}", file=sys.stderr)
        raise SystemExit(1)
