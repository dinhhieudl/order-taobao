# 📦 Quản lý Vận đơn Taobao

Hệ thống quản lý đơn hàng Taobao nội bộ, chạy trên laptop, truy cập từ mạng LAN.

## Tính năng

- 🔍 **Tìm kiếm nhanh** theo tên, 4-10 số cuối SĐT, mã vận đơn
- 🎨 **Color-coded trạng thái** — Đơn chưa thanh toán hiển thị đỏ/vàng cảnh báo
- ➕ **Tạo đơn mới** vào Google Sheets với auto-fill từ SĐT cũ
- ✅ **Validate mã VĐ TQ** — Tự động viết hoa, xóa khoảng trắng
- 💰 **Bảo toàn công thức Sheet** — Cột "Còn lại" không bị ghi đè
- 📋 **Danh sách đơn hàng** với lọc theo sheet, trạng thái
- 📊 **Dashboard** tổng quan doanh thu, công nợ, trạng thái
- 💰 **Quản lý công nợ** theo khách hàng
- 📈 **Báo cáo** theo ngày/tuần/tháng, theo ACC, phí ship
- 🚚 **Tracking vận đơn** GHN/ViettelPost (link trực tiếp)
- 🔄 **Đồng bộ 2 chiều** với Google Sheets
- ⚙️ **Cấu hình** credentials, tokens, sheet ID qua giao diện

## Cài đặt

```bash
# Clone project
git clone https://github.com/dinhhieudl/order-taobao.git
cd order-taobao

# Cài dependencies
pip install -r requirements.txt

# Chạy
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Windows (1 click):** Double-click `start_server.bat`

**Xem IP cho nhân viên:**
```bash
python scripts/network_info.py
```

Hoặc dùng Docker:
```bash
docker-compose up -d
```

## Cấu hình

Truy cập `http://<IP>:8000/cau-hinh` để cấu hình qua giao diện, hoặc tạo file `.env`:

```env
GOOGLE_CREDS_FILE=credentials/service-account.json
SPREADSHEET_ID=your_sheet_id_here
HOST=0.0.0.0
PORT=8000
GHN_TOKEN=        # Optional: để track tự động
VTP_TOKEN=        # Optional: để track tự động
```

## Workflow

1. **Đồng bộ Sheet** → Nhấn nút "Đồng bộ Sheet" ở sidebar
2. **Tìm kiếm** → Gõ tên/4-10 số cuối SĐT/mã vận đơn
3. **Tạo đơn** → Chọn DON/Don2, nhập thông tin, submit → tự ghi vào Sheet
4. **Xem chi tiết** → Click vào đơn hàng → xem sản phẩm, lịch sử KH, tracking
5. **Công nợ** → Xem danh sách khách nợ, filter theo tên
6. **Báo cáo** → Xem doanh thu theo ngày, theo ACC, phí ship ước tính

## Shipping Formula

- **DON (Tiểu ngạch):** `max(kg × 14,000, m³ × 2,100,000)`
- **Don2 (TMDT):** `kg × 28,000`
