"""Dashboard module - provides analytics, KPIs, and visualizations"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import statistics

from fastapi import APIRouter, Query
from pydantic import BaseModel

from database.db import get_db

router = APIRouter()


# --- New Response Models ---
class TargetResponse(BaseModel):
    target_id: int
    store_id: int
    store_name: str
    period_start: str
    period_end: str
    sales_target: str
    actual_sales: str
    attainment_pct: str
    variance: str

class PeriodComparison(BaseModel):
    current_period: Dict[str, Any]
    prior_period: Dict[str, Any]
    variance_pct: str
    variance_amount: str

class PromotionPerformance(BaseModel):
    promotion_id: int
    name: str
    start_date: str
    end_date: str
    transactions: int
    revenue: str
    items_sold: int
    uplift_pct: str

class StaffPerformance(BaseModel):
    staff_id: str
    name: str
    store_name: str
    transactions: int
    total_sales: str
    avg_ticket: str
    items_per_txn: str
    hours_worked: float
    sales_per_hour: str

class ForecastPoint(BaseModel):
    date: str
    predicted_sales: str
    confidence_lower: str
    confidence_upper: str
    actual_sales: Optional[str] = None

class CustomerMetrics(BaseModel):
    new_customers: int
    returning_customers: int
    total_customers: int
    avg_frequency: str
    avg_recency_days: str
    customer_lifetime_value: str

class ExecutiveScorecard(BaseModel):
    period: str
    revenue: Dict[str, Any]
    transactions: Dict[str, Any]
    margin: Dict[str, Any]
    top_store: Dict[str, Any]
    top_department: Dict[str, Any]
    alerts: List[str]

# --- Existing Models ---
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


# ============================================================
# NEW MICROSOFT DYNAMICS 365 SALES HUB-LIKE ENDPOINTS
# ============================================================

@router.get("/targets", response_model=List[TargetResponse])
async def get_sales_targets(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get sales targets vs actuals (quota attainment) - like D365 Sales quota management"""
    conn = get_db()
    cursor = conn.cursor()

    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND st.period_start >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND st.period_end <= ?"
        params.append(end_date)
    if store_id:
        date_filter += " AND st.store_id = ?"
        params.append(store_id)

    # Create mock targets table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_targets (
            target_id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            sales_target TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Insert default targets for demo if empty
    cursor.execute("SELECT COUNT(*) FROM sales_targets")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO sales_targets (store_id, period_start, period_end, sales_target)
            VALUES
                (1, '2026-11-01', '2026-11-30', '150000.00'),
                (2, '2026-11-01', '2026-11-30', '120000.00'),
                (1, '2026-10-01', '2026-10-31', '140000.00'),
                (2, '2026-10-01', '2026-10-31', '115000.00')
        """)
        conn.commit()

    query = f"""
        SELECT
            st.target_id,
            st.store_id,
            s.name as store_name,
            st.period_start,
            st.period_end,
            st.sales_target,
            COALESCE(SUM(CAST(t.total AS REAL)), 0) as actual_sales
        FROM sales_targets st
        JOIN stores s ON st.store_id = s.id
        LEFT JOIN transactions t ON t.store_id = st.store_id
            AND date(t.tx_timestamp) >= st.period_start
            AND date(t.tx_timestamp) <= st.period_end
            AND t.status = 'COMPLETE' AND t.is_cancelled = 0
        WHERE 1=1 {date_filter}
        GROUP BY st.target_id, st.store_id, s.name, st.period_start, st.period_end, st.sales_target
        ORDER BY st.period_start DESC, st.store_id
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    targets = []
    for row in rows:
        target = Decimal(str(row[5] or 0))
        actual = Decimal(str(row[6] or 0))
        attainment = (actual / target * 100) if target > 0 else Decimal('0')
        variance = actual - target
        targets.append(TargetResponse(
            target_id=row[0],
            store_id=row[1],
            store_name=row[2],
            period_start=row[3],
            period_end=row[4],
            sales_target=str(target),
            actual_sales=str(actual),
            attainment_pct=str(attainment.quantize(Decimal('0.01'))),
            variance=str(variance)
        ))

    conn.close()
    return targets


