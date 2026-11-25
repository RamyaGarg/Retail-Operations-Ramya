-- Retail Operations Platform Schema

-- Master Data
CREATE TABLE stores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location TEXT
);

CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tax_group VARCHAR(50),
    age_restriction BOOLEAN DEFAULT FALSE
);

CREATE TABLE staff (
    id VARCHAR(50) PRIMARY KEY,
    store_id INTEGER REFERENCES stores(id),
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50)
);

CREATE TABLE devices (
    id VARCHAR(50) PRIMARY KEY,
    store_id INTEGER REFERENCES stores(id),
    type VARCHAR(50), -- counter, selfcheckout
    name VARCHAR(255)
);

CREATE TABLE items (
    item_code VARCHAR(50),
    variant_code VARCHAR(50),
    description TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    price DECIMAL(19, 4) NOT NULL,
    tax_group VARCHAR(50),
    age_restriction BOOLEAN DEFAULT FALSE,
    cost DECIMAL(19, 4),
    PRIMARY KEY (item_code, variant_code)
);

-- Imports & Audit
CREATE TABLE imports (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    format VARCHAR(20), -- v2_xml, v3_json, pricelist, summary
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20), -- success, partial, failed, quarantined
    reason TEXT,
    accepted_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    flagged_count INTEGER DEFAULT 0
);

-- Transaction Data
CREATE TABLE transactions (
    id VARCHAR(100) PRIMARY KEY,
    store_id INTEGER REFERENCES stores(id),
    device_id VARCHAR(50) REFERENCES devices(id),
    staff_id VARCHAR(50) REFERENCES staff(id),
    timestamp TIMESTAMP NOT NULL,
    scan_num INTEGER,
    type VARCHAR(50), -- SALE, RETURN, VOID, NOSALE, CASHDROP
    status VARCHAR(50), -- COMPLETE, CANCELLED
    is_cancelled BOOLEAN DEFAULT FALSE,
    cancel_reason TEXT,
    void_reason TEXT,
    refund_reason TEXT,
    no_sale_reason TEXT,
    subtotal DECIMAL(19, 4) NOT NULL,
    tax_total DECIMAL(19, 4) NOT NULL,
    total DECIMAL(19, 4) NOT NULL,
    gift_card_loads DECIMAL(19, 4) DEFAULT 0,
    gift_card_redeems DECIMAL(19, 4) DEFAULT 0,
    biz_account_charges DECIMAL(19, 4) DEFAULT 0,
    import_id INTEGER REFERENCES imports(id)
);

CREATE TABLE transaction_lines (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) REFERENCES transactions(id),
    item_code VARCHAR(50),
    variant_code VARCHAR(50),
    description TEXT,
    quantity DECIMAL(19, 4) NOT NULL,
    unit_price DECIMAL(19, 4) NOT NULL,
    line_total DECIMAL(19, 4) NOT NULL,
    tax_amount DECIMAL(19, 4) NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    event_type VARCHAR(50), -- VOID_LINE, REFUND_LINE
    FOREIGN KEY (item_code, variant_code) REFERENCES items(item_code, variant_code)
);

CREATE TABLE transaction_tenders (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) REFERENCES transactions(id),
    type VARCHAR(50), -- cash, card, mobile, gc, biz_acct
    amount DECIMAL(19, 4) NOT NULL,
    reference TEXT
);

-- Summaries
CREATE TABLE shift_summaries (
    id VARCHAR(100) PRIMARY KEY,
    store_id INTEGER REFERENCES stores(id),
    date DATE NOT NULL,
    shift_num INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    reported_total_sales DECIMAL(19, 4),
    reported_total_tax DECIMAL(19, 4),
    opening_float DECIMAL(19, 4),
    counted_cash DECIMAL(19, 4),
    cash_drops DECIMAL(19, 4),
    import_id INTEGER REFERENCES imports(id)
);

CREATE TABLE eod_summaries (
    id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(id),
    date DATE NOT NULL,
    reported_total_sales DECIMAL(19, 4),
    reported_total_tax DECIMAL(19, 4),
    reported_transaction_count INTEGER,
    opening_float DECIMAL(19, 4),
    counted_cash DECIMAL(19, 4),
    cash_drops DECIMAL(19, 4),
    import_id INTEGER REFERENCES imports(id),
    UNIQUE(store_id, date)
);

-- Business Accounts
CREATE TABLE business_accounts (
    account_number VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    credit_limit DECIMAL(19, 4)
);

