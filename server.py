#!/usr/bin/env python3
"""Simple HTTP calculator — four basic arithmetic operations + advanced math."""

from __future__ import annotations

import json
import math
import re
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

# Advanced operations (two operands)
ADVANCED_OPS = {
    "pow": lambda a, b: a ** b,
    "mod": lambda a, b: a % b,
    "percent": lambda a, b: (a / 100) * b,  # Calculate b% of a
}

# Trigonometric and advanced functions (single operand)
MATH_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "log": math.log10,  # Log base 10
    "ln": math.log,     # Natural log
    "sqrt": math.sqrt,
    "exp": math.exp,
    "abs": abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
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
    "**": "pow",
    "^": "pow",
    "pow": "pow",
    "power": "pow",
    "%": "mod",
    "mod": "mod",
    "modulo": "mod",
}


class ExpressionParser:
    """Parse and evaluate mathematical expressions safely."""
    
    def __init__(self, expression: str):
        self.expression = expression.strip()
        self.pos = 0
        
    def parse(self) -> float:
        """Parse and evaluate the expression."""
        result = self._parse_addition()
        if self.pos < len(self.expression):
            raise ValueError(f"تجزیه نشد در موقعیت {self.pos}: {self.expression[self.pos:]}")
        return result
    
    def _current_char(self) -> str | None:
        """Get current character without consuming it."""
        if self.pos < len(self.expression):
            return self.expression[self.pos]
        return None
    
    def _consume_char(self) -> str | None:
        """Get and consume current character."""
        if self.pos < len(self.expression):
            ch = self.expression[self.pos]
            self.pos += 1
            return ch
        return None
    
    def _skip_whitespace(self) -> None:
        """Skip whitespace characters."""
        while self._current_char() and self._current_char() in ' \t':
            self._consume_char()
    
    def _parse_number(self) -> float:
        """Parse a number (integer or float)."""
        self._skip_whitespace()
        num_str = ""
        
        if self._current_char() == '-':
            num_str += self._consume_char()
        
        if self._current_char() == '+':
            self._consume_char()
        
        while self._current_char() and (self._current_char().isdigit() or self._current_char() == '.'):
            num_str += self._consume_char()
        
        if not num_str or num_str in '+-':
            raise ValueError("عدد غیر معتبر")
        
        try:
            return float(num_str)
        except ValueError:
            raise ValueError(f"نمی‌تواند عدد تجزیه کند: {num_str}")
    
    def _parse_function_call(self) -> float:
        """Parse function calls like sin(x), sqrt(x)."""
        self._skip_whitespace()
        
        # Try to match function name
        start_pos = self.pos
        while self._current_char() and self._current_char().isalpha():
            self._consume_char()
        
        func_name = self.expression[start_pos:self.pos].lower()
        
        if func_name and func_name in MATH_FUNCTIONS:
            self._skip_whitespace()
            if self._current_char() != '(':
                raise ValueError(f"توقع: '(' بعد از {func_name}")
            self._consume_char()  # consume '('
            value = self._parse_addition()
            self._skip_whitespace()
            if self._current_char() != ')':
                raise ValueError("توقع: ')'")
            self._consume_char()  # consume ')'
            try:
                return MATH_FUNCTIONS[func_name](value)
            except ValueError as e:
                raise ValueError(f"خطا در تابع {func_name}: {e}")
        
        # Not a function, reset and parse as number
        self.pos = start_pos
        return self._parse_number()
    
    def _parse_primary(self) -> float:
        """Parse primary expression: number, function, or parenthesized expression."""
        self._skip_whitespace()
        
        if self._current_char() == '(':
            self._consume_char()  # consume '('
            result = self._parse_addition()
            self._skip_whitespace()
            if self._current_char() != ')':
                raise ValueError("توقع: ')'")
            self._consume_char()  # consume ')'
            return result
        
        return self._parse_function_call()
    
    def _parse_exponentiation(self) -> float:
        """Parse exponentiation (highest precedence after primary)."""
        result = self._parse_primary()
        
        while True:
            self._skip_whitespace()
            if self._current_char() in ('*', '^'):
                if self.expression[self.pos:self.pos+2] == '**':
                    self._consume_char()
                    self._consume_char()
                    right = self._parse_primary()
                    result = result ** right
                elif self._current_char() == '^':
                    self._consume_char()
                    right = self._parse_primary()
                    result = result ** right
                else:
                    break
            else:
                break
        
        return result
    
    def _parse_multiplication(self) -> float:
        """Parse multiplication and division."""
        result = self._parse_exponentiation()
        
        while True:
            self._skip_whitespace()
            if self._current_char() == '*':
                if self.expression[self.pos:self.pos+2] == '**':
                    break  # Let exponentiation handle it
                self._consume_char()
                right = self._parse_exponentiation()
                result = result * right
            elif self._current_char() == '/':
                self._consume_char()
                right = self._parse_exponentiation()
                if right == 0:
                    raise ZeroDivisionError("تقسیم بر صفر مجاز نیست")
                result = result / right
            elif self._current_char() == '%':
                self._consume_char()
                right = self._parse_exponentiation()
                if right == 0:
                    raise ZeroDivisionError("مدول بر صفر مجاز نیست")
                result = result % right
            else:
                break
        
        return result
    
    def _parse_addition(self) -> float:
        """Parse addition and subtraction (lowest precedence)."""
        result = self._parse_multiplication()
        
        while True:
            self._skip_whitespace()
            if self._current_char() == '+':
                self._consume_char()
                right = self._parse_multiplication()
                result = result + right
            elif self._current_char() == '-':
                self._consume_char()
                right = self._parse_multiplication()
                result = result - right
            else:
                break
        
        return result


