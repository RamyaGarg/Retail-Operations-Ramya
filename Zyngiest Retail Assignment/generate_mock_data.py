#!/usr/bin/env python3
"""
Generate mock data for Multi-Store Retail Operations Platform
This script creates synthetic data files matching the assignment specification
"""

import os
import json
import random
import datetime
import uuid
from decimal import Decimal
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
random.seed(42)  # Reproducible data

# Data definitions
STORES = [
    {'id': 1, 'name': 'Brightleaf Downtown', 'location': '123 Main St'},
    {'id': 2, 'name': 'Brightleaf Uptown', 'location': '456 Oak Ave'}
]

DEPARTMENTS = [
    {'id': 1, 'name': 'Coffee', 'tax_group': 'tax_0', 'age_restriction': False},
    {'id': 2, 'name': 'Groceries', 'tax_group': 'tax_8', 'age_restriction': False},
    {'id': 3, 'name': 'Household', 'tax_group': 'tax_5', 'age_restriction': False}
]

TAX_GROUPS = {'tax_0': 0.00, 'tax_5': 0.05, 'tax_8': 0.08}

DEVICES = [
    {'id': 'REG001', 'store_id': 1, 'type': 'counter', 'name': 'Front Counter'},
    {'id': 'KIOSK001', 'store_id': 1, 'type': 'selfcheckout', 'name': 'SelfCheckout 1'},
    {'id': 'REG002', 'store_id': 1, 'type': 'counter', 'name': 'Side Counter'},
    {'id': 'REG001', 'store_id': 2, 'type': 'counter', 'name': 'Front Counter'},
    {'id': 'KIOSK001', 'store_id': 2, 'type': 'selfcheckout', 'name': 'SelfCheckout 1'},
    {'id': 'REG002', 'store_id': 2, 'type': 'counter', 'name': 'Side Counter'},
]

STAFF = [
    {'id': 'STF001', 'store_id': 1, 'name': 'Alice Johnson', 'role': 'cashier'},
    {'id': 'STF002', 'store_id': 1, 'name': 'Bob Smith', 'role': 'manager'},
    {'id': 'STF003', 'store_id': 1, 'name': 'Carol Davis', 'role': 'cashier'},
    {'id': 'STF004', 'store_id': 2, 'name': 'David Lee', 'role': 'cashier'},
    {'id': 'STF005', 'store_id': 2, 'name': 'Eve Chen', 'role': 'manager'},
]

