"""Page routes - render HTML templates."""
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from ..services.cache import get_sync_info
from ..services.tracking import parse_tracking_info
from ..models.database import get_db
from ..config import DON_RATE_PER_KG, DON_RATE_PER_M3, DON2_RATE_PER_KG
from datetime import datetime, timedelta
import re
from unidecode import unidecode

router = APIRouter(tags=["pages"])

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = await get_db()
    try:
        info = await get_sync_info()

        # Stats by sheet type
        don_stats = await db.execute_fetchall(
            "SELECT COUNT(*), COALESCE(SUM(total_price),0), COALESCE(SUM(deposit),0), COALESCE(SUM(remaining),0) FROM orders WHERE sheet_type='DON'"
        )
        don2_stats = await db.execute_fetchall(
            "SELECT COUNT(*), COALESCE(SUM(total_price),0), COALESCE(SUM(deposit),0), COALESCE(SUM(remaining),0) FROM orders WHERE sheet_type='Don2'"
        )

        # Status distribution
        status_rows = await db.execute_fetchall(
            "SELECT status, COUNT(*) as cnt FROM orders WHERE status != '' GROUP BY status ORDER BY cnt DESC"
        )

        # Orders without tracking VN (shipping pending)
        pending_vn = await db.execute_fetchall(
            "SELECT COUNT(*) FROM orders WHERE tracking_cn != '' AND (tracking_vn IS NULL OR tracking_vn = '')"
        )

        # Recent orders
        recent = await db.execute_fetchall(
            "SELECT * FROM orders ORDER BY row_start DESC LIMIT 10"
        )

        # Top customers by order count
        top_customers = await db.execute_fetchall(
            """SELECT customer_name, customer_phone, COUNT(*) as cnt,
                COALESCE(SUM(total_price),0) as total,
                COALESCE(SUM(remaining),0) as debt
            FROM orders WHERE customer_name != ''
            GROUP BY customer_phone
            ORDER BY cnt DESC LIMIT 10"""
        )

        return templates.TemplateResponse("pages/dashboard.html", {
            "request": request,
            "sync_info": info,
            "don_stats": don_stats[0] if don_stats else (0,0,0,0),
            "don2_stats": don2_stats[0] if don2_stats else (0,0,0,0),
            "status_rows": status_rows,
            "pending_vn": pending_vn[0][0] if pending_vn else 0,
            "recent": recent,
            "top_customers": top_customers,
        })
    finally:
        await db.close()

# Templates reference
from ..main import templates

@router.get("/tim-kiem", response_class=HTMLResponse)
async def search_page(request: Request, q: str = Query("", alias="q")):
    db = await get_db()
    try:
        results = []
        if q.strip():
            q_clean = re.sub(r'\s+', '', q)
            like = f"%{q}%"
            like_clean = f"%{q_clean}%"
            # Also search with unidecoded (diacritics-free) version
            q_ascii = unidecode(q)
            like_ascii = f"%{q_ascii}%"

            # Support search by last 4-10 digits of phone number
            phone_tail_conditions = ""
            phone_params = []
            if q_clean.isdigit() and 4 <= len(q_clean) <= 10:
                phone_tail_conditions = " OR o.customer_phone LIKE ?"
                phone_params = [f"%{q_clean}"]

            results = await db.execute_fetchall(
                f"""SELECT o.*, GROUP_CONCAT(oi.product_name, ' | ') as products
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.customer_phone LIKE ? OR o.customer_name LIKE ?
                    OR o.tracking_cn LIKE ? OR o.tracking_vn LIKE ?{phone_tail_conditions}
                GROUP BY o.id
                ORDER BY o.row_start DESC
                LIMIT 50""",
                [like_clean, like, like, like] + phone_params
            )

            # If no results with original query, try diacritics-free search
            if not results and q_ascii != q:
                results = await db.execute_fetchall(
                    f"""SELECT o.*, GROUP_CONCAT(oi.product_name, ' | ') as products
                    FROM orders o
                    LEFT JOIN order_items oi ON oi.order_id = o.id
                    WHERE o.customer_phone LIKE ? OR o.customer_name LIKE ?
                        OR o.tracking_cn LIKE ? OR o.tracking_vn LIKE ?{phone_tail_conditions}
                    GROUP BY o.id
                    ORDER BY o.row_start DESC
                    LIMIT 50""",
                    [like_clean, like_ascii, like, like] + phone_params
                )

        return templates.TemplateResponse("pages/search.html", {
            "request": request,
            "query": q,
            "results": results,
        })
    finally:
        await db.close()

