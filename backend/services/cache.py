"""Sync Google Sheets data into local SQLite cache for fast search."""
import json
from datetime import datetime
from unidecode import unidecode
from .sheets import read_all_orders
from ..models.database import get_db, init_db
from ..config import DON_RATE_PER_KG, DON_RATE_PER_M3, DON2_RATE_PER_KG

def calc_shipping(sheet_type: str, weight: float, volume: float) -> int:
    if sheet_type == "DON":
        return int(max(weight * DON_RATE_PER_KG, volume * DON_RATE_PER_M3))
    else:
        return int(weight * DON2_RATE_PER_KG)

async def sync_all():
    """Full sync from Google Sheets to SQLite cache."""
    await init_db()
    db = await get_db()
    try:
        # Clear existing data
        await db.execute("DELETE FROM order_items")
        await db.execute("DELETE FROM orders")
        await db.execute("DELETE FROM customers")
        await db.commit()

        orders = read_all_orders()
        now = datetime.now().isoformat()

        customer_map = {}

        for order in orders:
            name_ascii = (" " + unidecode(order["customer_name"]).lower() + " ") if order["customer_name"] else ""
            cursor = await db.execute(
                """INSERT INTO orders (
                    sheet_type, row_start, row_end, customer_name, customer_name_ascii, customer_phone,
                    customer_address, source, tracking_cn, tracking_vn, account,
                    note, total_price, deposit, remaining, extra_fee, status,
                    loading_code, waybill_code, order_date, carrier, carrier_code, last_sync
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    order["sheet_type"], order["row_start"], order["row_end"],
                    order["customer_name"], name_ascii, order["customer_phone"],
                    order["customer_address"], order["source"],
                    order["tracking_cn"], order["tracking_vn"],
                    order["account"], order["note"],
                    order["total_price"], order["deposit"], order["remaining"],
                    order["extra_fee"], order["status"],
                    order["loading_code"], order["waybill_code"],
                    order["order_date"], order["carrier"], order["carrier_code"],
                    now,
                )
            )
            order_id = cursor.lastrowid

            for item in order.get("items", []):
                await db.execute(
                    """INSERT INTO order_items (
                        order_id, row_index, product_name, weight, volume,
                        tracking_cn, tracking_cn_2, item_price
                    ) VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        order_id, item["row_index"], item["product_name"],
                        item["weight"], item["volume"],
                        item["tracking_cn"], item.get("tracking_cn_2", ""),
                        item["item_price"],
                    )
                )

            # Build customer map
            phone = order["customer_phone"]
            if phone:
                if phone not in customer_map:
                    customer_map[phone] = {
                        "name": order["customer_name"],
                        "phone": phone,
                        "address": order["customer_address"],
                        "order_count": 0,
                    }
                customer_map[phone]["order_count"] += 1

        # Insert customers
        for c in customer_map.values():
            name_ascii = (" " + unidecode(c["name"]).lower() + " ") if c["name"] else ""
            await db.execute(
                "INSERT OR REPLACE INTO customers (name, name_ascii, phone, address, last_sync) VALUES (?,?,?,?,?)",
                (c["name"], name_ascii, c["phone"], c["address"], now)
            )

        await db.commit()
        return len(orders)
    finally:
        await db.close()

async def get_sync_info() -> dict:
    db = await get_db()
    try:
        row = await db.execute_fetchall("SELECT COUNT(*) FROM orders")
        order_count = row[0][0] if row else 0
        row = await db.execute_fetchall("SELECT COUNT(*) FROM customers")
        customer_count = row[0][0] if row else 0
        row = await db.execute_fetchall("SELECT MAX(last_sync) FROM orders")
        last_sync = row[0][0] if row and row[0][0] else "Chưa đồng bộ"
        return {
            "order_count": order_count,
            "customer_count": customer_count,
            "last_sync": last_sync,
        }
    finally:
        await db.close()
