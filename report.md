# 📦 Báo cáo Dự án — Quản lý Vận đơn Taobao

> **Ngày:** 2026-05-04  
> **Giai đoạn:** Phase 3 — UX Optimization & Analytics Dashboard  
> **Trạng thái:** ✅ Đã hoàn thiện & sẵn sàng deploy

---

## 1. Tổng quan

Hệ thống quản lý đơn hàng Taobao nội bộ, chạy trên laptop làm server, truy cập từ mạng LAN. Dữ liệu đồng bộ 2 chiều với Google Sheets (source of truth).

### Tech Stack

| Layer | Công nghệ | Lý do |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Nhẹ, async, tự sinh API docs |
| Template | Jinja2 + HTMX | Server-rendered, không cần build JS |
| CSS | Tailwind CSS (CDN) | Responsive, không cần Node.js |
| Charts | Chart.js 4.x | Biểu đồ đẹp, nhẹ, không cần build |
| Cache | SQLite (aiosqlite) | Tìm kiếm SĐT/tên < 50ms |
| Database | Google Sheets API | Source of truth, sync 2 chiều |
| Export | openpyxl | Xuất Excel chuyên nghiệp |
| Deploy | Docker / uvicorn | Chạy trực tiếp trên Windows/Mac/Linux |

---

## 2. Tính năng Phase 3 — Mới

### 2.1 📊 Dashboard Analytics (Báo cáo chuyên sâu)

| Tính năng | Mô tả | Trạng thái |
|---|---|---|
| **KPI Cards** | 5 thẻ KPI: Tổng đơn, Doanh thu, Đã thu, Còn nợ, Chờ VĐ VN | ✅ |
| **Bar Chart: Top 10 Nợ** | Biểu đồ thanh ngang 10 khách nợ nhiều nhất (Chart.js) | ✅ |
| **Pie Chart: ACC Distribution** | Biểu đồ tròn tỷ lệ đơn giữa các ACC (Acc 1, Acc 2, Con cá, Acc Thảo) | ✅ |
| **Revenue by Sheet** | Thanh tiến trình doanh thu DON vs Don2 | ✅ |
| **Shipping Alerts** | Bảng cảnh báo đơn có VĐ TQ quá 7 ngày chưa có VĐ VN | ✅ |
| **Top Customers Table** | Bảng 10 khách hàng nhiều đơn nhất | ✅ |
| **Auto-refresh** | Toggle tự động reload mỗi 5 phút (sessionStorage) | ✅ |

### 2.2 🧠 Smart Form (Tạo đơn thông minh)

| Tính năng | Mô tả | Trạng thái |
|---|---|---|
| **Customer History** | Khi nhập SĐT → hiển thị bảng 3 đơn gần nhất của khách | ✅ |
| **Carrier Detection CN** | Tự phát hiện hãng vận chuyển TQ (YTO, SF, ZTO, STO, J&T, Cainiao...) theo prefix | ✅ |
| **Carrier Detection VN** | Tự phát hiện hãng VN (ViettelPost, GHN, GHTK, J&T...) | ✅ |
| **Carrier Logo** | Hiển thị badge màu + tên hãng ngay cạnh ô nhập liệu | ✅ |

### 2.3 ⌨️ Keyboard Shortcuts

| Phím tắt | Chức năng | Trạng thái |
|---|---|---|
| `Ctrl + S` | Lưu đơn (submit form) | ✅ |
| `Ctrl + Shift + N` | Tạo đơn mới (reset form) | ✅ |
| `Esc` | Blur ô input hiện tại | ✅ |

### 2.4 🔍 Bộ lọc nâng cao (Advanced Filters)

| Filter | Mô tả | Trạng thái |
|---|---|---|
| **Loại đơn** | Dropdown DON / Don2 | ✅ |
| **Trạng thái** | Dropdown động từ dữ liệu thực | ✅ |
| **Người đặt (ACC)** | Dropdown Acc 1, Acc 2, Con cá, Acc Thảo | ✅ |
| **Từ ngày / Đến ngày** | Date picker range | ✅ |
| **Xóa lọc** | Reset tất cả filter | ✅ |

### 2.5 📥 Export to Excel

| Tính năng | Mô tả | Trạng thái |
|---|---|---|
| **Export filtered** | Xuất đúng danh sách đang lọc ra .xlsx | ✅ |
| **Header styling** | Header xanh đậm, font bold, border | ✅ |
| **Summary row** | Tổng cộng Tổng giá / Cọc / Còn lại | ✅ |
| **Auto-width** | Tự động điều chỉnh độ rộng cột | ✅ |
| **Number format** | Hiển thị số theo format #,##0 | ✅ |

---

## 3. Kết quả QA — Kiểm thử với dữ liệu thực

### 3.1 Stress Test

| Metric | DON | Don2 | Tổng |
|---|---|---|---|
| Dòng dữ liệu (không tính header) | 2,098 | 770 | 2,868 |
| Đơn hàng parse được | 1,086 | 147 | **1,233** |
| Đơn nhiều sản phẩm | ~286 | ~142 | ~428 |
| Thời gian parse | <0.01s | <0.01s | **<0.01s** |

