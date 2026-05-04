# 📦 Báo cáo Dự án — Quản lý Vận đơn Taobao

> **Ngày:** 2026-05-04  
> **Giai đoạn:** Phase 2 — QA & DevOps  
> **Trạng thái:** ✅ Đã kiểm thử với dữ liệu thực

---

## 1. Tổng quan

Hệ thống quản lý đơn hàng Taobao nội bộ, chạy trên laptop làm server, truy cập từ mạng LAN. Dữ liệu đồng bộ 2 chiều với Google Sheets (source of truth).

### Tech Stack

| Layer | Công nghệ | Lý do |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Nhẹ, async, tự sinh API docs |
| Template | Jinja2 + HTMX | Server-rendered, không cần build JS |
| CSS | Tailwind CSS (CDN) | Responsive, không cần Node.js |
| Cache | SQLite (aiosqlite) | Tìm kiếm SĐT/tên < 50ms |
| Database | Google Sheets API | Source of truth, sync 2 chiều |
| Deploy | Docker / uvicorn | Chạy trực tiếp trên Windows/Mac/Linux |

---

## 2. Kết quả QA — Kiểm thử với dữ liệu thực

### 2.1 Stress Test

| Metric | DON | Don2 | Tổng |
|---|---|---|---|
| Dòng dữ liệu (không tính header) | 2,098 | 770 | 2,868 |
| Đơn hàng parse được | 1,086 | 147 | **1,233** |
| Đơn nhiều sản phẩm | ~286 | ~142 | ~428 |
| Thời gian parse | <0.01s | <0.01s | **<0.01s** |

### 2.2 Chất lượng dữ liệu

| Metric | Số lượng | Đánh giá |
|---|---|---|
| Đơn thiếu tên khách | 21 | ⚠️ Orphan sub-rows |
| Đơn thiếu SĐT | 293 | ⚠️ Có thể là đơn chưa hoàn tất |
| Đơn giá = 0 | 259 | ⚠️ Đơn chưa chốt giá |
| Thiếu VĐ TQ | 108 | Bình thường |
| Thiếu VĐ VN | 523 | Bình thường (đơn chưa ship VN) |
| SĐT gắn nhiều tên | 45 | ⚠️ Cần chuẩn hóa trên Sheet |

### 2.3 Bugs đã phát hiện & sửa

| # | Bug | Severity | Trạng thái | Chi tiết |
|---|---|---|---|---|
| 1 | **Parser gộp Cha-Con sai** | 🔴 CRITICAL | ✅ ĐÃ SỬA | 286 đơn multi-product bị tách thành đơn riêng lẻ vì parser chỉ gộp khi header KHÔNG có sản phẩm. Fix: header có tên → luôn collect sub-rows phía sau |
| 2 | **Column index crash** | 🟡 HIGH | ✅ ĐÃ SỬA | Thiếu safe access → crash khi dòng ngắn hơn expected. Fix: thêm safe_str/safe_money/safe_float wrappers |
| 3 | Cọc > Tổng giá | 🟠 MEDIUM | ⚠️ Dữ liệu Sheet | 6 đơn nhập sai (cọc > giá). Cần sửa trên Sheet |
| 4 | Còn lại ≠ Giá - Cọc | 🟢 LOW | ✅ Bình thường | 26 đơn đã thanh toán thêm trên Sheet. Đây là hành vi đúng |

### 2.4 Test cases

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

---

## 3. DevOps — Cấu hình vận hành

### 3.1 Môi trường

- **OS:** Linux/Windows/Mac
- **Python:** 3.10+
- **Port:** 8000 (configurable via .env)
- **Bind:** 0.0.0.0 (LAN access)

### 3.2 Files mới

| File | Mục đích |
|---|---|
| `start_server.bat` | One-click khởi động trên Windows |
| `scripts/network_info.py` | Hiển thị IP nội bộ cho nhân viên |
| `.env` | Cấu hình credentials, tokens |
| `credentials/` | Service Account JSON (gitignored) |
| `qa_test.py` | Script kiểm thử tự động |

