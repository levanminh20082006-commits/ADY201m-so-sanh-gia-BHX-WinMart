"""Collector error handling, using a local test server (no real website is contacted)."""
import http.server
import threading
import time

import pytest
from playwright.sync_api import sync_playwright

from report2 import collect, settings


class SlowHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/slow"):
            time.sleep(3)
        status = 503 if self.path.startswith("/error") else 200
        body = b"<html><title>Test</title><body>no products</body></html>"
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture(scope="module")
def context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser.new_context()
        browser.close()


def test_timeout_is_recorded_not_crashing(server, context, monkeypatch):
    monkeypatch.setattr(settings, "PAGE_TIMEOUT_MS", 500)
    record = collect.scrape_page(context, "bhx", "g", "slow", f"{server}/slow", "test")
    assert record["status"] == "failed" and "Timeout" in record["error"]


def test_http_error_is_recorded(server, context):
    record = collect.scrape_page(context, "bhx", "g", "error", f"{server}/error", "test")
    assert record["status"] == "failed" and "HTTP 503" in record["error"]


def test_connection_refused_is_recorded(context):
    record = collect.scrape_page(context, "bhx", "g", "x", "http://127.0.0.1:9/", "test")
    assert record["status"] == "failed" and record["error"]


def test_page_without_products_is_not_ok(server, context, monkeypatch):
    monkeypatch.setattr(settings, "MAX_SCROLL_ROUNDS", 1)
    record = collect.scrape_page(context, "bhx", "g", "empty", f"{server}/empty", "test")
    assert record["status"] == "no_items" and record["dom_cards"] == []


def test_end_reached_rules():
    wm = lambda n, total: {"url": f"x?pageNumber={n}&pageSize=8", "body": {"data": {"items": [{}] * 8},
                                                                          "paging": {"pageNumber": n, "totalPages": total}}}
    assert collect.end_reached("winmart", [wm(1, 3), wm(3, 3)])
    assert not collect.end_reached("winmart", [wm(1, 3), wm(2, 3)])
    bhx = lambda n_items: {"url": "x", "request_body": '{"PageSize":10}', "body": {"data": {"products": [{}] * n_items}}}
    assert collect.end_reached("bhx", [bhx(10), bhx(4)])
    assert not collect.end_reached("bhx", [bhx(10)])
    getcate = {"url": "https://api/GetCate?pageSize=10", "request_body": None, "body": {"data": {"products": [{}] * 9}}}
    assert collect.end_reached("bhx", [getcate])