### 3.2 Chất lượng dữ liệu

| Metric | Số lượng | Đánh giá |
|---|---|---|
| Đơn thiếu tên khách | 21 | ⚠️ Orphan sub-rows |
| Đơn thiếu SĐT | 293 | ⚠️ Có thể là đơn chưa hoàn tất |
| Đơn giá = 0 | 259 | ⚠️ Đơn chưa chốt giá |
| Thiếu VĐ TQ | 108 | Bình thường |
| Thiếu VĐ VN | 523 | Bình thường (đơn chưa ship VN) |
| SĐT gắn nhiều tên | 45 | ⚠️ Cần chuẩn hóa trên Sheet |

### 3.3 Bugs đã phát hiện & sửa

| # | Bug | Severity | Trạng thái | Chi tiết |
|---|---|---|---|---|
| 1 | **Parser gộp Cha-Con sai** | 🔴 CRITICAL | ✅ ĐÃ SỬA | 286 đơn multi-product bị tách thành đơn riêng lẻ |
| 2 | **Column index crash** | 🟡 HIGH | ✅ ĐÃ SỬA | Thiếu safe access → crash khi dòng ngắn hơn expected |
| 3 | Cọc > Tổng giá | 🟠 MEDIUM | ⚠️ Dữ liệu Sheet | 6 đơn nhập sai (cọc > giá) |
| 4 | Còn lại ≠ Giá - Cọc | 🟢 LOW | ✅ Bình thường | 26 đơn đã thanh toán thêm trên Sheet |

### 3.4 Test cases

| # | Test | Result |
|---|---|---|
| 1 | Parse 2,868 dòng không crash | ✅ PASS |
| 2 | Multi-product grouping (286 đơn) | ✅ PASS (sau fix) |
| 3 | Orphan sub-row handling (21 đơn) | ✅ PASS |
| 4 | Money parsing: `23.420.000 đ`, `1,500,000`, `1500000đ` | ✅ PASS |
| 5 | Carrier detection: VTP, GHN, GHTK, J&T | ✅ PASS |
| 6 | Shipping calculation: DON & Don2 | ✅ PASS |
| 7 | Row index integrity (row_start ≥ 2) | ✅ PASS |
| 8 | Safe access trên dòng thiếu cột | ✅ PASS |
| 9 | Chart.js dashboard render | ✅ PASS |
| 10 | Customer history API | ✅ PASS |
| 11 | Export Excel download | ✅ PASS |
| 12 | Carrier detection CN (YTO, SF, ZTO, STO, J&T, Cainiao) | ✅ PASS |
| 13 | Keyboard shortcuts (Ctrl+S, Ctrl+Shift+N) | ✅ PASS |
| 14 | Advanced filters (sheet + status + account + date) | ✅ PASS |
| 15 | Auto-refresh toggle | ✅ PASS |

---

## 4. DevOps — Cấu hình vận hành

### 4.1 Môi trường

- **OS:** Linux/Windows/Mac
- **Python:** 3.10+
- **Port:** 8000 (configurable via .env)
- **Bind:** 0.0.0.0 (LAN access)

### 4.2 Files mới/updated (Phase 3)

| File | Mục đích |
|---|---|
| `backend/routers/api.py` | +4 endpoints: dashboard-data, customer-history, export-orders, shipping-alerts |
| `backend/routers/pages.py` | +advanced filters (account, date_from, date_to) |
| `backend/templates/pages/dashboard.html` | Redesign: Chart.js charts, KPI cards, shipping alerts, auto-refresh |
| `backend/templates/pages/orders.html` | Advanced filters + Export Excel button |
| `backend/templates/pages/create_order.html` | Smart form, keyboard shortcuts, carrier detection |
| `requirements.txt` | +openpyxl |

### 4.3 Hướng dẫn triển khai

**Windows (1 click):**
```
Double-click start_server.bat
```

**Manual:**
```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Xem IP cho nhân viên:**
```bash
python scripts/network_info.py
```

**Truy cập:**
- Máy chủ: `http://localhost:8000`
- LAN: `http://<IP-laptop>:8000`

---

## 5. Cấu trúc thư mục (cập nhật)