### 3.3 Hướng dẫn triển khai

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

## 4. Tối ưu hiệu năng

### 4.1 Caching Strategy

| Layer | Cơ chế | TTL |
|---|---|---|
| Google Sheets → SQLite | Manual sync (nút "Đồng bộ") | Đến khi user nhấn sync |
| SQLite → UI | Direct query | Real-time |
| HTMX search | Debounce 300ms | Giảm API calls |

**Khuyến nghị Phase 3:** Auto-sync mỗi 5 phút bằng background task (APScheduler hoặc asyncio).

### 4.2 Search Optimization

- **SQLite INDEX** trên: `customer_phone`, `customer_name`, `tracking_cn`, `tracking_vn`
- **Query time:** < 50ms cho 5,000-10,000 dòng (đã test với 1,233 đơn)
- **Pagination:** 30 đơn/trang, chỉ load trang hiện tại

### 4.3 Hiệu năng thực tế

| Metric | Kết quả |
|---|---|
| Parse 2,868 dòng Sheet | < 0.01s |
| Search 1,233 đơn | < 50ms |
| Full sync Sheet → SQLite | ~3-5s (depends on API) |

---

## 5. Cấu trúc thư mục (cập nhật)

```
order-taobao/
├── backend/
│   ├── main.py
│   ├── config.py              # ENV-based config
│   ├── models/database.py     # SQLite schema + indexes
│   ├── routers/
│   │   ├── pages.py           # 7 HTML pages
│   │   └── api.py             # REST API + upload + config
│   ├── services/
│   │   ├── sheets.py          # Sheets read/write + safe parsing
│   │   ├── cache.py           # Sync Sheets → SQLite
│   │   └── tracking.py        # Carrier detection
│   ├── templates/
│   │   ├── base.html
│   │   └── pages/
│   │       ├── dashboard.html
│   │       ├── search.html    # Color-coded payment status
│   │       ├── orders.html
│   │       ├── order_detail.html
│   │       ├── create_order.html  # Tracking CN validation
│   │       ├── debt.html
│   │       ├── report.html
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
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
└── report.md
```

---

## 6. API Endpoints

| Method | Path | Mô tả |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/tim-kiem?q=` | Tìm kiếm (tên, 4-10 số cuối SĐT, tracking) |
| GET | `/don-hang` | Danh sách đơn (?sheet=&status=&page=) |
| GET | `/don-hang/{id}` | Chi tiết đơn |
| GET | `/tao-don` | Form tạo đơn |
| GET | `/cong-no` | Công nợ |
| GET | `/bao-cao` | Báo cáo |
| GET | `/cau-hinh` | Cấu hình credentials/tokens |
| POST | `/api/sync` | Đồng bộ Sheet → SQLite |
| GET | `/api/search-customer?q=` | Auto-fill khách hàng |
| GET | `/api/search-tracking?q=` | Tìm theo tracking |
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

---

## 8. Known Issues

| Issue | Severity | Workaround |
|---|---|---|
| 21 orphan sub-rows (thiếu tên) | Low | Sửa trực tiếp trên Sheet |
| 45 SĐT có nhiều tên | Low | Chuẩn hóa tên trên Sheet |
| 6 đơn cọc > giá | Medium | Sửa trên Sheet |
| Auto-sync chưa có | Low | Nhấn nút "Đồng bộ" thủ công |
| Không có auth/multi-user | Medium | Phase 3 |

---

## 9. Phase tiếp theo

| # | Tính năng | Ưu tiên |
|---|---|---|
| 1 | Auto-sync background (mỗi 5 phút) | Cao |
| 2 | Multi-user / phân quyền | Cao |
| 3 | Export Excel | Trung bình |
| 4 | Tracking tự động (GHN/VTP API) | Trung bình |
| 5 | Thanh toán batch | Thấp |

---

**Hết báo cáo Phase 2.**
