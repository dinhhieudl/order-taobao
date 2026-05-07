"""Tests for multi-product order creation.

Tests that when creating an order with multiple products, the system writes
multiple rows to the Google Sheet: header row + one row per additional product.

Test cases:
1. Single product → 1 row (backward compatible)
2. Multiple products → N rows (header + items)
3. Empty product list → 1 row with empty product
4. Product list with empty strings filtered
5. Build rows correctly for DON sheet
6. Build rows correctly for Don2 sheet
7. Buffer round-trip preserves product_names
"""
import sys
import os
import json
from unittest.mock import MagicMock, patch, call
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

def test_single_product_backward_compatible():
    """Single product_name (old format) should still work → 1 row."""
    from backend.services.sheets import append_order_to_sheet

    mock_ws = MagicMock()
    mock_sh = MagicMock()
    mock_sh.worksheet.return_value = mock_ws
    mock_ws.col_values.return_value = ["SẢN PHẨM", "Quạt"]  # 2 rows, last data at row 2

    with patch("backend.services.sheets.get_spreadsheet", return_value=mock_sh):
        order_data = {
            "order_date": "07/05",
            "customer_name": "Test User",
            "customer_phone": "0912345678",
            "customer_address": "Hanoi",
            "source": "",
            "product_name": "Quạt",  # Old single-product format
            "weight": 0,
            "volume": 0,
            "tracking_cn": "",
            "tracking_vn": "",
            "account": "",
            "note": "",
            "total_price": 500000,
            "deposit": 200000,
        }
        result = append_order_to_sheet("DON", order_data)

    assert result is True
    # Should write 1 row
    mock_ws.update.assert_called_once()
    args = mock_ws.update.call_args
    rows = args[1]["values"] if "values" in args[1] else args[0][0]
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    assert rows[0][6] == "Quạt"  # Product name in col G
    assert rows[0][2] == "Test User"  # Customer name in col C
    print("✅ PASS: Single product backward compatible → 1 row")


def test_multi_product_don():
    """Multiple products should write multiple rows for DON sheet."""
    from backend.services.sheets import append_order_to_sheet

    mock_ws = MagicMock()
    mock_sh = MagicMock()
    mock_sh.worksheet.return_value = mock_ws
    mock_ws.col_values.return_value = ["SẢN PHẨM", "Old Product"]  # Last data at row 2

    with patch("backend.services.sheets.get_spreadsheet", return_value=mock_sh):
        order_data = {
            "order_date": "07/05",
            "customer_name": "Nguyễn Long",
            "customer_phone": "0912345678",
            "customer_address": "Hanoi",
            "source": "",
            "product_names": ["Kệ gỗ", "Phụ kiện chụp ảnh", "Kính", "Quạt"],
            "weight": 0,
            "volume": 0,
            "tracking_cn": "",
            "tracking_vn": "",
            "account": "",
            "note": "Test multi-product",
            "total_price": 10045000,
            "deposit": 7000000,
        }
        result = append_order_to_sheet("DON", order_data)

    assert result is True
    mock_ws.update.assert_called_once()
    args = mock_ws.update.call_args
    rows = args[1]["values"] if "values" in args[1] else args[0][0]

    # Should have 4 rows (1 header + 3 items)
    assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}"

    # Header row: has all customer info + first product
    header = rows[0]
    assert header[2] == "Nguyễn Long", f"Header name: {header[2]}"
    assert header[6] == "Kệ gỗ", f"Header product: {header[6]}"
    assert header[1] == "07/05", f"Header date: {header[1]}"
    assert header[14] == 10045000, f"Header price: {header[14]}"
    assert header[15] == 7000000, f"Header deposit: {header[15]}"

    # Item rows: only product name, everything else empty
    for i, item_row in enumerate(rows[1:], 1):
        expected_product = ["Kệ gỗ", "Phụ kiện chụp ảnh", "Kính", "Quạt"][i]
        assert item_row[6] == expected_product, f"Item {i} product: {item_row[6]}"
        assert item_row[2] == "", f"Item {i} should have no name, got: {item_row[2]}"
        assert item_row[1] == "", f"Item {i} should have no date, got: {item_row[1]}"
        assert item_row[14] == "", f"Item {i} should have no price, got: {item_row[14]}"

    # Check range spans all rows
    range_str = args[1]["range_name"] if "range_name" in args[1] else args[0][1]
    assert "A3:P6" in range_str, f"Range should span 4 rows: {range_str}"

    print("✅ PASS: Multi-product DON → 4 rows (1 header + 3 items)")


