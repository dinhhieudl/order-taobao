# 📦 Báo cáo Dự án — Quản lý Vận đơn Taobao

> **Ngày:** 2026-05-04  
> **Giai đoạn:** Phase 1.5 — Nâng cấp theo yêu cầu  
> **Trạng thái:** ✅ Đã hoàn thành các yêu cầu kỹ thuật

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
order-taobao/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Biến môi trường, hằng số (ENV-based)
│   ├── models/
│   │   └── database.py          # SQLite schema + connection
│   ├── routers/
│   │   ├── pages.py             # 7 HTML pages (dashboard, search, orders, create, debt, report, settings)
│   │   └── api.py               # REST API endpoints (sync, search, create, calc, upload-creds, update-config)
│   ├── services/
│   │   ├── sheets.py            # Google Sheets read/write + parse logic (header/item grouping)
│   │   ├── cache.py             # Sync Sheets → SQLite
│   │   └── tracking.py          # Vận đơn carrier detection + URL
│   ├── templates/
│   │   ├── base.html            # Layout (sidebar, topbar, Tailwind, HTMX)
│   │   └── pages/
│   │       ├── dashboard.html   # Tổng quan: stats, status, top KH
│   │       ├── search.html      # Tìm kiếm theo tên/SĐT(4-10 số cuối)/tracking + color-coded
│   │       ├── orders.html      # Danh sách đơn + phân trang + lọc
│   │       ├── order_detail.html# Chi tiết đơn + sản phẩm + lịch sử KH
│   │       ├── create_order.html# Form tạo đơn mới (auto-fill, tracking CN validation)
│   │       ├── debt.html        # Công nợ theo khách hàng
│   │       ├── report.html      # Báo cáo doanh thu, ACC, phí ship
│   │       └── settings.html    # Cấu hình credentials, tokens, sheet ID
│   └── static/                  # Static files (reserved)
├── credentials/                 # Google Service Account JSON (gitignored)
├── data/                        # SQLite cache (auto-created, gitignored)
├── scripts/                     # (reserved cho future scripts)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── run.sh / run.bat
├── .env                         # Environment variables (gitignored)
├── .gitignore
├── README.md
└── report.md
```

---

## 3. Phân tích & Nâng cấp theo yêu cầu

### ✅ 3.1 Data Engine — Logic xử lý dòng Header/Item

**Trạng thái:** Đã có sẵn + Đã kiểm tra

Logic parse đã tồn tại trong `backend/services/sheets.py`:
- `parse_don_sheet()` và `parse_don2_sheet()` implements đúng logic:
  - **Dòng có Tên nhưng không có SP** → Header (dòng chính)
  - **Dòng có SP nhưng không có Tên** → Item (dòng con)
  - Gộp thành một đối tượng Order duy nhất với danh sách `items[]`
- Xử lý cả trường hợp đơn 1 sản phẩm (cùng dòng) và đơn nhiều sản phẩm (nhiều dòng)

**Về `@st.cache_data`:** Dự án dùng FastAPI (không phải Streamlit), nên `@st.cache_data` không áp dụng được. Thay vào đó, hệ thống dùng **SQLite cache** (`backend/services/cache.py`) cho tìm kiếm nhanh, với nút "Đồng bộ Sheet" để refresh dữ liệu. Đây là cách tiếp cận tốt hơn cho FastAPI.

### ✅ 3.2 Chức năng Tra cứu (Search) — ĐÃ NÂNG CẤP

**Thay đổi:**

| Tính năng | Trước | Sau |
|---|---|---|
| Tìm theo SĐT | Chỉ match đầy đủ | Hỗ trợ 4-10 số cuối SĐT |
| Tìm theo tên | ✅ Có | ✅ Giữ nguyên |
| Bảng kết quả | Liệt kê đơn giản | Bảng đầy đủ: Ngày, Tên, SP, Tổng giá, Cọc, Còn lại |
| Màu sắc trạng thái | ❌ Không có | ✅ Color-coded theo mức nợ |

**Color-coded logic:**
- 🔴 **Đỏ** — Chưa cọc (deposit = 0)
- 🟡 **Vàng** — Còn nợ > 50%
- 🟠 **Cam** — Còn nợ ≤ 50%
- ✅ **Xanh lá** — Đã thanh toán đủ

**Files thay đổi:**
- `backend/routers/pages.py` — Search query thêm điều kiện `customer_phone LIKE '%last_digits'`
- `backend/templates/pages/search.html` — Rewrite hoàn toàn với bảng + color coding

### ✅ 3.3 Chức năng Nhập đơn (Form) — ĐÃ NÂNG CẤP

**Thay đổi:**

| Tính năng | Trước | Sau |
|---|---|---|
| Auto-fill SĐT cũ | ✅ Có | ✅ Giữ nguyên |
| Validate mã VĐ TQ | Chỉ xóa khoảng trắng | ✅ Tự động VIẾT HOA + xóa khoảng trắng + chỉ giữ alphanumeric |
| Ô "Còn lại" | Có thể edit, gửi giá trị lên Sheet | ✅ Read-only, không gửi lên Sheet (giữ công thức Sheet) |
| Tự động tính Còn lại | ✅ Có (JS) | ✅ Giữ nguyên (Giá - Cọc) |

**Chi tiết kỹ thuật về "Còn lại":**
- Input field: `readonly`, `tabindex="-1"`, `cursor-not-allowed` — không thể edit bằng tay
- Khi submit form: field `remaining_display` không có `name` attribute (không gửi lên server)
- API endpoint: `remaining = 0` — không ghi vào Sheet
- Sheet column "hàng về tt" (cột 17): để trống → **giữ nguyên công thức có sẵn** trên Sheet
- Khi khách thanh toán thêm → cập nhật cột thanh toán trên Sheet → Sheet tự trừ vào "Còn lại"

**Files thay đổi:**
- `backend/routers/api.py` — `create_order()`: normalize tracking CN, không gửi remaining
- `backend/services/sheets.py` — `append_order_to_sheet()`: cột remaining để trống
- `backend/templates/pages/create_order.html` — Tracking CN validation, remaining read-only

### ✅ 3.4 Cấu hình Credentials — ĐÃ THÊM MỚI

**Trang cấu hình `/cau-hinh`:**
- Hiển thị cấu hình hiện tại (creds file, spreadsheet ID, tokens)
- Upload Google Service Account JSON → lưu vào `credentials/` + tự cập nhật `.env`
- Form chỉnh sửa: Google Credentials File, Spreadsheet ID, GHN Token, VTP Token
- Lưu vào file `.env` — cần restart server để áp dụng

**API endpoints mới:**
- `POST /api/upload-credentials` — Upload JSON credentials
- `POST /api/update-config` — Cập nhật `.env`

**Files mới:**
- `backend/templates/pages/settings.html`
- `credentials/` directory (gitignored)

**Files thay đổi:**
- `backend/config.py` — Thêm `CREDENTIALS_DIR`, đọc Sheet names từ ENV
- `backend/routers/pages.py` — Thêm route `/cau-hinh`
- `backend/routers/api.py` — Thêm 2 API endpoints
- `backend/templates/base.html` — Thêm link "Cấu hình" vào sidebar
- `.gitignore` — Thêm `credentials/`

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
| hàng về tt | remaining | **Để trống khi tạo đơn mới** — Sheet formula tự tính |
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

---

## 5. API Endpoints

| Method | Path | Mô tả |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/tim-kiem?q=` | Tìm kiếm (tên, 4-10 số cuối SĐT, tracking) |
| GET | `/don-hang` | Danh sách đơn (?sheet=&status=&page=) |
| GET | `/don-hang/{id}` | Chi tiết đơn |
| GET | `/tao-don` | Form tạo đơn |
| GET | `/cong-no` | Công nợ |
| GET | `/bao-cao` | Báo cáo |
| GET | `/cau-hinh` | Trang cấu hình credentials/tokens |
| POST | `/api/sync` | Đồng bộ Sheet → SQLite |
| GET | `/api/search-customer?q=` | Auto-fill khách hàng (HTMX) |
| GET | `/api/search-tracking?q=` | Tìm theo tracking (HTMX) |
| POST | `/api/create-order` | Tạo đơn mới → ghi Sheet (không ghi remaining) |
| GET | `/api/calc-shipping?sheet=&weight=&volume=` | Tính phí ship |
| GET | `/api/debt-summary?q=` | Công nợ HTMX |
| POST | `/api/upload-credentials` | Upload Google Service Account JSON |
| POST | `/api/update-config` | Cập nhật .env |