@router.get("/don-hang", response_class=HTMLResponse)
async def order_list(
    request: Request,
    sheet: str = Query("", alias="sheet"),
    status: str = Query("", alias="status"),
    date_from: str = Query("", alias="date_from"),
    date_to: str = Query("", alias="date_to"),
    page: int = Query(1, alias="page"),
):
    db = await get_db()
    try:
        per_page = 30
        offset = (page - 1) * per_page

        where_clauses = []
        params = []
        if sheet:
            where_clauses.append("o.sheet_type = ?")
            params.append(sheet)
        if status:
            where_clauses.append("o.status = ?")
            params.append(status)

        where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        count_row = await db.execute_fetchall(f"SELECT COUNT(*) FROM orders o {where}", params)
        total = count_row[0][0] if count_row else 0

        rows = await db.execute_fetchall(
            f"""SELECT o.*, GROUP_CONCAT(oi.product_name, ' | ') as products
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            {where}
            GROUP BY o.id
            ORDER BY o.row_start DESC
            LIMIT ? OFFSET ?""",
            params + [per_page, offset]
        )

        total_pages = (total + per_page - 1) // per_page

        # Get distinct statuses for filter dropdown
        status_rows = await db.execute_fetchall(
            "SELECT DISTINCT status FROM orders WHERE status != '' ORDER BY status"
        )
        statuses = [r[0] for r in status_rows]

        return templates.TemplateResponse("pages/orders.html", {
            "request": request,
            "orders": rows,
            "sheet_filter": sheet,
            "status_filter": status,
            "date_from": date_from,
            "date_to": date_to,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "statuses": statuses,
        })
    finally:
        await db.close()

@router.get("/don-hang/{order_id}", response_class=HTMLResponse)
async def order_detail(request: Request, order_id: int):
    db = await get_db()
    try:
        order = await db.execute_fetchall("SELECT * FROM orders WHERE id = ?", (order_id,))
        if not order:
            return HTMLResponse("<div class='p-4 text-red-500'>Không tìm thấy đơn hàng</div>", status_code=404)

        items = await db.execute_fetchall(
            "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
        )

        # Customer history
        phone = order[0][5]  # customer_phone
        history = await db.execute_fetchall(
            "SELECT * FROM orders WHERE customer_phone = ? AND id != ? ORDER BY row_start DESC LIMIT 20",
            (phone, order_id)
        )

        # Tracking info
        tracking_info = parse_tracking_info(order[0][8] or "")  # tracking_vn

        return templates.TemplateResponse("pages/order_detail.html", {
            "request": request,
            "order": order[0],
            "items": items,
            "history": history,
            "tracking": tracking_info,
        })
    finally:
        await db.close()

@router.get("/tao-don", response_class=HTMLResponse)
async def create_order_page(request: Request):
    return templates.TemplateResponse("pages/create_order.html", {
        "request": request,
    })

@router.get("/cong-no", response_class=HTMLResponse)
async def debt_page(request: Request, q: str = Query("", alias="q")):
    db = await get_db()
    try:
        like = f"%{q}%" if q else "%"
        debts = await db.execute_fetchall(
            """SELECT customer_name, customer_phone,
                COUNT(*) as order_count,
                COALESCE(SUM(total_price),0) as total_price,
                COALESCE(SUM(deposit),0) as total_deposit,
                COALESCE(SUM(remaining),0) as total_remaining
            FROM orders
            WHERE customer_name != '' AND remaining > 0
                AND (customer_name LIKE ? OR customer_phone LIKE ?)
            GROUP BY customer_phone
            ORDER BY total_remaining DESC""",
            (like, like)
        )

        totals = await db.execute_fetchall(
            "SELECT COALESCE(SUM(total_price),0), COALESCE(SUM(deposit),0), COALESCE(SUM(remaining),0) FROM orders WHERE remaining > 0"
        )

        return templates.TemplateResponse("pages/debt.html", {
            "request": request,
            "debts": debts,
            "totals": totals[0] if totals else (0,0,0),
            "query": q,
        })
    finally:
        await db.close()

