"""Connector module - handles import of transaction logs from outbox"""
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from database.db import get_db

router = APIRouter()

# Data package lives at <assignment root>/data_package_extracted/data_package (4 levels up)
DATA_PACKAGE_DIR = Path(__file__).parent.parent.parent.parent / "data_package_extracted" / "data_package"
OUTBOX_DIR = DATA_PACKAGE_DIR / "outbox"


class ImportResponse(BaseModel):
    filename: str
    format: str
    status: str
    accepted_count: int
    skipped_count: int
    flagged_count: int
    reason: Optional[str] = None


def parse_decimal(value, default=Decimal('0')) -> Decimal:
    """Parse string/number to Decimal, handling empty strings and invalid values"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        try:
            return Decimal(s)
        except:
            return default
    try:
        return Decimal(str(value))
    except:
        return default


def parse_xml_v2(filepath: Path) -> List[Dict[str, Any]]:
    """Parse XML v2 transaction log format"""
    transactions = []
    tree = ET.parse(filepath)
    root = tree.getroot()

    for tx_elem in root.findall('Transaction'):
        tx = {
            'id': tx_elem.get('id'),
            'store_id': int(tx_elem.get('store_id')),
            'device_id': tx_elem.get('device_id'),
            'staff_id': tx_elem.get('staff_id'),
            'timestamp': tx_elem.get('timestamp'),
            'scan_num': int(tx_elem.get('scan_num', 0)),
            'type': tx_elem.get('type'),
            'status': tx_elem.get('status'),
            'is_cancelled': tx_elem.get('is_cancelled', 'false').lower() == 'true',
            'cancel_reason': tx_elem.get('cancel_reason', ''),
            'void_reason': tx_elem.get('void_reason', ''),
            'refund_reason': tx_elem.get('refund_reason', ''),
            'no_sale_reason': tx_elem.get('no_sale_reason', ''),
        }

        # Parse lines
        lines = []
        lines_elem = tx_elem.find('Lines')
        if lines_elem is not None:
            for line_elem in lines_elem.findall('Line'):
                lines.append({
                    'item_code': line_elem.get('item_code'),
                    'variant_code': line_elem.get('variant_code'),
                    'description': line_elem.get('description'),
                    'quantity': parse_decimal(line_elem.get('quantity', '0')),
                    'unit_price': parse_decimal(line_elem.get('unit_price', '0')),
                    'line_total': parse_decimal(line_elem.get('line_total', '0')),
                    'tax_amount': parse_decimal(line_elem.get('tax_amount', '0')),
                    'department_id': int(line_elem.get('department_id', 0)),
                    'event_type': line_elem.get('event_type', ''),
                })
        tx['lines'] = lines

        # Parse tenders
        tenders = []
        tenders_elem = tx_elem.find('Tenders')
        if tenders_elem is not None:
            for tender_elem in tenders_elem.findall('Tender'):
                tenders.append({
                    'type': tender_elem.get('type'),
                    'amount': parse_decimal(tender_elem.get('amount', '0')),
                    'reference': tender_elem.get('reference', ''),
                })
        tx['tenders'] = tenders

        # Parse stats
        stats_elem = tx_elem.find('Stats')
        if stats_elem is not None:
            tx['subtotal'] = parse_decimal(stats_elem.find('Subtotal').get('amount', '0'))
            tx['tax_total'] = parse_decimal(stats_elem.find('TaxTotal').get('amount', '0'))
            tx['total'] = parse_decimal(stats_elem.find('Total').get('amount', '0'))
            tx['gift_card_loads'] = parse_decimal(stats_elem.find('GiftCardLoads').get('amount', '0'))
            tx['gift_card_redeems'] = parse_decimal(stats_elem.find('GiftCardRedeems').get('amount', '0'))
            tx['biz_account_charges'] = parse_decimal(stats_elem.find('BusinessAccountCharges').get('amount', '0'))
        else:
            tx['subtotal'] = Decimal('0')
            tx['tax_total'] = Decimal('0')
            tx['total'] = Decimal('0')
            tx['gift_card_loads'] = Decimal('0')
            tx['gift_card_redeems'] = Decimal('0')
            tx['biz_account_charges'] = Decimal('0')

        transactions.append(tx)

    return transactions


def parse_json_v3(filepath: Path) -> List[Dict[str, Any]]:
    """Parse JSON v3 transaction log format"""
    with open(filepath, 'r') as f:
        data = json.load(f)

    transactions = []
    for tx_data in data.get('transactions', []):
        tx = {
            'id': tx_data.get('tx_id'),
            'store_id': tx_data.get('store_id'),
            'device_id': tx_data.get('device_id'),
            'staff_id': tx_data.get('staff_id'),
            'timestamp': tx_data.get('timestamp'),
            'scan_num': tx_data.get('scan_num'),
            'type': tx_data.get('tx_type'),
            'status': tx_data.get('status'),
            'is_cancelled': tx_data.get('cancelled', False),
            'cancel_reason': tx_data.get('cancel_reason', ''),
            'void_reason': tx_data.get('void_reason', ''),
            'refund_reason': tx_data.get('refund_reason', ''),
            'no_sale_reason': tx_data.get('no_sale_reason', ''),
        }

        # Parse lines
        lines = []
        for line_data in tx_data.get('lines', []):
            lines.append({
                'item_code': line_data.get('item_code'),
                'variant_code': line_data.get('variant_code'),
                'description': line_data.get('desc'),
                'quantity': Decimal(str(line_data.get('qty', 0))),
                'unit_price': Decimal(str(line_data.get('price', 0))),
                'line_total': Decimal(str(line_data.get('total', 0))),
                'tax_amount': Decimal(str(line_data.get('tax', 0))),
                'department_id': line_data.get('dept_id'),
                'event_type': line_data.get('event', ''),
            })
        tx['lines'] = lines

        # Parse tenders
        tenders = []
        for tender_data in tx_data.get('tenders', []):
            tenders.append({
                'type': tender_data.get('type'),
                'amount': Decimal(str(tender_data.get('amount', 0))),
                'reference': tender_data.get('ref', ''),
            })
        tx['tenders'] = tenders

        # Parse summary
        summary = tx_data.get('summary', {})
        tx['subtotal'] = Decimal(str(summary.get('subtotal', 0)))
        tx['tax_total'] = Decimal(str(summary.get('tax_total', 0)))
        tx['total'] = Decimal(str(summary.get('total', 0)))
        tx['gift_card_loads'] = Decimal(str(summary.get('gc_loads', 0)))
        tx['gift_card_redeems'] = Decimal(str(summary.get('gc_redeems', 0)))
        tx['biz_account_charges'] = Decimal(str(summary.get('biz_charges', 0)))

        transactions.append(tx)

    return transactions


def parse_price_list_xml(filepath: Path) -> List[Dict[str, Any]]:
    """Parse BL01/BL02 price list XML (formatVersion="2.1").

    Real structure:
      <PriceList>
        <Departments><Department code="10" name="..." defaultTaxGroup="T2" minAge="0"/>...</Departments>
        <Items><Item code="200000001018" variant="000" description="..." dept="10"
                 price="2.45" taxGroup="T2" minAge="0" unit="EA" active="Y"/>...</Items>
      </PriceList>
    Returns (departments, items) tuples of rows to upsert.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    departments = []
    for dept_elem in root.findall("./Departments/Department"):
        departments.append({
            'code': dept_elem.get('code'),
            'name': dept_elem.get('name'),
            'tax_group': dept_elem.get('defaultTaxGroup'),
            'age_restriction': int(dept_elem.get('minAge', '0') or 0),
        })

    items = []
    for item_elem in root.findall("./Items/Item"):
        if item_elem.get('active', 'Y') == 'N':
            continue
        items.append({
            'item_code': item_elem.get('code'),
            'variant_code': item_elem.get('variant', '000'),
            'description': item_elem.get('description', ''),
            'department_id': int(item_elem.get('dept', '0') or 0),
            'price': parse_decimal(item_elem.get('price', '0')),
            'tax_group': item_elem.get('taxGroup'),
            'age_restriction': int(item_elem.get('minAge', '0') or 0),
        })

    return departments, items


