# ماشین حساب HTTP

یک ماشین حساب ساده با سرور HTTP که چهار عمل اصلی را انجام می‌دهد:

- جمع (`add` / `+`)
- تفریق (`sub` / `-`)
- ضرب (`mul` / `*`)
- تقسیم (`div` / `/`)

## اجرا

```bash
python3 server.py
```

سپس مرورگر را باز کنید:

```
http://localhost:8000
```

## API

### مسیرهای جداگانه

```
GET /api/add?a=10&b=3
GET /api/sub?a=10&b=3
GET /api/mul?a=10&b=3
GET /api/div?a=10&b=3
```

### مسیر عمومی

```
GET  /api/calc?a=10&b=3&op=mul
POST /api/calc
Content-Type: application/json

{"a": 10, "b": 3, "op": "div"}
```

### پاسخ موفق

```json
{"a": 10.0, "b": 3.0, "op": "add", "result": 13.0}
```

### خطا

```json
{"error": "تقسیم بر صفر مجاز نیست"}
```