ITEMS = [
    {'item_code': 'ITM001', 'variant_code': 'REG', 'description': 'Espresso', 'department_id': 1, 'price': '2.50', 'tax_group': 'tax_0', 'cost': 0.80},
    {'item_code': 'ITM002', 'variant_code': 'REG', 'description': 'Cappuccino', 'department_id': 1, 'price': '3.25', 'tax_group': 'tax_0', 'cost': 1.00},
    {'item_code': 'ITM003', 'variant_code': 'REG', 'description': 'Latte', 'department_id': 1, 'price': '3.75', 'tax_group': 'tax_0', 'cost': 1.20},
    {'item_code': 'ITM004', 'variant_code': 'REG', 'description': 'Bagel Cream Cheese', 'department_id': 1, 'price': '1.99', 'tax_group': 'tax_0', 'cost': 0.50},
    {'item_code': 'ITM001', 'variant_code': 'LGT', 'description': 'Espresso Large', 'department_id': 1, 'price': '3.00', 'tax_group': 'tax_0', 'cost': 1.00},
    {'item_code': 'MIL001', 'variant_code': 'REG', 'description': 'Milk 1L', 'department_id': 2, 'price': '2.49', 'tax_group': 'tax_8', 'cost': 1.50},
    {'item_code': 'BAN001', 'variant_code': 'REG', 'description': 'Bananas 1lb', 'department_id': 2, 'price': '0.79', 'tax_group': 'tax_8', 'cost': 0.30},
    {'item_code': 'BAN002', 'variant_code': 'REG', 'description': 'Bananas 2lb', 'department_id': 2, 'price': '1.49', 'tax_group': 'tax_8', 'cost': 0.55},
    {'item_code': 'DRK001', 'variant_code': 'REG', 'description': 'Coke 2L', 'department_id': 2, 'price': '2.99', 'tax_group': 'tax_8', 'cost': 1.80},
    {'item_code': 'HOH001', 'variant_code': 'REG', 'description': 'Toothpaste 4oz', 'department_id': 3, 'price': '4.99', 'tax_group': 'tax_5', 'cost': 2.50},
    {'item_code': 'HOH002', 'variant_code': 'REG', 'description': 'Shampoo 8oz', 'department_id': 3, 'price': '6.99', 'tax_group': 'tax_5', 'cost': 3.50},
    {'item_code': 'SNK001', 'variant_code': 'REG', 'description': 'Chips 11oz', 'department_id': 2, 'price': '1.99', 'tax_group': 'tax_8', 'cost': 0.80},
    {'item_code': 'SOD001', 'variant_code': 'REG', 'description': 'Soda 12pk', 'department_id': 2, 'price': '4.99', 'tax_group': 'tax_8', 'cost': 2.50},
    {'item_code': 'SOD002', 'variant_code': 'REG', 'description': 'Soda 6pk', 'department_id': 2, 'price': '3.49', 'tax_group': 'tax_8', 'cost': 1.80},
    {'item_code': 'CND001', 'variant_code': 'REG', 'description': 'Canned Beans', 'department_id': 2, 'price': '1.29', 'tax_group': 'tax_8', 'cost': 0.60},
    {'item_code': 'FRD001', 'variant_code': 'REG', 'description': 'Apple 3lb Bag', 'department_id': 2, 'price': '3.99', 'tax_group': 'tax_8', 'cost': 2.00},
    {'item_code': 'HOU001', 'variant_code': 'REG', 'description': 'Soap Bar', 'department_id': 3, 'price': '2.49', 'tax_group': 'tax_5', 'cost': 1.00},
    {'item_code': 'HOU002', 'variant_code': 'REG', 'description': 'Dish Soap', 'department_id': 3, 'price': '3.99', 'tax_group': 'tax_5', 'cost': 1.50},
]

BUSINESS_ACCOUNTS = [
    {'account_number': 'ACC001', 'name': 'Local Café', 'credit_limit': 1000.00},
    {'account_number': 'ACC002', 'name': 'Corner Deli', 'credit_limit': 500.00},
]

# Create directories
os.makedirs(os.path.join(BASE_DIR, 'outbox'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'inbox'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'master'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'invoices'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'docs'), exist_ok=True)

def prettify_xml(elem):
    """Return a pretty-printed XML string"""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def create_tlog_xml_v2(transactions, filename):
    """Create transaction log XML v2 format"""
    root = ET.Element('TransactionLog', attrib={'format': 'v2', 'batch_id': str(uuid.uuid4())[:8]})

    for tx in transactions:
        tx_elem = ET.SubElement(root, 'Transaction', attrib={
            'id': tx['id'],
            'store_id': str(tx['store_id']),
            'device_id': tx['device_id'],
            'staff_id': tx['staff_id'],
            'timestamp': tx['timestamp'].isoformat(),
            'scan_num': str(tx['scan_num']),
            'type': tx['type'],
            'status': tx['status'],
            'is_cancelled': str(tx.get('is_cancelled', False)).lower(),
            'cancel_reason': tx.get('cancel_reason', ''),
            'void_reason': tx.get('void_reason', ''),
            'refund_reason': tx.get('refund_reason', ''),
            'no_sale_reason': tx.get('no_sale_reason', '')
        })

        lines_elem = ET.SubElement(tx_elem, 'Lines')
        for line in tx.get('lines', []):
            line_elem = ET.SubElement(lines_elem, 'Line', attrib={
                'item_code': line['item_code'],
                'variant_code': line['variant_code'],
                'description': line['description'],
                'quantity': str(line['quantity']),
                'unit_price': str(line['unit_price']),
                'line_total': str(line['line_total']),
                'tax_amount': str(line['tax_amount']),
                'department_id': str(line['department_id']),
                'tender_id': line.get('tender_id', ''),
                'event_type': line.get('event_type', '')
            })

        tenders_elem = ET.SubElement(tx_elem, 'Tenders')
        for tender in tx.get('tenders', []):
            tender_elem = ET.SubElement(tenders_elem, 'Tender', attrib={
                'type': tender['type'],
                'amount': str(tender['amount']),
                'reference': tender.get('reference', '')
            })

        stats_elem = ET.SubElement(tx_elem, 'Stats')
        ET.SubElement(stats_elem, 'Subtotal', attrib={'amount': str(tx['subtotal'])})
        ET.SubElement(stats_elem, 'TaxTotal', attrib={'amount': str(tx['tax_total'])})
        ET.SubElement(stats_elem, 'Total', attrib={'amount': str(tx['total'])})
        ET.SubElement(stats_elem, 'GiftCardLoads', attrib={'amount': str(tx.get('gift_card_loads', 0))})
        ET.SubElement(stats_elem, 'GiftCardRedeems', attrib={'amount': str(tx.get('gift_card_redeems', 0))})
        ET.SubElement(stats_elem, 'BusinessAccountCharges', attrib={'amount': str(tx.get('biz_account_charges', 0))})

    with open(filename, 'w') as f:
        f.write(prettify_xml(root))