def parse_bl01_tlog_xml(filepath: Path) -> List[Dict[str, Any]]:
    """Parse BL01/BL02 TLOG XML format (formatVersion="2.1")"""
    transactions = []
    tree = ET.parse(filepath)
    root = tree.getroot()

    for tx_elem in root.findall('Transaction'):
        tx = {
            'id': f"TXN{tx_elem.get('seq')}",
            'store_id': 1 if 'BL01' in str(filepath.name) else 2,  # BL01=store 1, BL02=store 2
            'device_id': tx_elem.get('device', ''),
            'staff_id': tx_elem.get('staff', '0') if tx_elem.get('staff') else None,
            'timestamp': tx_elem.get('start', ''),
            'scan_num': int(tx_elem.get('seq', 0)),
            'type': tx_elem.get('type', 'SALE').upper(),
            'status': 'COMPLETE' if tx_elem.get('status') == 'COMPLETED' else tx_elem.get('status', 'COMPLETE'),
            'is_cancelled': tx_elem.get('status') == 'VOID',
            'cancel_reason': '',
            'void_reason': '',
            'refund_reason': '',
            'no_sale_reason': '',
        }

        # Parse lines - per-line tax from spec rates (T0=0%, T1=8%, T2=9.5%)
        tax_rates = {'T0': Decimal('0'), 'T1': Decimal('0.08'), 'T2': Decimal('0.095')}
        lines = []
        for line_elem in tx_elem.findall('ItemLine'):
            line_total = parse_decimal(line_elem.get('amount', '0'))
            qty = parse_decimal(line_elem.get('qty', '1'))
            unit_price = parse_decimal(line_elem.get('unitPrice', '0'))
            tax_group = line_elem.get('taxGroup', 'T0')
            line_tax = (line_total * tax_rates.get(tax_group, Decimal('0'))).quantize(Decimal('0.01'))

            # Handle open-department sales: itemCode may be omitted
            item_code = line_elem.get('itemCode') or ''
            if not item_code:
                # Generate placeholder for open-department items
                dept = line_elem.get('dept') or '0'
                item_code = f"OPEN_DEPT_{dept}"
            variant_code = line_elem.get('variant', '000')

            lines.append({
                'item_code': item_code,
                'variant_code': variant_code,
                'description': line_elem.get('desc', ''),
                'quantity': str(qty),
                'unit_price': str(unit_price),
                'line_total': str(line_total),
                'tax_amount': str(line_tax),
                'department_id': int(line_elem.get('dept', '0')),
                'event_type': '',
            })
        tx['lines'] = lines

        # Get totals
        total_elem = tx_elem.find('Total')
        tax_elem = tx_elem.find('Tax')

        subtotal = parse_decimal(total_elem.get('net', '0')) if total_elem is not None else Decimal('0')
        tax_total = parse_decimal(tax_elem.get('amount', '0')) if tax_elem is not None else Decimal('0')
        total = parse_decimal(total_elem.get('total', '0')) if total_elem is not None else subtotal + tax_total

        tx['subtotal'] = subtotal
        tx['tax_total'] = tax_total
        tx['total'] = total
        tx['gift_card_loads'] = Decimal('0')
        tx['gift_card_redeems'] = Decimal('0')
        tx['biz_account_charges'] = Decimal('0')

        # Parse tenders
        tx['tenders'] = []
        for tender_elem in tx_elem.findall('Tender'):
            tx['tenders'].append({
                'type': tender_elem.get('type', 'cash').lower(),
                'amount': parse_decimal(tender_elem.get('amount', '0')),
                'reference': f"{tender_elem.get('cardType', '')}{tender_elem.get('last4', '')}" if tender_elem.get('cardType') else ''
            })

        transactions.append(tx)

    return transactions