def calculate(a: float, b: float, op: str) -> float:
    key = OP_ALIASES.get(op.strip().lower())
    if key is None:
        raise ValueError(f"عملگر نامعتبر: {op!r}. مجاز: add, sub, mul, div, pow, mod")
    
    if key in OPERATIONS:
        if key == "div" and b == 0:
            raise ZeroDivisionError("تقسیم بر صفر مجاز نیست")
        return OPERATIONS[key](a, b)
    elif key in ADVANCED_OPS:
        try:
            return ADVANCED_OPS[key](a, b)
        except ValueError as e:
            raise ValueError(f"خطا در محاسبه: {e}")
    else:
        raise ValueError(f"عملگر پشتیبانی نشده: {key}")


def calculate_single(value: float, func: str) -> float:
    """Calculate single-operand functions like sqrt, sin, etc."""
    func_lower = func.strip().lower()
    if func_lower not in MATH_FUNCTIONS:
        raise ValueError(f"تابع نامعتبر: {func!r}. مجاز: sin, cos, tan, sqrt, log, ln, exp, abs, ceil, floor, factorial")
    try:
        return MATH_FUNCTIONS[func_lower](value)
    except ValueError as e:
        raise ValueError(f"خطا در تابع {func_lower}: {e}")


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
                endpoints = [
                    "/api/calc",
                    "/api/add", "/api/sub", "/api/mul", "/api/div",
                    "/api/pow", "/api/mod",
                    "/api/sin", "/api/cos", "/api/tan", "/api/sqrt",
                    "/api/log", "/api/ln", "/api/exp",
                    "/api/parse"
                ]
                self._send_json(200, {"message": "Calculator API", "endpoints": endpoints})
            return

        if path == "/api/calc":
            op = (query.get("op") or [None])[0]
            self._handle_calc((query.get("a") or [None])[0], (query.get("b") or [None])[0], op)
            return

        # Basic operations
        for name in ("add", "sub", "mul", "div"):
            if path == f"/api/{name}":
                self._handle_calc((query.get("a") or [None])[0], (query.get("b") or [None])[0], name)
                return

        # Advanced two-operand operations
        for name in ("pow", "mod"):
            if path == f"/api/{name}":
                self._handle_calc((query.get("a") or [None])[0], (query.get("b") or [None])[0], name)
                return

        # Single-operand math functions
        for name in list(MATH_FUNCTIONS.keys()):
            if path == f"/api/{name}":
                value_str = (query.get("x") or [None])[0]
                if value_str is None or value_str == "":
                    self._send_json(400, {"error": "پارامتر x الزامی است"})
                    return
                self._handle_function(value_str, name)
                return

        # Expression parsing
        if path == "/api/parse":
            expr = (query.get("expr") or [None])[0]
            if expr is None or expr == "":
                self._send_json(400, {"error": "پارامتر expr الزامی است"})
                return
            self._handle_parse(expr)
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

        # Basic operations
        for name in ("add", "sub", "mul", "div"):
            if path == f"/api/{name}":
                self._handle_calc(data.get("a"), data.get("b"), name)
                return

        # Advanced two-operand operations
        for name in ("pow", "mod"):
            if path == f"/api/{name}":
                self._handle_calc(data.get("a"), data.get("b"), name)
                return

        # Single-operand math functions
        for name in list(MATH_FUNCTIONS.keys()):
            if path == f"/api/{name}":
                value = data.get("x")
                if value is None:
                    self._send_json(400, {"error": "پارامتر x الزامی است"})
                    return
                self._handle_function(value, name)
                return

        # Expression parsing
        if path == "/api/parse":
            expr = data.get("expr")
            if expr is None or expr == "":
                self._send_json(400, {"error": "پارامتر expr الزامی است"})
                return
            self._handle_parse(expr)
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

    def _handle_function(self, raw_value, func: str) -> None:
        """Handle single-operand math functions."""
        try:
            value = float(raw_value)
            result = calculate_single(value, func)
            self._send_json(200, {"x": value, "function": func, "result": result})
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})

    def _handle_parse(self, expr: str) -> None:
        """Handle expression parsing."""
        try:
            parser = ExpressionParser(expr)
            result = parser.parse()
            self._send_json(200, {"expression": expr, "result": result})
        except (ValueError, ZeroDivisionError) as exc:
            self._send_json(400, {"error": str(exc)})


def main() -> None:
    server = HTTPServer((HOST, PORT), CalculatorHandler)
    print(f"Calculator running at http://{HOST}:{PORT}")
    print("\nBasic operations:")
    print(f"  GET  http://localhost:{PORT}/api/add?a=10&b=3")
    print(f"  GET  http://localhost:{PORT}/api/div?a=10&b=3")
    print("\nAdvanced operations:")
    print(f"  GET  http://localhost:{PORT}/api/pow?a=2&b=8  (2^8)")
    print(f"  GET  http://localhost:{PORT}/api/mod?a=10&b=3")
    print("\nTrigonometric & Math functions:")
    print(f"  GET  http://localhost:{PORT}/api/sin?x=1.57")
    print(f"  GET  http://localhost:{PORT}/api/sqrt?x=16")
    print(f"  GET  http://localhost:{PORT}/api/log?x=100")
    print("\nExpression parsing:")
    print(f"  GET  http://localhost:{PORT}/api/parse?expr=2+3*4")
    print(f"  GET  http://localhost:{PORT}/api/parse?expr=sin(1.57)+cos(0)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
