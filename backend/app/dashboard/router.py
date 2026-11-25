"""Dashboard module - provides analytics, KPIs, and visualizations"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from database.db import get_db

router = APIRouter()


class KPIResponse(BaseModel):
    total_sales: str
    total_transactions: int
    avg_transaction_value: str
    total_tax: str
    gross_margin: str
    sales_by_store: Dict[str, str]
    sales_by_department: Dict[str, str]
    tender_breakdown: Dict[str, str]


class SalesTrendPoint(BaseModel):
    date: str
    sales: str
    transactions: int
    tax: str


class TopItem(BaseModel):
    item_code: str
    description: str
    quantity_sold: int
    revenue: str
    margin: str


@router.get("/kpis", response_model=KPIResponse)
async def get_kpis(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get key performance indicators"""
    conn = get_db()
    cursor = conn.cursor()

    # Build date filter
    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND date(tx_timestamp) >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND date(tx_timestamp) <= ?"
        params.append(end_date)
    if store_id:
        date_filter += " AND store_id = ?"
        params.append(store_id)

    # Total sales
    query = f"""
        SELECT
            COALESCE(SUM(CAST(total AS REAL)), 0) as total_sales,
            COUNT(*) as total_transactions,
            COALESCE(SUM(CAST(tax_total AS REAL)), 0) as total_tax
        FROM transactions
        WHERE status = 'COMPLETE' AND is_cancelled = 0 {date_filter}
    """
    cursor.execute(query, params)
    row = cursor.fetchone()
    total_sales = Decimal(str(row[0] or 0))
    total_transactions = row[1] or 0
    total_tax = Decimal(str(row[2] or 0))

    # Average transaction value
    avg_txn = total_sales / total_transactions if total_transactions > 0 else Decimal('0')

    # Gross margin (sales - cost)
    query = f"""
        SELECT
            COALESCE(SUM(CAST(tl.line_total AS REAL)), 0) as revenue,
            COALESCE(SUM(CAST(i.cost AS REAL) * CAST(tl.quantity AS REAL)), 0) as cost
        FROM transaction_lines tl
        JOIN transactions t ON tl.transaction_id = t.id
        JOIN items i ON tl.item_code = i.item_code AND tl.variant_code = i.variant_code
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
    """
    cursor.execute(query, params)
    row = cursor.fetchone()
    revenue = Decimal(str(row[0] or 0))
    cost = Decimal(str(row[1] or 0))
    gross_margin = revenue - cost

    # Sales by store
    query = f"""
        SELECT s.name, COALESCE(SUM(CAST(t.total AS REAL)), 0) as sales
        FROM transactions t
        JOIN stores s ON t.store_id = s.id
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        GROUP BY s.id, s.name
    """
    cursor.execute(query, params)
    sales_by_store = {row[0]: str(row[1]) for row in cursor.fetchall()}

    # Sales by department
    query = f"""
        SELECT d.name, COALESCE(SUM(CAST(tl.line_total AS REAL)), 0) as sales
        FROM transaction_lines tl
        JOIN transactions t ON tl.transaction_id = t.id
        JOIN departments d ON tl.department_id = d.id
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        GROUP BY d.id, d.name
    """
    cursor.execute(query, params)
    sales_by_department = {row[0]: str(row[1]) for row in cursor.fetchall()}

    # Tender breakdown
    query = f"""
        SELECT tt.type, COALESCE(SUM(CAST(tt.amount AS REAL)), 0) as amount
        FROM transaction_tenders tt
        JOIN transactions t ON tt.transaction_id = t.id
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        GROUP BY tt.type
    """
    cursor.execute(query, params)
    tender_breakdown = {row[0] or 'unknown': str(row[1]) for row in cursor.fetchall()}

    conn.close()

    return KPIResponse(
        total_sales=str(total_sales),
        total_transactions=total_transactions,
        avg_transaction_value=str(avg_txn),
        total_tax=str(total_tax),
        gross_margin=str(gross_margin),
        sales_by_store=sales_by_store,
        sales_by_department=sales_by_department,
        tender_breakdown=tender_breakdown
    )