def parse_tlog_json_v3(filepath: Path) -> List[Dict[str, Any]]:
    """Parse BL01/BL02 TLOG JSON format (formatVersion="3.0")"""
    with open(filepath, 'r') as f:
        data = json.load(f)

    # Extract store_id from filename: BL01=store 1, BL02=store 2
    store_id = 1 if 'BL01' in filepath.name else 2

    transactions = []
    for tx_data in data.get('transactions', []):
        tx_kind = tx_data.get('kind', 'sale').lower()
        tx_state = tx_data.get('state', 'completed').lower()

        # Build transaction ID with TXN prefix
        tx_id = f"TXN{tx_data.get('sequenceNo', 0)}"

        # Determine transaction type and status based on JSON v3 format spec
        # kind can be: sale, refund, cash_drop
        # state can be: completed, cancelled
        if tx_kind == 'cash_drop':
            tx_type = 'CASH_DROP'
            tx_status = 'COMPLETE'
        elif tx_kind == 'refund':
            tx_type = 'REFUND'
            tx_status = 'COMPLETE'
        else:
            tx_type = 'SALE'
            tx_status = 'COMPLETE' if tx_state == 'completed' else tx_state.upper()

        tx = {
            'id': tx_id,
            'store_id': store_id,
            'device_id': tx_data.get('terminal', ''),
            'staff_id': tx_data.get('operator', '0') if tx_data.get('operator') and tx_data.get('operator') != '0' else None,
            'timestamp': tx_data.get('startedAt', ''),
            'scan_num': tx_data.get('sequenceNo', 0),
            'type': tx_type,
            'status': tx_status,
            'is_cancelled': tx_state == 'cancelled',
            'cancel_reason': '',
            'void_reason': '',
            'refund_reason': '',
            'no_sale_reason': '',
            'refund_of': tx_data.get('refundOf', ''),  # For refund transactions
            'drop_envelope_no': None,  # For cash drops
            'drop_amount': None,  # For cash drops
        }

        # Parse cash drop info if present
        if tx_kind == 'cash_drop' and 'drop' in tx_data:
            drop = tx_data['drop']
            tx['drop_envelope_no'] = drop.get('envelopeNo')
            tx['drop_amount'] = parse_decimal(drop.get('amountMinor')) / Decimal('100')

        # Tax rates per spec: T0=0%, T1=8%, T2=9.5%
        tax_rates = {'T0': Decimal('0'), 'T1': Decimal('0.08'), 'T2': Decimal('0.095')}

        # Parse lines - amounts are in Minor (cents), convert to dollars
        lines = []
        for line_data in tx_data.get('lines', []):
            # Skip voided lines
            if line_data.get('voided', False):
                continue

            # For cash drops, skip line items (cash drops have a 'drop' object instead)
            if tx_kind == 'cash_drop':
                continue

            line_total = parse_decimal(line_data.get('extendedMinor')) / Decimal('100')
            qty = parse_decimal(line_data.get('quantity'))
            unit_price = parse_decimal(line_data.get('unitPriceMinor')) / Decimal('100')

            # Compute per-line tax from tax code rate
            tax_code = line_data.get('taxCode', 'T0')
            rate = tax_rates.get(tax_code, Decimal('0'))
            line_tax = (line_total * rate).quantize(Decimal('0.01'))

            # Handle open-department sales: item_code is null/omitted
            item_code = line_data.get('sku') or ''
            if not item_code:
                # Generate placeholder for open-department items
                dept = line_data.get('department') or '0'
                item_code = f"OPEN_DEPT_{dept}"
            variant_code = line_data.get('variant') or '000'

            lines.append({
                'item_code': item_code,
                'variant_code': variant_code,
                'description': line_data.get('text', ''),
                'quantity': str(qty),
                'unit_price': str(unit_price),
                'line_total': str(line_total),
                'tax_amount': str(line_tax),
                'department_id': int(line_data.get('department', '0')) if line_data.get('department') else 0,
                'event_type': line_data.get('lineType', ''),
            })
        tx['lines'] = lines

        # Calculate totals from the totals object
        totals = tx_data.get('totals', {})
        subtotal = parse_decimal(totals.get('netMinor')) / Decimal('100')
        tax_total = parse_decimal(totals.get('taxMinor')) / Decimal('100')
        total = parse_decimal(totals.get('grandMinor')) / Decimal('100')

        tx['subtotal'] = subtotal
        tx['tax_total'] = tax_total
        tx['total'] = total
        tx['gift_card_loads'] = Decimal('0')
        tx['gift_card_redeems'] = Decimal('0')
        tx['biz_account_charges'] = Decimal('0')

        # Parse tenders - amounts in Minor
        tx['tenders'] = []
        for tender_data in tx_data.get('payments', []):
            amount = parse_decimal(tender_data.get('amountMinor')) / Decimal('100')
            tender_type = tender_data.get('method', 'cash').lower()
            reference = ''
            account_number = None
            tendered = None
            change = None

            if tender_data.get('cardType'):
                # Card payment with cardType field
                reference = f"{tender_data.get('cardType', '')}{tender_data.get('panSuffix', '')}"
            elif tender_data.get('network'):
                # Card payment with network field
                reference = f"{tender_data.get('network', '')}{tender_data.get('panSuffix', '')}"
            elif tender_data.get('wallet'):
                # Mobile payment
                reference = tender_data.get('wallet', '')
            elif tender_data.get('accountId'):
                # Account payment - extract account number
                reference = tender_data.get('accountId', '')
                account_number = tender_data.get('accountId', '')
            elif tender_data.get('tenderedMinor') is not None:
                # Cash payment with tendered and change amounts
                tendered = Decimal(str(tender_data.get('tenderedMinor', 0))) / Decimal('100')
                change = Decimal(str(tender_data.get('changeMinor', 0))) / Decimal('100')

            tx['tenders'].append({
                'type': tender_type,
                'amount': amount,
                'reference': reference,
                'tendered': tendered,
                'change': change,
            })

            # Handle business account charges (positive amount means a charge)
            if tender_type == 'account' and amount > 0 and account_number:
                tx['biz_account_charges'] += amount
                tx['biz_account_number'] = account_number

        if 'biz_account_number' not in tx:
            tx['biz_account_number'] = None

        transactions.append(tx)

    return transactions


