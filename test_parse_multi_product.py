"""Tests for multi-product order PARSING (read from sheet rows → order dicts).

Tests the group-aware parsing logic in parse_don_sheet / parse_don2_sheet
where a single customer order spans multiple rows:
  - Row 1 (header): customer info + optionally first product
  - Row 2..N (sub-rows): product-only rows (no customer name)

Bug being fixed: when header row has BOTH name AND product, sub-rows were
skipped entirely — only 1 product shown instead of all products.

Test cases cover:
1. Single row, single product (basic case)
2. Header with product + sub-rows (the main bug scenario)
3. Header WITHOUT product + sub-rows (product starts on sub-row)
4. Orphan sub-row without header (edge case)
5. Empty rows skipped
6. Don2 sheet variant
7. Multi-product items have correct row_indices
8. Sub-row tracking_cn preserved
9. Main row tracking_cn on order-level, sub-row tracking_cn on item-level
10. Don2 rows 280-296 realistic scenario
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


# ============================================================
# DON sheet tests
# ============================================================

def test_don_single_row_single_product():
    """Single row with name + product → 1 order, 1 item."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        # stt(0), date(1), name(2), phone(3), addr(4), source(5), product(6),
        # weight(7), volume(8), tracking_cn(9), tracking_vn(10), acc(11), M(12),
        # note(13), price(14), deposit(15), remaining(16), extra(17), status(18),
        # loading(19), waybill(20), cn2(21), cn3(22)
        ["1", "07/05", "Nguyễn A", "0912345678", "Hanoi", "", "Quạt",
         "5", "0.1", "TRACK001", "VTP:VN001", "acc1", "", "note", "500000", "200000",
         "300000", "", "Đã giao", "LC01", "WB01", "", ""],
    ]

    orders = parse_don_sheet(rows)
    assert len(orders) == 1

    o = orders[0]
    assert o["customer_name"] == "Nguyễn A"
    assert o["customer_phone"] == "0912345678"
    assert o["total_price"] == 500000
    assert len(o["items"]) == 1
    assert o["items"][0]["product_name"] == "Quạt"
    assert o["items"][0]["weight"] == 5.0
    assert o["items"][0]["tracking_cn"] == "TRACK001"
    assert o["items"][0]["item_price"] == 500000  # single-row → price from main
    print("✅ PASS: DON single row, single product")


def test_don_header_with_product_and_subrows():
    """Header has name + product, followed by sub-rows with products.
    This is the MAIN BUG scenario: all products must be collected."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        # Header: name + first product
        ["1", "26/04", "Nguyễn Long", "0912345678", "Hanoi", "", "LÔ HÀNG",
         "2.0", "0.5", "TD001", "", "acc1", "", "", "10045000", "7000000",
         "3045000", "", "", "", "", "", ""],
        # Sub-row 1: product only
        ["", "", "", "", "", "", "Kệ gỗ",
         "0.68", "0.1", "78997384622117", "", "", "", "", "", "",
         "", "", "", "", "", "", ""],
        # Sub-row 2: product only
        ["", "", "", "", "", "", "Phụ kiện chụp ảnh",
         "0.10", "0.05", "773416865482946", "", "", "", "", "", "",
         "", "", "", "", "", "", ""],
        # Sub-row 3: product only
        ["", "", "", "", "", "", "Kính",
         "0.10", "0.02", "435137777095133", "", "", "", "", "", "",
         "", "", "", "", "", "", ""],
    ]

    orders = parse_don_sheet(rows)
    assert len(orders) == 1

    o = orders[0]
    assert o["customer_name"] == "Nguyễn Long"
    assert o["total_price"] == 10045000
    assert o["deposit"] == 7000000
    assert o["row_start"] == 2  # 0-indexed row 0 → sheet row 2
    assert o["row_end"] == 5    # 3 sub-rows → row 5

    # CRITICAL: must have 4 items (header product + 3 sub-row products)
    assert len(o["items"]) == 4, f"Expected 4 items, got {len(o['items'])}"

    assert o["items"][0]["product_name"] == "LÔ HÀNG"
    assert o["items"][0]["weight"] == 2.0
    assert o["items"][0]["tracking_cn"] == "TD001"

    assert o["items"][1]["product_name"] == "Kệ gỗ"
    assert o["items"][1]["weight"] == 0.68
    assert o["items"][1]["tracking_cn"] == "78997384622117"

    assert o["items"][2]["product_name"] == "Phụ kiện chụp ảnh"
    assert o["items"][2]["tracking_cn"] == "773416865482946"

    assert o["items"][3]["product_name"] == "Kính"
    assert o["items"][3]["tracking_cn"] == "435137777095133"

    # Item prices: main row price only for single-row orders
    assert o["items"][0]["item_price"] == 0  # multi-product → 0
    assert o["items"][1]["item_price"] == 0
    print("✅ PASS: DON header with product + sub-rows → all 4 items collected")


def test_don_header_without_product_subrows_only():
    """Header has name but NO product. Sub-rows have products."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        # Header: name only, no product
        ["1", "07/05", "Trần B", "0987654321", "HCM", "", "",
         "", "", "", "", "acc2", "", "note", "", "", "", "", "", "", "", "", ""],
        # Sub-row 1
        ["", "", "", "", "", "", "Laptop",
         "2.5", "0.02", "TRK001", "", "", "", "", "15000000", "",
         "", "", "", "", "", "", ""],
        # Sub-row 2
        ["", "", "", "", "", "", "Chuột",
         "0.2", "0.001", "TRK002", "", "", "", "", "500000", "",
         "", "", "", "", "", "", ""],
    ]

    orders = parse_don_sheet(rows)
    assert len(orders) == 1

    o = orders[0]
    assert o["customer_name"] == "Trần B"
    assert len(o["items"]) == 2
    assert o["items"][0]["product_name"] == "Laptop"
    assert o["items"][0]["weight"] == 2.5
    assert o["items"][0]["item_price"] == 15000000
    assert o["items"][1]["product_name"] == "Chuột"
    assert o["items"][1]["item_price"] == 500000
    print("✅ PASS: DON header without product, sub-rows only")


