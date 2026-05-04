# 📦 Báo cáo Dự án — Quản lý Vận đơn Taobao

> **Ngày:** 2026-05-04  
> **Giai đoạn:** Phase 1 — MVP hoàn thành  
> **Trạng thái:** ✅ Sẵn sàng cho DevOps & QA

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

## 2. Cấu trúc thư mục

```
taobao-orders/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Biến môi trường, hằng số
│   ├── models/
│   │   └── database.py          # SQLite schema + connection
│   ├── routers/
│   │   ├── pages.py             # 6 HTML pages (dashboard, search, orders, create, debt, report)
│   │   └── api.py               # REST API endpoints (sync, search, create, calc)
│   ├── services/
│   │   ├── sheets.py            # Google Sheets read/write + parse logic
│   │   ├── cache.py             # Sync Sheets → SQLite
│   │   └── tracking.py          # Vận đơn carrier detection + URL
│   └── templates/
│       ├── base.html            # Layout (sidebar, topbar, Tailwind, HTMX)
│       └── pages/
│           ├── dashboard.html   # Tổng quan: stats, status, top KH
│           ├── search.html      # Tìm kiếm theo SĐT/tên/tracking
│           ├── orders.html      # Danh sách đơn + phân trang + lọc
│           ├── order_detail.html# Chi tiết đơn + sản phẩm + lịch sử KH
│           ├── create_order.html# Form tạo đơn mới (auto-fill, tính ship)
│           ├── debt.html        # Công nợ theo khách hàng
│           └── report.html      # Báo cáo doanh thu, ACC, phí ship
├── data/                        # SQLite cache (auto-created)
├── scripts/                     # (reserved cho future scripts)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── run.sh / run.bat
├── .gitignore
└── README.md
```

---

## 3. Tính năng đã hoàn thành

### ✅ P0 — Core

| # | Tính năng | Mô tả | Trạng thái |
|---|---|---|---|
| 1 | Đồng bộ Google Sheets | Đọc DON + Don2, parse đơn nhiều SP, ghi vào SQLite cache | ✅ |
| 2 | Tìm kiếm SĐT/Tên/Tracking | Fuzzy search, kết quả realtime qua HTMX | ✅ |
| 3 | Tạo đơn mới | Form chọn DON/Don2, auto-fill từ SĐT, ghi thẳng vào Sheet | ✅ |
| 4 | Dashboard tổng quan | Stats theo sheet, trạng thái, top KH, đơn gần đây | ✅ |
| 5 | Danh sách đơn hàng | Bảng + phân trang + lọc theo sheet/trạng thái | ✅ |
| 6 | Chi tiết đơn | Sản phẩm, vận đơn, tài chính, lịch sử KH | ✅ |

### ✅ P1 — Business

| # | Tính năng | Mô tả | Trạng thái |
|---|---|---|---|
| 7 | Công nợ | Bảng nợ theo KH, thanh tiến độ, filter | ✅ |
| 8 | Báo cáo doanh thu | Theo sheet type, theo ACC, theo ngày, phí ship | ✅ |
| 9 | Tính phí ship tự động | DON: max(kg×14k, m³×2.1M) / Don2: kg×28k | ✅ |
| 10 | Tracking vận đơn | Detect carrier (GHN/VTP/GHTK/J&T), link tra cứu | ✅ |

### ⏳ P2 — Chưa triển khai (Phase 2)

| # | Tính năng | Ghi chú |
|---|---|---|
| 11 | Tracking tự động (API) | Cần GHN/VTP token |
| 12 | Multi-user / phân quyền | Cần thiết kế auth |
| 13 | Export Excel | Cần thư viện openpyxl |
| 14 | Upload ảnh sản phẩm | Cần storage |
| 15 | Thông báo Zalo/SMS | Cần Zalo OA token |

---

## 4. Data Schema

### Google Sheets → SQLite mapping

**Sheet DON (Tiểu ngạch):**

| Cột Sheet | Field SQLite | Ghi chú |
|---|---|---|
| stt (cột 1) | order_date | Định dạng dd/mm |
| Tên | customer_name | |
| SDT | customer_phone | INDEX, tìm kiếm chính |
| Địa chỉ | customer_address | |
| SẢN PHẨM | → order_items.product_name | Nhiều SP = nhiều dòng con |
| KHỐI LƯỢNG | → order_items.weight | kg, tính ship |
| KÍCH THƯỚC | → order_items.volume | m³, tính ship |
| Vận đơn TQ | tracking_cn / order_items.tracking_cn | |
| Vận đơn VN | tracking_vn | Parse prefix → carrier |
| ACC | account | Acc 1/2/Con cá/Acc Thảo |
| GIÁ | total_price | Dòng chính |
| CỌC | deposit | Dòng chính |
| hàng về tt | remaining | Dòng chính |
| Trạng Thái | status | Hiển thị nguyên bản |

**Cấu trúc đơn nhiều sản phẩm:**
```
Row 1: [stt, ngày, TÊN, SĐT, ĐC, ..., ..., ..., VD_TQ, ..., GIÁ, CỌC, CÒN]  ← dòng chính
Row 2: [  ,     ,    ,    ,   , ..., SP1, kg, m³, VD_TQ1, ..., giá1]          ← item
Row 3: [  ,     ,    ,    ,   , ..., SP2, kg, m³, VD_TQ2, ..., giá2]          ← item
```

