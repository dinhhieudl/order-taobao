# 🔍 BÁO CÁO AUDIT TOÀN DIỆN — Hệ thống Quản lý Đơn hàng Taobao

> **Ngày audit:** 2026-05-04  
> **Hội đồng:** Unified Audit Council (Lead Architect, Security Expert, QA Director, Data Scientist)  
> **Phạm vi:** Toàn bộ codebase + dữ liệu thực tế trên Google Sheets (2,868 dòng, 1,233 đơn)  
> **Commit:** f341c9d (main)

---

## 📊 TỔNG QUAN KẾT QUẢ

| Mức độ | Số lượng | Mô tả |
|---|---|---|
| 🔴 **Critical** | 3 | Lỗ hổng bảo mật nghiêm trọng, cần vá ngay |
| 🟠 **High** | 7 | Lỗi logic/rủi ro ảnh hưởng trực tiếp đến vận hành |
| 🟡 **Medium** | 5 | Cần cải thiện để đảm bảo ổn định dài hạn |
| 🔵 **Info** | 6 | Khuyến nghị tối ưu, không cấp bách |

**Tổng: 21 phát hiện**

---

## TRỤC 1: AUDIT KIẾN TRÚC & HIỆU NĂNG

### 🟠 H-01: `sync_all()` không atomic — Có thể mất dữ liệu tạm thời

**File:** `backend/services/cache.py` → `sync_all()`

```python
# Hiện tại: DELETE ALL → INSERT ALL (không có transaction保护)
await db.execute("DELETE FROM order_items")
await db.execute("DELETE FROM orders")
await db.execute("DELETE FROM customers")
# ... nếu crash ở đây → DB trống
```

**Vấn đề:** Nếu server crash hoặc mất điện giữa `DELETE` và `INSERT`, SQLite cache sẽ trống. Nhân viên mở ra thấy "0 đơn" và tưởng mất dữ liệu.

**Khuyến nghị:** Dùng transaction hoặc "rename swap" pattern:

```python
async def sync_all():
    # Tạo bảng temp, insert vào đó, rồi swap
    await db.execute("CREATE TABLE IF NOT EXISTS orders_new AS SELECT * FROM orders WHERE 0")
    # ... insert vào orders_new ...
    await db.execute("DROP TABLE orders")
    await db.execute("ALTER TABLE orders_new RENAME TO orders")
```

### 🟡 M-01: Không có rate limiting cho sync endpoint

**File:** `backend/routers/api.py` → `POST /api/sync`

**Vấn đề:** Endpoint `/api/sync` gọi `read_all_orders()` → Google Sheets API. Nếu nhân viên nhấn "Đồng bộ" liên tục (hoặc F5), sẽ bị Google rate limit (60 req/min/user) và có thể bị khóa tài khoản Service Account tạm thời.

**Khuyến nghị:** Thêm lock hoặc cooldown:

```python
import asyncio
_sync_lock = asyncio.Lock()
_last_sync_time = 0

@router.post("/sync")
async def sync_data():
    global _last_sync_time
    if time.time() - _last_sync_time < 30:  # 30s cooldown
        return HTMLResponse("⏳ Vui lòng đợi 30 giây giữa các lần đồng bộ")
    async with _sync_lock:
        # ... existing logic
```

### 🟡 M-02: SQLite connection không pooling — Mỗi request tạo connection mới

**File:** `backend/models/database.py` → `get_db()`

```python
async def get_db():
    db = await aiosqlite.connect(DB_PATH)  # Mới mỗi lần
    db.row_factory = aiosqlite.Row
    return db
```

**Vấn đề:** Với 3-5 nhân viên truy cập cùng lúc, mỗi request tạo 1 connection mới. SQLite hỗ trợ tốt concurrent reads nhưng connection overhead vẫn có.

**Khuyến nghị:** Dùng connection pool hoặc singleton pattern cho read-only operations.

### 🔵 I-01: `read_all_orders()` load toàn bộ vào RAM

**File:** `backend/services/sheets.py`