def test_don_orphan_subrow():
    """Sub-row without a preceding header → treated as standalone."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        # Orphan: product but no name, no date
        ["", "", "", "", "", "", "Orphan Product",
         "1.0", "0.1", "ORPHAN01", "", "", "", "", "100000", "",
         "", "", "", "", "", "", ""],
    ]

    orders = parse_don_sheet(rows)
    assert len(orders) == 1
    assert orders[0]["customer_name"] == ""
    assert orders[0]["items"][0]["product_name"] == "Orphan Product"
    print("✅ PASS: DON orphan sub-row → standalone order")


def test_don_empty_rows_skipped():
    """Empty rows should be skipped."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
         "", "", "", "", "", "", ""],  # completely empty
        ["1", "07/05", "Test", "0911", "", "", "Product",
         "", "", "", "", "", "", "", "100000", "", "", "", "", "", "", "", ""],
    ]

    orders = parse_don_sheet(rows)
    assert len(orders) == 1
    assert orders[0]["customer_name"] == "Test"
    print("✅ PASS: DON empty rows skipped")


def test_don_two_separate_orders():
    """Two separate single-product orders should parse as 2 orders."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        ["1", "01/05", "Khách A", "0911", "", "", "SP A",
         "", "", "", "", "", "", "", "100000", "", "", "", "", "", "", "", ""],
        ["2", "02/05", "Khách B", "0922", "", "", "SP B",
         "", "", "", "", "", "", "", "200000", "", "", "", "", "", "", "", ""],
    ]

    orders = parse_don_sheet(rows)
    assert len(orders) == 2
    assert orders[0]["customer_name"] == "Khách A"
    assert orders[1]["customer_name"] == "Khách B"
    assert len(orders[0]["items"]) == 1
    assert len(orders[1]["items"]) == 1
    print("✅ PASS: DON two separate orders parsed correctly")


def test_don_order_then_multi_product():
    """Single-product order followed by multi-product order."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        # Order 1: single product
        ["1", "01/05", "Khách A", "0911", "", "", "SP A",
         "", "", "", "", "", "", "", "100000", "", "", "", "", "", "", "", ""],
        # Order 2: header + 2 sub-rows
        ["2", "02/05", "Khách B", "0922", "", "", "Main SP",
         "1.0", "", "TRK1", "", "", "", "", "500000", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "Sub SP 1",
         "0.5", "", "TRK2", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "Sub SP 2",
         "0.3", "", "TRK3", "", "", "", "", "", "", "", "", "", "", "", "", ""],
    ]

    orders = parse_don_sheet(rows)
    assert len(orders) == 2

    assert orders[0]["customer_name"] == "Khách A"
    assert len(orders[0]["items"]) == 1

    assert orders[1]["customer_name"] == "Khách B"
    assert len(orders[1]["items"]) == 3, f"Expected 3 items, got {len(orders[1]['items'])}"
    assert orders[1]["items"][0]["product_name"] == "Main SP"
    assert orders[1]["items"][1]["product_name"] == "Sub SP 1"
    assert orders[1]["items"][2]["product_name"] == "Sub SP 2"
    print("✅ PASS: DON single order then multi-product order")


