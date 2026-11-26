"""Reconciliation module - handles cash reconciliation, EOD and shift summaries"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.db import get_db

router = APIRouter()


class ShiftSummaryResponse(BaseModel):
    id: str
    store_id: int
    store_name: str
    date: str
    shift_num: int
    start_time: Optional[str]
    end_time: Optional[str]
    reported_total_sales: str
    reported_total_tax: str
    opening_float: str
    counted_cash: str
    cash_drops: str
    calculated_sales: str
    cash_variance: str


class EODSummaryResponse(BaseModel):
    id: int
    store_id: int
    store_name: str
    date: str
    reported_total_sales: str
    reported_total_tax: str
    reported_transaction_count: int
    opening_float: str
    counted_cash: str
    cash_drops: str
    calculated_total_sales: str
    calculated_tax: str
    calculated_transaction_count: int
    sales_variance: str
    tax_variance: str
    cash_variance: str
    transaction_variance: int


class ReconciliationDetail(BaseModel):
    date: str
    store_id: int
    store_name: str
    shift_summaries: List[ShiftSummaryResponse]
    eod_summary: Optional[EODSummaryResponse]


def calculate_cash_position(store_id: int, target_date: str) -> Dict[str, Decimal]:
    """Calculate expected cash position from transactions"""
    conn = get_db()
    cursor = conn.cursor()

    # Get cash tenders for the day
    cursor.execute("""
        SELECT COALESCE(SUM(CAST(tt.amount AS REAL)), 0)
        FROM transaction_tenders tt
        JOIN transactions t ON tt.transaction_id = t.id
        WHERE t.store_id = ? AND date(t.tx_timestamp) = ?
        AND t.status = 'COMPLETE' AND t.is_cancelled = 0
        AND tt.type = 'cash'
    """, (store_id, target_date))
    cash_sales = Decimal(str(cursor.fetchone()[0] or 0))

    # Get cash refunds (returns paid in cash)
    cursor.execute("""
        SELECT COALESCE(SUM(CAST(t.total AS REAL)), 0)
        FROM transactions t
        WHERE t.store_id = ? AND date(t.tx_timestamp) = ?
        AND t.type = 'RETURN' AND t.status = 'COMPLETE'
    """, (store_id, target_date))
    cash_refunds = Decimal(str(cursor.fetchone()[0] or 0))

    # Get cash drops
    cursor.execute("""
        SELECT COALESCE(SUM(CAST(cash_drops AS REAL)), 0)
        FROM shift_summaries
        WHERE store_id = ? AND s_date = ?
    """, (store_id, target_date))
    cash_drops = Decimal(str(cursor.fetchone()[0] or 0))

    # Get opening float
    cursor.execute("""
        SELECT opening_float FROM shift_summaries
        WHERE store_id = ? AND s_date = ? AND shift_num = 1
    """, (store_id, target_date))
    row = cursor.fetchone()
    opening_float = Decimal(str(row[0] or 0)) if row else Decimal('0')

    conn.close()

    expected_cash = opening_float + cash_sales - cash_refunds - cash_drops

    return {
        'opening_float': opening_float,
        'cash_sales': cash_sales,
        'cash_refunds': cash_refunds,
        'cash_drops': cash_drops,
        'expected_cash': expected_cash
    }


@router.get("/shift-summaries", response_model=List[ShiftSummaryResponse])
async def get_shift_summaries(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get shift summaries with reconciliation data"""
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = []
    params = []
    if store_id:
        where_clauses.append("ss.store_id = ?")
        params.append(store_id)
    if start_date:
        where_clauses.append("ss.s_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("ss.s_date <= ?")
        params.append(end_date)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT
            ss.id, ss.store_id, s.name as store_name, ss.s_date, ss.shift_num,
            ss.start_time, ss.end_time, ss.reported_total_sales, ss.reported_total_tax,
            ss.opening_float, ss.counted_cash, ss.cash_drops
        FROM shift_summaries ss
        JOIN stores s ON ss.store_id = s.id
        {where_sql}
        ORDER BY ss.s_date DESC, ss.shift_num
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        shift_id, sid, store_name, s_date, shift_num, start_time, end_time, reported_sales, reported_tax, opening_float, counted_cash, cash_drops = row

        # Calculate expected from transactions
        conn_calc = get_db()
        cursor_calc = conn_calc.cursor()
        cursor_calc.execute("""
            SELECT COALESCE(SUM(CAST(total AS REAL)), 0), COALESCE(SUM(CAST(tax_total AS REAL)), 0)
            FROM transactions
            WHERE store_id = ? AND date(tx_timestamp) = ? AND status = 'COMPLETE' AND is_cancelled = 0
            -- Note: In real implementation, would filter by shift time range
        """, (sid, s_date))
        calc_row = cursor_calc.fetchone()
        calculated_sales = Decimal(str(calc_row[0] or 0))
        conn_calc.close()

        # Cash variance
        cash_position = calculate_cash_position(sid, s_date)
        cash_variance = Decimal(str(counted_cash or 0)) - cash_position['expected_cash']

        results.append(ShiftSummaryResponse(
            id=shift_id,
            store_id=sid,
            store_name=store_name,
            date=s_date,
            shift_num=shift_num,
            start_time=start_time,
            end_time=end_time,
            reported_total_sales=str(Decimal(str(reported_sales or 0))),
            reported_total_tax=str(Decimal(str(reported_tax or 0))),
            opening_float=str(Decimal(str(opening_float or 0))),
            counted_cash=str(Decimal(str(counted_cash or 0))),
            cash_drops=str(Decimal(str(cash_drops or 0))),
            calculated_sales=str(calculated_sales),
            cash_variance=str(cash_variance)
        ))

    conn.close()
    return results


@router.get("/eod-summaries", response_model=List[EODSummaryResponse])
async def get_eod_summaries(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get EOD summaries with reconciliation data"""
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = []
    params = []
    if store_id:
        where_clauses.append("eod.store_id = ?")
        params.append(store_id)
    if start_date:
        where_clauses.append("eod.s_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("eod.s_date <= ?")
        params.append(end_date)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT
            eod.id, eod.store_id, s.name as store_name, eod.s_date,
            eod.reported_total_sales, eod.reported_total_tax, eod.reported_transaction_count,
            eod.opening_float, eod.counted_cash, eod.cash_drops
        FROM eod_summaries eod
        JOIN stores s ON eod.store_id = s.id
        {where_sql}
        ORDER BY eod.s_date DESC
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        eod_id, sid, store_name, s_date, reported_sales, reported_tax, reported_txns, opening_float, counted_cash, cash_drops = row

        # Calculate actuals from transactions
        conn_calc = get_db()
        cursor_calc = conn_calc.cursor()
        cursor_calc.execute("""
            SELECT
                COALESCE(SUM(CAST(total AS REAL)), 0) as total_sales,
                COALESCE(SUM(CAST(tax_total AS REAL)), 0) as total_tax,
                COUNT(*) as txn_count
            FROM transactions
            WHERE store_id = ? AND date(tx_timestamp) = ?
            AND status = 'COMPLETE' AND is_cancelled = 0
        """, (sid, s_date))
        calc_row = cursor_calc.fetchone()
        calculated_sales = Decimal(str(calc_row[0] or 0))
        calculated_tax = Decimal(str(calc_row[1] or 0))
        calculated_txns = calc_row[2] or 0
        conn_calc.close()

        # Variances
        sales_var = calculated_sales - Decimal(str(reported_sales or 0))
        tax_var = calculated_tax - Decimal(str(reported_tax or 0))
        txn_var = calculated_txns - (reported_txns or 0)

        # Cash variance
        cash_position = calculate_cash_position(sid, s_date)
        cash_var = Decimal(str(counted_cash or 0)) - cash_position['expected_cash']

        results.append(EODSummaryResponse(
            id=eod_id,
            store_id=sid,
            store_name=store_name,
            date=s_date,
            reported_total_sales=str(Decimal(str(reported_sales or 0))),
            reported_total_tax=str(Decimal(str(reported_tax or 0))),
            reported_transaction_count=reported_txns or 0,
            opening_float=str(Decimal(str(opening_float or 0))),
            counted_cash=str(Decimal(str(counted_cash or 0))),
            cash_drops=str(Decimal(str(cash_drops or 0))),
            calculated_total_sales=str(calculated_sales),
            calculated_tax=str(calculated_tax),
            calculated_transaction_count=calculated_txns,
            sales_variance=str(sales_var),
            tax_variance=str(tax_var),
            cash_variance=str(cash_var),
            transaction_variance=txn_var
        ))

    conn.close()
    return results


@router.get("/daily-reconciliation/{store_id}/{target_date}", response_model=ReconciliationDetail)
async def get_daily_reconciliation(store_id: int, target_date: str):
    """Get full reconciliation detail for a store/date"""
    # Get store name
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
    store_row = cursor.fetchone()
    store_name = store_row[0] if store_row else "Unknown"
    conn.close()

    # Get shift summaries
    shifts = await get_shift_summaries(store_id=store_id, start_date=target_date, end_date=target_date)

    # Get EOD summary
    eod_list = await get_eod_summaries(store_id=store_id, start_date=target_date, end_date=target_date)
    eod = eod_list[0] if eod_list else None

    return ReconciliationDetail(
        date=target_date,
        store_id=store_id,
        store_name=store_name,
        shift_summaries=shifts,
        eod_summary=eod
    )


@router.get("/cash-variance-report")
async def get_cash_variance_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get cash variance report across all stores/dates"""
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = []
    params = []
    if start_date:
        where_clauses.append("eod.s_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("eod.s_date <= ?")
        params.append(end_date)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT
            eod.store_id, s.name as store_name, eod.s_date,
            eod.opening_float, eod.counted_cash, eod.cash_drops,
            eod.reported_total_sales
        FROM eod_summaries eod
        JOIN stores s ON eod.store_id = s.id
        {where_sql}
        ORDER BY eod.s_date DESC, eod.store_id
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        sid, store_name, s_date, opening_float, counted_cash, cash_drops, reported_sales = row

        cash_position = calculate_cash_position(sid, s_date)
        variance = Decimal(str(counted_cash or 0)) - cash_position['expected_cash']

        results.append({
            "store_id": sid,
            "store_name": store_name,
            "date": s_date,
            "opening_float": str(Decimal(str(opening_float or 0))),
            "cash_sales": str(cash_position['cash_sales']),
            "cash_refunds": str(cash_position['cash_refunds']),
            "cash_drops": str(cash_position['cash_drops']),
            "expected_cash": str(cash_position['expected_cash']),
            "counted_cash": str(Decimal(str(counted_cash or 0))),
            "variance": str(variance),
            "reported_sales": str(Decimal(str(reported_sales or 0)))
        })

    conn.close()
    return {"report": results}


@router.get("/discrepancies")
async def get_discrepancies(
    threshold: float = 0.01,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get all discrepancies above threshold"""
    eod_summaries = await get_eod_summaries(start_date=start_date, end_date=end_date)

    discrepancies = []
    for eod in eod_summaries:
        for field, value in [
            ("sales_variance", eod.sales_variance),
            ("tax_variance", eod.tax_variance),
            ("cash_variance", eod.cash_variance),
        ]:
            if abs(Decimal(value)) >= Decimal(str(threshold)):
                discrepancies.append({
                    "store_id": eod.store_id,
                    "store_name": eod.store_name,
                    "date": eod.date,
                    "field": field,
                    "reported": getattr(eod, f"reported_{field.replace('_variance', '')}") if field != "cash_variance" else eod.counted_cash,
                    "calculated": getattr(eod, f"calculated_{field.replace('_variance', '')}") if field != "cash_variance" else "N/A",
                    "variance": value
                })

    return {"discrepancies": discrepancies}