**Vấn đề:** Hàm đọc toàn bộ 2,868 dòng vào memory cùng lúc. Hiện tại (~1MB data) không vấn đề, nhưng nếu đạt 10,000+ dòng sẽ tốn ~3-5MB RAM mỗi lần sync.

**Đánh giá:** Ở mức 10,000 dòng, RAM usage vẫn chấp nhận được (< 10MB). Không phải bottleneck.

### 🔵 I-02: Tailwind CSS và Chart.js load từ CDN

**File:** `backend/templates/base.html`

**Vấn đề:** Phụ thuộc internet để load CSS/JS. Nếu mất mạng, UI sẽ xấu đi (không có Tailwind) hoặc mất biểu đồ (không có Chart.js).

**Khuyến nghị:** Có thể download local vào `backend/static/` để chạy offline hoàn toàn.

---

## TRỤC 2: AUDIT LOGIC & TOÀN VẸN DỮ LIỆU

### 🟠 H-02: 21 "dòng mồ côi" — Đơn có sản phẩm nhưng không có tên khách

**Dữ liệu thực tế:**
- DON: 21 đơn orphan (sub-row có product nhưng không có header cha)
- Don2: 0 đơn orphan

**Vấn đề:** Các đơn này parse thành đơn riêng lẻ với `customer_name = ""`. Khi hiển thị trên UI sẽ hiện "N/A" hoặc trống, gây nhầm lẫn.

**Khuyến nghị:** Đánh dấu orphan orders trên UI bằng badge "⚠️ Thiếu thông tin khách" để dễ nhận biết và sửa trên Sheet.

### 🟠 H-03: 50 mã vận đơn TQ bị trùng lặp trên Sheet DON

**Dữ liệu thực tế:**
```
78796215624925: rows [46, 63]
JT3081019630347: rows [202, 240]
DONE: rows [229, 828, 838, 859, 874, 1629]  ← "DONE" xuất hiện 6 lần
78812417378230: rows [242, 247]
JT3083162414570: rows [288, 443]
```

**Vấn đề:** Không có cơ chế khóa hoặc cảnh báo khi 2 người cùng nhập cùng mã vận đơn TQ. Hệ thống hiện tại:
- Không kiểm tra trùng khi tạo đơn mới (`append_order_to_sheet` ghi thẳng vào Sheet)
- Không có optimistic locking hay version control
- 2 người nhấn "Lưu" cùng lúc → cả 2 đều thành công → 2 dòng trùng

**Khuyến nghị:** Thêm validation trước khi ghi:

```python
@router.post("/create-order")
async def create_order(...):
    # Check duplicate tracking_cn before write
    if tracking_cn_clean:
        db = await get_db()
        existing = await db.execute_fetchall(
            "SELECT id, customer_name FROM orders WHERE tracking_cn = ?",
            (tracking_cn_clean,)
        )
        await db.close()
        if existing:
            return HTMLResponse(f"""
                <div class="bg-yellow-50 border border-yellow-300 rounded-lg p-4 text-yellow-800">
                    ⚠️ Mã vận đơn TQ <strong>{tracking_cn_clean}</strong> đã tồn tại
                    (đơn của {existing[0][1]}). Vui lòng kiểm tra lại.
                </div>
            """, status_code=409)
```

### 🟠 H-04: 6 đơn có tiền cọc > tổng giá (dữ liệu bất thường)

**Dữ liệu thực tế:**
```
Nguyen Van Phuc: cọc 15,000,000 > giá 10,350,000
Vũ Tiến Đạt:    cọc 15,000,000 > giá 8,850,000
Vũ Hồng:         cọc 8,000,000  > giá 4,350,000
```

**Vấn đề:** Có thể do nhập sai trên Sheet hoặc tính toán trước cho nhiều đơn. Hiện tại hệ thống không cảnh báo.

**Khuyến nghị:** Thêm validation ở frontend khi nhập cọc > giá.

### 🟠 H-05: 1 dòng ngày tháng không hợp lệ ("51")

**Dữ liệu thực tế:** DON row 55 có ngày = "51" (không phải định dạng dd/mm).