---

## 6. Cấu hình & Environment Variables

| Variable | Default | Mô tả |
|---|---|---|
| `GOOGLE_CREDS_FILE` | `an-helper-*.json` | Service Account JSON (configurable via UI) |
| `SPREADSHEET_ID` | `1mFlnU...` | Google Sheet ID (configurable via UI) |
| `SHEET_DON` | `DON` | Tên sheet tiểu ngạch |
| `SHEET_DON2` | `Don2` | Tên sheet TMDT |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Port |
| `GHN_TOKEN` | (empty) | GHN API token (configurable via UI) |
| `VTP_TOKEN` | (empty) | ViettelPost API token (configurable via UI) |

---

## 7. Hướng dẫn triển khai

### DevOps

**Option A — Chạy trực tiếp:**
```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Option B — Docker:**
```bash
docker-compose up -d
```

**Truy cập LAN:**
- Truy cập: `http://<IP>:8000`
- Trang cấu hình: `http://<IP>:8000/cau-hinh`

### QA — Test cases mới

| # | Test | Steps | Expected |
|---|---|---|---|
| 1 | Tìm 4-10 số cuối SĐT | Gõ "786505" vào ô tìm kiếm | Hiện đơn có SĐT chứa "786505" |
| 2 | Color-coded kết quả | Tìm khách có nợ | Đơn chưa cọc = đỏ, nợ > 50% = vàng |
| 3 | Tracking CN uppercase | Nhập "abc 123" vào VĐ TQ | Tự chuyển thành "ABC123" |
| 4 | Remaining read-only | Thử edit ô "Còn lại" | Không thể edit |
| 5 | Sheet formula preserved | Tạo đơn mới → kiểm tra Sheet | Cột "hàng về tt" trống, có công thức |
| 6 | Upload credentials | Vào /cau-hinh → upload JSON | Lưu vào credentials/, cập nhật .env |
| 7 | Update config | Sửa Spreadsheet ID → lưu | .env được cập nhật |