@router.get("/sales-trend", response_model=List[SalesTrendPoint])
async def get_sales_trend(
    store_id: Optional[int] = None,
    days: int = 30
):
    """Get daily sales trend"""
    conn = get_db()
    cursor = conn.cursor()

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    date_filter = " AND date(tx_timestamp) >= ? AND date(tx_timestamp) <= ?"
    params = [start_date.isoformat(), end_date.isoformat()]

    if store_id:
        date_filter += " AND store_id = ?"
        params.append(store_id)

    query = f"""
        SELECT
            date(tx_timestamp) as sale_date,
            COALESCE(SUM(CAST(total AS REAL)), 0) as sales,
            COUNT(*) as transactions,
            COALESCE(SUM(CAST(tax_total AS REAL)), 0) as tax
        FROM transactions
        WHERE status = 'COMPLETE' AND is_cancelled = 0 {date_filter}
        GROUP BY date(tx_timestamp)
        ORDER BY sale_date
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        SalesTrendPoint(
            date=row[0],
            sales=str(Decimal(str(row[1] or 0))),
            transactions=row[2] or 0,
            tax=str(Decimal(str(row[3] or 0)))
        )
        for row in rows
    ]


@router.get("/top-items", response_model=List[TopItem])
async def get_top_items(
    store_id: Optional[int] = None,
    limit: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get top selling items"""
    conn = get_db()
    cursor = conn.cursor()

    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND date(t.tx_timestamp) >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND date(t.tx_timestamp) <= ?"
        params.append(end_date)
    if store_id:
        date_filter += " AND t.store_id = ?"
        params.append(store_id)

    query = f"""
        SELECT
            tl.item_code,
            i.description,
            COALESCE(SUM(CAST(tl.quantity AS REAL)), 0) as qty_sold,
            COALESCE(SUM(CAST(tl.line_total AS REAL)), 0) as revenue,
            COALESCE(SUM(CAST(i.cost AS REAL) * CAST(tl.quantity AS REAL)), 0) as cost
        FROM transaction_lines tl
        JOIN transactions t ON tl.transaction_id = t.id
        JOIN items i ON tl.item_code = i.item_code AND tl.variant_code = i.variant_code
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        GROUP BY tl.item_code, i.description
        ORDER BY revenue DESC
        LIMIT ?
    """
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        TopItem(
            item_code=row[0],
            description=row[1],
            quantity_sold=int(row[2] or 0),
            revenue=str(Decimal(str(row[3] or 0))),
            margin=str(Decimal(str(row[3] or 0)) - Decimal(str(row[4] or 0)))
        )
        for row in rows
    ]


