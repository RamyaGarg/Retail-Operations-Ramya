import sqlite3
import os
import csv
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "retail.db")

# Path to data package - 3 levels up from this file + data_package_extracted/data_package
DATA_PACKAGE_DIR = Path(__file__).parent.parent.parent / "data_package_extracted" / "data_package"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS stores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT
    );

    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        tax_group TEXT,
        age_restriction INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS staff (
        id TEXT PRIMARY KEY,
        store_id INTEGER REFERENCES stores(id),
        name TEXT NOT NULL,
        role TEXT
    );

    CREATE TABLE IF NOT EXISTS devices (
        store_id INTEGER NOT NULL,
        id TEXT NOT NULL,
        type TEXT,
        name TEXT,
        PRIMARY KEY (store_id, id)
    );

    CREATE TABLE IF NOT EXISTS items (
        item_code TEXT NOT NULL,
        variant_code TEXT NOT NULL,
        description TEXT NOT NULL,
        department_id INTEGER REFERENCES departments(id),
        price TEXT NOT NULL,
        tax_group TEXT,
        age_restriction INTEGER DEFAULT 0,
        cost TEXT,
        PRIMARY KEY (item_code, variant_code)
    );

    CREATE TABLE IF NOT EXISTS imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE NOT NULL,
        format TEXT,
        processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT,
        reason TEXT,
        accepted_count INTEGER DEFAULT 0,
        skipped_count INTEGER DEFAULT 0,
        flagged_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        store_id INTEGER NOT NULL,
        device_id TEXT NOT NULL,
        staff_id TEXT,
        tx_timestamp TEXT NOT NULL,
        scan_num INTEGER,
        type TEXT,
        status TEXT,
        is_cancelled INTEGER DEFAULT 0,
        cancel_reason TEXT,
        void_reason TEXT,
        refund_reason TEXT,
        no_sale_reason TEXT,
        subtotal TEXT NOT NULL,
        tax_total TEXT NOT NULL,
        total TEXT NOT NULL,
        gift_card_loads TEXT DEFAULT '0.0000',
        gift_card_redeems TEXT DEFAULT '0.0000',
        biz_account_charges TEXT DEFAULT '0.0000',
        import_id INTEGER REFERENCES imports(id),
        FOREIGN KEY (store_id, device_id) REFERENCES devices(store_id, id),
        FOREIGN KEY (store_id) REFERENCES stores(id),
        FOREIGN KEY (staff_id) REFERENCES staff(id)
    );

    CREATE TABLE IF NOT EXISTS transaction_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT NOT NULL,
        item_code TEXT NOT NULL,
        variant_code TEXT NOT NULL,
        description TEXT,
        quantity TEXT NOT NULL,
        unit_price TEXT NOT NULL,
        line_total TEXT NOT NULL,
        tax_amount TEXT NOT NULL,
        department_id INTEGER REFERENCES departments(id),
        event_type TEXT,
        FOREIGN KEY (transaction_id) REFERENCES transactions(id),
        FOREIGN KEY (item_code, variant_code) REFERENCES items(item_code, variant_code)
    );

    CREATE TABLE IF NOT EXISTS transaction_tenders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT NOT NULL,
        type TEXT,
        amount TEXT NOT NULL,
        reference TEXT,
        FOREIGN KEY (transaction_id) REFERENCES transactions(id)
    );

    CREATE TABLE IF NOT EXISTS shift_summaries (
        id TEXT PRIMARY KEY,
        store_id INTEGER NOT NULL,
        s_date TEXT NOT NULL,
        shift_num INTEGER,
        start_time TEXT,
        end_time TEXT,
        reported_total_sales TEXT,
        reported_total_tax TEXT,
        opening_float TEXT,
        counted_cash TEXT,
        cash_drops TEXT,
        import_id INTEGER REFERENCES imports(id),
        FOREIGN KEY (store_id) REFERENCES stores(id)
    );

    CREATE TABLE IF NOT EXISTS eod_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id INTEGER NOT NULL,
        s_date TEXT NOT NULL,
        reported_total_sales TEXT,
        reported_total_tax TEXT,
        reported_transaction_count INTEGER,
        opening_float TEXT,
        counted_cash TEXT,
        cash_drops TEXT,
        import_id INTEGER REFERENCES imports(id),
        UNIQUE(store_id, s_date),
        FOREIGN KEY (store_id) REFERENCES stores(id)
    );

    CREATE TABLE IF NOT EXISTS business_accounts (
        account_number TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        credit_limit TEXT
    );

    CREATE TABLE IF NOT EXISTS business_account_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_number TEXT NOT NULL,
        transaction_id TEXT NOT NULL,
        ba_timestamp TEXT NOT NULL,
        amount TEXT NOT NULL,
        type TEXT,
        FOREIGN KEY (account_number) REFERENCES business_accounts(account_number),
        FOREIGN KEY (transaction_id) REFERENCES transactions(id)
    );

    CREATE TABLE IF NOT EXISTS price_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        change_id TEXT UNIQUE,
        item_code TEXT,
        variant_code TEXT,
        old_price TEXT,
        new_price TEXT,
        status TEXT,
        reason TEXT,
        pc_created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        pc_processed_at TEXT,
        FOREIGN KEY (item_code, variant_code) REFERENCES items(item_code, variant_code)
    );
    """)

    cursor.execute("SELECT COUNT(*) FROM stores;")
    if cursor.fetchone()[0] == 0:
        _load_master_data(cursor)

    conn.commit()
    conn.close()


def _load_master_data(cursor):
    """Load master data from data package CSV files"""

    # Create a mapping for store IDs (BL01 code -> numeric ID)
    store_id_map = {}

    # Load stores
    stores_path = DATA_PACKAGE_DIR / "master" / "stores.csv"
    if stores_path.exists():
        with open(stores_path, 'r') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=1):
                store_code = row['store_id']
                name = row['store_name']
                address = f"{row.get('address', '')}, {row.get('city', '')}, {row.get('state', '')}"

                cursor.execute(
                    "INSERT INTO stores (id, name, location) VALUES (?, ?, ?)",
                    (i, name, address)
                )
                store_id_map[store_code] = i

    # Load staff - use staff_id from CSV directly (201-204 for BL01, 301-302 for BL02)
    staff_path = DATA_PACKAGE_DIR / "master" / "staff.csv"
    if staff_path.exists():
        with open(staff_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                store_code = row['store_id']
                staff_code = row['staff_id']

                cursor.execute(
                    "INSERT INTO staff (id, store_id, name, role) VALUES (?, ?, ?, ?)",
                    (staff_code, store_id_map.get(store_code), row['name'], row['role'])
                )

    # Load devices
    devices_path = DATA_PACKAGE_DIR / "master" / "devices.csv"
    if devices_path.exists():
        with open(devices_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                store_code = row['store_id']
                device_id = row['device_id']
                device_type = row['device_type'].lower()  # counter, selfcheckout
                display_name = row['display_name']

                cursor.execute(
                    "INSERT INTO devices (store_id, id, type, name) VALUES (?, ?, ?, ?)",
                    (store_id_map.get(store_code), device_id, device_type, display_name)
                )

    # Load business accounts
    biz_accounts_path = DATA_PACKAGE_DIR / "business_accounts.csv"
    if biz_accounts_path.exists():
        with open(biz_accounts_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute(
                    "INSERT INTO business_accounts (account_number, name, credit_limit) VALUES (?, ?, ?)",
                    (row['account_id'], row['business_name'], row['credit_limit'])
                )


def reset_and_load_master_data():
    """Reset database to clean state and load only master data from data package"""
    conn = get_db()
    cursor = conn.cursor()

    # Clear tables in reverse FK order
    for table in ['business_account_activity', 'transaction_tenders', 'transaction_lines',
                   'transactions', 'shift_summaries', 'eod_summaries', 'price_changes',
                   'sales_targets', 'promotions', 'items', 'devices', 'staff',
                   'departments', 'stores', 'business_accounts']:
        cursor.execute(f"DELETE FROM {table}")

    # Clear imports and load fresh
    cursor.execute("DELETE FROM imports")

    # Clear and reload master data
    cursor.execute("DELETE FROM business_accounts")
    _load_master_data(cursor)

    conn.commit()
    conn.close()
    print("Master data loaded from data package into existing database")


if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")