# ============================================================
# Don2 sheet tests
# ============================================================

def test_don2_single_row_single_product():
    """Don2: single row with name + product → 1 order, 1 item."""
    from backend.services.sheets import parse_don2_sheet

    # Don2: date(0), name(1), phone(2), addr(3), source(4), product(5),
    #       weight(6), volume(7), tracking_cn(8), tracking_cn_2(9),
    #       tracking_vn(10), acc(11), M(12), note(13), price(14), deposit(15)
    rows = [
        ["07/05", "Nguyễn A", "0912345678", "Hanoi", "", "Quạt",
         "5", "0.1", "TD001", "", "VTP:VN001", "acc1", "", "note", "500000", "200000",
         "300000", "", "Đã giao", "", ""],
    ]

    orders = parse_don2_sheet(rows)
    assert len(orders) == 1
    o = orders[0]
    assert o["customer_name"] == "Nguyễn A"
    assert o["sheet_type"] == "Don2"
    assert len(o["items"]) == 1
    assert o["items"][0]["product_name"] == "Quạt"
    assert o["items"][0]["item_price"] == 500000
    print("✅ PASS: Don2 single row, single product")


def test_don2_header_with_product_and_subrows():
    """Don2: header has name + product, followed by sub-rows.
    This is the Don2 rows 280-296 scenario."""
    from backend.services.sheets import parse_don2_sheet

    rows = [
        # Row 280: header with name + first product
        ["26/04", "Nguyễn Long", "0912345678", "Hanoi", "", "LÔ HÀNG",
         "2.0", "0.5", "TD001", "", "", "acc1", "", "", "10045000", "7000000",
         "3045000", "", "", "", ""],
        # Row 281: sub-row
        ["", "", "", "", "", "Kệ gỗ",
         "0.68", "0.1", "78997384622117", "", "", "", "", "", "", "",
         "", "", "", "", ""],
        # Row 282: sub-row
        ["", "", "", "", "", "Phụ kiện chụp ảnh",
         "0.10", "0.05", "773416865482946", "", "", "", "", "", "", "",
         "", "", "", "", ""],
        # Row 283: sub-row
        ["", "", "", "", "", "Kính",
         "0.10", "0.02", "435137777095133", "", "", "", "", "", "", "",
         "", "", "", "", ""],
    ]

    orders = parse_don2_sheet(rows)
    assert len(orders) == 1

    o = orders[0]
    assert o["customer_name"] == "Nguyễn Long"
    assert o["sheet_type"] == "Don2"
    assert o["order_date"] == "26/04"
    assert o["total_price"] == 10045000

    # CRITICAL: must have 4 items (header product + 3 sub-row products)
    assert len(o["items"]) == 4, f"Expected 4 items, got {len(o['items'])}"

    assert o["items"][0]["product_name"] == "LÔ HÀNG"
    assert o["items"][0]["weight"] == 2.0
    assert o["items"][0]["tracking_cn"] == "TD001"

    assert o["items"][1]["product_name"] == "Kệ gỗ"
    assert o["items"][1]["weight"] == 0.68
    assert o["items"][1]["tracking_cn"] == "78997384622117"

    assert o["items"][2]["product_name"] == "Phụ kiện chụp ảnh"
    assert o["items"][2]["tracking_cn"] == "773416865482946"

    assert o["items"][3]["product_name"] == "Kính"
    assert o["items"][3]["tracking_cn"] == "435137777095133"
    print("✅ PASS: Don2 header with product + sub-rows → all 4 items collected")