CREATE TABLE business_account_activity (
    id SERIAL PRIMARY KEY,
    account_number VARCHAR(50) REFERENCES business_accounts(account_number),
    transaction_id VARCHAR(100) REFERENCES transactions(id),
    timestamp TIMESTAMP NOT NULL,
    amount DECIMAL(19, 4) NOT NULL, -- negative for charges, positive for payments
    type VARCHAR(50) -- charge, payment
);

-- Price Change Tracking
CREATE TABLE price_changes (
    id SERIAL PRIMARY KEY,
    change_id VARCHAR(100) UNIQUE,
    item_code VARCHAR(50),
    variant_code VARCHAR(50),
    old_price DECIMAL(19, 4),
    new_price DECIMAL(19, 4),
    status VARCHAR(20), -- Pending, Applied, Rejected
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (item_code, variant_code) REFERENCES items(item_code, variant_code)
);

-- Seed Master Data
INSERT INTO stores (name, location) VALUES ('Brightleaf Downtown', '123 Main St');
INSERT INTO stores (name, location) VALUES ('Brightleaf Uptown', '456 Oak Ave');

INSERT INTO departments (id, name, tax_group) VALUES (1, 'Coffee', 'tax_0');
INSERT INTO departments (id, name, tax_group) VALUES (2, 'Groceries', 'tax_8');
INSERT INTO departments (id, name, tax_group) VALUES (3, 'Household', 'tax_5');

INSERT INTO staff (id, store_id, name, role) VALUES ('STF001', 1, 'Alice Johnson', 'cashier');
INSERT INTO staff (id, store_id, name, role) VALUES ('STF002', 1, 'Bob Smith', 'manager');
INSERT INTO staff (id, store_id, name, role) VALUES ('STF003', 1, 'Carol Davis', 'cashier');
INSERT INTO staff (id, store_id, name, role) VALUES ('STF004', 2, 'David Lee', 'cashier');
INSERT INTO staff (id, store_id, name, role) VALUES ('STF005', 2, 'Eve Chen', 'manager');

INSERT INTO devices (id, store_id, type, name) VALUES ('REG001', 1, 'counter', 'Front Counter');
INSERT INTO devices (id, store_id, type, name) VALUES ('KIOSK001', 1, 'selfcheckout', 'SelfCheckout 1');
INSERT INTO devices (id, store_id, type, name) VALUES ('REG002', 1, 'counter', 'Side Counter');
INSERT INTO devices (id, store_id, type, name) VALUES ('REG001', 2, 'counter', 'Front Counter');
INSERT INTO devices (id, store_id, type, name) VALUES ('KIOSK001', 2, 'selfcheckout', 'SelfCheckout 1');
INSERT INTO devices (id, store_id, type, name) VALUES ('REG002', 2, 'counter', 'Side Counter');

-- Seed Items
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM001', 'REG', 'Espresso', 1, 2.50, 'tax_0', 0.80);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM002', 'REG', 'Cappuccino', 1, 3.25, 'tax_0', 1.00);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM003', 'REG', 'Latte', 1, 3.75, 'tax_0', 1.20);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM004', 'REG', 'Bagel Cream Cheese', 1, 1.99, 'tax_0', 0.50);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('ITM001', 'LGT', 'Espresso Large', 1, 3.00, 'tax_0', 1.00);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('MIL001', 'REG', 'Milk 1L', 2, 2.49, 'tax_8', 1.50);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('BAN001', 'REG', 'Bananas 1lb', 2, 0.79, 'tax_8', 0.30);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('BAN002', 'REG', 'Bananas 2lb', 2, 1.49, 'tax_8', 0.55);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('DRK001', 'REG', 'Coke 2L', 2, 2.99, 'tax_8', 1.80);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('HOH001', 'REG', 'Toothpaste 4oz', 3, 4.99, 'tax_5', 2.50);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('HOH002', 'REG', 'Shampoo 8oz', 3, 6.99, 'tax_5', 3.50);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('SNK001', 'REG', 'Chips 11oz', 2, 1.99, 'tax_8', 0.80);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('SOD001', 'REG', 'Soda 12pk', 2, 4.99, 'tax_8', 2.50);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('SOD002', 'REG', 'Soda 6pk', 2, 3.49, 'tax_8', 1.80);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('CND001', 'REG', 'Canned Beans', 2, 1.29, 'tax_8', 0.60);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('FRD001', 'REG', 'Apple 3lb Bag', 2, 3.99, 'tax_8', 2.00);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('HOU001', 'REG', 'Soap Bar', 3, 2.49, 'tax_5', 1.00);
INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group, cost) VALUES ('HOU002', 'REG', 'Dish Soap', 3, 3.99, 'tax_5', 1.50);
