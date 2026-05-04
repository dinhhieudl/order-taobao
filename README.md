# 📦 Quản lý Vận đơn Taobao

Hệ thống quản lý đơn hàng Taobao nội bộ, chạy trên laptop, truy cập từ mạng LAN.

## Tính năng

- 🔍 **Tìm kiếm nhanh** theo SĐT, tên khách hàng, mã vận đơn
- ➕ **Tạo đơn mới** vào Google Sheets (DON / Don2)
- 📋 **Danh sách đơn hàng** với lọc theo sheet, trạng thái
- 📊 **Dashboard** tổng quan doanh thu, công nợ, trạng thái
- 💰 **Quản lý công nợ** theo khách hàng
- 📈 **Báo cáo** theo ngày/tuần/tháng, theo ACC, phí ship
- 🚚 **Tracking vận đơn** GHN/ViettelPost (link trực tiếp)
- 🔄 **Đồng bộ 2 chiều** với Google Sheets

## Cài đặt

### Cách 1: Chạy trực tiếp (khuyên dùng cho Windows)

```bash
# Cài Python 3.10+ (nếu chưa có)
# Download: https://www.python.org/downloads/

# Clone project
cd taobao-orders

# Cài dependencies
pip install -r requirements.txt

# Chạy
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Cách 2: Docker

```bash
docker-compose up -d
```

### Cách 3: Script

```bash
# Linux/Mac
./run.sh

# Windows
run.bat
```

## Truy cập

Sau khi chạy, truy cập từ bất kỳ thiết bị nào trong mạng LAN:

- **Máy chạy server:** http://localhost:8000
- **Thiết bị khác trong LAN:** http://<IP-laptop>:8000

Để tìm IP laptop:
```bash
# Windows
ipconfig

# Mac/Linux
ifconfig
```

## Cấu trúc

```
taobao-orders/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Cấu hình
│   ├── models/database.py   # SQLite cache
│   ├── routers/
│   │   ├── pages.py         # HTML pages
│   │   └── api.py           # API endpoints
│   ├── services/
│   │   ├── sheets.py        # Google Sheets read/write
│   │   ├── cache.py         # SQLite sync
│   │   └── tracking.py      # Vận đơn tracking
│   └── templates/           # HTML templates
├── data/cache.db            # SQLite database (auto-created)
├── an-helper-*.json         # Google Service Account credentials
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Cấu hình

Chỉnh sửa trong `backend/config.py` hoặc tạo file `.env`:

```env
GOOGLE_CREDS_FILE=an-helper-2e2bcd71c709.json
SPREADSHEET_ID=1mFlnUi2HNMFCxxTXAzBc2IMwn32v2qq6IhCCPi5eM1w
HOST=0.0.0.0
PORT=8000
GHN_TOKEN=        # Optional: để track tự động
VTP_TOKEN=        # Optional: để track tự động
```

## Workflow

1. **Đồng bộ Sheet** → Nhấn nút "Đồng bộ Sheet" ở sidebar
2. **Tìm kiếm** → Gõ SĐT/tên/mã vận đơn ở thanh tìm kiếm trên cùng
3. **Tạo đơn** → Chọn DON/Don2, nhập thông tin, submit → tự ghi vào Sheet
4. **Xem chi tiết** → Click vào đơn hàng → xem sản phẩm, lịch sử KH, tracking
5. **Công nợ** → Xem danh sách khách nợ, filter theo tên
6. **Báo cáo** → Xem doanh thu theo ngày, theo ACC, phí ship ước tính

## Shipping Formula

- **DON (Tiểu ngạch):** `max(kg × 14,000, m³ × 2,100,000)`
- **Don2 (TMDT):** `kg × 28,000`
