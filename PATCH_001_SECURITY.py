"""
PATCH_001_SECURITY.py — Bản vá cho các lỗ hổng Critical và High
Ngày: 2026-05-04

Áp dụng: Copy nội dung các hàm vào file tương ứng trong project.

HƯỚNG DẪN:
1. Backup project trước: cp -r order-taobao order-taobao-backup
2. Áp dụng từng patch theo thứ tự
3. Chạy qa_test.py để verify
4. Restart server

PATCHES:
- [C-01] XSS fix: escape customer data trong fillCustomer()
- [C-02] Basic Auth: thêm xác thực cho tất cả endpoints
- [C-03] Admin auth: bảo vệ /api/update-config và /api/upload-credentials
- [H-03] Duplicate tracking_cn check trước khi tạo đơn
- [H-08] Local buffer khi Google Sheets API fails
"""

# ============================================================
# PATCH C-01: XSS Fix — Escape customer data trong HTML/JS
# ============================================================
# File: backend/routers/api.py → search_customer()
# Thay thế đoạn tạo items trong hàm search_customer()

PATCH_C_01 = """
# Thêm vào đầu file api.py:
import html as html_module

def js_escape(s: str) -> str:
    \"\"\"Escape string for safe embedding in JS onclick handler.\"\"\"
    if not s:
        return ""
    return (s
        .replace("\\\\", "\\\\\\\\")
        .replace("'", "\\\\'")
        .replace('"', '\\\\"')
        .replace("\\n", "\\\\n")
        .replace("\\r", "\\\\r")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))

# Trong hàm search_customer(), thay đổi dòng:
#   hx-on:click="fillCustomer('{r[0]}', '{r[1]}', '{r[2]}')"
# Thành:
#   hx-on:click="fillCustomer('{js_escape(r[0])}', '{js_escape(r[1])}', '{js_escape(r[2])}')"

# Tương tự cho customer_history() endpoint
"""


# ============================================================
# PATCH C-02 + C-03: Basic Auth
# ============================================================
# File: Tạo mới backend/auth.py

AUTH_CONTENT = '''"""Basic Authentication for order management system."""
import secrets
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .config import BASE_DIR
import os

security = HTTPBasic()

# Load users from environment or use defaults
# Set in .env: AUTH_USERS=admin:pass123,nv1:nv1pass,nv2:nv2pass
def _load_users() -> dict:
    users_str = os.getenv("AUTH_USERS", "")
    if users_str:
        users = {}
        for pair in users_str.split(","):
            if ":" in pair:
                username, password = pair.split(":", 1)
                users[username.strip()] = password.strip()
        return users
    # Default: no auth if not configured (backward compatible)
    return {}

USERS = _load_users()

def verify_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify any authenticated user."""
    if not USERS:
        # No auth configured — allow all (backward compatible)
        return "anonymous"
    
    correct_pw = USERS.get(credentials.username)
    if not correct_pw or not secrets.compare_digest(
        credentials.password.encode(), correct_pw.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail="Sai tên đăng nhập hoặc mật khẩu",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify admin user only."""
    if not USERS:
        return "anonymous"
    
    username = verify_user(credentials)
    # Only admin can access config endpoints
    admin_users = [u for u, p in USERS.items() if u == "admin"]
    if username not in admin_users and username != "anonymous":
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới có quyền thực hiện thao tác này",
        )
    return username
'''

# ============================================================
# PATCH H-03: Duplicate tracking_cn check
# ============================================================
# File: backend/routers/api.py → create_order()
# Thêm validation TRƯỚC khi gọi append_order_to_sheet

PATCH_H_03 = """
# Thêm vào đầu create_order(), SAU khi clean tracking_cn:

    # Check duplicate tracking_cn
    if tracking_cn_clean:
        db = await get_db()
        try:
            existing = await db.execute_fetchall(
                "SELECT id, customer_name, sheet_type FROM orders WHERE tracking_cn = ?",
                (tracking_cn_clean,)
            )
            if existing:
                dup_info = existing[0]
                return HTMLResponse(f'''
                <div class="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
                    <div class="flex items-center gap-2 text-yellow-800 font-medium">
                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                        </svg>
                        Mã VĐ TQ trùng lặp!
                    </div>
                    <div class="text-sm text-yellow-700 mt-2">
                        Mã <strong>{tracking_cn_clean}</strong> đã tồn tại trong đơn
                        <strong>{dup_info[1]}</strong> (sheet {dup_info[2]}, #{dup_info[0]}).
                    </div>
                    <div class="text-sm text-yellow-600 mt-1">
                        Nếu đây là đơn hợp lệ, hãy thêm ghi chú phân biệt.
                    </div>
                </div>
                ''', status_code=409)
        finally:
            await db.close()
"""