### SQLite Tables

```sql
orders       (id, sheet_type, row_start, row_end, customer_name, phone, address,
              tracking_cn, tracking_vn, account, total_price, deposit, remaining,
              status, order_date, carrier, ...)

order_items  (id, order_id FK, product_name, weight, volume, tracking_cn, item_price)

customers    (id, name, phone UNIQUE, address, last_sync)
```

### Indexes (tối ưu tìm kiếm)

```
customers: phone, name
orders:    customer_phone, customer_name, tracking_cn, tracking_vn, status, order_date, sheet_type
```

---

## 5. API Endpoints

| Method | Path | Mô tả |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/tim-kiem?q=` | Tìm kiếm |
| GET | `/don-hang` | Danh sách đơn (?sheet=&status=&page=) |
| GET | `/don-hang/{id}` | Chi tiết đơn |
| GET | `/tao-don` | Form tạo đơn |
| GET | `/cong-no` | Công nợ |
| GET | `/bao-cao` | Báo cáo |
| POST | `/api/sync` | Đồng bộ Sheet → SQLite |
| GET | `/api/search-customer?q=` | Auto-fill khách hàng (HTMX) |
| GET | `/api/search-tracking?q=` | Tìm theo tracking (HTMX) |
| POST | `/api/create-order` | Tạo đơn mới → ghi Sheet |
| GET | `/api/calc-shipping?sheet=&weight=&volume=` | Tính phí ship |

---

## 6. Cấu hình & Environment Variables

| Variable | Default | Mô tả |
|---|---|---|
| `GOOGLE_CREDS_FILE` | `an-helper-*.json` | Service Account JSON |
| `SPREADSHEET_ID` | `1mFlnU...` | Google Sheet ID |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Port |
| `GHN_TOKEN` | (empty) | GHN API token (optional) |
| `VTP_TOKEN` | (empty) | ViettelPost API token (optional) |

---

## 7. Hướng dẫn triển khai

### DevOps

**Option A — Chạy trực tiếp (Windows):**
```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Option B — Docker:**
```bash
# Đặt file credentials vào root project
cp /path/to/service-account.json ./credentials.json
# Sửa docker-compose.yml nếu cần
docker-compose up -d
```

**Truy cập LAN:**
- Tìm IP laptop: `ipconfig` (Windows) / `ifconfig` (Mac/Linux)
- Truy cập: `http://<IP>:8000`

### QA

**Test cases chính:**

| # | Test | Steps | Expected |
|---|---|---|---|
| 1 | Đồng bộ | Nhấn "Đồng bộ Sheet" | Hiện "Đã đồng bộ X đơn" |
| 2 | Tìm SĐT | Gõ SĐT ở thanh tìm kiếm | Hiện đơn hàng matching |
| 3 | Tạo đơn | Điền form → Submit | Đơn xuất hiện trong Sheet |
| 4 | Auto-fill | Gõ SĐT đã có → chọn | Tên, ĐC tự điền |
| 5 | Tính ship | Nhập kg/m³ → xem | Giá ship = max(kg×14k, m³×2.1M) |
| 6 | Công nợ | Vào /cong-no | Bảng nợ hiển thị đúng |
| 7 | Pagination | Vào /don-hang → chuyển trang | Trang 2, 3... load đúng |
| 8 | Mobile | Mở trên phone | Responsive, sidebar ẩn |

---

## 8. Known Issues & Limitations

| Issue | Severity | Workaround |
|---|---|---|
| Tên sản phẩm không chuẩn hóa (quạt gree vs Quạt Gree) | Low | Sửa trực tiếp trong Sheet |
| Cột 17 header là giá trị tiền (23.420.000 đ) | Low | Bỏ qua trong parser |
| Don2: cột NGUỒN, PHÍ VẬN CHUYỂN, DOANH THU trống 0% | Low | Chưa dùng,预留 |
| Tracking tự động cần API token | Medium | Dùng link tra cứu thủ công |
| Không có auth/multi-user | Medium | Phase 2 |
| SQLite cache cần đồng bộ thủ công | Low | Có nút "Đồng bộ" trong app |

---

## 9. Metrics (từ data hiện tại)

- **Tổng đơn:** 2,225 (DON: 1,491 / Don2: 734)
- **Khách hàng unique:** 616
- **Tổng doanh thu:** ~6.46 tỷ VNĐ
- **Còn phải thu:** ~2.42 tỷ VNĐ
- **Đơn có VĐ TQ nhưng chưa có VĐ VN:** ~1,052 (đơn tồn ship)
- **Phí ship ước tính:** ~1.36 tỷ VNĐ

---

## 10. File cần thiết cho Phase 2

| File | Mục đích |
|---|---|
| `credentials.json` | Service Account — KHÔNG commit vào git |
| `.env` | Environment variables (GHN_TOKEN, VTP_TOKEN khi có) |
| `data/cache.db` | SQLite cache (auto-generated sau sync đầu) |

---

**Hết báo cáo Phase 1.**  
Sẵn sàng bàn giao cho DevOps deploy và QA test.
