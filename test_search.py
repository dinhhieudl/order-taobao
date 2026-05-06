"""Test search logic with mock data.

Mock customers:
  - Nguyễn Đức Bằng
  - Trần Văn Phúc
  - Lê Văn Phúc

Test queries:
  - 'duc bang' → should return Nguyễn Đức Bằng
  - 'van phuc' → should return both Trần Văn Phúc AND Lê Văn Phúc
"""
import sqlite3
import os
import sys
from unidecode import unidecode

DB_PATH = "/tmp/test_search.db"

# Clean up
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

def create_test_db():
    """Create a test DB with mock data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create schema (same as production)
    c.executescript("""
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
    CREATE INDEX IF NOT EXISTS idx_orders_name_ascii ON orders(customer_name_ascii);
    """)

    # Mock data
    mock_customers = [
        ("Nguyễn Đức Bằng", "0912345678", "Hà Nội"),
        ("Trần Văn Phúc", "0987654321", "TP.HCM"),
        ("Lê Văn Phúc", "0909123456", "Đà Nẵng"),
    ]

    for name, phone, addr in mock_customers:
        name_ascii = " " + unidecode(name).lower() + " "
        c.execute(
            """INSERT INTO orders (sheet_type, row_start, row_end, customer_name, customer_name_ascii,
                customer_phone, customer_address, order_date, last_sync)
            VALUES ('DON', 1, 1, ?, ?, ?, ?, '06/05', datetime('now'))""",
            (name, name_ascii, phone, addr)
        )

    conn.commit()
    conn.close()
    print(f"✅ Created test DB with {len(mock_customers)} mock customers")


def search_customer(db_path, query):
    """Replicate the refactored search logic."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    q_clean = query.replace(" ", "")
    q_ascii = unidecode(query).strip().lower()
    q_words = q_ascii.split()

    # Build name matching: each word must appear in customer_name_ascii
    name_conditions = []
    name_params = []
    for word in q_words:
        name_conditions.append("LOWER(customer_name_ascii) LIKE ?")
        name_params.append(f"% {word} %")

    name_where = " AND ".join(name_conditions) if name_conditions else "1=0"

    sql = f"""SELECT customer_name, customer_phone, customer_address,
            COUNT(*) as order_count
        FROM orders
        WHERE customer_phone LIKE ?
           OR ({name_where})
        GROUP BY customer_phone
        ORDER BY order_count DESC
        LIMIT 10"""

    params = [f"%{q_clean}%"] + name_params
    results = conn.execute(sql, params).fetchall()
    conn.close()
    return results


def run_tests():
    create_test_db()

    all_pass = True

    # Test 1: 'duc bang' → should return Nguyễn Đức Bằng
    print("\n🔍 Test 1: Search 'duc bang'")
    results = search_customer(DB_PATH, "duc bang")
    names = [r[0] for r in results]
    print(f"   Results: {names}")

    if "Nguyễn Đức Bằng" in names:
        print("   ✅ PASS — Found 'Nguyễn Đức Bằng'")
    else:
        print("   ❌ FAIL — 'Nguyễn Đức Bằng' not found!")
        all_pass = False

    # Should NOT match the others
    if "Trần Văn Phúc" not in names and "Lê Văn Phúc" not in names:
        print("   ✅ PASS — No false positives for 'Văn Phúc'")
    else:
        print("   ❌ FAIL — False positive: matched 'Văn Phúc' when searching 'duc bang'")
        all_pass = False

    # Test 2: 'van phuc' → should return both Trần Văn Phúc AND Lê Văn Phúc
    print("\n🔍 Test 2: Search 'van phuc'")
    results = search_customer(DB_PATH, "van phuc")
    names = [r[0] for r in results]
    print(f"   Results: {names}")

    if "Trần Văn Phúc" in names:
        print("   ✅ PASS — Found 'Trần Văn Phúc'")
    else:
        print("   ❌ FAIL — 'Trần Văn Phúc' not found!")
        all_pass = False

    if "Lê Văn Phúc" in names:
        print("   ✅ PASS — Found 'Lê Văn Phúc'")
    else:
        print("   ❌ FAIL — 'Lê Văn Phúc' not found!")
        all_pass = False

    if "Nguyễn Đức Bằng" not in names:
        print("   ✅ PASS — No false positive for 'Nguyễn Đức Bằng'")
    else:
        print("   ❌ FAIL — False positive: matched 'Nguyễn Đức Bằng' when searching 'van phuc'")
        all_pass = False

    # Test 3: Vietnamese with diacritics: 'đức bằng' → should still work
    print("\n🔍 Test 3: Search 'đức bằng' (with diacritics)")
    results = search_customer(DB_PATH, "đức bằng")
    names = [r[0] for r in results]
    print(f"   Results: {names}")

    if "Nguyễn Đức Bằng" in names:
        print("   ✅ PASS — Found 'Nguyễn Đức Bằng' from diacritics query")
    else:
        print("   ❌ FAIL — 'Nguyễn Đức Bằng' not found from diacritics query!")
        all_pass = False

    # Test 4: Partial single word: 'phuc' → should match both Phúc
    print("\n🔍 Test 4: Search 'phuc' (single word)")
    results = search_customer(DB_PATH, "phuc")
    names = [r[0] for r in results]
    print(f"   Results: {names}")

    if "Trần Văn Phúc" in names and "Lê Văn Phúc" in names:
        print("   ✅ PASS — Found both 'Văn Phúc' entries")
    else:
        print("   ❌ FAIL — Did not find both 'Văn Phúc' entries!")
        all_pass = False

    # Test 5: Phone search still works
    print("\n🔍 Test 5: Search '0912' (phone)")
    results = search_customer(DB_PATH, "0912")
    names = [r[0] for r in results]
    print(f"   Results: {names}")

    if "Nguyễn Đức Bằng" in names:
        print("   ✅ PASS — Phone search works")
    else:
        print("   ❌ FAIL — Phone search broken!")
        all_pass = False

    # Cleanup
    os.remove(DB_PATH)

    print("\n" + "=" * 50)
    if all_pass:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("💥 SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