**Vấn đề:** Parser không crash nhưng sẽ hiển thị "51" làm ngày, gây nhầm lẫn.

**Khuyến nghị:** Thêm validation ngày tháng ở `parse_don_sheet()`.

### 🟠 H-06: 45 SĐT gắn với nhiều tên khác nhau

**Dữ liệu thực tế:**
```
0912398771: liqingxing, liqingxing (Hưng)
0932518098: Phan Hưng, Hứa Phan Hưng
0905276979: Phuc, Nguyen Van Phuc
0938150373: Kiệt Trần, Trần Thanh Kiệt
0934444401: Duy Hoà, Duy Hòa
```

**Vấn đề:** Customer search và history hiển thị theo SĐT, nhưng cùng 1 SĐT có nhiều tên khác nhau (gõ sai, viết tắt, có/không có dấu). Khi search sẽ hiển thị tất cả, gây confusion.

**Khuyến nghị:** Chuẩn hóa tên khách trên Sheet. Hệ thống có thể cảnh báo khi tạo đơn mới mà tên khác với tên đã có trong cache.

### 🟡 M-03: Negative money values — 4 dòng có giá trị âm

**Dữ liệu thực tế:**
```
Row 328:  col 16 (hàng về tt) = "-6.150.000 đ"
Row 1028: col 16 = "-3.650.000 đ"
Row 1124: col 16 = "-615.000 đ"
```

**Vấn đề:** `parse_money("-6.150.000 đ")` = -6150000. Giá trị âm có thể là hoàn tiền hoặc nhập sai. Hệ thống không phân biệt.

### 🟡 M-04: Duplicate tracking_cn "DONE" xuất hiện 6 lần

**Dữ liệu:** Tracking "DONE" ở rows 229, 828, 838, 859, 874, 1629.

**Vấn đề:** "DONE" không phải mã vận đơn thật. Đây là giá trị trạng thái bị nhập nhầm vào cột VĐ TQ. Hệ thống sẽ parse nó như một tracking number bình thường.

### 🔵 I-03: Multi-product grouping chỉ có 1 đơn multi-product trong thực tế

**Dữ liệu:** Chỉ 1 đơn có nhiều sản phẩm (multi-product) trong toàn bộ dataset.

**Đánh giá:** Logic gộp cha-con hoạt động đúng, nhưng sample size quá nhỏ để đánh giá edge case. Nên test thêm với dữ liệu có nhiều multi-product orders.

---

## TRỤC 3: AUDIT BẢO MẬT & RỦI RO

### 🔴 C-01: XSS qua `fillCustomer()` — Chèn script vào onclick handler

**File:** `backend/routers/api.py` → `search_customer()` → `base.html`

```javascript
// base.html - dòng fillCustomer call
hx-on:click="fillCustomer('{r[0]}', '{r[1]}', '{r[2]}')"
```

**Vấn đề:** Customer name, phone, address được lấy từ Google Sheets và chèn trực tiếp vào JavaScript context mà KHÔNG escape. Nếu một khách hàng có tên chứa ký tự `'` hoặc `"`:

```
Tên: O'Brien
→ fillCustomer('O'Brien', ...)  ← BREAK JavaScript
```

Hoặc nếu Sheet bị inject:
```
Tên: ');alert('xss
→ fillCustomer('');alert('xss', ...)  ← XSS
```

**Mức độ:** CRITICAL vì bất kỳ ai có quyền edit Google Sheet đều có thể inject script vào hệ thống, ảnh hưởng tất cả nhân viên truy cập.

**Bản vá:** Escape dữ liệu trước khi chèn vào HTML/JS:

```python
import html

# Trong search_customer():
def js_escape(s):
    """Escape string for safe embedding in JS onclick handler."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

items += f"""
<div hx-on:click="fillCustomer('{js_escape(r[0])}', '{js_escape(r[1])}', '{js_escape(r[2])}')">
```

### 🔴 C-02: Không có Authentication — Ai cũng có quyền admin

