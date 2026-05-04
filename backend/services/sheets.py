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
    """Parse DON sheet into order groups. Multi-product: main row has customer, sub-rows have products."""
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

        if has_name and not has_product:
            # Main row of multi-product order
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
        elif has_name and has_product:
            # Single order
            orders.append(_build_order_don([r], sheet_type="DON", row_start=i + 2))
            i += 1
        elif not has_name and has_product:
            # Sub-row without main - treat as standalone
            orders.append(_build_order_don([r], sheet_type="DON", row_start=i + 2))
            i += 1
        else:
            i += 1
    return orders

def parse_don2_sheet(rows: list) -> list:
    """Parse Don2 sheet - similar structure but different column indices."""
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

        if has_name and not has_product:
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
        elif has_name and has_product:
            orders.append(_build_order_don2([r], row_start=i + 2))
            i += 1
        elif not has_name and has_product:
            orders.append(_build_order_don2([r], row_start=i + 2))
            i += 1
        else:
            i += 1
    return orders

def _build_order_don(group: list, sheet_type: str, row_start: int) -> dict:
    main = group[0]
    items = []

    # If main row has product, it's a single order
    if main[6].strip():
        items.append({
            "row_index": row_start,
            "product_name": main[6].strip(),
            "weight": parse_float(main[7]),
            "volume": parse_float(main[8]),
            "tracking_cn": main[9].strip(),
            "tracking_cn_2": "",
            "item_price": parse_money(main[14]) if len(group) == 1 else 0,
        })
    else:
        # Multi-product: items from sub-rows
        for idx, sub in enumerate(group[1:]):
            items.append({
                "row_index": row_start + idx + 1,
                "product_name": sub[6].strip(),
                "weight": parse_float(sub[7]),
                "volume": parse_float(sub[8]),
                "tracking_cn": sub[9].strip(),
                "tracking_cn_2": "",
                "item_price": parse_money(sub[14]),
            })

    tracking_vn = main[10].strip()
    carrier, carrier_code = detect_carrier(tracking_vn)

    return {
        "sheet_type": sheet_type,
        "row_start": row_start,
        "row_end": row_start + len(group) - 1,
        "customer_name": main[2].strip(),
        "customer_phone": main[3].strip().replace(" ", ""),
        "customer_address": main[4].strip(),
        "source": main[5].strip(),
        "tracking_cn": main[9].strip(),
        "tracking_vn": tracking_vn,
        "account": main[11].strip(),
        "note": main[13].strip(),
        "total_price": parse_money(main[14]),
        "deposit": parse_money(main[15]),
        "remaining": parse_money(main[16]),
        "extra_fee": parse_money(main[17]),
        "status": main[18].strip(),
        "loading_code": main[19].strip(),
        "waybill_code": main[20].strip(),
        "order_date": main[1].strip(),
        "carrier": carrier,
        "carrier_code": carrier_code,
        "items": items,
    }

def _build_order_don2(group: list, row_start: int) -> dict:
    main = group[0]
    items = []

    if main[5].strip():
        items.append({
            "row_index": row_start,
            "product_name": main[5].strip(),
            "weight": parse_float(main[6]),
            "volume": parse_float(main[7]),
            "tracking_cn": main[8].strip(),
            "tracking_cn_2": main[9].strip(),
            "item_price": parse_money(main[14]) if len(group) == 1 else 0,
        })
    else:
        for idx, sub in enumerate(group[1:]):
            items.append({
                "row_index": row_start + idx + 1,
                "product_name": sub[5].strip(),
                "weight": parse_float(sub[6]),
                "volume": parse_float(sub[7]),
                "tracking_cn": sub[8].strip(),
                "tracking_cn_2": sub[9].strip(),
                "item_price": parse_money(sub[14]),
            })

    tracking_vn = main[10].strip()
    carrier, carrier_code = detect_carrier(tracking_vn)

    return {
        "sheet_type": "Don2",
        "row_start": row_start,
        "row_end": row_start + len(group) - 1,
        "customer_name": main[1].strip(),
        "customer_phone": main[2].strip().replace(" ", ""),
        "customer_address": main[3].strip(),
        "source": main[4].strip(),
        "tracking_cn": main[8].strip(),
        "tracking_vn": tracking_vn,
        "account": main[11].strip(),
        "note": main[13].strip(),
        "total_price": parse_money(main[14]),
        "deposit": parse_money(main[15]),
        "remaining": parse_money(main[16]),
        "extra_fee": parse_money(main[17]),
        "status": main[18].strip(),
        "loading_code": "",
        "waybill_code": "",
        "order_date": main[0].strip(),
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

def append_order_to_sheet(sheet_type: str, order_data: dict):
    """Append a new order to the appropriate sheet."""
    sh = get_spreadsheet()

    if sheet_type == "DON":
        ws = sh.worksheet(SHEET_DON)
        # DON columns: stt, stt(ngày), Tên, SDT, Địa chỉ, NGUỒN, SẢN PHẨM, KHỐI LƯỢNG,
        # KÍCH THƯỚC, Vận đơn TQ, Vận đơn VN, ACC, (trống), NOTE, GIÁ, CỌC, hàng về tt,
        # extra, Trạng Thái, Mã bốc, Mã vận đơn, Cân nặng, Thể tích
        row = [
            "",  # stt
            order_data.get("order_date", ""),
            order_data.get("customer_name", ""),
            order_data.get("customer_phone", ""),
            order_data.get("customer_address", ""),
            order_data.get("source", ""),
            order_data.get("product_name", ""),
            str(order_data.get("weight", "")),
            str(order_data.get("volume", "")),
            order_data.get("tracking_cn", ""),
            order_data.get("tracking_vn", ""),
            order_data.get("account", ""),
            "",  # empty col
            order_data.get("note", ""),
            f"{order_data.get('total_price', 0):,.0f} đ" if order_data.get("total_price") else "",
            f"{order_data.get('deposit', 0):,.0f} đ" if order_data.get("deposit") else "",
            f"{order_data.get('remaining', 0):,.0f} đ" if order_data.get("remaining") else "",
            "",  # extra fee
            order_data.get("status", ""),
            "",  # mã bốc
            "",  # mã vận đơn
            "",  # cân nặng
            "",  # thể tích
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
    else:
        ws = sh.worksheet(SHEET_DON2)
        row = [
            order_data.get("order_date", ""),
            order_data.get("customer_name", ""),
            order_data.get("customer_phone", ""),
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
            f"{order_data.get('total_price', 0):,.0f} đ" if order_data.get("total_price") else "",
            f"{order_data.get('deposit', 0):,.0f} đ" if order_data.get("deposit") else "",
            f"{order_data.get('remaining', 0):,.0f} đ" if order_data.get("remaining") else "",
            "",  # extra
            order_data.get("status", ""),
            "",  # shipping fee manual
            "",  # revenue
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")

    return True