def test_multi_product_don2():
    """Multiple products should write multiple rows for Don2 sheet."""
    from backend.services.sheets import append_order_to_sheet

    mock_ws = MagicMock()
    mock_sh = MagicMock()
    mock_sh.worksheet.return_value = mock_ws
    # Don2: product in col F (index 6, 1-based = col 6)
    mock_ws.col_values.return_value = ["SẢN PHẨM", "Old"]  # Last data at row 2

    with patch("backend.services.sheets.get_spreadsheet", return_value=mock_sh):
        order_data = {
            "order_date": "26/04",
            "customer_name": "Nguyễn Long",
            "customer_phone": "0912345678",
            "customer_address": "Hanoi",
            "source": "",
            "product_names": ["LÔ HÀNG", "Kệ gỗ", "Phụ kiện chụp ảnh"],
            "weight": 0,
            "volume": 0,
            "tracking_cn": "",
            "tracking_vn": "",
            "account": "",
            "note": "",
            "total_price": 10045000,
            "deposit": 7000000,
        }
        result = append_order_to_sheet("Don2", order_data)

    assert result is True
    mock_ws.update.assert_called_once()
    args = mock_ws.update.call_args
    rows = args[1]["values"] if "values" in args[1] else args[0][0]

    assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"

    # Header row (Don2: col 0=date, col 1=name, col 5=product)
    header = rows[0]
    assert header[1] == "Nguyễn Long", f"Header name: {header[1]}"
    assert header[5] == "LÔ HÀNG", f"Header product: {header[5]}"
    assert header[0] == "26/04", f"Header date: {header[0]}"

    # Item rows
    assert rows[1][5] == "Kệ gỗ", f"Item 1 product: {rows[1][5]}"
    assert rows[1][1] == "", f"Item 1 should have no name"
    assert rows[2][5] == "Phụ kiện chụp ảnh", f"Item 2 product: {rows[2][5]}"
    assert rows[2][1] == "", f"Item 2 should have no name"

    print("✅ PASS: Multi-product Don2 → 3 rows (1 header + 2 items)")


def test_empty_product_list():
    """Empty product list should write 1 row with empty product."""
    from backend.services.sheets import append_order_to_sheet

    mock_ws = MagicMock()
    mock_sh = MagicMock()
    mock_sh.worksheet.return_value = mock_ws
    mock_ws.col_values.return_value = ["SẢN PHẨM"]

    with patch("backend.services.sheets.get_spreadsheet", return_value=mock_sh):
        order_data = {
            "order_date": "07/05",
            "customer_name": "Test",
            "customer_phone": "",
            "customer_address": "",
            "source": "",
            "product_names": [],  # Empty list
            "weight": 0,
            "volume": 0,
            "tracking_cn": "",
            "tracking_vn": "",
            "account": "",
            "note": "",
            "total_price": 0,
            "deposit": 0,
        }
        result = append_order_to_sheet("DON", order_data)

    assert result is True
    args = mock_ws.update.call_args
    rows = args[1]["values"] if "values" in args[1] else args[0][0]
    assert len(rows) == 1
    assert rows[0][6] == ""  # Empty product
    print("✅ PASS: Empty product list → 1 row with empty product")