def create_tlog_json_v3(transactions, filename):
    """Create transaction log JSON v3 format"""
    log_data = {
        'format': 'v3',
        'batch_id': str(uuid.uuid4())[:8],
        'transactions': []
    }

    for tx in transactions:
        tx_record = {
            'tx_id': tx['id'],
            'store_id': tx['store_id'],
            'device_id': tx['device_id'],
            'staff_id': tx['staff_id'],
            'timestamp': tx['timestamp'].isoformat(),
            'scan_num': tx['scan_num'],
            'tx_type': tx['type'],
            'status': tx['status'],
            'cancelled': tx.get('is_cancelled', False),
            'cancel_reason': tx.get('cancel_reason', ''),
            'void_reason': tx.get('void_reason', ''),
            'refund_reason': tx.get('refund_reason', ''),
            'no_sale_reason': tx.get('no_sale_reason', ''),
            'items': [],
            'tenders': [],
            'summary': {
                'subtotal': float(tx['subtotal']),
                'tax_total': float(tx['tax_total']),
                'total': float(tx['total']),
                'gc_loads': float(tx.get('gift_card_loads', 0)),
                'gc_redeems': float(tx.get('gift_card_redeems', 0)),
                'biz_charges': float(tx.get('biz_account_charges', 0))
            }
        }

        for line in tx.get('lines', []):
            tx_record['items'].append({
                'item_code': line['item_code'],
                'variant_code': line['variant_code'],
                'desc': line['description'],
                'qty': float(line['quantity']),
                'price': float(line['unit_price']),
                'total': float(line['line_total']),
                'tax': float(line['tax_amount']),
                'dept_id': line['department_id'],
                'tender_id': line.get('tender_id', ''),
                'event': line.get('event_type', '')
            })

        for tender in tx.get('tenders', []):
            tx_record['tenders'].append({
                'type': tender['type'],
                'amount': float(str(tender['amount'])),
                'ref': tender.get('reference', '')
            })

        log_data['transactions'].append(tx_record)

    with open(filename, 'w') as f:
        json.dump(log_data, f, indent=2)

def create_price_list_xml_v2(filename):
    """Create the hub's price list export"""
    root = ET.Element('PriceList', attrib={'version': '2', 'export_time': datetime.datetime.now().isoformat()})

    for dept in DEPARTMENTS:
        dept_items = [i for i in ITEMS if i['department_id'] == dept['id']]
        if dept_items:
            dept_elem = ET.SubElement(root, 'Department', attrib={
                'id': str(dept['id']),
                'name': dept['name']
            })
            for item in dept_items:
                ET.SubElement(dept_elem, 'Item', attrib={
                    'item_code': item['item_code'],
                    'variant_code': item['variant_code'],
                    'description': item['description'],
                    'price': item['price'],
                    'tax_group': item['tax_group'],
                    'age_restriction': str(item.get('age_restriction', False)).lower()
                })

    with open(filename, 'w') as f:
        f.write(prettify_xml(root))