# ============================================================
# PATCH H-08: Local Buffer
# ============================================================
# File: Tạo mới backend/services/buffer.py

BUFFER_CONTENT = '''"""Local buffer for orders when Google Sheets API is unavailable."""
import json
from pathlib import Path
from datetime import datetime
from ..config import DATA_DIR

BUFFER_FILE = DATA_DIR / "pending_orders.json"

def save_to_buffer(order_data: dict, error: str = ""):
    """Save order to local buffer when Sheets API fails."""
    pending = load_buffer()
    order_data["_buffered_at"] = datetime.now().isoformat()
    order_data["_error"] = error
    pending.append(order_data)
    BUFFER_FILE.parent.mkdir(exist_ok=True)
    BUFFER_FILE.write_text(json.dumps(pending, ensure_ascii=False, indent=2))

def load_buffer() -> list:
    """Load pending orders from buffer."""
    if BUFFER_FILE.exists():
        try:
            return json.loads(BUFFER_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return []
    return []

def get_buffer_count() -> int:
    """Get number of pending orders in buffer."""
    return len(load_buffer())

async def flush_buffer() -> tuple:
    """Retry sending buffered orders to Sheets. Returns (sent, failed)."""
    from .sheets import append_order_to_sheet
    
    pending = load_buffer()
    if not pending:
        return 0, 0
    
    sent = 0
    remaining = []
    for order in pending:
        sheet_type = order.pop("sheet_type", "DON")
        order.pop("_buffered_at", None)
        order.pop("_error", None)
        try:
            append_order_to_sheet(sheet_type, order)
            sent += 1
        except Exception as e:
            order["_error"] = str(e)
            remaining.append(order)
    
    if remaining:
        BUFFER_FILE.write_text(json.dumps(remaining, ensure_ascii=False, indent=2))
    else:
        BUFFER_FILE.unlink(missing_ok=True)
    
    return sent, len(remaining)
'''

# ============================================================
# PATCH: Modified create_order with buffer support
# ============================================================
# File: backend/routers/api.py → create_order()
# Thay thế phần try/except trong create_order()

PATCH_BUFFERED_CREATE = '''
    try:
        append_order_to_sheet(sheet_type, order_data)
        # ... existing success response ...
    except Exception as e:
        # Save to buffer instead of just showing error
        from ..services.buffer import save_to_buffer, get_buffer_count
        save_to_buffer(order_data, str(e))
        buffer_count = get_buffer_count()
        return HTMLResponse(f"""
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div class="flex items-center gap-2 text-amber-700 font-medium">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                ⚠️ Không gửi được lên Google Sheets — Đã lưu tạm cục bộ
            </div>
            <div class="text-sm text-amber-600 mt-1">
                Đơn hàng của <strong>{customer_name}</strong> đã được lưu vào bộ đệm.
                {buffer_count} đơn đang chờ gửi. Hệ thống sẽ tự động thử lại khi có kết nối.
            </div>
            <div class="text-xs text-amber-500 mt-2">
                Lỗi: {str(e)}
            </div>
        </div>
        """)
'''

# ============================================================
# HƯỚNG DẪN ÁP DỤNG
# ============================================================
print("""
=== HƯỚNG DẪN ÁP DUNG PATCH ===

1. Tạo file backend/auth.py với nội dung AUTH_CONTENT
2. Tạo file backend/services/buffer.py với nội dung BUFFER_CONTENT
3. Sửa backend/routers/api.py:
   a. Thêm import: from ..auth import verify_user, verify_admin
   b. Thêm import: from ..services.buffer import save_to_buffer, get_buffer_count
   c. Áp dụng PATCH C-01 (js_escape function)
   d. Áp dụng PATCH H-03 (duplicate check)
   e. Áp dụng PATCH_BUFFERED_CREATE (buffer on failure)
   f. Thêm Depends(verify_user) vào tất cả endpoints
   g. Thêm Depends(verify_admin) vào update-config và upload-credentials
4. Thêm vào .env:
   AUTH_USERS=admin:mat-khau-manh,nv1:mat-khau-nv1
5. Restart server
6. Chạy qa_test.py để verify

BACKUP TRƯỚC KHI ÁP DỤNG:
  cp -r order-taobao order-taobao-backup
""")