def process_transaction_file(filename: str, filepath: Path) -> ImportResponse:
    """Process a single transaction log file"""
    conn = get_db()
    cursor = conn.cursor()

    # Check if already imported
    cursor.execute("SELECT id FROM imports WHERE filename = ?", (filename,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return ImportResponse(
            filename=filename,
            format="unknown",
            status="skipped",
            accepted_count=0,
            skipped_count=1,
            flagged_count=0,
            reason="Already imported"
        )

    # Determine format and parse
    # Hub receipt and summary files have dedicated handlers
    if filename.startswith(('ACK_', 'REJ_')):
        conn.close()
        return record_hub_receipt(filename, filepath)
    if filename.startswith('EOD_'):
        conn.close()
        return process_eod_file(filename, filepath)
    if filename.startswith('SHIFT_'):
        conn.close()
        return process_shift_file(filename, filepath)

    try:
        if filename.endswith('.xml'):
            if '_V2' in filename:
                transactions = parse_xml_v2(filepath)
                fmt = "v2_xml"
            elif filename.startswith('PRICELIST'):
                departments, items = parse_price_list_xml(filepath)
                # Process price list
                return process_price_list(filename, filepath, departments, items)
            elif filename.startswith('TLOG_BL0'):
                transactions = parse_bl01_tlog_xml(filepath)
                fmt = "bl01_tlog"
            else:
                conn.close()
                return ImportResponse(
                    filename=filename,
                    format="unknown",
                    status="failed",
                    accepted_count=0,
                    skipped_count=0,
                    flagged_count=1,
                    reason=f"Unsupported TLOG format: {filename}"
                )
        elif filename.endswith('.json'):
            if filename.startswith('TLOG_BL0'):
                transactions = parse_tlog_json_v3(filepath)
                fmt = "tlog_json_v3"
            else:
                conn.close()
                return ImportResponse(
                    filename=filename,
                    format="unknown",
                    status="failed",
                    accepted_count=0,
                    skipped_count=0,
                    flagged_count=1,
                    reason=f"Unsupported JSON format: {filename}"
                )
        else:
            conn.close()
            return ImportResponse(
                filename=filename,
                format="unknown",
                status="failed",
                accepted_count=0,
                skipped_count=0,
                flagged_count=1,
                reason=f"Unknown format: {filename}"
            )
    except Exception as e:
        conn.close()
        return ImportResponse(
            filename=filename,
            format="unknown",
            status="failed",
            accepted_count=0,
            skipped_count=0,
            flagged_count=1,
            reason=str(e)
        )

    # Create import record
    cursor.execute("""
        INSERT INTO imports (filename, format, status, processed_at, accepted_count, skipped_count, flagged_count)
        VALUES (?, ?, 'processing', ?, 0, 0, 0)
    """, (filename, fmt, datetime.now().isoformat()))
    import_id = cursor.lastrowid
    conn.commit()

    accepted = 0
    skipped = 0
    flagged = 0

    # Ensure open-department placeholder items exist, so lines without an
    # itemCode/SKU retain a valid item reference
    placeholders = set()
    for tx in transactions:
        for line in tx.get('lines', []):
            code = line['item_code']
            if code.startswith('OPEN_DEPT_'):
                placeholders.add((code, line['variant_code'],
                                  line.get('description') or 'Open Department',
                                  line.get('department_id')))
    for code, variant, desc, dept_id in placeholders:
        cursor.execute("""
            INSERT INTO items (item_code, variant_code, description, department_id, price, tax_group)
            VALUES (?, ?, ?, ?, '0', NULL)
            ON CONFLICT(item_code, variant_code) DO NOTHING
        """, (code, variant, desc, dept_id))

    for tx in transactions:
        try:
            # Check if transaction already exists
            cursor.execute("SELECT id FROM transactions WHERE id = ?", (tx['id'],))
            if cursor.fetchone():
                skipped += 1
                continue

            # Insert transaction
            cursor.execute("""
                INSERT INTO transactions (
                    id, store_id, device_id, staff_id, tx_timestamp, scan_num,
                    type, status, is_cancelled, cancel_reason, void_reason,
                    refund_reason, no_sale_reason, subtotal, tax_total, total,
                    gift_card_loads, gift_card_redeems, biz_account_charges,
                    import_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx['id'], tx['store_id'], tx['device_id'], tx['staff_id'],
                tx['timestamp'], tx['scan_num'], tx['type'], tx['status'],
                1 if tx['is_cancelled'] else 0, tx['cancel_reason'],
                tx['void_reason'], tx['refund_reason'], tx['no_sale_reason'],
                str(tx['subtotal']), str(tx['tax_total']), str(tx['total']),
                str(tx['gift_card_loads']), str(tx['gift_card_redeems']),
                str(tx['biz_account_charges']), import_id
            ))

            # Insert transaction lines
            for line in tx.get('lines', []):
                cursor.execute("""
                    INSERT INTO transaction_lines (
                        transaction_id, item_code, variant_code, description,
                        quantity, unit_price, line_total, tax_amount,
                        department_id, event_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tx['id'], line['item_code'], line['variant_code'],
                    line['description'], str(line['quantity']),
                    str(line['unit_price']), str(line['line_total']),
                    str(line['tax_amount']), line['department_id'],
                    line['event_type']
                ))

            # Insert tenders
            for tender in tx.get('tenders', []):
                cursor.execute("""
                    INSERT INTO transaction_tenders (
                        transaction_id, type, amount, reference
                    ) VALUES (?, ?, ?, ?)
                """, (
                    tx['id'], tender['type'], str(tender['amount']),
                    tender['reference']
                ))

            # Handle business account charges - use the parsed account number,
            # and only record activity for accounts that exist in business_accounts
            if tx['biz_account_charges'] > 0:
                account_number = tx.get('biz_account_number')
                if account_number:
                    cursor.execute(
                        "SELECT 1 FROM business_accounts WHERE account_number = ?",
                        (account_number,)
                    )
                    if cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO business_account_activity (
                                account_number, transaction_id, ba_timestamp, amount, type
                            ) VALUES (?, ?, ?, ?, 'charge')
                        """, (
                            account_number, tx['id'], tx['timestamp'],
                            str(-tx['biz_account_charges'])  # Negative for charge
                        ))

            accepted += 1

        except Exception as e:
            flagged += 1
            print(f"Error processing transaction {tx['id']}: {e}")

    # Update import record
    status = "success" if flagged == 0 else "partial" if accepted > 0 else "failed"
    cursor.execute("""
        UPDATE imports SET status = ?, accepted_count = ?, skipped_count = ?, flagged_count = ?
        WHERE id = ?
    """, (status, accepted, skipped, flagged, import_id))
    conn.commit()
    conn.close()

    return ImportResponse(
        filename=filename,
        format=fmt,
        status=status,
        accepted_count=accepted,
        skipped_count=skipped,
        flagged_count=flagged
    )


def process_price_list(filename: str, filepath: Path, departments: List[Dict], items: List[Dict]) -> ImportResponse:
    """Process price list file - upsert departments and items into the database"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM imports WHERE filename = ?", (filename,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return ImportResponse(
            filename=filename,
            format="pricelist",
            status="skipped",
            accepted_count=0,
            skipped_count=1,
            flagged_count=0,
            reason="Already imported"
        )

    # Upsert departments (keyed by code, which matches items.department_id)
    for dept in departments:
        code = int(dept['code']) if dept['code'] else 0
        cursor.execute("""
            INSERT INTO departments (id, name, tax_group, age_restriction)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET name = excluded.name,
                tax_group = excluded.tax_group,
                age_restriction = excluded.age_restriction
        """, (code, dept['name'], dept['tax_group'], dept['age_restriction']))

    # Upsert items
    for item in items:
        cursor.execute("""
            INSERT INTO items (item_code, variant_code, description, department_id, price,
                               tax_group, age_restriction)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_code, variant_code) DO UPDATE SET
                description = excluded.description,
                department_id = excluded.department_id,
                price = excluded.price,
                tax_group = excluded.tax_group,
                age_restriction = excluded.age_restriction
        """, (
            item['item_code'], item['variant_code'], item['description'],
            item['department_id'], str(item['price']), item['tax_group'],
            item['age_restriction'],
        ))

    cursor.execute("""
        INSERT INTO imports (filename, format, status, processed_at, accepted_count, skipped_count, flagged_count)
        VALUES (?, 'pricelist', 'success', ?, ?, 0, 0)
    """, (filename, datetime.now().isoformat(), len(items)))
    conn.commit()
    conn.close()

    return ImportResponse(
        filename=filename,
        format="pricelist",
        status="success",
        accepted_count=len(items),
        skipped_count=0,
        flagged_count=0,
        reason=f"{len(departments)} departments, {len(items)} items upserted"
    )


def _store_code_to_id(store_code: str) -> int:
    """Map a Brightleaf store code (BL01/BL02) to its numeric store id"""
    return 1 if store_code == 'BL01' else 2


def _check_already_imported(filename: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM imports WHERE filename = ?", (filename,))
    found = cursor.fetchone() is not None
    conn.close()
    return found


def _account_charge_activity(cursor, account_number: Any, seq: Any, amount: Decimal, timestamp: str) -> None:
    """Record a business account charge if the account is known (negative amount = charge)"""
    if not account_number or amount <= 0:
        return
    cursor.execute("SELECT 1 FROM business_accounts WHERE account_number = ?", (account_number,))
    if cursor.fetchone():
        cursor.execute("""
            INSERT INTO business_account_activity (
                account_number, transaction_id, ba_timestamp, amount, type
            ) VALUES (?, ?, ?, ?, 'charge')
        """, (account_number, str(seq), timestamp, str(-amount)))


def _record_import(filename: str, fmt: str, status: str, accepted: int, reason: Optional[str] = None) -> ImportResponse:
    """Create an imports row and return the matching response"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO imports (filename, format, status, processed_at, accepted_count, skipped_count, flagged_count)
        VALUES (?, ?, ?, ?, ?, 0, 0)
    """, (filename, fmt, status, datetime.now().isoformat(), accepted))
    conn.commit()
    conn.close()
    return ImportResponse(
        filename=filename,
        format=fmt,
        status=status,
        accepted_count=accepted,
        skipped_count=0,
        flagged_count=0,
        reason=reason
    )


def process_eod_file(filename: str, filepath: Path) -> ImportResponse:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM imports WHERE filename = ?", (filename,))
    found = cursor.fetchone() is not None
    conn.close()
    return found


def _account_charge_activity(cursor, account_number: str, seq: Any, amount: Decimal, timestamp: str) -> None:
    """Record a business account charge if the account is known (negative amount = charge)"""
    if not account_number or amount <= 0:
        return
    cursor.execute("SELECT 1 FROM business_accounts WHERE account_number = ?", (account_number,))
    if cursor.fetchone():
        cursor.execute("""
            INSERT INTO business_account_activity (
                account_number, transaction_id, ba_timestamp, amount, type
            ) VALUES (?, ?, ?, ?, 'charge')
        """, (account_number, str(seq), timestamp, str(-amount)))


def process_eod_file(filename: str, filepath: Path) -> ImportResponse:
    """Import a store end-of-day report into eod_summaries (XML v2.1 or JSON endofday/3.0)"""
    if _check_already_imported(filename):
        return ImportResponse(
            filename=filename, format="eod", status="skipped",
            accepted_count=0, skipped_count=1, flagged_count=0,
            reason="Already imported"
        )

    if filename.endswith('.xml'):
        tree = ET.parse(filepath)
        root = tree.getroot()
        store_code = root.get('storeId') or 'BL01'
        s_date = root.get('businessDate') or ''
        closed = root.get('closed') or ''
        scale = Decimal('1')

        totals = root.find('Totals')
        reported_total_sales = parse_decimal(totals.get('netSales')) if totals is not None else Decimal('0')
        reported_total_tax = parse_decimal(totals.get('tax')) if totals is not None else Decimal('0')
        reported_transaction_count = int(totals.get('transactions', '0')) if totals is not None else 0

        cash_drops_elem = root.find('CashDrops')
        cash_drops = parse_decimal(cash_drops_elem.get('amount')) if cash_drops_elem is not None else Decimal('0')

        charges = []
        charges_elem = root.find('AccountCharges')
        if charges_elem is not None:
            for c in charges_elem.findall('Charge'):
                charges.append((c.get('account', ''), c.get('seq', ''), parse_decimal(c.get('amount'))))
    else:
        data = json.loads(filepath.read_text(encoding='utf-8'))
        store_code = data.get('store') or 'BL01'
        s_date = data.get('businessDay') or ''
        closed = data.get('closedAt') or ''
        scale = Decimal('100')

        totals = data.get('totals') or {}
        reported_total_sales = parse_decimal(totals.get('netMinor')) / scale
        reported_total_tax = parse_decimal(totals.get('taxMinor')) / scale
        reported_transaction_count = int(parse_decimal(totals.get('transactions')))

        drops = data.get('cashDrops') or {}
        cash_drops = parse_decimal(drops.get('amountMinor')) / scale

        charges = [
            (c.get('accountId', ''), c.get('sequenceNo', ''), parse_decimal(c.get('amountMinor')) / scale)
            for c in (data.get('accountCharges') or [])
        ]

    store_id = _store_code_to_id(store_code)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO imports (filename, format, status, processed_at, accepted_count, skipped_count, flagged_count)
        VALUES (?, 'eod', 'success', ?, 1, 0, 0)
    """, (filename, datetime.now().isoformat()))
    import_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO eod_summaries (
            store_id, s_date, reported_total_sales, reported_total_tax,
            reported_transaction_count, opening_float, counted_cash, cash_drops, import_id
        ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
        ON CONFLICT(store_id, s_date) DO UPDATE SET
            reported_total_sales = excluded.reported_total_sales,
            reported_total_tax = excluded.reported_total_tax,
            reported_transaction_count = excluded.reported_transaction_count,
            cash_drops = excluded.cash_drops,
            import_id = excluded.import_id
    """, (store_id, s_date, str(reported_total_sales), str(reported_total_tax),
          reported_transaction_count, str(cash_drops), import_id))

    for account_number, seq, amount in charges:
        _account_charge_activity(cursor, account_number, seq, amount, closed)

    conn.commit()
    conn.close()
    return ImportResponse(
        filename=filename, format="eod", status="success",
        accepted_count=1, skipped_count=0, flagged_count=0,
        reason=f"{store_code} {s_date}: {reported_transaction_count} transactions, "
               f"net sales {reported_total_sales}"
    )


def process_shift_file(filename: str, filepath: Path) -> ImportResponse:
    """Import a store shift close report into shift_summaries (XML v2.1 or JSON shift/3.0)"""
    if _check_already_imported(filename):
        return ImportResponse(
            filename=filename, format="shift", status="skipped",
            accepted_count=0, skipped_count=1, flagged_count=0,
            reason="Already imported"
        )

    if filename.endswith('.xml'):
        tree = ET.parse(filepath)
        root = tree.getroot()
        store_code = root.get('storeId') or 'BL01'
        s_date = root.get('businessDate') or ''
        shift_num = int(root.get('shiftNo', '0'))
        closed = root.get('closed') or ''
        scale = Decimal('1')

        # Reported sales for the shift: all tenders, excluding gift-card loads
        reported_total_sales = Decimal('0')
        tenders_elem = root.find('Tenders')
        if tenders_elem is not None:
            for t in tenders_elem.findall('Tender'):
                if t.get('type', '').upper() != 'GIFT':
                    reported_total_sales += parse_decimal(t.get('amount'))

        cash_drops_elem = root.find('CashDrops')
        cash_drops = parse_decimal(cash_drops_elem.get('amount')) if cash_drops_elem is not None else Decimal('0')

        cash_elem = root.find('Cash')
        opening_float = parse_decimal(cash_elem.get('openingFloat')) if cash_elem is not None else None
        counted_cash = parse_decimal(cash_elem.get('countedCash')) if cash_elem is not None else None

        charges = []
        charges_elem = root.find('AccountCharges')
        if charges_elem is not None:
            for c in charges_elem.findall('Charge'):
                charges.append((c.get('account', ''), c.get('seq', ''), parse_decimal(c.get('amount'))))
    else:
        data = json.loads(filepath.read_text(encoding='utf-8'))
        store_code = data.get('store') or 'BL01'
        s_date = data.get('businessDay') or ''
        shift_num = int(parse_decimal(data.get('shiftNo')))
        closed = data.get('closedAt') or ''
        scale = Decimal('100')

        reported_total_sales = Decimal('0')
        for p in data.get('payments') or []:
            if p.get('method', 'cash').lower() != 'gift':
                reported_total_sales += parse_decimal(p.get('amountMinor')) / scale

        drops = data.get('cashDrops') or {}
        cash_drops = parse_decimal(drops.get('amountMinor')) / scale

        cash = data.get('cash') or {}
        opening_float = (parse_decimal(cash.get('openingFloatMinor')) / scale
                         if cash.get('openingFloatMinor') is not None else None)
        counted_cash = (parse_decimal(cash.get('countedMinor')) / scale
                        if cash.get('countedMinor') is not None else None)

        charges = [
            (c.get('accountId', ''), c.get('sequenceNo', ''), parse_decimal(c.get('amountMinor')) / scale)
            for c in (data.get('accountCharges') or [])
        ]

    store_id = _store_code_to_id(store_code)
    # Summary row id: store code + business day + shift number, stable across re-imports
    row_id = f"{store_code}_{s_date}_{shift_num}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO imports (filename, format, status, processed_at, accepted_count, skipped_count, flagged_count)
        VALUES (?, 'shift', 'success', ?, 1, 0, 0)
    """, (filename, datetime.now().isoformat()))
    import_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO shift_summaries (
            id, store_id, s_date, shift_num, start_time, end_time,
            reported_total_sales, reported_total_tax, opening_float, counted_cash, cash_drops, import_id
        ) VALUES (?, ?, ?, ?, NULL, ?, ?, NULL, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            end_time = excluded.end_time,
            reported_total_sales = excluded.reported_total_sales,
            opening_float = excluded.opening_float,
            counted_cash = excluded.counted_cash,
            cash_drops = excluded.cash_drops,
            import_id = excluded.import_id
    """, (row_id, store_id, s_date, shift_num, closed,
          str(reported_total_sales),
          str(opening_float) if opening_float is not None else None,
          str(counted_cash) if counted_cash is not None else None,
          str(cash_drops), import_id))

    for account_number, seq, amount in charges:
        _account_charge_activity(cursor, account_number, seq, amount, closed)

    conn.commit()
    conn.close()
    return ImportResponse(
        filename=filename, format="shift", status="success",
        accepted_count=1, skipped_count=0, flagged_count=0,
        reason=f"{store_code} shift {shift_num} on {s_date}: sales {reported_total_sales}"
    )


def record_hub_receipt(filename: str, filepath: Path) -> ImportResponse:
    """Record an ACK/REJ receipt for a hub price change into price_changes"""
    if _check_already_imported(filename):
        return ImportResponse(
            filename=filename, format="hub_receipt", status="skipped",
            accepted_count=0, skipped_count=1, flagged_count=0,
            reason="Already imported"
        )

    tree = ET.parse(filepath)
    root = tree.getroot()

    if root.tag == 'ChangeAck':
        change_id = root.get('changeId') or ''
        result = (root.get('result') or 'APPLIED').upper()
        processed = root.get('processed') or datetime.now().isoformat()
        status = 'Applied' if result == 'APPLIED' else result
        reason = None
    elif root.tag == 'ChangeReject':
        change_id = root.get('changeId') or ''
        result = (root.get('result') or 'REJECTED').upper()
        processed = root.get('processed') or datetime.now().isoformat()
        status = 'Rejected'
        reason = root.get('message') or root.get('errorCode')

    else:
        # Hub-generated receipts use <Acknowledgement>/<Rejection> elements
        change_id = root.get('change_id') or root.get('changeId') or ''
        if root.tag == 'Rejection':
            status = 'Rejected'
            reason = root.get('reason')
            processed = root.get('timestamp') or datetime.now().isoformat()
        else:
            status = 'Applied'
            reason = None
            processed = root.get('timestamp') or datetime.now().isoformat()

    conn = get_db()
    cursor = conn.cursor()
    # Mark the matching hub price change as processed, if one exists
    cursor.execute("""
        UPDATE price_changes
        SET status = ?, pc_processed_at = ?
        WHERE change_id = ? AND pc_processed_at IS NULL
    """, (status, processed, change_id))
    conn.commit()
    conn.close()
    return _record_import(filename, "hub_receipt", "success", 1,
                          f"{change_id}: {status}" + (f" ({reason})" if reason else ""))


@router.get("/files")
async def list_outbox_files():
    """List all files in outbox directory"""
    files = []
    for f in OUTBOX_DIR.iterdir():
        if f.is_file():
            stat = f.stat()
            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    return {"files": sorted(files, key=lambda x: x['filename'])}


@router.post("/import/{filename}")
async def import_file(filename: str, background_tasks: BackgroundTasks):
    """Import a single file from outbox"""
    filepath = OUTBOX_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    result = process_transaction_file(filename, filepath)
    return result


@router.post("/import-all")
async def import_all_files(background_tasks: BackgroundTasks):
    """Import all files from outbox"""
    results = []
    for f in sorted(OUTBOX_DIR.iterdir()):
        if f.is_file() and not f.name.startswith('.'):
            result = process_transaction_file(f.name, f)
            results.append(result.dict())
    return {"results": results}