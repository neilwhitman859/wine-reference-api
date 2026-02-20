#!/usr/bin/env python3
"""Capture the Wine Reference UI reliably in this container.

Usage:
  python scripts/ui_loop.py --name "Opus One" --vintage 2019 --out artifacts/ui.png
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


def wait_for_server(url: str, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError(f"Server did not become ready: {url}")


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def capture_ui(base_url: str, name: str, vintage: str, output: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright is not installed. Install with: pip install playwright"
        ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Firefox is more stable than Chromium in this container.
        try:
            browser = p.firefox.launch()
        except Exception as exc:
            raise RuntimeError(
                "Firefox browser runtime is missing. Run: python -m playwright install firefox"
            ) from exc
        page = browser.new_page(viewport={"width": 1440, "height": 1800})
        page.goto(base_url, wait_until="domcontentloaded")
        page.wait_for_selector("#name", timeout=15000)
        page.fill("#name", name)
        if vintage:
            page.fill("#vintage", vintage)
        page.click("#submit-btn")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(output), full_page=True)
        browser.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--name", default="Opus One")
    parser.add_argument("--vintage", default="2019")
    parser.add_argument("--out", default="artifacts/ui-screenshot.png")
    args = parser.parse_args()

    if not port_is_free(args.port):
        raise RuntimeError(
            f"Port {args.port} is in use. Stop other servers or pass --port <free-port>."
        )

    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(args.port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        base_url = f"http://127.0.0.1:{args.port}"
        wait_for_server(base_url)
        capture_ui(base_url, args.name, args.vintage, Path(args.out))
        print(f"Saved screenshot: {args.out}")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