@router.get("/period-comparison", response_model=PeriodComparison)
async def get_period_comparison(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    compare_to: str = "prior_period"  # prior_period, prior_year
):
    """Compare current period vs prior period (WoW, MoM, YoY) - like D365 period-over-period analytics"""
    conn = get_db()
    cursor = conn.cursor()

    # Parse dates
    if not start_date or not end_date:
        end = date.today()
        start = end - timedelta(days=30)
        start_date = start.isoformat()
        end_date = end.isoformat()

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    period_days = (end - start).days + 1

    # Calculate prior period
    if compare_to == "prior_year":
        prior_start = start - timedelta(days=365)
        prior_end = end - timedelta(days=365)
    else:
        prior_start = start - timedelta(days=period_days)
        prior_end = start - timedelta(days=1)

    def get_period_metrics(sd, ed, sid):
        date_filter = " AND date(tx_timestamp) >= ? AND date(tx_timestamp) <= ?"
        params = [sd, ed]
        if sid:
            date_filter += " AND store_id = ?"
            params.append(sid)

        query = f"""
            SELECT
                COALESCE(SUM(CAST(total AS REAL)), 0) as sales,
                COUNT(*) as transactions,
                COALESCE(SUM(CAST(tax_total AS REAL)), 0) as tax,
                COALESCE(AVG(CAST(total AS REAL)), 0) as avg_ticket
            FROM transactions
            WHERE status = 'COMPLETE' AND is_cancelled = 0 {date_filter}
        """
        cursor.execute(query, params)
        row = cursor.fetchone()
        return {
            "sales": Decimal(str(row[0] or 0)),
            "transactions": row[1] or 0,
            "tax": Decimal(str(row[2] or 0)),
            "avg_ticket": Decimal(str(row[3] or 0))
        }

    current = get_period_metrics(start_date, end_date, store_id)
    prior = get_period_metrics(prior_start.isoformat(), prior_end.isoformat(), store_id)

    # Calculate variance
    sales_var_pct = ((current["sales"] - prior["sales"]) / prior["sales"] * 100) if prior["sales"] > 0 else Decimal('0')
    sales_var_amt = current["sales"] - prior["sales"]

    conn.close()
    return PeriodComparison(
        current_period={
            "sales": str(current["sales"]),
            "transactions": current["transactions"],
            "tax": str(current["tax"]),
            "avg_ticket": str(current["avg_ticket"]),
            "period_start": start_date,
            "period_end": end_date
        },
        prior_period={
            "sales": str(prior["sales"]),
            "transactions": prior["transactions"],
            "tax": str(prior["tax"]),
            "avg_ticket": str(prior["avg_ticket"]),
            "period_start": prior_start.isoformat(),
            "period_end": prior_end.isoformat()
        },
        variance_pct=str(sales_var_pct.quantize(Decimal('0.01'))),
        variance_amount=str(sales_var_amt)
    )