def test_filter_empty_product_names():
    """Product names list with empty strings should filter them out."""
    # Simulate the filtering logic from create_order
    product_name = ["Quạt", "", "  ", "Kệ gỗ", ""]
    product_list = [p.strip() for p in product_name if p.strip()]
    assert product_list == ["Quạt", "Kệ gỗ"], f"Filtered: {product_list}"
    print("✅ PASS: Empty product names filtered correctly")


def test_insert_at_correct_row():
    """Verify insert_at is calculated correctly after last data row."""
    from backend.services.sheets import _find_last_data_row

    mock_ws = MagicMock()
    # col_values returns 0-indexed list, _find_last_data_row converts to 1-based
    # [0]=Header, [1]=P1, [2]=P2, [3]=P3, [4]="", [5]=""
    # Last non-empty at index 3 → returns 3+1 = 4
    mock_ws.col_values.return_value = ["Header", "P1", "P2", "P3", "", ""]

    result = _find_last_data_row(mock_ws, 6)
    assert result == 4, f"Expected last data row 4, got {result}"
    print("✅ PASS: Insert position calculated correctly")


def test_buffer_roundtrip():
    """Buffer save/load should preserve product_names list."""
    from backend.services.buffer import save_to_buffer, load_buffer
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        buffer_file = Path(tmpdir) / "pending_orders.json"

        with patch("backend.services.buffer.BUFFER_FILE", buffer_file):
            order_data = {
                "sheet_type": "DON",
                "order_date": "07/05",
                "customer_name": "Test",
                "customer_phone": "",
                "customer_address": "",
                "source": "",
                "product_names": ["Quạt", "Kệ gỗ", "Kính"],
                "weight": 0,
                "volume": 0,
                "tracking_cn": "",
                "tracking_vn": "",
                "account": "",
                "note": "",
                "total_price": 500000,
                "deposit": 200000,
            }
            save_to_buffer(order_data, "test error")
            pending = load_buffer()

            assert len(pending) == 1
            assert pending[0]["product_names"] == ["Quạt", "Kệ gỗ", "Kính"]
            assert pending[0]["_error"] == "test error"

    print("✅ PASS: Buffer round-trip preserves product_names")


def test_range_name_spans_all_rows():
    """Verify the update range spans all rows to write."""
    from backend.services.sheets import append_order_to_sheet

    mock_ws = MagicMock()
    mock_sh = MagicMock()
    mock_sh.worksheet.return_value = mock_ws
    mock_ws.col_values.return_value = ["Header", "Old"]  # Last data at row 2

    with patch("backend.services.sheets.get_spreadsheet", return_value=mock_sh):
        order_data = {
            "order_date": "07/05",
            "customer_name": "Test",
            "customer_phone": "",
            "customer_address": "",
            "source": "",
            "product_names": ["P1", "P2", "P3", "P4", "P5"],
            "weight": 0,
            "volume": 0,
            "tracking_cn": "",
            "tracking_vn": "",
            "account": "",
            "note": "",
            "total_price": 0,
            "deposit": 0,
        }
        append_order_to_sheet("DON", order_data)

    args = mock_ws.update.call_args
    range_str = args[1]["range_name"] if "range_name" in args[1] else args[0][1]
    rows = args[1]["values"] if "values" in args[1] else args[0][0]

    # insert_at = 2+1 = 3, 5 rows → A3:P7
    assert "A3:P7" in range_str, f"Expected A3:P7, got {range_str}"
    assert len(rows) == 5, f"Expected 5 rows, got {len(rows)}"
    print("✅ PASS: Range spans all rows correctly")


if __name__ == "__main__":
    tests = [
        test_single_product_backward_compatible,
        test_multi_product_don,
        test_multi_product_don2,
        test_empty_product_list,
        test_filter_empty_product_names,
        test_insert_at_correct_row,
        test_buffer_roundtrip,
        test_range_name_spans_all_rows,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed:
        sys.exit(1)
    print("🎉 All tests passed!")
