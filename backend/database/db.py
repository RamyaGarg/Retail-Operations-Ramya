import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "retail.db")

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

    # Seed data if empty
    cursor.execute("SELECT COUNT(*) FROM stores;")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
        INSERT INTO stores (id, name, location) VALUES (1, 'Brightleaf Downtown', '123 Main St');
        INSERT INTO stores (id, name, location) VALUES (2, 'Brightleaf Uptown', '456 Oak Ave');

        INSERT INTO departments (id, name, tax_group) VALUES (1, 'Coffee', 'tax_0');
        INSERT INTO departments (id, name, tax_group) VALUES (2, 'Groceries', 'tax_8');
        INSERT INTO departments (id, name, tax_group) VALUES (3, 'Household', 'tax_5');

        INSERT INTO staff (id, store_id, name, role) VALUES ('STF001', 1, 'Alice Johnson', 'cashier');
        INSERT INTO staff (id, store_id, name, role) VALUES ('STF002', 1, 'Bob Smith', 'manager');
        INSERT INTO staff (id, store_id, name, role) VALUES ('STF003', 1, 'Carol Davis', 'cashier');
        INSERT INTO staff (id, store_id, name, role) VALUES ('STF004', 2, 'David Lee', 'cashier');
        INSERT INTO staff (id, store_id, name, role) VALUES ('STF005', 2, 'Eve Chen', 'manager');

        INSERT INTO devices (store_id, id, type, name) VALUES (1, 'REG001', 'counter', 'Front Counter');
        INSERT INTO devices (store_id, id, type, name) VALUES (1, 'KIOSK001', 'selfcheckout', 'SelfCheckout 1');
        INSERT INTO devices (store_id, id, type, name) VALUES (1, 'REG002', 'counter', 'Side Counter');
        INSERT INTO devices (store_id, id, type, name) VALUES (2, 'REG001', 'counter', 'Front Counter');
        INSERT INTO devices (store_id, id, type, name) VALUES (2, 'KIOSK001', 'selfcheckout', 'SelfCheckout 1');
        INSERT INTO devices (store_id, id, type, name) VALUES (2, 'REG002', 'counter', 'Side Counter');

        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM001', 'REG', 'Espresso', 1, '2.5000', 'tax_0', '0.8000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM002', 'REG', 'Cappuccino', 1, '3.2500', 'tax_0', '1.0000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM003', 'REG', 'Latte', 1, '3.7500', 'tax_0', '1.2000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM004', 'REG', 'Bagel Cream Cheese', 1, '1.9900', 'tax_0', '0.5000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM001', 'LGT', 'Espresso Large', 1, '3.0000', 'tax_0', '1.0000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('MIL001', 'REG', 'Milk 1L', 2, '2.4900', 'tax_8', '1.5000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('BAN001', 'REG', 'Bananas 1lb', 2, '0.7900', 'tax_8', '0.3000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('BAN002', 'REG', 'Bananas 2lb', 2, '1.4900', 'tax_8', '0.5500');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('DRK001', 'REG', 'Coke 2L', 2, '2.9900', 'tax_8', '1.8000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('HOH001', 'REG', 'Toothpaste 4oz', 3, '4.9900', 'tax_5', '2.5000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('HOH002', 'REG', 'Shampoo 8oz', 3, '6.9900', 'tax_5', '3.5000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('SNK001', 'REG', 'Chips 11oz', 2, '1.9900', 'tax_8', '0.8000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('SOD001', 'REG', 'Soda 12pk', 2, '4.9900', 'tax_8', '2.5000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('SOD002', 'REG', 'Soda 6pk', 2, '3.4900', 'tax_8', '1.8000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('CND001', 'REG', 'Canned Beans', 2, '1.2900', 'tax_8', '0.6000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('FRD001', 'REG', 'Apple 3lb Bag', 2, '3.9900', 'tax_8', '2.0000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('HOU001', 'REG', 'Soap Bar', 3, '2.4900', 'tax_5', '1.0000');
        INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('HOU002', 'REG', 'Dish Soap', 3, '3.9900', 'tax_5', '1.5000');

        INSERT INTO business_accounts (account_number, name, credit_limit) VALUES ('ACC001', 'Local Café', '1000.0000');
        INSERT INTO business_accounts (account_number, name, credit_limit) VALUES ('ACC002', 'Corner Deli', '500.0000');
        """)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