def test_don2_17_products_realistic():
    """Don2 realistic: 1 header + 16 sub-rows = 17 products total.
    Simulates the actual Don2 rows 280-296 scenario."""
    from backend.services.sheets import parse_don2_sheet

    products = [
        ("LÔ HÀNG", "2.0", "0.5", "TD001"),
        ("Kệ gỗ", "0.68", "0.1", "78997384622117"),
        ("Phụ kiện chụp ảnh", "0.10", "0.05", "773416865482946"),
        ("Kính", "0.10", "0.02", "435137777095133"),
        ("Đèn", "0.15", "0.03", "TRK005"),
        ("Quạt", "0.80", "0.10", "TRK006"),
        ("Gương", "0.30", "0.04", "TRK007"),
        ("Kệ sách", "1.20", "0.15", "TRK008"),
        ("Bàn phím", "0.10", "0.005", "TRK009"),
        ("Chuột", "0.05", "0.002", "TRK010"),
        ("Tai nghe", "0.08", "0.003", "TRK011"),
        ("Loa", "0.50", "0.06", "TRK012"),
        ("Ổ cứng", "0.10", "0.003", "TRK013"),
        ("RAM", "0.02", "0.001", "TRK014"),
        ("Màn hình", "3.00", "0.08", "TRK015"),
        ("Webcam", "0.08", "0.002", "TRK016"),
        ("Micro", "0.10", "0.003", "TRK017"),
    ]

    rows = []
    for i, (name, w, v, t) in enumerate(products):
        if i == 0:
            rows.append(["26/04", "Nguyễn Long", "0912345678", "Hanoi", "", name,
                         w, v, t, "", "", "acc1", "", "", "10045000", "7000000",
                         "3045000", "", "", "", ""])
        else:
            rows.append(["", "", "", "", "", name,
                         w, v, t, "", "", "", "", "", "", "",
                         "", "", "", "", ""])

    orders = parse_don2_sheet(rows)
    assert len(orders) == 1
    assert len(orders[0]["items"]) == 17, f"Expected 17 items, got {len(orders[0]['items'])}"

    # Verify all product names
    expected_names = [p[0] for p in products]
    actual_names = [item["product_name"] for item in orders[0]["items"]]
    assert actual_names == expected_names, f"Product names mismatch:\nExpected: {expected_names}\nActual: {actual_names}"

    # Verify individual item weights
    assert orders[0]["items"][0]["weight"] == 2.0
    assert orders[0]["items"][1]["weight"] == 0.68
    assert orders[0]["items"][-1]["weight"] == 0.10

    print("✅ PASS: Don2 17 products realistic scenario")


def test_don2_orphan_subrow():
    """Don2: orphan sub-row without header."""
    from backend.services.sheets import parse_don2_sheet

    rows = [
        ["", "", "", "", "", "Orphan Product",
         "1.0", "0.1", "ORPHAN01", "", "", "", "", "100000", "",
         "", "", "", "", ""],
    ]

    orders = parse_don2_sheet(rows)
    assert len(orders) == 1
    assert orders[0]["customer_name"] == ""
    assert orders[0]["items"][0]["product_name"] == "Orphan Product"
    print("✅ PASS: Don2 orphan sub-row → standalone order")


# ============================================================
# Item-level data integrity tests
# ============================================================

def test_subrow_tracking_cn_preserved():
    """Each sub-row's tracking_cn must be on its own item, not lost."""
    from backend.services.sheets import parse_don2_sheet

    rows = [
        ["26/04", "Test", "0911", "", "", "Main",
         "", "", "MAIN_TRK", "", "", "", "", "", "100000", "", "", "", "", "", ""],
        ["", "", "", "", "", "Sub1",
         "", "", "SUB1_TRK", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "Sub2",
         "", "", "SUB2_TRK", "", "", "", "", "", "", "", "", "", "", "", ""],
    ]

    orders = parse_don2_sheet(rows)
    assert orders[0]["items"][0]["tracking_cn"] == "MAIN_TRK"
    assert orders[0]["items"][1]["tracking_cn"] == "SUB1_TRK"
    assert orders[0]["items"][2]["tracking_cn"] == "SUB2_TRK"
    # Order-level tracking_cn is from main row
    assert orders[0]["tracking_cn"] == "MAIN_TRK"
    print("✅ PASS: Sub-row tracking_cn preserved on items")