```
order-taobao/
├── backend/
│   ├── main.py
│   ├── config.py              # ENV-based config
│   ├── models/database.py     # SQLite schema + indexes
│   ├── routers/
│   │   ├── pages.py           # 7 HTML pages + advanced filters
│   │   └── api.py             # REST API + charts + export + smart form
│   ├── services/
│   │   ├── sheets.py          # Sheets read/write + safe parsing
│   │   ├── cache.py           # Sync Sheets → SQLite
│   │   └── tracking.py        # Carrier detection + URLs
│   ├── templates/
│   │   ├── base.html          # Sidebar, global search, auto-refresh
│   │   └── pages/
│   │       ├── dashboard.html # 📊 Chart.js: debt bar, ACC pie, shipping alerts
│   │       ├── search.html    # Color-coded payment status
│   │       ├── orders.html    # 🔍 Advanced filters + 📥 Export Excel
│   │       ├── order_detail.html
│   │       ├── create_order.html  # 🧠 Smart form + ⌨️ shortcuts + 🚚 carrier detection
│   │       ├── debt.html
│   │       ├── report.html    # Revenue breakdown tables
│   │       └── settings.html  # Credentials config UI
│   └── static/
├── credentials/               # Service Account JSON (gitignored)
├── data/                      # SQLite cache (gitignored)
├── scripts/
│   └── network_info.py        # IP info for LAN setup
├── start_server.bat           # One-click Windows startup
├── qa_test.py                 # Automated QA test script
├── .env                       # Environment variables (gitignored)
├── .gitignore
├── requirements.txt           # +openpyxl
├── Dockerfile
├── docker-compose.yml
├── README.md
└── report.md                  # ← Bạn đang đọc file này
```

---

## 6. API Endpoints (cập nhật)

| Method | Path | Mô tả |
|---|---|---|
| GET | `/` | Dashboard (KPI + charts + alerts) |
| GET | `/tim-kiem?q=` | Tìm kiếm (tên, 4-10 số cuối SĐT, tracking) |
| GET | `/don-hang` | Danh sách đơn (?sheet=&status=&account=&date_from=&date_to=&page=) |
| GET | `/don-hang/{id}` | Chi tiết đơn |
| GET | `/tao-don` | Form tạo đơn (smart form + shortcuts) |
| GET | `/cong-no` | Công nợ |
| GET | `/bao-cao` | Báo cáo chi tiết |
| GET | `/cau-hinh` | Cấu hình credentials/tokens |
| POST | `/api/sync` | Đồng bộ Sheet → SQLite |
| GET | `/api/search-customer?q=` | Auto-fill khách hàng |
| GET | `/api/customer-history?phone=` | 🆕 3 đơn gần nhất (smart form) |
| GET | `/api/search-tracking?q=` | Tìm theo tracking |
| GET | `/api/dashboard-data` | 🆕 JSON data cho charts |
| GET | `/api/export-orders?...` | 🆕 Xuất Excel |
| POST | `/api/create-order` | Tạo đơn → ghi Sheet |
| GET | `/api/calc-shipping` | Tính phí ship |
| GET | `/api/debt-summary` | Công nợ HTMX |
| POST | `/api/upload-credentials` | Upload Service Account JSON |
| POST | `/api/update-config` | Cập nhật .env |

---

## 7. Metrics thực tế

- **Tổng đơn:** 1,233 (DON: 1,086 / Don2: 147)
- **Đơn multi-product:** ~428
- **Khách hàng unique:** ~450 (ước tính)
- **Parse time:** < 0.01s
- **Search time:** < 50ms
- **Chart render:** < 200ms (Chart.js client-side)
- **Export time:** < 2s (1,233 đơn → .xlsx)

---

## 8. Audit Results (2026-05-04)

Xem chi tiết: `AUDIT_REPORT.md`

### Đã vá (Critical + High)

| Patch | Mô tả |
|---|---|
| C-01: XSS Fix | `js_escape()` cho tất cả customer data trong HTML/JS |
| C-02: Basic Auth | Thêm xác thực qua `AUTH_USERS` env var |
| C-03: Admin Auth | Bảo vệ `/api/update-config`, `/api/upload-credentials` |
| H-03: Duplicate Check | Kiểm tra trùng VĐ TQ trước khi tạo đơn |
| H-08: Local Buffer | Lưu tạm đơn vào `data/pending_orders.json` khi Sheets API lỗi |

### Files mới

| File | Mục đích |
|---|---|
| `backend/auth.py` | Basic Auth module |
| `backend/services/buffer.py` | Local buffer cho đơn hàng lỗi |
| `AUDIT_REPORT.md` | Báo cáo audit đầy đủ |
| `PATCH_001_SECURITY.py` | Reference patches |

### Còn lại cần sửa trên Sheet

| Issue | Severity | Workaround |
|---|---|---|
| 21 orphan sub-rows (thiếu tên) | Low | Sửa trực tiếp trên Sheet |
| 45 SĐT có nhiều tên | Low | Chuẩn hóa tên trên Sheet |
| 6 đơn cọc > giá | Medium | Sửa trên Sheet |
| Auto-sync chưa có | Low | Dùng nút "Đồng bộ" hoặc Auto-refresh |

---

## 9. Phase tiếp theo

| # | Tính năng | Ưu tiên |
|---|---|---|
| 1 | Auto-sync background (APScheduler) | Cao |
| 2 | Multi-user / phân quyền | Cao |
| 3 | Tracking tự động (GHN/VTP API) | Trung bình |
| 4 | Thanh toán batch | Thấp |
| 5 | Mobile responsive improvements | Thấp |

---

**Hết báo cáo Phase 3.**
