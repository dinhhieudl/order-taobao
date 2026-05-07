# 📦 Báo cáo Dự án — Quản lý Vận đơn Taobao

> **Ngày:** 2026-05-07  
> **Giai đoạn:** Phase 5 — Multi-Product Order Support  
> **Trạng thái:** ✅ Đã hoàn thiện & push lên repo

---

## 1. Tổng quan thay đổi Phase 5

Fix tính năng tạo đơn hàng nhiều sản phẩm: khi nhập đơn gồm nhiều sản phẩm, hệ thống ghi nhiều dòng vào Google Sheet (mỗi dòng 1 sản phẩm), chỉ dòng đầu tiên chứa thông tin khách hàng.

### Ví dụ thực tế (Don2 rows 280-296)

```
Row 280: [date=26/04] [name=Nguyễn Long] [product=LÔ HÀNG] [price=10.045.000đ] [deposit=7.000.000đ]
Row 281: [product=Kệ gỗ] [weight=0,68] [tracking=78997384622117]
Row 282: [product=Phụ kiện chụp ảnh] [weight=0,10] [tracking=773416865482946]
Row 283: [product=Kính] [weight=0,10] [tracking=435137777095133]
... (16 sản phẩm)
```

### Tech Stack (không đổi)

| Layer | Công nghệ |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Template | Jinja2 + HTMX |
| CSS | Tailwind CSS (CDN) |
| Charts | Chart.js 4.x |
| Cache | SQLite (aiosqlite) |
| Database | Google Sheets API (source of truth) |
| Export | openpyxl |
| Search | + unidecode (diacritics-free) |

---

## 2. Danh sách Fix — Chi tiết

### 2.1 🔴 Multi-Product Order (Logic chính)

| # | Vấn đề | Fix | File |
|---|---|---|---|
| 1 | **Tạo đơn nhiều SP ghi 1 dòng** với product names nối bằng " \| " | `append_order_to_sheet` giờ nhận `product_names` (list), ghi N dòng: header + item rows | `sheets.py` |
| 2 | **Endpoint join product names** thành 1 string | Chuyển sang truyền `product_names` list trực tiếp | `api.py` |
| 3 | **Thiếu test coverage** cho multi-product | Viết 8 unit tests + 2 live integration tests | `test_multi_product.py` |

### 2.2 Chi tiết kỹ thuật

**`sheets.py` — `append_order_to_sheet()`:**
- Nhận `order_data["product_names"]` (list) thay vì `product_name` (string)
- Fallback: nếu chỉ có `product_name` (backward compatible), chuyển thành list 1 phần tử
- **Header row** (idx=0): ghi đầy đủ thông tin khách hàng + sản phẩm đầu tiên
- **Item rows** (idx>0): chỉ ghi tên sản phẩm (cột G/F), các cột khác để trống
- Batch update tất cả rows trong 1 API call (hiệu quả, tránh rate limit)

**`api.py` — `create_order()`:**
- Lọc bỏ product names rỗng: `[p.strip() for p in product_name if p.strip()]`
- Truyền `product_names` list vào `order_data`
- Success message hiển thị số sản phẩm: "3 sản phẩm"

**Cột sản phẩm theo sheet:**
- DON: cột G (index 7, 1-based)
- Don2: cột F (index 6, 1-based)

---

## 3. Test Results

### 3.1 Unit Tests (8/8 PASS)

| # | Test case | Kết quả |
|---|---|---|
| 1 | Single product backward compatible → 1 row | ✅ |
| 2 | Multi-product DON → 4 rows (1 header + 3 items) | ✅ |
| 3 | Multi-product Don2 → 3 rows (1 header + 2 items) | ✅ |
| 4 | Empty product list → 1 row with empty product | ✅ |
| 5 | Empty product names filtered correctly | ✅ |
| 6 | Insert position calculated correctly | ✅ |
| 7 | Buffer round-trip preserves product_names | ✅ |
| 8 | Range spans all rows correctly | ✅ |

### 3.2 Live Integration Tests (Google Sheet)

| # | Sheet | Input | Kết quả |
|---|---|---|---|
| 1 | Don2 | 3 sản phẩm (A, B, C) | ✅ Row 301: header+A, Row 302: B, Row 303: C |
| 2 | DON | 1 sản phẩm (Quạt Gree) | ✅ Row 1996: header+product |

- Test data đã được xóa sạch sau khi verify
- Cấu trúc sheet không bị hỏng

---

## 4. Files thay đổi

| File | Thay đổi |
|---|---|
| `backend/services/sheets.py` | Refactor `append_order_to_sheet` — multi-row write with `product_names` list |
| `backend/routers/api.py` | Update `create_order` — pass product list, filter empty, show count |
| `test_multi_product.py` | **Mới** — 8 unit tests cho multi-product logic |
| `report.md` | Cập nhật báo cáo Phase 5 |

---

## 5. Metrics

- **Code changes:** 3 files modified, 1 new file
- **Unit tests:** 8/8 pass
- **Live tests:** 2/2 pass (Don2 + DON)
- **Backward compatible:** ✅ Single product vẫn hoạt động như cũ
- **Buffer compatible:** ✅ `product_names` list lưu/restored đúng qua buffer

---

## 6. API Endpoints (cập nhật)

| Method | Path | Thay đổi Phase 5 |
|---|---|---|
| POST | `/api/create-order` | **Multi-product** — ghi N rows, hiển thị số SP |

---

**Hết báo cáo Phase 5.**
