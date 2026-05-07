# 📦 Báo cáo Dự án — Quản lý Vận đơn Taobao

> **Ngày:** 2026-05-07  
> **Giai đoạn:** Phase 6 — Multi-Product Display & Parsing Fix  
> **Trạng thái:** ✅ Đã fix & test kĩ

---

## 1. Tổng quan thay đổi Phase 6

### 1.1 Fix Bug Parsing (Critical)

Fix bug **nghiêm trọng** trong logic parse đơn hàng nhiều sản phẩm: khi dòng đầu tiên (header) có cả tên khách hàng VÀ sản phẩm, hệ thống chỉ lấy sản phẩm của dòng header, **bỏ qua toàn bộ các dòng sản phẩm phía sau**.

**Bug gốc (Root Cause):**

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

**Fix:** Bỏ `if/else`, thay bằng 2 bước độc lập — LUÔN thêm header product + LUÔN xử lý sub-rows.

### 1.2 Cải thiện hiển thị đơn hàng nhiều sản phẩm

Đơn hàng nhiều sản phẩm giờ hiển thị như **1 đơn hàng duy nhất** trong danh sách, với badge `📦 N SP` để nhận biết. Chi tiết đầy đủ chỉ hiện khi nhấn vào xem chi tiết.

**Trước:** Danh sách hiện raw `GROUP_CONCAT` → "LÔ HÀNG | Kệ gỗ | Phụ kiện chụp ảnh | Kính | ..." (quá dài)  
**Sau:** `📦 17 SP LÔ HÀNG` (gọn, rõ ràng)

**Áp dụng cho:**
- `/don-hang` — Danh sách đơn hàng
- `/tim-kiem` — Kết quả tìm kiếm
- `/` — Dashboard (đơn gần đây)

**Trang chi tiết** (`/don-hang/xxxx`) giữ nguyên — hiển thị bảng sản phẩm đầy đủ.

---

## 2. Chi tiết kỹ thuật

### 2.1 Parsing Fix — `sheets.py`

**`_build_order_don()` và `_build_order_don2()`:**

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

| Scenario | Trước fix | Sau fix |
|---|---|---|
| Header có name + product, 0 sub-row | ✅ 1 item | ✅ 1 item |
| Header có name + product, N sub-rows | ❌ 1 item (mất N) | ✅ N+1 items |
| Header có name, không product, N sub-rows | ✅ N items | ✅ N items |
| Sub-row mồ côi (không header) | ✅ 1 item | ✅ 1 item |

### 2.2 Display Enhancement — Templates

**Badge logic (Jinja2):**
```jinja2
{% set products = (o[24] or '').split(' | ') %}
{% set product_count = products|length %}
{% if product_count > 1 %}
📦 {{ product_count }} SP  {{ products[0] }}
{% else %}
{{ products_str }}
{% endif %}
```

**Dashboard fix:** Recent orders query đổi từ `SELECT *` sang `SELECT o.*, GROUP_CONCAT(...)` để có dữ liệu sản phẩm.

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
| 2 | Multi-product DON → 4 rows | ✅ |
| 3 | Multi-product Don2 → 3 rows | ✅ |
| 4 | Empty product list → 1 row | ✅ |
| 5 | Empty product names filtered | ✅ |
| 6 | Insert position calculated correctly | ✅ |
| 7 | Buffer round-trip preserves product_names | ✅ |
| 8 | Range spans all rows correctly | ✅ |

### 3.3 Template Rendering Tests (4/4 PASS)

| # | Test case | Kết quả |
|---|---|---|
| 1 | Single product → normal display | ✅ |
| 2 | Multi product → badge with count + first product | ✅ |
| 3 | 17 products → badge shows 17 SP | ✅ |
| 4 | Empty product → normal display | ✅ |

### 3.4 Tổng kết

| Category | Tests | Pass | Fail |
|---|---|---|---|
| Parsing logic | 17 | 17 | 0 |
| Write logic | 8 | 8 | 0 |
| Template rendering | 4 | 4 | 0 |
| **Tổng** | **29** | **29** | **0** |

---

## 4. Files thay đổi

| File | Thay đổi |
|---|---|
| `backend/services/sheets.py` | Fix `_build_order_don()` + `_build_order_don2()` — always collect all products |
| `backend/routers/pages.py` | Dashboard recent orders: add GROUP_CONCAT for products |
| `backend/templates/pages/orders.html` | Product column: badge `📦 N SP` + first product |
| `backend/templates/pages/search.html` | Same badge treatment |
| `backend/templates/pages/dashboard.html` | Same badge treatment for recent orders |
| `test_parse_multi_product.py` | 17 unit tests cho parsing logic |
| `report.md` | Cập nhật báo cáo Phase 6 |

---

## 5. Backward Compatibility

- ✅ Single-product orders: hiển thị như cũ
- ✅ Multi-product orders: badge gọn gàng thay vì chuỗi dài
- ✅ Detail page (`/don-hang/xxxx`): bảng sản phẩm đầy đủ, không đổi
- ✅ Write logic: không thay đổi
- ✅ Existing tests: 8/8 vẫn pass

---

## 6. Metrics

- **Bug severity:** 🔴 Critical (mất dữ liệu sản phẩm)
- **Code changes:** 6 files modified, 1 new test file
- **Test coverage:** 29/29 pass
- **Backward compatible:** ✅ 100%

---

**Hết báo cáo Phase 6.**
