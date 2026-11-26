"""Seed transaction data for Sales Hub dashboard testing"""
import sqlite3
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "retail.db")


def seed_transactions(num_transactions=1000):
    """Generate realistic transaction data for testing"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Get reference data
    cursor.execute("SELECT id, name FROM stores")
    stores = {row['id']: row['name'] for row in cursor.fetchall()}

    cursor.execute("SELECT id, store_id FROM staff")
    staff = {row['id']: row['store_id'] for row in cursor.fetchall()}

    cursor.execute("SELECT item_code, variant_code, description, price, department_id FROM items")
    items = cursor.fetchall()

    cursor.execute("SELECT id FROM devices")
    devices = [row['id'] for row in cursor.fetchall()]

    # Get business accounts
    cursor.execute("SELECT account_number FROM business_accounts")
    biz_accounts = [row['account_number'] for row in cursor.fetchall()]
    if not biz_accounts:
        biz_accounts = ['ACC001', 'ACC002']

    # Get departments
    cursor.execute("SELECT id, name FROM departments")
    departments = {row['id']: row['name'] for row in cursor.fetchall()}

    # Ensure business accounts exist
    cursor.execute("SELECT COUNT(*) FROM business_accounts")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
            INSERT INTO business_accounts (account_number, name, credit_limit) VALUES ('ACC001', 'Local Café', '1000.0000');
            INSERT INTO business_accounts (account_number, name, credit_limit) VALUES ('ACC002', 'Corner Deli', '500.0000');
        """)

    # Clear existing data
    cursor.execute("DELETE FROM transaction_tenders")
    cursor.execute("DELETE FROM business_account_activity")
    cursor.execute("DELETE FROM transaction_lines")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM shift_summaries")
    cursor.execute("DELETE FROM eod_summaries")
    cursor.execute("DELETE FROM sales_targets")
    cursor.execute("DELETE FROM promotions")
    cursor.execute("DELETE FROM staff_shifts")

    # Seed sales_targets
    today = datetime.now()
    for store_id in stores.keys():
        for i in range(3):
            period = today - timedelta(days=30*i)
            period_start = period.replace(day=1)
            period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            target = random.uniform(10000, 50000)
            cursor.execute("""
                INSERT INTO sales_targets
                (store_id, period_start, period_end, sales_target)
                VALUES (?, ?, ?, ?)
            """, (
                store_id,
                period_start.strftime('%Y-%m-%d'),
                period_end.strftime('%Y-%m-%d'),
                str(round(target, 2))
            ))

    # Seed promotions
    promotions_data = [
        ("Spring Kickoff", "2026-03-01", "2026-03-31", 10.00, 1),
        ("Summer Sale", "2026-07-01", "2026-07-31", 15.00, 2),
        ("Back to School", "2026-08-15", "2026-09-15", 15.00, 1),
        ("Winter Clearance", "2026-11-01", "2026-11-30", 20.00, 1)
    ]
    for name, start, end, discount_pct, store_id in promotions_data:
        cursor.execute("""
            INSERT INTO promotions (name, start_date, end_date, discount_pct, store_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name, start, end, discount_pct, store_id))

    # Seed staff shifts
    for staff_id, store_id in staff.items():
        for i in range(15):
            shift_date = today - timedelta(days=i)
            cursor.execute("""
                INSERT INTO staff_shifts (staff_id, store_id, shift_date, hours_worked)
                VALUES (?, ?, ?, ?)
            """, (staff_id, store_id, shift_date.strftime('%Y-%m-%d'), 8.0))

    # Generate transactions
    transaction_count = 0
    start_date = datetime.now() - timedelta(days=30)

    for i in range(num_transactions):
        store_id = random.choice(list(stores.keys()))
        store_staff = [s for s, store in staff.items() if store == store_id]
        if not store_staff:
            continue
        staff_id = random.choice(store_staff)

        tx_date = start_date + timedelta(days=random.randint(0, 30),
                                           hours=random.randint(8, 20),
                                           minutes=random.randint(0, 59))
        tx_timestamp = tx_date.strftime('%Y-%m-%d %H:%M:%S')
        device_id = random.choice(devices)

        total = Decimal(str(round(random.uniform(15, 250), 2)))
        tax_total = Decimal(str(round(total * Decimal('0.08'), 2)))
        subtotal = total - tax_total

        tx_type = 'SALE'
        if random.random() < 0.03:
            tx_type = 'RETURN'
            total = -total
            tax_total = -tax_total
            subtotal = -subtotal

        status = 'COMPLETE'
        if random.random() < 0.01:
            status = 'VOID'

        transaction_id = f"TXN{i:06d}"

        cursor.execute("""
            INSERT INTO transactions
            (id, store_id, device_id, staff_id, tx_timestamp, scan_num, type, status,
             is_cancelled, subtotal, tax_total, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id,
            store_id,
            device_id,
            staff_id,
            tx_timestamp,
            i,
            tx_type,
            status,
            1 if status == 'VOID' else 0,
            str(subtotal),
            str(tax_total),
            str(total)
        ))

        num_items = random.randint(1, 4)
        for j in range(num_items):
            item = random.choice(items)
            quantity = random.randint(1, 3)
            unit_price = Decimal(item['price'])
            line_total = unit_price * quantity
            tax_amount = line_total * Decimal('0.08')

            cursor.execute("""
                INSERT INTO transaction_lines
                (transaction_id, item_code, variant_code, description, quantity,
                 unit_price, line_total, tax_amount, department_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction_id,
                item['item_code'],
                item['variant_code'],
                item['description'],
                str(quantity),
                str(round(unit_price, 4)),
                str(round(line_total, 4)),
                str(round(tax_amount, 4)),
                item['department_id']
            ))

        cursor.execute("""
            INSERT INTO transaction_tenders
            (transaction_id, type, amount, reference)
            VALUES (?, ?, ?, ?)
        """, (
            transaction_id,
            'credit' if total > 0 else 'cash',
            str(abs(total)),
            f"REF{transaction_count}"
        ))

        # Occasionally create business account activity (about 5% of transactions)
        if random.random() < 0.05:
            biz_account = random.choice(biz_accounts)
            charge_amount = Decimal(str(round(random.uniform(50, 200), 2)))
            ba_timestamp = tx_date.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO business_account_activity
                (account_number, transaction_id, ba_timestamp, amount, type)
                VALUES (?, ?, ?, ?, 'charge')
            """, (biz_account, transaction_id, ba_timestamp, str(-charge_amount)))

        if status != 'VOID':
            transaction_count += 1

    conn.commit()
    conn.close()
    print(f"Successfully seeded {transaction_count} completed transactions!")

if __name__ == "__main__":
    seed_transactions(2000)
