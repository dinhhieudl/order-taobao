"""Google Sheets read/write service with group-aware parsing."""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from ..config import GOOGLE_CREDS_FILE, SPREADSHEET_ID, SHEET_DON, SHEET_DON2

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

def get_gspread_client():
    creds = Credentials.from_service_account_file(GOOGLE_CREDS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def get_spreadsheet():
    gc = get_gspread_client()
    return gc.open_by_key(SPREADSHEET_ID)

def parse_money(val: str) -> int:
    if not val or not val.strip():
        return 0
    v = val.strip().replace(".", "").replace(",", "").replace(" đ", "").replace("đ", "").strip()
    try:
        return int(v)
    except ValueError:
        return 0

def parse_float(val: str) -> float:
    if not val or not val.strip():
        return 0.0
    v = val.strip().replace(",", ".").replace("kg", "").replace("m3", "").strip()
    try:
        return float(v)
    except ValueError:
        return 0.0

def detect_carrier(tracking_vn: str) -> tuple:
    if not tracking_vn:
        return "", ""
    t = tracking_vn.upper().strip()
    if "VTP" in t or "VIETTEL" in t:
        code = t.replace("VTP:", "").replace("VTP", "").strip()
        return "ViettelPost", code
    elif "GHN" in t:
        code = t.replace("GHN:", "").replace("GHN", "").strip()
        return "GHN", code
    elif "GHTK" in t:
        return "GHTK", t
    elif "J&T" in t or "JNT" in t:
        return "J&T", t
    return "Khác", t

def parse_don_sheet(rows: list) -> list:
    """Parse DON sheet into order groups.
    
    Multi-product logic:
    - If row has Tên but no SP → Header (main row), collect following sub-rows
    - If row has SP but no Tên → Item (sub-row), belongs to previous header
    - If row has BOTH Tên AND SP → It's a header with its own product.
      STILL check if next rows are sub-rows (no name, has product).
    """
    orders = []
    i = 0
    while i < len(rows):
        r = rows[i]
        # Pad row to at least 23 columns
        while len(r) < 23:
            r.append("")

        has_name = r[2].strip()
        has_product = r[6].strip()
        has_date = r[1].strip()

        if not has_name and not has_product and not has_date:
            i += 1
            continue

        if has_name:
            # Header row (with or without product) — collect sub-rows
            group = [r]
            j = i + 1
            while j < len(rows):
                sr = rows[j]
                while len(sr) < 23:
                    sr.append("")
                sr_name = sr[2].strip()
                sr_product = sr[6].strip()
                if not sr_name and sr_product:
                    group.append(sr)
                    j += 1
                else:
                    break
            orders.append(_build_order_don(group, sheet_type="DON", row_start=i + 2))
            i = j
        elif not has_name and has_product:
            # Orphan sub-row without header — treat as standalone
            orders.append(_build_order_don([r], sheet_type="DON", row_start=i + 2))
            i += 1
        else:
            i += 1
    return orders

def parse_don2_sheet(rows: list) -> list:
    """Parse Don2 sheet - similar structure but different column indices.
    
    Same multi-product logic as DON: if row has name, collect following sub-rows.
    """
    orders = []
    i = 0
    while i < len(rows):
        r = rows[i]
        while len(r) < 21:
            r.append("")

        has_name = r[1].strip()
        has_product = r[5].strip()
        has_date = r[0].strip()

        if not has_name and not has_product and not has_date:
            i += 1
            continue

        if has_name:
            # Header row (with or without product) — collect sub-rows
            group = [r]
            j = i + 1
            while j < len(rows):
                sr = rows[j]
                while len(sr) < 21:
                    sr.append("")
                sr_name = sr[1].strip()
                sr_product = sr[5].strip()
                if not sr_name and sr_product:
                    group.append(sr)
                    j += 1
                else:
                    break
            orders.append(_build_order_don2(group, row_start=i + 2))
            i = j
        elif not has_name and has_product:
            orders.append(_build_order_don2([r], row_start=i + 2))
            i += 1
        else:
            i += 1
    return orders

def _build_order_don(group: list, sheet_type: str, row_start: int) -> dict:
    """Build order dict from group of rows. Never crashes on bad data."""
    main = group[0]
    items = []

    def safe_str(val, idx):
        try:
            return val[idx].strip() if idx < len(val) and val[idx] else ""
        except (IndexError, AttributeError):
            return ""

    def safe_money(val, idx):
        try:
            return parse_money(val[idx]) if idx < len(val) else 0
        except (IndexError, AttributeError, ValueError):
            return 0

    def safe_float(val, idx):
        try:
            return parse_float(val[idx]) if idx < len(val) else 0.0
        except (IndexError, AttributeError, ValueError):
            return 0.0

    # If main row has product, it's a single order (or header+product on same row)
    product = safe_str(main, 6)
    if product:
        items.append({
            "row_index": row_start,
            "product_name": product,
            "weight": safe_float(main, 7),
            "volume": safe_float(main, 8),
            "tracking_cn": safe_str(main, 9),
            "tracking_cn_2": "",
            "item_price": safe_money(main, 14) if len(group) == 1 else 0,
        })
    else:
        # Multi-product: items from sub-rows
        for idx, sub in enumerate(group[1:]):
            items.append({
                "row_index": row_start + idx + 1,
                "product_name": safe_str(sub, 6),
                "weight": safe_float(sub, 7),
                "volume": safe_float(sub, 8),
                "tracking_cn": safe_str(sub, 9),
                "tracking_cn_2": "",
                "item_price": safe_money(sub, 14),
            })

    tracking_vn = safe_str(main, 10)
    carrier, carrier_code = detect_carrier(tracking_vn)

    return {
        "sheet_type": sheet_type,
        "row_start": row_start,
        "row_end": row_start + len(group) - 1,
        "customer_name": safe_str(main, 2),
        "customer_phone": safe_str(main, 3).replace(" ", ""),
        "customer_address": safe_str(main, 4),
        "source": safe_str(main, 5),
        "tracking_cn": safe_str(main, 9),
        "tracking_vn": tracking_vn,
        "account": safe_str(main, 11),
        "note": safe_str(main, 13),
        "total_price": safe_money(main, 14),
        "deposit": safe_money(main, 15),
        "remaining": safe_money(main, 17),
        "extra_fee": 0,
        "status": safe_str(main, 18),
        "loading_code": safe_str(main, 19),
        "waybill_code": safe_str(main, 20),
        "order_date": safe_str(main, 1),
        "carrier": carrier,
        "carrier_code": carrier_code,
        "items": items,
    }

def _build_order_don2(group: list, row_start: int) -> dict:
    """Build order dict from Don2 group of rows. Never crashes on bad data."""
    main = group[0]
    items = []

    def safe_str(val, idx):
        try:
            return val[idx].strip() if idx < len(val) and val[idx] else ""
        except (IndexError, AttributeError):
            return ""

    def safe_money(val, idx):
        try:
            return parse_money(val[idx]) if idx < len(val) else 0
        except (IndexError, AttributeError, ValueError):
            return 0

    def safe_float(val, idx):
        try:
            return parse_float(val[idx]) if idx < len(val) else 0.0
        except (IndexError, AttributeError, ValueError):
            return 0.0

    product = safe_str(main, 5)
    if product:
        items.append({
            "row_index": row_start,
            "product_name": product,
            "weight": safe_float(main, 6),
            "volume": safe_float(main, 7),
            "tracking_cn": safe_str(main, 8),
            "tracking_cn_2": safe_str(main, 9),
            "item_price": safe_money(main, 14) if len(group) == 1 else 0,
        })
    else:
        for idx, sub in enumerate(group[1:]):
            items.append({
                "row_index": row_start + idx + 1,
                "product_name": safe_str(sub, 5),
                "weight": safe_float(sub, 6),
                "volume": safe_float(sub, 7),
                "tracking_cn": safe_str(sub, 8),
                "tracking_cn_2": safe_str(sub, 9),
                "item_price": safe_money(sub, 14),
            })

    tracking_vn = safe_str(main, 10)
    carrier, carrier_code = detect_carrier(tracking_vn)

    return {
        "sheet_type": "Don2",
        "row_start": row_start,
        "row_end": row_start + len(group) - 1,
        "customer_name": safe_str(main, 1),
        "customer_phone": safe_str(main, 2).replace(" ", ""),
        "customer_address": safe_str(main, 3),
        "source": safe_str(main, 4),
        "tracking_cn": safe_str(main, 8),
        "tracking_vn": tracking_vn,
        "account": safe_str(main, 11),
        "note": safe_str(main, 13),
        "total_price": safe_money(main, 14),
        "deposit": safe_money(main, 15),
        "remaining": safe_money(main, 17),
        "extra_fee": 0,
        "status": safe_str(main, 18),
        "loading_code": "",
        "waybill_code": "",
        "order_date": safe_str(main, 0),
        "carrier": carrier,
        "carrier_code": carrier_code,
        "items": items,
    }

def read_all_orders() -> list:
    """Read and parse both DON and Don2 sheets."""
    sh = get_spreadsheet()
    don_ws = sh.worksheet(SHEET_DON)
    don_rows = don_ws.get_all_values()[1:]  # skip header
    don_orders = parse_don_sheet(don_rows)

    don2_ws = sh.worksheet(SHEET_DON2)
    don2_rows = don2_ws.get_all_values()[1:]
    don2_orders = parse_don2_sheet(don2_rows)

    return don_orders + don2_orders

def _find_last_data_row(ws, product_col: int) -> int:
    """Find the last row number (1-based) that has content in the product column.
    
    Scans from bottom up using col_values() to handle sparse columns.
    Returns 1 if no data found (will insert at row 2, right after header).
    """
    col_vals = ws.col_values(product_col)
    for i in range(len(col_vals) - 1, -1, -1):
        if col_vals[i] and col_vals[i].strip():
            return i + 1  # Convert 0-based to 1-based row number
    return 1  # Header only, insert at row 2


def append_order_to_sheet(sheet_type: str, order_data: dict):
    """Insert a new order after the last row with product data.
    
    Uses insert_rows() instead of append_row() to place data right after
    the last row that has content in the product column. This preserves
    any formulas, formatting, or data in columns of rows below.
    
    Note: 'remaining' (hàng về tt) is intentionally left empty to preserve
    the sheet's existing formula. The sheet calculates remaining automatically
    when payment is recorded in the payment column.
    """
    sh = get_spreadsheet()

    if sheet_type == "DON":
        ws = sh.worksheet(SHEET_DON)
        # DON columns: stt(A), stt/ngày(B), Tên(C), SDT(D), Địa chỉ(E), NGUỒN(F), SẢN PHẨM(G),
        # KHỐI LƯỢNG(H), KÍCH THƯỚC(I), Vận đơn TQ(J), Vận đơn VN(K), ACC(L), (M), NOTE(N),
        # GIÁ(O), CỌC(P), hàng về tt(Q), extra(R), Trạng Thái(S), Mã bốc(T), Mã vận đơn(U),
        # Cân nặng(V), Thể tích(W)
        # SẢN PHẨM = column G = col index 7 (1-based)
        product_col = 7
        last_data_row = _find_last_data_row(ws, product_col)
        insert_at = last_data_row + 1

        # Note: col A = stt is auto/empty, row starts from col B
        # DON columns: stt(A), stt/ngày(B), Tên(C), SDT(D), Địa chỉ(E), NGUỒN(F), SẢN PHẨM(G),
        # KHỐI LƯỢNG(H), KÍCH THƯỚC(I), Vận đơn TQ(J), Vận đơn VN(K), ACC(L), (M), NOTE(N),
        # GIÁ(O), CỌC(P), hàng về tt(Q), extra(R), Trạng Thái(S), Mã bốc(T), Mã vận đơn(U),
        # Cân nặng(V), Thể tích(W)
        row = [
            "",  # A - stt (leave empty)
            order_data.get("order_date", ""),
            order_data.get("customer_name", ""),
            f"'{order_data.get('customer_phone')}" if order_data.get("customer_phone") else "",
            order_data.get("customer_address", ""),
            order_data.get("source", ""),
            order_data.get("product_name", ""),
            str(order_data.get("weight", "")),
            str(order_data.get("volume", "")),
            order_data.get("tracking_cn", ""),
            order_data.get("tracking_vn", ""),
            order_data.get("account", ""),
            "",  # M - empty col
            order_data.get("note", ""),
            order_data.get("total_price") or "",
            order_data.get("deposit") or "",
        ]
        
        try:
            ws.update(values=[row], range_name=f"A{insert_at}:P{insert_at}", value_input_option="USER_ENTERED")
        except Exception:
            ws.add_rows(1)
            ws.update(values=[row], range_name=f"A{insert_at}:P{insert_at}", value_input_option="USER_ENTERED")
    else:
        ws = sh.worksheet(SHEET_DON2)
        # Don2: SẢN PHẨM = column F = col index 6 (1-based)
        product_col = 6
        last_data_row = _find_last_data_row(ws, product_col)
        insert_at = last_data_row + 1

        row = [
            order_data.get("order_date", ""),
            order_data.get("customer_name", ""),
            f"'{order_data.get('customer_phone')}" if order_data.get("customer_phone") else "",
            order_data.get("customer_address", ""),
            order_data.get("source", ""),
            order_data.get("product_name", ""),
            str(order_data.get("weight", "")),
            str(order_data.get("volume", "")),
            order_data.get("tracking_cn", ""),
            "",  # tracking_cn_2
            order_data.get("tracking_vn", ""),
            order_data.get("account", ""),
            "",  # empty col
            order_data.get("note", ""),
            order_data.get("total_price") or "",
            order_data.get("deposit") or "",
        ]
        
        try:
            ws.update(values=[row], range_name=f"A{insert_at}:P{insert_at}", value_input_option="USER_ENTERED")
        except Exception:
            ws.add_rows(1)
            ws.update(values=[row], range_name=f"A{insert_at}:P{insert_at}", value_input_option="USER_ENTERED")

    return True