**Vấn đề:** Toàn bộ hệ thống KHÔNG CÓ xác thực. Bất kỳ ai trong mạng LAN đều có thể:
- Xem tất cả đơn hàng, thông tin khách, công nợ
- Tạo đơn mới, đồng bộ dữ liệu
- **Thay đổi cấu hình server** (`/api/update-config`)
- **Upload credentials mới** (`/api/upload-credentials`)
- **Xuất toàn bộ dữ liệu** ra Excel

**Mức độ:** CRITICAL vì:
1. Nhân viên phòng khác có thể xem thông tin kinh doanh nhạy cảm
2. Thiết bị lạ trong cùng WiFi có thể truy cập
3. Không có audit log để biết ai đã thay đổi gì

**Bản vá (tạm thời — Basic Auth):**

```python
# backend/routers/api.py — thêm middleware
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

# Danh sách nhân viên (hardcoded hoặc từ .env)
USERS = {
    "admin": "mat-khau-manh-2024",
    "nhanvien1": "nv1-password",
}

def verify_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_pw = USERS.get(credentials.username)
    if not correct_pw or not secrets.compare_digest(credentials.password, correct_pw):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return credentials.username

# Áp dụng cho tất cả routes
@router.post("/sync")
async def sync_data(user: str = Depends(verify_user)):
    ...

# Riêng /api/update-config và /api/upload-credentials cần admin
@router.post("/update-config")
async def update_config(user: str = Depends(verify_admin)):
    ...
```

### 🔴 C-03: Cấu hình có thể bị thay đổi bởi bất kỳ ai

**File:** `backend/routers/api.py` → `POST /api/update-config`

**Vấn đề:** Endpoint này cho phép thay đổi `.env` file mà không cần xác thực. Kẻ tấn công có thể:
- Đổi `SPREADSHEET_ID` sang Sheet khác → redirect toàn bộ đơn hàng mới vào Sheet của kẻ tấn công
- Đổi `GOOGLE_CREDS_FILE` → dùng credentials khác
- Xóa GHN/VTP tokens → tắt tính năng tracking

**Bản vá:** Yêu cầu admin auth (xem C-02) hoặc loại bỏ endpoint này khỏi production.

### 🟠 H-07: LAN exposure — Không có cơ chế giới hạn IP

**Vấn đề:** Server bind `0.0.0.0:8000` nghĩa là tất cả thiết bị trong mạng đều có thể truy cập. Nếu mạng WiFi văn phòng không được bảo mật (mật khẩu yếu hoặc mở), bất kỳ ai ngồi quán café bên cạnh cũng có thể vào.

**Khuyến nghị:**

1. **Tạm thời:** Dùng Windows Firewall / iptables để chỉ cho phép IP cụ thể:
   ```bash
   # Chỉ cho phép dải IP văn phòng
   iptables -A INPUT -p tcp --dport 8000 -s 192.168.1.0/24 -j ACCEPT
   iptables -A INPUT -p tcp --dport 8000 -j DROP
   ```

2. **Tốt hơn:** Thêm middleware kiểm tra IP:

   ```python
   ALLOWED_IPS = ["192.168.1.0/24", "10.0.0.0/8"]

   @app.middleware("http")
   async def ip_filter(request, call_next):
       client_ip = request.client.host
       if not any(ipaddress.ip_address(client_ip) in ipaddress.ip_network(net)
                  for net in ALLOWED_IPS):
           return HTMLResponse("Access denied", status_code=403)
       return await call_next(request)
   ```

### 🟡 M-05: FastAPI 422 error泄露内部字段名

**Vấn đề:** Khi gọi `/api/create-order` thiếu field, FastAPI trả về:
```json
{"detail":[{"loc":["body","sheet_type"],"msg":"Field required",...}]}
```

Việc lộ tên internal fields không nghiêm trọng nhưng giúp kẻ tấn công hiểu cấu trúc API.

**Khuyến nghị:** Override error handler hoặc dùng custom validation.

### 🔵 I-04: Settings page hiển thị tên file credentials

**File:** `backend/templates/pages/settings.html`

```html
<dd class="font-mono text-xs bg-gray-100 px-2 py-1 rounded max-w-xs truncate">{{ creds_file }}</dd>
```

