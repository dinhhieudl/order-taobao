"""QA Test Script — Kiểm thử chất lượng dữ liệu & Logic"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["GOOGLE_CREDS_FILE"] = "credentials/an-helper-2e2bcd71c709.json"
os.environ["SPREADSHEET_ID"] = "1mFlnUi2HNMFCxxTXAzBc2IMwn32v2qq6IhCCPi5eM1w"

from backend.services.sheets import (
    get_spreadsheet, parse_don_sheet, parse_don2_sheet,
    parse_money, parse_float, detect_carrier, read_all_orders,
    SHEET_DON, SHEET_DON2
)
from backend.services.cache import calc_shipping
from datetime import datetime
import traceback

PASS = 0
FAIL = 0
WARN = 0
BUGS = []

def ok(msg):
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")

def fail(msg, detail=""):
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")
    if detail:
        print(f"     → {detail}")

def warn(msg, detail=""):
    global WARN
    WARN += 1
    print(f"  ⚠️  {msg}")
    if detail:
        print(f"     → {detail}")

def bug(id, title, severity, detail):
    BUGS.append({"id": id, "title": title, "severity": severity, "detail": detail})
    print(f"  🐛 BUG #{id} [{severity}]: {title}")
    print(f"     → {detail}")

print("=" * 70)
print("📦 QA TEST — Quản lý Vận đơn Taobao")
print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================================
# 1. CONNECTIVITY TEST
# ============================================================
print("\n1️⃣  KẾT NỐI GOOGLE SHEETS")
print("-" * 40)
try:
    sh = get_spreadsheet()
    ok(f"Kết nối Spreadsheet thành công: {sh.title}")
    
    try:
        don_ws = sh.worksheet(SHEET_DON)
        don_all = don_ws.get_all_values()
        ok(f"Sheet '{SHEET_DON}': {len(don_all)} dòng (bao gồm header)")
    except Exception as e:
        fail(f"Không đọc được sheet '{SHEET_DON}'", str(e))
        don_all = []

    try:
        don2_ws = sh.worksheet(SHEET_DON2)
        don2_all = don2_ws.get_all_values()
        ok(f"Sheet '{SHEET_DON2}': {len(don2_all)} dòng (bao gồm header)")
    except Exception as e:
        fail(f"Không đọc được sheet '{SHEET_DON2}'", str(e))
        don2_all = []
except Exception as e:
    fail(f"Không kết nối được Google Sheets", str(e))
    print("\n⛔ Dừng test — không có dữ liệu.")
    sys.exit(1)

# ============================================================
# 2. HEADER STRUCTURE VALIDATION
# ============================================================
print("\n2️⃣  KIỂM TRA CẤU TRÚC HEADER")
print("-" * 40)

if don_all:
    header = don_all[0]
    print(f"  Header DON ({len(header)} cột):")
    for i, h in enumerate(header):
        if h.strip():
            print(f"    [{i}] {h.strip()}")
    
    # Check critical columns
    expected_don = {2: "Tên", 3: "SDT", 6: "SẢN PHẨM", 14: "GIÁ", 15: "CỌC"}
    for col, name in expected_don.items():
        if col < len(header) and name.lower() in header[col].lower():
            ok(f"Cột {col} = '{header[col].strip()}' ✓")
        else:
            actual = header[col].strip() if col < len(header) else "N/A"
            warn(f"Cột {col} kỳ vọng '{name}', thực tế '{actual}'")

if don2_all:
    header2 = don2_all[0]
    print(f"\n  Header Don2 ({len(header2)} cột):")
    for i, h in enumerate(header2):
        if h.strip():
            print(f"    [{i}] {h.strip()}")

# ============================================================
# 3. DATA PARSING — STRESS TEST
# ============================================================
print("\n3️⃣  STRESS TEST — PARSE TOÀN BỘ DỮ LIỆU")
print("-" * 40)

# Parse DON
don_rows = don_all[1:]  # skip header
try:
    don_orders = parse_don_sheet(don_rows)
    ok(f"DON: Parse thành công {len(don_orders)} đơn từ {len(don_rows)} dòng")
except Exception as e:
    fail(f"DON: Parse CRASHED", str(e))
    traceback.print_exc()
    don_orders = []

# Parse Don2
don2_rows = don2_all[1:]
try:
    don2_orders = parse_don2_sheet(don2_rows)
    ok(f"Don2: Parse thành công {len(don2_orders)} đơn từ {len(don2_rows)} dòng")
except Exception as e:
    fail(f"Don2: Parse CRASHED", str(e))
    traceback.print_exc()
    don2_orders = []

all_orders = don_orders + don2_orders
print(f"\n  📊 Tổng: {len(all_orders)} đơn ({len(don_orders)} DON + {len(don2_orders)} Don2)")

# ============================================================
# 4. DATA QUALITY ANALYSIS
# ============================================================
print("\n4️⃣  PHÂN TÍCH CHẤT LƯỢNG DỮ LIỆU")
print("-" * 40)

empty_name = 0
empty_phone = 0
empty_product = 0
empty_price = 0
invalid_price = 0
multi_product = 0
empty_tracking_cn = 0
empty_tracking_vn = 0
duplicate_phone_names = {}
price_zero_but_items = 0

for o in all_orders:
    if not o["customer_name"]:
        empty_name += 1
    if not o["customer_phone"]:
        empty_phone += 1
    if not o["items"] or all(not it["product_name"] for it in o["items"]):
        empty_product += 1
    if o["total_price"] == 0:
        empty_price += 1
    if len(o["items"]) > 1:
        multi_product += 1
    if not o["tracking_cn"]:
        empty_tracking_cn += 1
    if not o["tracking_vn"]:
        empty_tracking_vn += 1
    
    # Check phone → name consistency
    phone = o["customer_phone"]
    name = o["customer_name"]
    if phone and name:
        if phone not in duplicate_phone_names:
            duplicate_phone_names[phone] = set()
        duplicate_phone_names[phone].add(name)

print(f"  Đơn thiếu tên khách:     {empty_name}")
print(f"  Đơn thiếu SĐT:           {empty_phone}")
print(f"  Đơn thiếu sản phẩm:      {empty_product}")
print(f"  Đơn giá = 0:             {empty_price}")
print(f"  Đơn nhiều SP (multi):    {multi_product}")
print(f"  Thiếu VĐ TQ:             {empty_tracking_cn}")
print(f"  Thiếu VĐ VN:             {empty_tracking_vn}")

# Phone → multiple names (potential data issue)
phone_multi_name = {p: names for p, names in duplicate_phone_names.items() if len(names) > 1}
if phone_multi_name:
    warn(f"Có {len(phone_multi_name)} SĐT gắn với nhiều tên khác nhau:")
    for p, names in list(phone_multi_name.items())[:5]:
        print(f"     → {p}: {', '.join(names)}")
    if len(phone_multi_name) > 5:
        print(f"     → ... và {len(phone_multi_name) - 5} nữa")

# ============================================================
# 5. BUG DETECTION — Edge Cases
# ============================================================
print("\n5️⃣  KIỂM TRA BUG TIỀM ẨN")
print("-" * 40)

# BUG 1: Column index out of range
crash_rows = []
for i, r in enumerate(don_rows):
    try:
        while len(r) < 23:
            r.append("")
        _ = r[22]  # test access
    except:
        crash_rows.append(i + 2)  # +2 for header + 1-index

if crash_rows:
    bug(1, "Dòng ngắn hơn expected columns", "HIGH",
        f"DON có {len(crash_rows)} dòng thiếu cột (row {crash_rows[:5]}...). "
        "Parser có thể crash nếu không pad đúng cách.")
else:
    ok("DON: Tất cả dòng đủ cột sau khi pad")

# BUG 2: Money parsing edge cases
test_money = ["0", "", "  ", "abc", "23.420.000 đ", "1,500,000", "1500000đ", "-100000", "0 đ"]
print("\n  Test parse_money():")
for val in test_money:
    result = parse_money(val)
    if val and val.strip() and result == 0 and val.strip() not in ["0", "0 đ"]:
        warn(f"parse_money('{val}') = 0 — có thể là dữ liệu lỗi hoặc format lạ")
    else:
        ok(f"parse_money('{val}') = {result}")

# BUG 3: Tracking CN with special characters
test_tracking = ["800060572993", " SF1234567890 ", "abc-123", "JD0012345678", "", "N/A", "none"]
print("\n  Test tracking CN normalization:")
for val in test_tracking:
    cleaned = val.strip().upper().replace(" ", "").replace("\t", "")
    # Check if it would be a valid tracking
    if val and not cleaned.isalnum():
        warn(f"Tracking '{val}' → '{cleaned}' chứa ký tự đặc biệt")

# BUG 4: Multi-product grouping logic — check for orphan sub-rows
print("\n  Kiểm tra logic gộp Cha-Con:")
orphan_items = 0
for o in all_orders:
    if not o["customer_name"] and o["items"]:
        orphan_items += 1

if orphan_items > 0:
    warn(f"Có {orphan_items} đơn không có tên khách nhưng có sản phẩm (orphan sub-rows)")
else:
    ok("Không có orphan sub-rows")

# BUG 5: Row index tracking for write-back integrity
print("\n  Kiểm tra row_start integrity:")
row_start_issues = 0
for o in all_orders:
    if o["row_start"] < 2:  # row 1 is header
        row_start_issues += 1
        if row_start_issues <= 3:
            warn(f"Đơn '{o['customer_name']}' có row_start={o['row_start']} (dưới header)")

if row_start_issues == 0:
    ok("Tất cả row_start >= 2 (sau header)")
else:
    bug(5, "Row index không chính xác", "MEDIUM",
        f"{row_start_issues} đơn có row_start < 2, có thể ghi đè header khi update")

# BUG 6: Deposit > Total Price (data anomaly)
deposit_exceeds = 0
for o in all_orders:
    if o["deposit"] > 0 and o["total_price"] > 0 and o["deposit"] > o["total_price"]:
        deposit_exceeds += 1
        if deposit_exceeds <= 3:
            warn(f"Đơn '{o['customer_name']}' cọc ({o['deposit']:,}) > giá ({o['total_price']:,})")

if deposit_exceeds > 0:
    bug(6, "Cọc lớn hơn tổng giá", "MEDIUM",
        f"{deposit_exceeds} đơn có tiền cọc > tổng giá. "
        "Có thể do nhập sai hoặc Sheet formula lỗi.")
else:
    ok("Không có đơn nào cọc > giá")

# BUG 7: Remaining calculation mismatch
remaining_mismatch = 0
for o in all_orders:
    if o["total_price"] > 0:
        expected_remaining = o["total_price"] - o["deposit"]
        actual = o["remaining"]
        # Allow 1% tolerance for rounding
        if abs(expected_remaining - actual) > max(1000, expected_remaining * 0.01):
            remaining_mismatch += 1
            if remaining_mismatch <= 3:
                warn(f"Đơn '{o['customer_name']}': "
                     f"Giá-Cọc={expected_remaining:,} nhưng Còn lại={actual:,}")

if remaining_mismatch > 0:
    bug(7, "Còn lại ≠ Giá - Cọc", "LOW",
        f"{remaining_mismatch} đơn có 'Còn lại' không khớp Giá-Cọc. "
        "Có thể do đã thanh toán thêm trên Sheet (bình thường).")
else:
    ok("Tất cả còn lại = giá - cọc (hoặc đã thanh toán hết)")

# ============================================================
# 6. SHIPPING CALCULATION TEST
# ============================================================
print("\n6️⃣  KIỂM TRA TÍNH PHÍ SHIP")
print("-" * 40)

test_cases = [
    ("DON", 10, 0, 140000),
    ("DON", 0, 0.5, 1050000),
    ("DON", 100, 0.1, 210000),
    ("Don2", 5, 0, 140000),
    ("DON", 0, 0, 0),
]

for sheet, w, v, expected in test_cases:
    result = calc_shipping(sheet, w, v)
    if result == expected:
        ok(f"calc_shipping('{sheet}', {w}, {v}) = {result:,} ✓")
    else:
        fail(f"calc_shipping('{sheet}', {w}, {v}) = {result:,}, kỳ vọng {expected:,}")

# ============================================================
# 7. CARRIER DETECTION TEST
# ============================================================
print("\n7️⃣  KIỂM TRA DETECT CARRIER")
print("-" * 40)

test_carriers = [
    ("VTP: 109764457793", "ViettelPost"),
    ("GHN: ABC123", "GHN"),
    ("GHTK-12345", "GHTK"),
    ("J&T: 998877", "J&T"),
    ("", ""),
    ("ABC123XYZ", "Khác"),
]

for code, expected in test_carriers:
    carrier, _ = detect_carrier(code)
    if carrier == expected:
        ok(f"detect_carrier('{code}') = '{carrier}' ✓")
    else:
        warn(f"detect_carrier('{code}') = '{carrier}', kỳ vọng '{expected}'")

# ============================================================
# 8. PERFORMANCE METRICS
# ============================================================
print("\n8️⃣  HIỆU NĂNG")
print("-" * 40)

import time

# Time the full parse
start = time.time()
_ = parse_don_sheet(don_rows)
_ = parse_don2_sheet(don2_rows)
parse_time = time.time() - start
print(f"  Thời gian parse toàn bộ: {parse_time:.2f}s")

if parse_time > 5:
    warn(f"Parse mất {parse_time:.2f}s — quá chậm cho 5000+ đơn")
else:
    ok(f"Parse nhanh ({parse_time:.2f}s)")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("📊 TỔNG KẾT")
print("=" * 70)
print(f"  ✅ PASS:  {PASS}")
print(f"  ❌ FAIL:  {FAIL}")
print(f"  ⚠️  WARN:  {WARN}")
print(f"  🐛 BUGS:  {len(BUGS)}")

if BUGS:
    print("\n  DANH SÁCH BUG:")
    for b in BUGS:
        print(f"    #{b['id']} [{b['severity']}] {b['title']}")
        print(f"       {b['detail']}")

print("\n" + "=" * 70)
