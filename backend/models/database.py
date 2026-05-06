"""SQLite cache for fast customer/order search + Google Sheets sync."""
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "cache.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    name_ascii TEXT,
    phone TEXT UNIQUE,
    address TEXT,
    sheet_type TEXT DEFAULT 'DON',
    row_indices TEXT,
    last_sync TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sheet_type TEXT NOT NULL,
    row_start INTEGER NOT NULL,
    row_end INTEGER,
    customer_name TEXT,
    customer_name_ascii TEXT,
    customer_phone TEXT,
    customer_address TEXT,
    source TEXT,
    tracking_cn TEXT,
    tracking_vn TEXT,
    account TEXT,
    note TEXT,
    total_price INTEGER DEFAULT 0,
    deposit INTEGER DEFAULT 0,
    remaining INTEGER DEFAULT 0,
    extra_fee INTEGER DEFAULT 0,
    status TEXT,
    loading_code TEXT,
    waybill_code TEXT,
    order_date TEXT,
    carrier TEXT,
    carrier_code TEXT,
    last_sync TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    row_index INTEGER,
    product_name TEXT,
    weight REAL DEFAULT 0,
    volume REAL DEFAULT 0,
    tracking_cn TEXT,
    tracking_cn_2 TEXT,
    item_price INTEGER DEFAULT 0,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(customer_phone);
CREATE INDEX IF NOT EXISTS idx_orders_name ON orders(customer_name);
CREATE INDEX IF NOT EXISTS idx_orders_name_ascii ON orders(customer_name_ascii);
CREATE INDEX IF NOT EXISTS idx_orders_tracking_cn ON orders(tracking_cn);
CREATE INDEX IF NOT EXISTS idx_orders_tracking_vn ON orders(tracking_vn);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_sheet ON orders(sheet_type);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db
