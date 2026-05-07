# 📦 Báo cáo Dự án — Quản lý Vận đơn Taobao

> **Ngày:** 2026-05-07  
> **Giai đoạn:** Phase 6 — Multi-Product Parsing Fix  
> **Trạng thái:** ✅ Đã fix & test kĩ

---

## 1. Tổng quan thay đổi Phase 6

Fix bug **nghiêm trọng** trong logic parse đơn hàng nhiều sản phẩm: khi dòng đầu tiên (header) có cả tên khách hàng VÀ sản phẩm, hệ thống chỉ lấy sản phẩm của dòng header, **bỏ qua toàn bộ các dòng sản phẩm phía sau**.

### Bug gốc (Root Cause)

Trong `_build_order_don()` và `_build_order_don2()`:

```python
# BUG: if/else — chỉ chạy 1 nhánh
product = safe_str(main, 6)
if product:
    items.append(...)       # ← chỉ lấy sản phẩm header
else:
    for sub in group[1:]:   # ← chỉ lấy sub-rows (KHÔNG bao giờ chạy nếu header có product)
        items.append(...)
```

**Hậu quả:** Đơn hàng 17 sản phẩm (như Don2 rows 280-296) chỉ hiển thị 1 sản phẩm "LÔ HÀNG", mất 16 sản phẩm còn lại.

### Ví dụ thực tế bị ảnh hưởng (Don2 rows 280-296)

```
Row 280: [name=Nguyễn Long] [product=LÔ HÀNG] [price=10.045.000đ] ← Header + product
Row 281: [product=Kệ gỗ] [weight=0.68] [tracking=78997384622117]   ← BỊ MẤT
Row 282: [product=Phụ kiện chụp ảnh] [tracking=773416865482946]     ← BỊ MẤT
Row 283: [product=Kính] [tracking=435137777095133]                   ← BỊ MẤT
... (13 sản phẩm nữa) ← TẤT CẢ BỊ MẤT
```

**Trước fix:** Hiển thị 1 sản phẩm ("LÔ HÀNG")  
**Sau fix:** Hiển thị đúng 17 sản phẩm

---

## 2. Chi tiết Fix

### 2.1 `_build_order_don()` — `sheets.py`

**Thay đổi:** Bỏ cấu trúc `if/else`, thay bằng 2 bước độc lập:

```python
# Bước 1: LUÔN thêm sản phẩm của header row (nếu có)
product = safe_str(main, 6)
if product:
    items.append({...})

# Bước 2: LUÔN xử lý sub-rows (bất kể header có product hay không)
for sub in group[1:]:
    sub_product = safe_str(sub, 6)
    if sub_product:
        items.append({...})
```

### 2.2 `_build_order_don2()` — `sheets.py`

Fix tương tự cho Don2 sheet (product ở cột F thay vì G).

### 2.3 Logic mới

| Scenario | Trước fix | Sau fix |
|---|---|---|
| Header có name + product, 0 sub-row | ✅ 1 item | ✅ 1 item (không đổi) |
| Header có name + product, N sub-rows | ❌ 1 item (mất N items) | ✅ N+1 items |
| Header có name, không product, N sub-rows | ✅ N items | ✅ N items (không đổi) |
| Sub-row mồ côi (không header) | ✅ 1 item standalone | ✅ 1 item standalone (không đổi) |

---

## 3. Test Results

### 3.1 Unit Tests — Parsing Logic (17/17 PASS)

| # | Test case | Sheet | Kết quả |
|---|---|---|---|
| 1 | Single row, single product | DON | ✅ |
| 2 | Header with product + sub-rows → all items collected | DON | ✅ |
| 3 | Header without product, sub-rows only | DON | ✅ |
| 4 | Orphan sub-row → standalone order | DON | ✅ |
| 5 | Empty rows skipped | DON | ✅ |
| 6 | Two separate orders parsed correctly | DON | ✅ |
| 7 | Single order then multi-product order | DON | ✅ |
| 8 | Single row, single product | Don2 | ✅ |
| 9 | Header with product + sub-rows → all items collected | Don2 | ✅ |
| 10 | **17 products realistic scenario (rows 280-296)** | Don2 | ✅ |
| 11 | Orphan sub-row → standalone order | Don2 | ✅ |
| 12 | Sub-row tracking_cn preserved on items | — | ✅ |
| 13 | Item row_indices correct | — | ✅ |
| 14 | Don2 tracking_cn_2 on items | Don2 | ✅ |
| 15 | Empty input → no orders | — | ✅ |
| 16 | Short rows padded correctly | DON | ✅ |
| 17 | Empty sub-row breaks group → orphan order | DON | ✅ |

### 3.2 Unit Tests — Write Logic (8/8 PASS)

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

### 3.3 Tổng kết

| Category | Tests | Pass | Fail |
|---|---|---|---|
| Parsing logic (Phase 6 mới) | 17 | 17 | 0 |
| Write logic (Phase 5) | 8 | 8 | 0 |
| **Tổng** | **25** | **25** | **0** |

---

## 4. Files thay đổi

| File | Thay đổi |
|---|---|
| `backend/services/sheets.py` | Fix `_build_order_don()` và `_build_order_don2()` — always collect all products |
| `test_parse_multi_product.py` | **Mới** — 17 unit tests cho parsing logic |
| `report.md` | Cập nhật báo cáo Phase 6 |

---

## 5. Backward Compatibility

- ✅ **Single-product orders:** Không thay đổi (1 item như cũ)
- ✅ **Header without product + sub-rows:** Không thay đổi (N items như cũ)
- ✅ **Orphan sub-rows:** Không thay đổi (standalone như cũ)
- ✅ **Write logic:** Không thay đổi (Phase 5 vẫn hoạt động đúng)
- ✅ **Existing tests:** 8/8 vẫn pass

---

## 6. Tech Stack (không đổi)

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

## 7. Metrics

- **Bug severity:** 🔴 Critical (mất dữ liệu sản phẩm khi hiển thị)
- **Code changes:** 1 file modified (`sheets.py`), 1 new test file
- **Lines changed:** ~40 lines (logic refactor)
- **Test coverage:** 25/25 pass (17 new + 8 existing)
- **Backward compatible:** ✅ 100%
- **Risk:** Low (pure parsing logic, no DB/schema changes)

---

**Hết báo cáo Phase 6.**