@router.get("/bao-cao", response_class=HTMLResponse)
async def report_page(
    request: Request,
    month: int = Query(0, alias="month"),
    year: int = Query(0, alias="year"),
):
    db = await get_db()
    try:
        # Default to current month/year
        now = datetime.now()
        if not month:
            month = now.month
        if not year:
            year = now.year

        # Revenue by sheet type (filtered by month)
        # order_date is DD/MM format, so filter by month part
        month_str = f"{month:02d}"
        by_sheet = await db.execute_fetchall(
            """SELECT sheet_type,
                COUNT(*) as orders,
                COALESCE(SUM(total_price),0) as revenue,
                COALESCE(SUM(deposit),0) as collected,
                COALESCE(SUM(remaining),0) as outstanding
            FROM orders
            WHERE substr(order_date, 4, 2) = ?
            GROUP BY sheet_type""",
            (month_str,)
        )

        # Revenue by date (filtered by month)
        by_date = await db.execute_fetchall(
            """SELECT order_date,
                COUNT(*) as orders,
                COALESCE(SUM(total_price),0) as revenue
            FROM orders WHERE order_date != '' AND substr(order_date, 4, 2) = ?
            GROUP BY order_date
            ORDER BY CAST(substr(order_date, 1, 2) AS INTEGER) DESC""",
            (month_str,)
        )

        # Shipping cost estimate (filtered by month)
        shipping_don = await db.execute_fetchall(
            """SELECT COUNT(*),
                COALESCE(SUM(
                    CASE
                        WHEN weight * 14000 > volume * 2100000 THEN weight * 14000
                        ELSE volume * 2100000
                    END
                ), 0)
            FROM order_items oi JOIN orders o ON oi.order_id = o.id
            WHERE o.sheet_type = 'DON' AND (weight > 0 OR volume > 0)
                AND substr(o.order_date, 4, 2) = ?""",
            (month_str,)
        )

        shipping_don2 = await db.execute_fetchall(
            """SELECT COUNT(*), COALESCE(SUM(weight * 28000), 0)
            FROM order_items oi JOIN orders o ON oi.order_id = o.id
            WHERE o.sheet_type = 'Don2' AND weight > 0
                AND substr(o.order_date, 4, 2) = ?""",
            (month_str,)
        )

        # Monthly totals
        monthly_totals = await db.execute_fetchall(
            """SELECT COUNT(*) as orders,
                COALESCE(SUM(total_price),0) as revenue,
                COALESCE(SUM(deposit),0) as collected,
                COALESCE(SUM(remaining),0) as outstanding
            FROM orders
            WHERE substr(order_date, 4, 2) = ?""",
            (month_str,)
        )

        return templates.TemplateResponse("pages/report.html", {
            "request": request,
            "by_sheet": by_sheet,
            "by_date": by_date,
            "shipping_don": shipping_don[0] if shipping_don else (0,0),
            "shipping_don2": shipping_don2[0] if shipping_don2 else (0,0),
            "current_month": month,
            "current_year": year,
            "monthly_totals": monthly_totals[0] if monthly_totals else (0,0,0,0),
        })
    finally:
        await db.close()


@router.get("/cau-hinh", response_class=HTMLResponse)
async def settings_page(request: Request):
    from ..config import GOOGLE_CREDS_FILE, SPREADSHEET_ID, GHN_TOKEN, VTP_TOKEN
    import os
    
    # Get just the filename, not full path
    creds_filename = os.path.basename(GOOGLE_CREDS_FILE)
    
    return templates.TemplateResponse("pages/settings.html", {
        "request": request,
        "creds_file": creds_filename,
        "spreadsheet_id": SPREADSHEET_ID,
        "ghn_token": GHN_TOKEN,
        "vtp_token": VTP_TOKEN,
    })