@router.get("/promotions", response_model=List[PromotionPerformance])
async def get_promotion_performance(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Promotion/campaign effectiveness tracking - like D365 campaign analytics"""
    conn = get_db()
    cursor = conn.cursor()

    # Create mock promotions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            promotion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            discount_pct REAL DEFAULT 0,
            store_id INTEGER
        )
    """)

    # Insert demo promotions
    cursor.execute("SELECT COUNT(*) FROM promotions")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO promotions (name, description, start_date, end_date, discount_pct, store_id)
            VALUES
                ('Black Friday 2026', 'Store-wide 20% off', '2026-11-25', '2026-11-28', 20, NULL),
                ('Winter Clearance', '50% off seasonal items', '2026-12-01', '2026-12-31', 50, 1),
                ('Loyalty Week', 'Double points for members', '2026-11-15', '2026-11-21', 0, 2),
                ('Back to School', 'Kids section 15% off', '2026-08-01', '2026-08-31', 15, NULL)
        """)
        conn.commit()

    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND start_date >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND end_date <= ?"
        params.append(end_date)
    if store_id:
        date_filter += " AND (store_id = ? OR store_id IS NULL)"
        params.append(store_id)

    query = f"""
        SELECT promotion_id, name, start_date, end_date
        FROM promotions
        WHERE 1=1 {date_filter}
        ORDER BY start_date DESC
    """
    cursor.execute(query, params)
    promo_rows = cursor.fetchall()

    promotions = []
    for prow in promo_rows:
        pid, name, pstart, pend = prow

        # Get performance during promo period
        perf_params = [pstart, pend]
        perf_filter = " AND date(t.tx_timestamp) >= ? AND date(t.tx_timestamp) <= ?"
        if store_id:
            perf_filter += " AND t.store_id = ?"
            perf_params.append(store_id)

        query = f"""
            SELECT
                COUNT(DISTINCT t.id) as transactions,
                COALESCE(SUM(CAST(t.total AS REAL)), 0) as revenue,
                COALESCE(SUM(CAST(tl.quantity AS REAL)), 0) as items_sold
            FROM transactions t
            JOIN transaction_lines tl ON tl.transaction_id = t.id
            WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0 {perf_filter}
        """
        cursor.execute(query, perf_params)
        perf = cursor.fetchone()

        # Get baseline (same period length before promo)
        promo_start = date.fromisoformat(pstart)
        promo_end = date.fromisoformat(pend)
        promo_days = (promo_end - promo_start).days + 1
        baseline_start = promo_start - timedelta(days=promo_days)
        baseline_end = promo_start - timedelta(days=1)

        base_params = [baseline_start.isoformat(), baseline_end.isoformat()]
        if store_id:
            base_params.append(store_id)

        query = f"""
            SELECT COALESCE(SUM(CAST(total AS REAL)), 0) as revenue
            FROM transactions
            WHERE status = 'COMPLETE' AND is_cancelled = 0
                AND date(tx_timestamp) >= ? AND date(tx_timestamp) <= ?
                {(" AND store_id = ?" if store_id else "")}
        """
        cursor.execute(query, base_params)
        baseline = cursor.fetchone()
        baseline_rev = Decimal(str(baseline[0] or 0))
        promo_rev = Decimal(str(perf[1] or 0))

        uplift = ((promo_rev - baseline_rev) / baseline_rev * 100) if baseline_rev > 0 else Decimal('0')

        promotions.append(PromotionPerformance(
            promotion_id=pid,
            name=name,
            start_date=pstart,
            end_date=pend,
            transactions=perf[0] or 0,
            revenue=str(promo_rev),
            items_sold=int(perf[2] or 0),
            uplift_pct=str(uplift.quantize(Decimal('0.01')))
        ))

    conn.close()
    return promotions


@router.get("/staff-performance", response_model=List[StaffPerformance])
async def get_staff_performance(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Staff/associate performance metrics - like D365 sales team performance"""
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

    # Need staff-transaction linkage. Create mock shift data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff_shifts (
            shift_id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT NOT NULL,
            store_id INTEGER NOT NULL,
            shift_date TEXT NOT NULL,
            hours_worked REAL NOT NULL,
            FOREIGN KEY (staff_id) REFERENCES staff(id),
            FOREIGN KEY (store_id) REFERENCES stores(id)
        )
    """)

    # Insert demo shifts if empty
    cursor.execute("SELECT COUNT(*) FROM staff_shifts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO staff_shifts (staff_id, store_id, shift_date, hours_worked)
            SELECT s.id, s.store_id, date(t.tx_timestamp), 8.0
            FROM staff s
            JOIN transactions t ON t.store_id = s.store_id
            WHERE t.status = 'COMPLETE'
            GROUP BY s.id, date(t.tx_timestamp)
        """)
        conn.commit()

    query = f"""
        SELECT
            st.id as staff_id,
            st.name,
            s.name as store_name,
            COUNT(DISTINCT t.id) as transactions,
            COALESCE(SUM(CAST(t.total AS REAL)), 0) as total_sales,
            COALESCE(SUM(CAST(tl.quantity AS REAL)), 0) as total_items,
            COALESCE(SUM(ss.hours_worked), 0) as hours_worked
        FROM staff st
        JOIN stores s ON st.store_id = s.id
        LEFT JOIN transactions t ON t.store_id = st.store_id
            AND t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        LEFT JOIN transaction_lines tl ON tl.transaction_id = t.id
        LEFT JOIN staff_shifts ss ON ss.staff_id = st.id
            AND ss.shift_date = date(t.tx_timestamp)
        GROUP BY st.id, st.name, s.name
        HAVING transactions > 0
        ORDER BY total_sales DESC
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    staff_perf = []
    for row in rows:
        transactions = row[3] or 0
        total_sales = Decimal(str(row[4] or 0))
        total_items = Decimal(str(row[5] or 0))
        hours = Decimal(str(row[6] or 0))

        staff_perf.append(StaffPerformance(
            staff_id=str(row[0]),
            name=row[1],
            store_name=row[2],
            transactions=transactions,
            total_sales=str(total_sales),
            avg_ticket=str((total_sales / transactions).quantize(Decimal('0.01')) if transactions > 0 else '0.00'),
            items_per_txn=str((total_items / transactions).quantize(Decimal('0.01')) if transactions > 0 else '0.00'),
            hours_worked=float(hours),
            sales_per_hour=str((total_sales / hours).quantize(Decimal('0.01')) if hours > 0 else '0.00')
        ))

    conn.close()
    return staff_perf


@router.get("/forecast", response_model=List[ForecastPoint])
async def get_sales_forecast(
    store_id: Optional[int] = None,
    days_ahead: int = 14,
    history_days: int = 60
):
    """Simple sales forecasting using moving average + trend - predictive analytics like D365 AI for Sales"""
    conn = get_db()
    cursor = conn.cursor()

    end_date = date.today()
    start_date = end_date - timedelta(days=history_days)

    date_filter = " AND date(tx_timestamp) >= ? AND date(tx_timestamp) <= ?"
    params = [start_date.isoformat(), end_date.isoformat()]
    if store_id:
        date_filter += " AND store_id = ?"
        params.append(store_id)

    query = f"""
        SELECT
            date(tx_timestamp) as sale_date,
            COALESCE(SUM(CAST(total AS REAL)), 0) as sales
        FROM transactions
        WHERE status = 'COMPLETE' AND is_cancelled = 0 {date_filter}
        GROUP BY date(tx_timestamp)
        ORDER BY sale_date
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Build daily sales dict
    daily_sales = {row[0]: Decimal(str(row[1] or 0)) for row in rows}

    # Fill missing dates with 0
    all_dates = []
    d = start_date
    while d <= end_date:
        all_dates.append(d.isoformat())
        d += timedelta(days=1)

    sales_values = [daily_sales.get(d, Decimal('0')) for d in all_dates]

    # Simple forecasting: 7-day moving average + linear trend
    window = 7
    if len(sales_values) >= window:
        # Calculate trend (linear regression slope)
        n = len(sales_values)
        x_vals = list(range(n))
        y_vals = [float(v) for v in sales_values]

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0

        # Moving average of last window days
        ma = sum(y_vals[-window:]) / window
    else:
        ma = float(sum(sales_values) / len(sales_values)) if sales_values else 0
        slope = 0

    # Generate forecast
    forecast = []
    for i in range(1, days_ahead + 1):
        pred_date = end_date + timedelta(days=i)
        predicted = max(Decimal('0'), Decimal(str(ma + slope * i)))
        # Simple confidence interval: ±20%
        lower = predicted * Decimal('0.8')
        upper = predicted * Decimal('1.2')

        # Check if we have actual data for this date (for backtesting)
        actual = daily_sales.get(pred_date.isoformat())

        forecast.append(ForecastPoint(
            date=pred_date.isoformat(),
            predicted_sales=str(predicted.quantize(Decimal('0.01'))),
            confidence_lower=str(lower.quantize(Decimal('0.01'))),
            confidence_upper=str(upper.quantize(Decimal('0.01'))),
            actual_sales=str(actual.quantize(Decimal('0.01'))) if actual else None
        ))

    conn.close()
    return forecast