def create_shift_summary(store_id, date, transactions):
    """Create shift summary"""
    summary = {
        'store_id': store_id,
        'date': date.isoformat(),
        'shift_id': f'SHIFT_{store_id}_{date.strftime("%Y%m%d")}_1',
        'start_time': f'{date.strftime("%Y-%m-%d")}T08:00:00',
        'end_time': f'{date.strftime("%Y-%m-%d")}T14:00:00',
        'sales_by_dept': {},
        'tender_totals': {},
        'tax_by_group': {},
        'gc_loads': '0.00',
        'gc_redeems': '0.00',
        'biz_account_charges': '0.00',
        'opening_float': '100.00',
        'counted_cash': '0.00',
        'cash_taken': '0.00',
        'cash_refunds': '0.00',
        'cash_drops': '0.00'
    }
    return summary

def create_eod_summary(store_id, date, transactions):
    """Create end-of-day summary"""
    total_sales = sum(t['total'] for t in transactions)

    dept_sales = {}
    for t in transactions:
        for d, v in t.get('dept_totals', {}).items():
            dept_sales[d] = dept_sales.get(d, Decimal('0')) + Decimal(str(v))

    return {
        'store_id': store_id,
        'date': date.isoformat(),
        'total_sales': str(total_sales),
        'total_tax': str(sum(t['tax_total'] for t in transactions)),
        'sales_by_dept': {k: str(v) for k, v in dept_sales.items()},
        'tender_totals': {'cash': '0', 'card': '0', 'mobile': '0', 'gc': '0', 'biz_acct': '0'},
        'gc_loads': '0.00',
        'gc_redeems': '0.00',
        'biz_account_charges': '0.00',
        'opening_float': '100.00',
        'counted_cash': str(total_sales - Decimal('10')),  # Intentional discrepancy for testing
        'cash_drops': '0.00',
        'transaction_count': len(transactions)
    }

def generate_transactions_14_days():
    """Generate 14 days of transactions for 2 stores"""
    all_transactions = []

    # Day 0-6: Use XML v2 format
    # Day 7-13: Use JSON v3 format (hub upgrade)

    start_date = datetime.date.today() - datetime.timedelta(days=14)

    for day_offset in range(14):
        current_date = start_date + datetime.timedelta(days=day_offset)
        use_v3 = day_offset >= 7  # v3 from day 7 onwards

        for store_id in [1, 2]:
            device_id = f'REG001' if store_id == 1 else 'REG001'
            staff_id = 'STF001'  # Simplest test case

            # Generate transactions throughout the day
            for batch in range(3):  # 3 batches per store per day
                transactions = []
                num_txs = random.randint(20, 50)

                for i in range(num_txs):
                    scan_num = random.randint(10000, 99999)
                    tx_time = datetime.datetime.combine(current_date, datetime.time(
                        random.randint(8, 18), random.randint(0, 59), random.randint(0, 59)
                    ))

                    # Pick a random item
                    item = random.choice(ITEMS)
                    dept_id = item['department_id']
                    price = Decimal(item['price'])

                    # Calculate quantities and taxes
                    qty = Decimal(str(random.randint(1, 5) if random.random() > 0.1 else 0))
                    subtotal = price * qty
                    tax_rate = TAX_GROUPS[item['tax_group']]
                    tax = subtotal * Decimal(str(tax_rate))
                    total = subtotal + tax

                    tx = {
                        'id': f'TX_{uuid.uuid4().hex[:12]}',
                        'store_id': store_id,
                        'device_id': device_id,
                        'staff_id': staff_id,
                        'timestamp': tx_time,
                        'scan_num': scan_num,
                        'type': 'SALE',
                        'status': 'COMPLETE',
                        'subtotal': subtotal,
                        'tax_total': tax,
                        'total': total,
                        'gift_card_loads': Decimal('0'),
                        'gift_card_redeems': Decimal('0'),
                        'biz_account_charges': Decimal('0'),
                        'lines': [{
                            'item_code': item['item_code'],
                            'variant_code': item['variant_code'],
                            'description': item['description'],
                            'quantity': qty,
                            'unit_price': price,
                            'line_total': subtotal,
                            'tax_amount': tax,
                            'department_id': dept_id,
                            'tender_id': '',
                            'event_type': ''
                        }],
                        'tenders': [{
                            'type': random.choice(['cash', 'card', 'mobile']),
                            'amount': total,
                            'reference': ''
                        }],
                        'dept_totals': {dept_id: subtotal}
                    }
                    transactions.append(tx)

                all_transactions.extend(transactions)

    return all_transactions