---

## 8. Known Issues & Limitations

| Issue | Severity | Workaround |
|---|---|---|
| Tên sản phẩm không chuẩn hóa | Low | Sửa trực tiếp trong Sheet |
| Tracking tự động cần API token | Medium | Dùng link tra cứu thủ công |
| Không có auth/multi-user | Medium | Phase 2 |
| SQLite cache cần đồng bộ thủ công | Low | Có nút "Đồng bộ" trong app |
| Config thay đổi cần restart | Low | Phase 2: hot-reload |

---

## 9. Metrics (từ data hiện tại)

- **Tổng đơn:** ~2,225 (DON: ~1,491 / Don2: ~734)
- **Khách hàng unique:** ~616
- **Tổng doanh thu:** ~6.46 tỷ VNĐ
- **Còn phải thu:** ~2.42 tỷ VNĐ

---

## 10. Phase tiếp theo (Gợi ý)

| # | Tính năng | Mô tả |
|---|---|---|
| 1 | Tracking tự động (API) | Gọi GHN/VTP API để lấy trạng thái vận đơn tự động |
| 2 | Multi-user / phân quyền | Đăng nhập, phân quyền xem/sửa |
| 3 | Export Excel | Xuất báo cáo ra file Excel |
| 4 | Thanh toán batch | Ghi thanh toán hàng loạt vào Sheet |
| 5 | Auto-sync | Tự đồng bộ Sheet mỗi N phút (background task) |

---

**Hết báo cáo Phase 1.5.**