@router.get("/store-comparison")
async def get_store_comparison(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Compare performance across stores"""
    conn = get_db()
    cursor = conn.cursor()

    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND date(tx_timestamp) >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND date(tx_timestamp) <= ?"
        params.append(end_date)

    query = f"""
        SELECT
            s.id,
            s.name,
            s.location,
            COUNT(DISTINCT t.id) as transactions,
            COALESCE(SUM(CAST(t.total AS REAL)), 0) as total_sales,
            COALESCE(SUM(CAST(t.tax_total AS REAL)), 0) as total_tax,
            COALESCE(AVG(CAST(t.total AS REAL)), 0) as avg_ticket
        FROM stores s
        LEFT JOIN transactions t ON s.id = t.store_id
            AND t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        GROUP BY s.id, s.name, s.location
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    stores = []
    for row in rows:
        stores.append({
            "store_id": row[0],
            "name": row[1],
            "location": row[2],
            "transactions": row[3] or 0,
            "total_sales": str(Decimal(str(row[4] or 0))),
            "total_tax": str(Decimal(str(row[5] or 0))),
            "avg_ticket": str(Decimal(str(row[6] or 0)))
        })

    conn.close()
    return {"stores": stores}


@router.get("/department-performance")
async def get_department_performance(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get performance by department"""
    conn = get_db()
    cursor = conn.cursor()

    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND date(t.tx_timestamp) >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND date(t.tx_timestamp) <= ?"
        params.append(end_date)
    if store_id:
        date_filter += " AND t.store_id = ?"
        params.append(store_id)

    query = f"""
        SELECT
            d.id,
            d.name,
            d.tax_group,
            COUNT(DISTINCT t.id) as transactions,
            COALESCE(SUM(CAST(tl.line_total AS REAL)), 0) as revenue,
            COALESCE(SUM(CAST(tl.tax_amount AS REAL)), 0) as tax,
            COALESCE(SUM(CAST(i.cost AS REAL) * CAST(tl.quantity AS REAL)), 0) as cost
        FROM departments d
        LEFT JOIN transaction_lines tl ON d.id = tl.department_id
        LEFT JOIN transactions t ON tl.transaction_id = t.id
            AND t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        LEFT JOIN items i ON tl.item_code = i.item_code AND tl.variant_code = i.variant_code
        GROUP BY d.id, d.name, d.tax_group
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    departments = []
    for row in rows:
        revenue = Decimal(str(row[4] or 0))
        cost = Decimal(str(row[6] or 0))
        departments.append({
            "department_id": row[0],
            "name": row[1],
            "tax_group": row[2],
            "transactions": row[3] or 0,
            "revenue": str(revenue),
            "tax": str(Decimal(str(row[5] or 0))),
            "cost": str(cost),
            "margin": str(revenue - cost),
            "margin_pct": str(((revenue - cost) / revenue * 100) if revenue > 0 else Decimal('0'))
        })

    conn.close()
    return {"departments": departments}


@router.get("/hourly-heatmap")
async def get_hourly_heatmap(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get hourly sales heatmap"""
    conn = get_db()
    cursor = conn.cursor()

    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND date(tx_timestamp) >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND date(tx_timestamp) <= ?"
        params.append(end_date)
    if store_id:
        date_filter += " AND store_id = ?"
        params.append(store_id)

    query = f"""
        SELECT
            CAST(strftime('%H', tx_timestamp) AS INTEGER) as hour,
            CAST(strftime('%w', tx_timestamp) AS INTEGER) as dow,
            COALESCE(SUM(CAST(total AS REAL)), 0) as sales,
            COUNT(*) as transactions
        FROM transactions
        WHERE status = 'COMPLETE' AND is_cancelled = 0 {date_filter}
        GROUP BY hour, dow
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Build 24x7 matrix
    heatmap = [[{"sales": "0", "transactions": 0} for _ in range(7)] for _ in range(24)]
    for row in rows:
        hour = row[0]
        dow = row[1]  # 0=Sunday
        heatmap[hour][dow] = {
            "sales": str(Decimal(str(row[2] or 0))),
            "transactions": row[3] or 0
        }

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    conn.close()
    return {"heatmap": heatmap, "days": days}


@router.get("/tender-mix")
async def get_tender_mix(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get payment tender mix"""
    conn = get_db()
    cursor = conn.cursor()

    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND date(t.tx_timestamp) >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND date(t.tx_timestamp) <= ?"
        params.append(end_date)
    if store_id:
        date_filter += " AND t.store_id = ?"
        params.append(store_id)

    query = f"""
        SELECT
            tt.type,
            COUNT(*) as count,
            COALESCE(SUM(CAST(tt.amount AS REAL)), 0) as amount
        FROM transaction_tenders tt
        JOIN transactions t ON tt.transaction_id = t.id
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        GROUP BY tt.type
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    tender_mix = []
    total_amount = sum(Decimal(str(row[2] or 0)) for row in rows)
    for row in rows:
        amount = Decimal(str(row[2] or 0))
        tender_mix.append({
            "type": row[0] or 'unknown',
            "count": row[1] or 0,
            "amount": str(amount),
            "percentage": str((amount / total_amount * 100) if total_amount > 0 else Decimal('0'))
        })

    conn.close()
    return {"tender_mix": tender_mix, "total_amount": str(total_amount)}