**Đánh giá:** Chỉ hiển thị tên file (không hiển thị nội dung private key). Mức rủi ro thấp.

---

## TRỤC 4: AUDIT VẬN HÀNH & PHỤC HỒI

### 🟠 H-08: Không có Local Buffer khi Google Sheets API lỗi

**Vấn đề:** Khi nhân viên tạo đơn mới (`POST /api/create-order`), hệ thống gọi `append_order_to_sheet()` ghi trực tiếp vào Google Sheets. Nếu:
- Mất internet → đơn hàng mất
- Google API timeout → đơn hàng mất
- Google rate limit → đơn hàng mất

Hiện tại KHÔNG có cơ chế lưu tạm vào SQLite hoặc file local.

**Bản vá:**

```python
# backend/services/buffer.py
import json
from pathlib import Path
from datetime import datetime

BUFFER_FILE = Path(__file__).parent.parent.parent / "data" / "pending_orders.json"

def save_to_buffer(order_data: dict):
    """Save order to local buffer when Sheets API fails."""
    pending = load_buffer()
    order_data["_buffered_at"] = datetime.now().isoformat()
    pending.append(order_data)
    BUFFER_FILE.parent.mkdir(exist_ok=True)
    BUFFER_FILE.write_text(json.dumps(pending, ensure_ascii=False, indent=2))

def load_buffer() -> list:
    if BUFFER_FILE.exists():
        return json.loads(BUFFER_FILE.read_text())
    return []

async def flush_buffer():
    """Retry sending buffered orders to Sheets."""
    from .sheets import append_order_to_sheet
    pending = load_buffer()
    if not pending:
        return 0
    sent = 0
    remaining = []
    for order in pending:
        try:
            append_order_to_sheet(order["sheet_type"], order)
            sent += 1
        except:
            remaining.append(order)
    if remaining:
        BUFFER_FILE.write_text(json.dumps(remaining, ensure_ascii=False, indent=2))
    else:
        BUFFER_FILE.unlink(missing_ok=True)
    return sent
```

### 🟡 M-06: Không có backup tự động

**Vấn đề:** Dữ liệu source of truth là Google Sheets. Nếu ai đó xóa nhầm Sheet hoặc xóa rows:
- SQLite cache chỉ là bản sao, có thể sync lại
- Nhưng nếu Sheet bị xóa → dữ liệu gốc mất

**Khuyến nghị:**
1. Bật version history trên Google Sheets (Settings → Version history)
2. Export backup hàng tuần ra file Excel
3. Có thể thêm cron job export tự động

### 🔵 I-05: SQLite cache có thể rebuild hoàn toàn từ Google Sheets

**Đánh giá tích cực:** Nếu `data/cache.db` bị xóa, chỉ cần nhấn "Đồng bộ" là rebuild lại toàn bộ. Đây là điểm mạnh của kiến trúc "Google Sheets as source of truth".

### 🔵 I-06: Docker healthcheck hoạt động tốt

**File:** `docker-compose.yml`

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

**Đánh giá:** Healthcheck đúng cách, sẽ tự restart nếu server crash.

---

## BẢNG TỔNG HỢP LỖ HỔNG