@router.get("/customer-metrics", response_model=CustomerMetrics)
async def get_customer_metrics(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Customer analytics: new vs returning, frequency, CLV - like D365 Customer Insights"""
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

    # For demo, use business_accounts as customers linked to transactions
    # Get all customers with transaction history via business_account_activity
    query = f"""
        SELECT
            ba.account_number,
            ba.name,
            COUNT(DISTINCT t.id) as txn_count,
            COALESCE(SUM(CAST(t.total AS REAL)), 0) as total_spend,
            MIN(date(t.tx_timestamp)) as first_purchase,
            MAX(date(t.tx_timestamp)) as last_purchase
        FROM business_accounts ba
        LEFT JOIN business_account_activity baa ON ba.account_number = baa.account_number
        LEFT JOIN transactions t ON t.id = baa.transaction_id
            AND t.status = 'COMPLETE' AND t.is_cancelled = 0 {date_filter}
        GROUP BY ba.account_number, ba.name
        HAVING txn_count > 0
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    total_customers = len(rows)
    new_customers = 0
    returning_customers = 0
    frequencies = []
    recencies = []
    lifetime_values = []

    period_end = date.today()
    if end_date:
        period_end = date.fromisoformat(end_date)

    for row in rows:
        txn_count = row[2]
        total_spend = Decimal(str(row[3] or 0))
        first_purchase = date.fromisoformat(row[4]) if row[4] else period_end
        last_purchase = date.fromisoformat(row[5]) if row[5] else period_end

        # New vs returning (new = first purchase in current period)
        if first_purchase >= date.fromisoformat(start_date) if start_date else period_end - timedelta(days=30):
            new_customers += 1
        else:
            returning_customers += 1

        # Frequency: purchases per 30 days
        days_active = (period_end - first_purchase).days + 1
        freq = (txn_count / days_active * 30) if days_active > 0 else 0
        frequencies.append(freq)

        # Recency: days since last purchase
        recency = (period_end - last_purchase).days
        recencies.append(recency)

        # Simple CLV: avg spend per visit * visits per year * 3 years
        avg_spend = total_spend / txn_count if txn_count > 0 else Decimal('0')
        clv = avg_spend * Decimal(str(freq * 12 * 3))
        lifetime_values.append(clv)

    conn.close()

    avg_freq = sum(frequencies) / len(frequencies) if frequencies else 0
    avg_recency = sum(recencies) / len(recencies) if recencies else 0
    avg_clv = sum(lifetime_values) / len(lifetime_values) if lifetime_values else Decimal('0')

    return CustomerMetrics(
        new_customers=new_customers,
        returning_customers=returning_customers,
        total_customers=total_customers,
        avg_frequency=str(Decimal(str(avg_freq)).quantize(Decimal('0.01'))),
        avg_recency_days=str(Decimal(str(avg_recency)).quantize(Decimal('0.01'))),
        customer_lifetime_value=str(avg_clv.quantize(Decimal('0.01')))
    )


@router.get("/executive-scorecard", response_model=ExecutiveScorecard)
async def get_executive_scorecard(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """One-page executive summary - like D365 Sales Hub executive dashboard"""
    conn = get_db()
    cursor = conn.cursor()

    if not start_date or not end_date:
        end = date.today()
        start = end - timedelta(days=30)
        start_date = start.isoformat()
        end_date = end.isoformat()

    # Current period
    query = """
        SELECT
            COALESCE(SUM(CAST(total AS REAL)), 0) as sales,
            COUNT(*) as transactions,
            COALESCE(AVG(CAST(total AS REAL)), 0) as avg_ticket
        FROM transactions
        WHERE status = 'COMPLETE' AND is_cancelled = 0
            AND date(tx_timestamp) >= ? AND date(tx_timestamp) <= ?
    """
    cursor.execute(query, [start_date, end_date])
    curr = cursor.fetchone()

    # Prior period for comparison
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    period_days = (end - start).days + 1
    prior_start = start - timedelta(days=period_days)
    prior_end = start - timedelta(days=1)

    cursor.execute(query, [prior_start.isoformat(), prior_end.isoformat()])
    prior = cursor.fetchone()

    # Top store
    cursor.execute("""
        SELECT s.name, COALESCE(SUM(CAST(t.total AS REAL)), 0) as sales
        FROM transactions t
        JOIN stores s ON t.store_id = s.id
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0
            AND date(t.tx_timestamp) >= ? AND date(t.tx_timestamp) <= ?
        GROUP BY s.id, s.name
        ORDER BY sales DESC
        LIMIT 1
    """, [start_date, end_date])
    top_store_row = cursor.fetchone()

    # Top department
    cursor.execute("""
        SELECT d.name, COALESCE(SUM(CAST(tl.line_total AS REAL)), 0) as revenue
        FROM transaction_lines tl
        JOIN transactions t ON tl.transaction_id = t.id
        JOIN departments d ON tl.department_id = d.id
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0
            AND date(t.tx_timestamp) >= ? AND date(t.tx_timestamp) <= ?
        GROUP BY d.id, d.name
        ORDER BY revenue DESC
        LIMIT 1
    """, [start_date, end_date])
    top_dept_row = cursor.fetchone()

    # Margin
    cursor.execute("""
        SELECT
            COALESCE(SUM(CAST(tl.line_total AS REAL)), 0) as revenue,
            COALESCE(SUM(CAST(i.cost AS REAL) * CAST(tl.quantity AS REAL)), 0) as cost
        FROM transaction_lines tl
        JOIN transactions t ON tl.transaction_id = t.id
        JOIN items i ON tl.item_code = i.item_code AND tl.variant_code = i.variant_code
        WHERE t.status = 'COMPLETE' AND t.is_cancelled = 0
            AND date(t.tx_timestamp) >= ? AND date(t.tx_timestamp) <= ?
    """, [start_date, end_date])
    margin_row = cursor.fetchone()

    # Build alerts
    alerts = []
    curr_sales = Decimal(str(curr[0] or 0))
    prior_sales = Decimal(str(prior[0] or 0))
    if prior_sales > 0:
        pct_change = (curr_sales - prior_sales) / prior_sales * 100
        if pct_change < -10:
            alerts.append(f"WARNING: Sales down {abs(pct_change):.1f}% vs prior period")
        elif pct_change > 10:
            alerts.append(f"SUCCESS: Sales up {pct_change:.1f}% vs prior period")

    curr_txns = curr[1] or 0
    prior_txns = prior[1] or 0
    if prior_txns > 0 and curr_txns < prior_txns * 0.9:
        alerts.append(f"WARNING: Transaction volume down {(1 - curr_txns/prior_txns)*100:.1f}%")

    revenue = Decimal(str(margin_row[0] or 0))
    cost = Decimal(str(margin_row[1] or 0))
    margin = revenue - cost
    margin_pct = (margin / revenue * 100) if revenue > 0 else Decimal('0')
    if margin_pct < 20:
        alerts.append(f"WARNING: Gross margin at {margin_pct:.1f}% - below target")

    conn.close()

    return ExecutiveScorecard(
        period=f"{start_date} to {end_date}",
        revenue={
            "current": str(curr_sales),
            "prior": str(prior_sales),
            "variance_pct": str(((curr_sales - prior_sales) / prior_sales * 100).quantize(Decimal('0.01'))) if prior_sales > 0 else "0"
        },
        transactions={
            "current": curr_txns,
            "prior": prior_txns,
            "variance_pct": str(((curr_txns - prior_txns) / prior_txns * 100).quantize(Decimal('0.01'))) if prior_txns > 0 else "0"
        },
        margin={
            "gross_margin": str(margin),
            "margin_pct": str(margin_pct.quantize(Decimal('0.01')))
        },
        top_store={
            "name": top_store_row[0] if top_store_row else "N/A",
            "sales": str(Decimal(str(top_store_row[1] or 0))) if top_store_row else "0"
        },
        top_department={
            "name": top_dept_row[0] if top_dept_row else "N/A",
            "revenue": str(Decimal(str(top_dept_row[1] or 0))) if top_dept_row else "0"
        },
        alerts=alerts
    )
# End of router.py - auto reloaded by StatReload on file changes