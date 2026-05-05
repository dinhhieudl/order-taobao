# 📦 Báo cáo Dự án — Quản lý Vận đơn Taobao

> **Ngày:** 2026-05-05  
> **Giai đoạn:** Phase 4 — Stabilization: Bug Fixes & Logic Optimization  
> **Trạng thái:** ✅ Đã hoàn thiện & push lên repo

---

## 1. Tổng quan thay đổi Phase 4

Fix triệt để các lỗi logic tính toán, UX, và tối ưu hóa hệ thống dựa trên feedback thực tế.

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

### 2.1 🔴 Logic & Tính toán

| # | Vấn đề | Fix | File |
|---|---|---|---|
| 1 | **Công nợ: extra_fee trùng index với remaining** | `extra_fee` đặt = 0 (cột R/17 là debt, không phải extra fee riêng) | `sheets.py` |
| 2 | **Cảnh báo vận chuyển: dùng `last_sync` thay vì check status** | Chuyển sang check `status NOT LIKE '%Nhập kho TQ%'` — chỉ alert đơn chưa nhập kho TQ | `api.py` |
| 3 | **Cảnh báo vận chuyển: thiếu cột Status** | Thêm `status` vào JSON response + hiển thị trên dashboard | `api.py`, `dashboard.html` |

### 2.2 🟡 Giao diện (UI/UX)

| # | Vấn đề | Fix | File |
|---|---|---|---|
| 4 | **SĐT tự xóa sau 1-2 ký tự** | Tăng debounce từ 300ms → 500ms; thêm `_filling` flag để `fillCustomer()` không trigger loadCustomerHistory | `create_order.html`, `base.html` |
| 5 | **Tìm kiếm không dấu** | Thêm `unidecode` fallback — nếu kết quả rỗng, tìm lại với phiên bản không dấu | `pages.py`, `api.py`, `requirements.txt` |
| 6 | **Auth yêu cầu Sign-in khi sync** | Bỏ `Depends(verify_user)` khỏi `/api/sync` (chưa deploy auth) | `api.py` |
| 7 | **Thiếu Loading Spinner** | Thêm HTMX indicator spinner vào nút "Đồng bộ ngay" (dashboard + sidebar) | `dashboard.html`, `base.html` |

### 2.3 🟢 Báo cáo

| # | Vấn đề | Fix | File |
|---|---|---|---|
| 8 | **Báo cáo theo ngày → theo Tháng** | Thêm month/year selector; filter toàn bộ query theo `substr(order_date, 4, 2)`; thêm monthly summary cards | `pages.py`, `report.html` |

---

## 3. Test Results — Data Entry

### 3.1 Ghi thực tế vào Google Sheet DON

| # | Ngày | Tên | SĐT | Địa chỉ | SP | Giá | Cọc | Kết quả |
|---|---|---|---|---|---|---|---|---|
| 1 | 05/05 | ba mòe | (trống) | (trống) | 3x quạt gree | 0 | 0 | ✅ Ghi thành công |
| 2 | 05/05 | Đỗ Tiến Đạt | 0917194646 | 69 Hai Bà Trưng, Buôn Ma Thuột, Đắk Lắk | (trống) | 1.750.000 | 1.000.000 | ✅ Ghi thành công |

- Cấu trúc dòng Sheet không bị hỏng
- Record trống SĐT xử lý đúng (null-safe)
- Unicode tiếng Việt (Đỗ Tiến Đạt, Đắk Lắk) ghi OK

---

## 4. Files thay đổi

| File | Thay đổi |
|---|---|
| `backend/services/sheets.py` | Fix `extra_fee` = 0 (không trùng index với remaining) |
| `backend/routers/api.py` | +unidecode cho search-customer; fix shipping alerts query; bỏ auth sync; thêm status vào alerts |
| `backend/routers/pages.py` | +unidecode cho search; monthly report filter |
| `backend/templates/pages/report.html` | +Month/Year selector; +Monthly summary cards; +empty state |
| `backend/templates/pages/create_order.html` | Fix phone input debounce 500ms; +`_filling` guard |
| `backend/templates/pages/dashboard.html` | +Loading spinner sync button; +Status column shipping alerts |
| `backend/templates/base.html` | +`_filling` flag in `fillCustomer()` |
| `requirements.txt` | +unidecode==1.3.8 |
| `an-helper-2e2bcd71c709.json` | Credentials file (valid RSA key) |
| `report.md` | Cập nhật báo cáo Phase 4 |

---

## 5. Metrics

- **Orders synced:** ~1,233+ (DON + Don2)
- **Test records:** 2 (ba mòe + Đỗ Tiến Đạt)
- **Code changes:** 8 files modified
- **New dependency:** unidecode (diacritics search)

---

## 6. API Endpoints (cập nhật)

| Method | Path | Thay đổi Phase 4 |
|---|---|---|
| POST | `/api/sync` | **Bỏ auth** — không yêu cầu đăng nhập |
| GET | `/api/search-customer?q=` | **+unidecode** — tìm không dấu |
| GET | `/api/dashboard-data` | **Fix shipping alerts** — check status, thêm status field |
| GET | `/bao-cao?month=&year=` | **Monthly filter** — mặc định tháng hiện tại |
| GET | `/tim-kiem?q=` | **+unidecode** — fallback tìm không dấu |

---

## 7. Cấu trúc logic Công nợ (xác nhận)

```
Sheet DON columns:
A(0)=stt | B(1)=ngày | C(2)=Tên | D(3)=SDT | E(4)=Địa chỉ | F(5)=NGUỒN
G(6)=SẢN PHẨM | H(7)=KL | I(8)=KT | J(9)=VĐ TQ | K(10)=VĐ VN
L(11)=ACC | M(12)= | N(13)=NOTE | O(14)=GIÁ | P(15)=CỌC
Q(16)=hàng về tt | R(17)=extra → ĐÂY LÀ CỘT NỢ (remaining)
S(18)=Trạng Thái | T(19)=Mã bốc | U(20)=Mã VĐ | V(21)=Cân nặng | W(22)=Thể tích

Công thức: Nợ = giá trị tại index 17 (ô ngay bên phải "hàng về tt" tại index 16)
```

---

**Hết báo cáo Phase 4.**