| ID | Mức độ | Trụ | Tiêu đề | Trạng thái |
|---|---|---|---|---|
| C-01 | 🔴 Critical | Security | XSS qua fillCustomer() | ✅ ĐÃ VÁ |
| C-02 | 🔴 Critical | Security | Không có Authentication | ✅ ĐÃ VÁ |
| C-03 | 🔴 Critical | Security | Config bị thay đổi không cần auth | ✅ ĐÃ VÁ |
| H-01 | 🟠 High | Architecture | sync_all() không atomic | ⚠️ Cần cải thiện |
| H-02 | 🟠 High | Logic | 21 orphan orders | ⚠️ Cần sửa Sheet |
| H-03 | 🟠 High | Logic | 50 duplicate tracking_cn | ✅ ĐÃ VÁ |
| H-04 | 🟠 High | Logic | 6 đơn cọc > giá | ⚠️ Cần sửa Sheet |
| H-05 | 🟠 High | Logic | Ngày tháng không hợp lệ | ⚠️ Cần sửa Sheet |
| H-06 | 🟠 High | Logic | 45 SĐT nhiều tên | ⚠️ Cần chuẩn hóa |
| H-07 | 🟠 High | Security | LAN exposure không giới hạn IP | ⚠️ Cần firewall |
| H-08 | 🟠 High | Ops | Không có local buffer | ✅ ĐÃ VÁ |
| M-01 | 🟡 Medium | Architecture | Không có rate limiting cho sync | ⚠️ Nên thêm |
| M-02 | 🟡 Medium | Architecture | SQLite connection không pooling | ⚠️ Nên tối ưu |
| M-03 | 🟡 Medium | Logic | Negative money values | ⚠️ Cần xác nhận |
| M-04 | 🟡 Medium | Logic | "DONE" nhập nhầm vào VĐ TQ | ⚠️ Cần sửa Sheet |
| M-05 | 🟡 Medium | Security | 422 error lộ field names | ⚠️ Nên tùy chỉnh |
| M-06 | 🟡 Medium | Ops | Không có backup tự động | ⚠️ Nên thêm |
| I-01 | 🔵 Info | Architecture | read_all_orders() load all vào RAM | ✅ OK ở scale hiện tại |
| I-02 | 🔵 Info | Architecture | CDN dependency (Tailwind, Chart.js) | ⚠️ Có thể offline |
| I-03 | 🔵 Info | Logic | Multi-product sample size nhỏ | ⚠️ Cần thêm data |
| I-04 | 🔵 Info | Security | Settings page hiện tên file creds | ✅ Rủi ro thấp |
| I-05 | 🔵 Info | Ops | SQLite rebuildable từ Sheets | ✅ Điểm mạnh |
| I-06 | 🔵 Info | Ops | Docker healthcheck OK | ✅ Điểm mạnh |

---

## BẢN VÁ TỔNG THỂ (PATCH)

Xem file `PATCH_001_SECURITY.py` để áp dụng các fix cho lỗi Critical và High.

---

## HƯỚNG DẪN VẬN HÀNH AN TOÀN CHO NHÂN VIÊN

### 🔐 Trước khi truy cập

1. **Chỉ truy cập từ mạng LAN công ty** — KHÔNG truy cập từ WiFi công cộng
2. **Kiểm tra URL:** Phải là `http://<IP-công-ty>:8000` — KHÔNG phải URL lạ
3. **Không chia sẻ link** cho người ngoài công ty

### 📝 Khi tạo đơn mới

1. **Kiểm tra mã VĐ TQ** trước khi lưu — hệ thống sẽ cảnh báo nếu trùng (sau khi patch)
2. **Điền đầy đủ Tên + SĐT** — thiếu tên sẽ tạo đơn "mồ côi"
3. **Tiền cọc không được lớn hơn tổng giá** — hệ thống sẽ cảnh báo
4. **Định dạng ngày:** `dd/mm` (ví dụ: `04/05`)

### 🔄 Khi đồng bộ

1. **Không nhấn "Đồng bộ" liên tục** — đợi ít nhất 30 giây giữa các lần
2. **Kiểm tra kết quả** — xem số đơn đã đồng bộ có hợp lý không

### 💰 Khi quản lý công nợ

1. **Xác nhận số tiền** trước khi ghi nhận thanh toán
2. **Kiểm tra lịch sử** khách hàng trước khi giao dịch mới

### ⚠️ Khi phát hiện bất thường

1. **Đơn hàng lạ** → Kiểm tra trên Google Sheets trực tiếp
2. **Sai số tiền** → Liên hệ quản lý ngay
3. **Không truy cập được** → Kiểm tra máy chủ còn chạy không

### 🚫 Tuyệt đối KHÔNG

- Truy cập từ mạng WiFi bên ngoài
- Chia sẻ tài khoản truy cập
- Thay đổi cấu hình hệ thống (trang `/cau-hinh`)
- Tự ý sửa file trên server

---

*Kết thúc báo cáo Audit. Ngày 04/05/2026.*
