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

OUTBOX_DIR = Path(__file__).parent.parent.parent.parent / "outbox"


class ImportResponse(BaseModel):
    filename: str
    format: str
    status: str
    accepted_count: int
    skipped_count: int
    flagged_count: int
    reason: Optional[str] = None


def parse_decimal(value: str) -> Decimal:
    """Parse string to Decimal, handling empty strings"""
    if not value or value.strip() == '':
        return Decimal('0')
    return Decimal(value)


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
        for line_data in tx_data.get('items', []):
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
    """Parse price list XML v2 format"""
    items = []
    tree = ET.parse(filepath)
    root = tree.getroot()

    for dept_elem in root.findall('Department'):
        dept_id = int(dept_elem.get('id'))
        for item_elem in dept_elem.findall('Item'):
            items.append({
                'item_code': item_elem.get('item_code'),
                'variant_code': item_elem.get('variant_code'),
                'description': item_elem.get('description'),
                'price': parse_decimal(item_elem.get('price')),
                'tax_group': item_elem.get('tax_group'),
                'age_restriction': item_elem.get('age_restriction', 'false').lower() == 'true',
                'department_id': dept_id,
            })

    return items


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
    try:
        if filename.endswith('.xml') and '_V2' in filename:
            transactions = parse_xml_v2(filepath)
            fmt = "v2_xml"
        elif filename.endswith('.json') and '_V3' in filename:
            transactions = parse_json_v3(filepath)
            fmt = "v3_json"
        elif filename.startswith('PRICELIST'):
            items = parse_price_list_xml(filepath)
            # Process price list
            return process_price_list(filename, filepath, items)
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

            # Handle business account charges
            if tx['biz_account_charges'] > 0:
                cursor.execute("""
                    INSERT INTO business_account_activity (
                        account_number, transaction_id, ba_timestamp, amount, type
                    ) VALUES (?, ?, ?, ?, 'charge')
                """, (
                    'ACC001', tx['id'], tx['timestamp'],
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


def process_price_list(filename: str, filepath: Path, items: List[Dict]) -> ImportResponse:
    """Process price list file"""
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

    cursor.execute("""
        INSERT INTO imports (filename, format, status, processed_at, accepted_count)
        VALUES (?, 'pricelist', 'success', ?, ?)
    """, (filename, datetime.now().isoformat(), len(items)))
    conn.commit()
    conn.close()

    return ImportResponse(
        filename=filename,
        format="pricelist",
        status="success",
        accepted_count=len(items),
        skipped_count=0,
        flagged_count=0
    )


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