def generate_files():
    """Generate all required files"""
    print("Generating transaction logs...")

    # Generate transactions
    transactions = generate_transactions_14_days()

    # Split transactions by date and format
    start_date = datetime.date.today() - datetime.timedelta(days=14)

    for day_offset in range(14):
        current_date = start_date + datetime.timedelta(days=day_offset)
        date_str = current_date.strftime('%Y%m%d')
        use_v3 = day_offset >= 7

        store1_txs = [t for t in transactions if t['store_id'] == 1 and t['timestamp'].date() == current_date]
        store2_txs = [t for t in transactions if t['store_id'] == 2 and t['timestamp'].date() == current_date]

        if store1_txs:
            fmt = 'json' if use_v3 else 'xml'
            suffix = 'TLOG_S01' + ('_V3' if use_v3 else '_V2')
            filename = os.path.join(BASE_DIR, 'outbox', f'{suffix}_{date_str}.{fmt}')
            if use_v3:
                create_tlog_json_v3(store1_txs, filename)
            else:
                create_tlog_xml_v2(store1_txs, filename)
            print(f'  Created {os.path.basename(filename)} with {len(store1_txs)} transactions')

        if store2_txs:
            suffix = 'TLOG_S02' + ('_V3' if use_v3 else '_V2')
            filename = os.path.join(BASE_DIR, 'outbox', f'{suffix}_{date_str}.{fmt}')
            if use_v3:
                create_tlog_json_v3(store2_txs, filename)
            else:
                create_tlog_xml_v2(store2_txs, filename)
            print(f'  Created {os.path.basename(filename)} with {len(store2_txs)} transactions')

    # Create price list
    print("\nGenerating price list...")
    create_price_list_xml_v2(os.path.join(BASE_DIR, 'outbox', 'PRICELIST_BRIGHTLEAF_001.xml'))

    # Create some ACK/REJ files for price changes
    print("\nGenerating ACK/REJ files...")
    ack_content = {
        'change_id': 'CHG001',
        'status': 'APPLIED',
        'items_processed': 3,
        'timestamp': datetime.datetime.now().isoformat()
    }
    with open(os.path.join(BASE_DIR, 'outbox', 'ACK_CMG001.xml'), 'w') as f:
        f.write(prettify_xml(ET.Element('Acknowledgement', attrib={'change_id': 'CHG001'})))

    rej_elem = ET.Element('Rejection', attrib={'change_id': 'CHG002', 'reason': 'Invalid item_code: ITM999'})
    with open(os.path.join(BASE_DIR, 'outbox', 'REJ_CMG002.xml'), 'w') as f:
        f.write(prettify_xml(rej_elem))

    # Create sample price change file in inbox
    print("\nGenerating price change file...")
    change_root = ET.Element('PriceChanges', attrib={'source': 'Brightleaf Market', 'created': datetime.datetime.now().isoformat()})
    change_elem = ET.SubElement(change_root, 'Change', attrib={
        'item_code': 'ITM003',
        'variant_code': 'REG',
        'new_price': '4.25',
        'reason': 'Cost increase'
    })
    with open(os.path.join(BASE_DIR, 'inbox', 'PRICE_CHANGE_001.xml'), 'w') as f:
        f.write(prettify_xml(change_root))

    print(f"\nData generation complete!")
    print(f"Files created in: {BASE_DIR}")

if __name__ == '__main__':
    generate_files()