def test_item_row_indices_correct():
    """Each item's row_index must match its position in the sheet."""
    from backend.services.sheets import parse_don2_sheet

    rows = [
        ["26/04", "Test", "0911", "", "", "Product1", "", "", "", "", "", "", "", "", "100", "", "", "", "", ""],
        ["", "", "", "", "", "Product2", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "Product3", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
    ]

    orders = parse_don2_sheet(rows)
    # row_start=2 (1-indexed, after header row)
    assert orders[0]["row_start"] == 2
    assert orders[0]["row_end"] == 4
    assert orders[0]["items"][0]["row_index"] == 2
    assert orders[0]["items"][1]["row_index"] == 3
    assert orders[0]["items"][2]["row_index"] == 4
    print("✅ PASS: Item row_indices correct")


def test_don_tracking_cn_2_on_don2_items():
    """Don2 items should have tracking_cn_2 field populated."""
    from backend.services.sheets import parse_don2_sheet

    rows = [
        ["26/04", "Test", "0911", "", "", "Product1",
         "", "", "TRK1", "TRK1_2", "", "", "", "", "100", "", "", "", "", "", ""],
        ["", "", "", "", "", "Product2",
         "", "", "TRK2", "TRK2_2", "", "", "", "", "", "", "", "", "", "", ""],
    ]

    orders = parse_don2_sheet(rows)
    assert orders[0]["items"][0]["tracking_cn_2"] == "TRK1_2"
    assert orders[0]["items"][1]["tracking_cn_2"] == "TRK2_2"
    print("✅ PASS: Don2 tracking_cn_2 on items")


# ============================================================
# Edge cases
# ============================================================

def test_empty_input():
    """Empty rows list → no orders."""
    from backend.services.sheets import parse_don_sheet, parse_don2_sheet

    assert parse_don_sheet([]) == []
    assert parse_don2_sheet([]) == []
    print("✅ PASS: Empty input → no orders")


def test_short_rows_padded():
    """Rows with fewer columns than expected should be padded, not crash."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        ["1", "07/05", "Test", "0911"],  # Only 4 columns
    ]

    orders = parse_don_sheet(rows)
    assert len(orders) == 1
    assert orders[0]["customer_name"] == "Test"
    assert orders[0]["items"] == []  # No product column
    print("✅ PASS: Short rows padded correctly")


def test_subrow_with_empty_product_breaks_group():
    """Sub-rows with empty product name break the group — next product becomes orphan."""
    from backend.services.sheets import parse_don_sheet

    rows = [
        ["1", "07/05", "Test", "0911", "", "", "Main Product",
         "", "", "", "", "", "", "", "100", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "",  # Empty product — breaks group
         "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "Sub Product",
         "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
    ]

    orders = parse_don_sheet(rows)
    # Empty sub-row breaks the group: main order = 1 item, sub becomes orphan = 1 item
    assert len(orders) == 2, f"Expected 2 orders, got {len(orders)}"
    assert orders[0]["customer_name"] == "Test"
    assert len(orders[0]["items"]) == 1
    assert orders[0]["items"][0]["product_name"] == "Main Product"
    assert orders[1]["customer_name"] == ""  # orphan
    assert orders[1]["items"][0]["product_name"] == "Sub Product"
    print("✅ PASS: Empty sub-row breaks group → orphan order")


if __name__ == "__main__":
    tests = [
        # DON sheet
        test_don_single_row_single_product,
        test_don_header_with_product_and_subrows,
        test_don_header_without_product_subrows_only,
        test_don_orphan_subrow,
        test_don_empty_rows_skipped,
        test_don_two_separate_orders,
        test_don_order_then_multi_product,
        # Don2 sheet
        test_don2_single_row_single_product,
        test_don2_header_with_product_and_subrows,
        test_don2_17_products_realistic,
        test_don2_orphan_subrow,
        # Item data integrity
        test_subrow_tracking_cn_preserved,
        test_item_row_indices_correct,
        test_don_tracking_cn_2_on_don2_items,
        # Edge cases
        test_empty_input,
        test_short_rows_padded,
        test_subrow_with_empty_product_breaks_group,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ FAIL: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed:
        sys.exit(1)
    print("🎉 All tests passed!")
