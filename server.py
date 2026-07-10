#!/usr/bin/env python3
"""Simple HTTP calculator — four basic arithmetic operations."""

from __future__ import annotations

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOST = "0.0.0.0"
PORT = 8000
STATIC_DIR = Path(__file__).resolve().parent / "static"

OPERATIONS = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": lambda a, b: a / b,
}

OP_ALIASES = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "x": "mul",
    "/": "div",
    "add": "add",
    "sub": "sub",
    "subtract": "sub",
    "mul": "mul",
    "multiply": "mul",
    "div": "div",
    "divide": "div",
}


def calculate(a: float, b: float, op: str) -> float:
    key = OP_ALIASES.get(op.strip().lower())
    if key is None:
        raise ValueError(f"عملگر نامعتبر: {op!r}. مجاز: add, sub, mul, div یا + - * /")
    if key == "div" and b == 0:
        raise ZeroDivisionError("تقسیم بر صفر مجاز نیست")
    return OPERATIONS[key](a, b)


def parse_numbers(raw_a: str | None, raw_b: str | None) -> tuple[float, float]:
    if raw_a is None or raw_b is None or raw_a == "" or raw_b == "":
        raise ValueError("پارامترهای a و b الزامی هستند")
    try:
        return float(raw_a), float(raw_b)
    except ValueError as exc:
        raise ValueError("a و b باید عدد باشند") from exc


class CalculatorHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            index = STATIC_DIR / "index.html"
            if index.exists():
                self._send_file(index, "text/html; charset=utf-8")
            else:
                self._send_json(200, {"message": "Calculator API", "endpoints": ["/api/calc", "/api/add", "/api/sub", "/api/mul", "/api/div"]})
            return

        if path == "/api/calc":
            op = (query.get("op") or [None])[0]
            self._handle_calc((query.get("a") or [None])[0], (query.get("b") or [None])[0], op)
            return

        for name in ("add", "sub", "mul", "div"):
            if path == f"/api/{name}":
                self._handle_calc((query.get("a") or [None])[0], (query.get("b") or [None])[0], name)
                return

        self._send_json(404, {"error": "مسیر پیدا نشد"})

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"

        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "بدنه درخواست باید JSON معتبر باشد"})
            return

        if path == "/api/calc":
            self._handle_calc(data.get("a"), data.get("b"), data.get("op"))
            return

        for name in ("add", "sub", "mul", "div"):
            if path == f"/api/{name}":
                self._handle_calc(data.get("a"), data.get("b"), name)
                return

        self._send_json(404, {"error": "مسیر پیدا نشد"})

    def _handle_calc(self, raw_a, raw_b, op) -> None:
        try:
            a, b = parse_numbers(
                None if raw_a is None else str(raw_a),
                None if raw_b is None else str(raw_b),
            )
            if op is None or str(op).strip() == "":
                raise ValueError("پارامتر op الزامی است")
            result = calculate(a, b, str(op))
            self._send_json(200, {"a": a, "b": b, "op": str(op), "result": result})
        except ZeroDivisionError as exc:
            self._send_json(400, {"error": str(exc)})
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})


def main() -> None:
    server = HTTPServer((HOST, PORT), CalculatorHandler)
    print(f"Calculator running at http://{HOST}:{PORT}")
    print("Examples:")
    print(f"  GET  http://localhost:{PORT}/api/add?a=10&b=3")
    print(f"  GET  http://localhost:{PORT}/api/calc?a=10&b=3&op=mul")
    print(f"  POST http://localhost:{PORT}/api/calc  {{\"a\":10,\"b\":3,\"op\":\"div\"}}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
