"""Hub Simulator module - simulates central hub communication"""
import os
import xml.etree.ElementTree as ET
import json
import threading
import time
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
INBOX_DIR = DATA_PACKAGE_DIR / "inbox"
OUTBOX_DIR = DATA_PACKAGE_DIR / "outbox"

# Hub simulator state
hub_state = {
    "running": False,
    "interval_seconds": 30,
    "last_run": None,
    "thread": None
}


class HubConfig(BaseModel):
    interval_seconds: int = 30
    auto_process: bool = True


class HubStatus(BaseModel):
    running: bool
    interval_seconds: int
    last_run: Optional[str]
    inbox_files: int
    outbox_files: int


def simulate_hub_cycle():
    """Single hub processing cycle - processes inbox, generates outbox"""
    results = {
        "cycle_time": datetime.now().isoformat(),
        "processed_files": [],
        "generated_files": [],
        "errors": []
    }

    try:
        # 1. Process price change requests from stores
        for filepath in INBOX_DIR.glob("PRICE_CHANGE_*.xml"):
            try:
                process_price_change_file(filepath)
                results["processed_files"].append(filepath.name)
            except Exception as e:
                results["errors"].append(f"Price change {filepath.name}: {str(e)}")

        # 2. Process invoice submissions from stores
        for filepath in INBOX_DIR.glob("INVOICE_*.xml"):
            try:
                process_invoice_file(filepath)
                results["processed_files"].append(filepath.name)
            except Exception as e:
                results["errors"].append(f"Invoice {filepath.name}: {str(e)}")

        # 3. Generate price list updates for stores
        price_list_file = generate_price_list_update()
        if price_list_file:
            results["generated_files"].append(price_list_file)

        # 4. Generate ACK/REJ for pending price changes
        ack_files = generate_ack_rej_files()
        results["generated_files"].extend(ack_files)

        # 5. Generate new price change instructions for stores
        new_changes = generate_new_price_changes()
        results["generated_files"].extend(new_changes)

    except Exception as e:
        results["errors"].append(f"Hub cycle error: {str(e)}")

    hub_state["last_run"] = datetime.now().isoformat()
    return results


def process_price_change_file(filepath: Path):
    """Process a price change request file from store"""
    tree = ET.parse(filepath)
    root = tree.getroot()

    for change_elem in root.findall('Change'):
        item_code = change_elem.get('item_code')
        variant_code = change_elem.get('variant_code', 'DEFAULT')
        requested_price = change_elem.get('new_price')
        store_id = change_elem.get('store_id', '1')
        change_id = change_elem.get('change_id', f"HUB_{datetime.now().strftime('%Y%m%d%H%M%S')}")

        # In real hub, this would go through approval workflow
        # For simulator, auto-approve and send ACK
        conn = get_db()
        cursor = conn.cursor()

        # Get current price
        cursor.execute("""
            SELECT price FROM items WHERE item_code = ? AND variant_code = ?
        """, (item_code, variant_code))
        row = cursor.fetchone()
        conn.close()

        old_price = row[0] if row else "0.00"

        # Generate ACK
        ack_root = ET.Element('Acknowledgement', attrib={
            'change_id': change_id,
            'original_change_id': change_elem.get('change_id', ''),
            'status': 'APPLIED',
            'timestamp': datetime.now().isoformat(),
            'hub_id': 'HUB001'
        })
        ET.SubElement(ack_root, 'Item', attrib={
            'item_code': item_code,
            'variant_code': variant_code,
            'old_price': old_price,
            'new_price': requested_price,
            'effective_date': datetime.now().strftime('%Y-%m-%d')
        })

        from xml.dom import minidom
        rough = ET.tostring(ack_root, encoding='unicode')
        reparsed = minidom.parseString(rough)
        pretty = reparsed.toprettyxml(indent="  ")

        ack_filename = f"ACK_{change_id}.xml"
        with open(OUTBOX_DIR / ack_filename, 'w') as f:
            f.write(pretty)

        # Archive processed file
        filepath.rename(INBOX_DIR / f"PROCESSED_{filepath.name}")


def process_invoice_file(filepath: Path):
    """Process invoice submission from store"""
    # In real implementation, would validate and forward to finance
    filepath.rename(INBOX_DIR / f"PROCESSED_{filepath.name}")


def generate_price_list_update() -> Optional[str]:
    """Generate updated price list for distribution to stores"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            i.item_code, i.variant_code, i.description,
            i.department_id, d.name as department_name,
            i.price, i.tax_group, i.age_restriction
        FROM items i
        JOIN departments d ON i.department_id = d.id
        ORDER BY d.id, i.item_code, i.variant_code
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    root = ET.Element('PriceList', attrib={
        'version': '2',
        'export_time': datetime.now().isoformat(),
        'source': 'Central Hub',
        'hub_id': 'HUB001',
        'sequence': str(int(time.time()))
    })

    dept_items = {}
    for row in rows:
        dept_id = row[3]
        if dept_id not in dept_items:
            dept_items[dept_id] = {
                'name': row[4],
                'items': []
            }
        dept_items[dept_id]['items'].append({
            'item_code': row[0],
            'variant_code': row[1],
            'description': row[2],
            'price': row[5],
            'tax_group': row[6],
            'age_restriction': str(bool(row[7])).lower()
        })

    for dept_id, dept_data in dept_items.items():
        dept_elem = ET.SubElement(root, 'Department', attrib={
            'id': str(dept_id),
            'name': dept_data['name']
        })
        for item in dept_data['items']:
            ET.SubElement(dept_elem, 'Item', attrib=item)

    from xml.dom import minidom
    rough = ET.tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough)
    pretty = reparsed.toprettyxml(indent="  ")

    filename = f"PRICELIST_HUB_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
    with open(OUTBOX_DIR / filename, 'w') as f:
        f.write(pretty)

    return filename


def generate_ack_rej_files() -> List[str]:
    """Generate ACK/REJ files for pending price changes"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT change_id, item_code, variant_code, old_price, new_price, status, reason
        FROM price_changes
        WHERE status IN ('Applied', 'Rejected') AND pc_processed_at IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()

    generated = []

    for row in rows:
        change_id, item_code, variant_code, old_price, new_price, status, reason = row

        # Check if ACK/REJ already sent (simple check by filename)
        ack_file = OUTBOX_DIR / f"ACK_{change_id}.xml"
        rej_file = OUTBOX_DIR / f"REJ_{change_id}.xml"

        if ack_file.exists() or rej_file.exists():
            continue

        if status == 'Applied':
            root = ET.Element('Acknowledgement', attrib={
                'change_id': change_id,
                'status': 'APPLIED',
                'timestamp': datetime.now().isoformat(),
                'hub_id': 'HUB001'
            })
            ET.SubElement(root, 'Item', attrib={
                'item_code': item_code,
                'variant_code': variant_code,
                'old_price': old_price,
                'new_price': new_price
            })
            filename = f"ACK_{change_id}.xml"
        else:
            root = ET.Element('Rejection', attrib={
                'change_id': change_id,
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'hub_id': 'HUB001'
            })
            ET.SubElement(root, 'Item', attrib={
                'item_code': item_code,
                'variant_code': variant_code,
                'requested_price': new_price
            })
            filename = f"REJ_{change_id}.xml"

        from xml.dom import minidom
        rough = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough)
        pretty = reparsed.toprettyxml(indent="  ")

        with open(OUTBOX_DIR / filename, 'w') as f:
            f.write(pretty)

        generated.append(filename)

    return generated


def generate_new_price_changes() -> List[str]:
    """Generate new price change instructions from hub to stores"""
    # In real implementation, hub would send periodic price updates
    # For simulator, occasionally create random price changes
    import random

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT item_code, variant_code, price FROM items
        ORDER BY RANDOM() LIMIT 3
    """)
    rows = cursor.fetchall()
    conn.close()

    generated = []

    for row in rows:
        item_code, variant_code, current_price = row

        # 30% chance to generate a change
        if random.random() > 0.7:
            # Small price adjustment (-5% to +5%)
            current = Decimal(current_price)
            adjustment = Decimal(str(random.uniform(-0.05, 0.05)))
            new_price = current * (Decimal('1') + adjustment)
            new_price = str(round(new_price, 2))

            if new_price != current_price:
                change_id = f"HUB_CHG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100, 999)}"

                root = ET.Element('PriceChange', attrib={
                    'change_id': change_id,
                    'source': 'HUB',
                    'priority': 'NORMAL',
                    'effective_date': datetime.now().strftime('%Y-%m-%d'),
                    'timestamp': datetime.now().isoformat()
                })
                ET.SubElement(root, 'Change', attrib={
                    'item_code': item_code,
                    'variant_code': variant_code,
                    'old_price': current_price,
                    'new_price': new_price,
                    'reason': 'Hub price optimization'
                })

                from xml.dom import minidom
                rough = ET.tostring(root, encoding='unicode')
                reparsed = minidom.parseString(rough)
                pretty = reparsed.toprettyxml(indent="  ")

                filename = f"PRICE_CHANGE_{change_id}.xml"
                with open(OUTBOX_DIR / filename, 'w') as f:
                    f.write(pretty)

                generated.append(filename)

    return generated


def hub_worker():
    """Background worker that runs hub cycles"""
    while hub_state["running"]:
        try:
            simulate_hub_cycle()
        except Exception as e:
            print(f"Hub worker error: {e}")

        time.sleep(hub_state["interval_seconds"])


@router.get("/status", response_model=HubStatus)
async def get_hub_status():
    """Get hub simulator status"""
    inbox_count = len(list(INBOX_DIR.glob("*")))
    outbox_count = len(list(OUTBOX_DIR.glob("*")))

    return HubStatus(
        running=hub_state["running"],
        interval_seconds=hub_state["interval_seconds"],
        last_run=hub_state["last_run"],
        inbox_files=inbox_count,
        outbox_files=outbox_count
    )


@router.post("/start")
async def start_hub(config: HubConfig):
    """Start the hub simulator"""
    if hub_state["running"]:
        raise HTTPException(status_code=400, detail="Hub already running")

    hub_state["interval_seconds"] = config.interval_seconds
    hub_state["running"] = True
    hub_state["thread"] = threading.Thread(target=hub_worker, daemon=True)
    hub_state["thread"].start()

    return {"message": "Hub simulator started", "interval_seconds": config.interval_seconds}


@router.post("/stop")
async def stop_hub():
    """Stop the hub simulator"""
    hub_state["running"] = False
    if hub_state["thread"]:
        hub_state["thread"].join(timeout=5)
        hub_state["thread"] = None

    return {"message": "Hub simulator stopped"}


@router.post("/cycle")
async def run_single_cycle():
    """Run a single hub processing cycle manually"""
    results = simulate_hub_cycle()
    return results


@router.get("/inbox-files")
async def list_inbox_files():
    """List files in inbox directory"""
    files = []
    for filepath in INBOX_DIR.glob("*"):
        if filepath.is_file():
            stat = filepath.stat()
            files.append({
                "name": filepath.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    return {"files": files}


@router.get("/outbox-files")
async def list_outbox_files():
    """List files in outbox directory"""
    files = []
    for filepath in OUTBOX_DIR.glob("*"):
        if filepath.is_file():
            stat = filepath.stat()
            files.append({
                "name": filepath.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    return {"files": files}


@router.get("/outbox-file/{filename}")
async def get_outbox_file(filename: str):
    """Get content of an outbox file"""
    filepath = OUTBOX_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    with open(filepath, 'r') as f:
        content = f.read()

    return {"filename": filename, "content": content}


@router.post("/simulate-store-submission")
async def simulate_store_submission(store_id: int = 1):
    """Simulate a store submitting transaction logs and price change requests"""
    import random

    results = {"transaction_log": None, "price_changes": []}

    # Generate a transaction log (XML v2 or JSON v3)
    if random.random() > 0.5:
        # XML v2
        filename = f"TLOG_S{store_id:03d}_{datetime.now().strftime('%Y%m%d%H%M%S')}_v2.xml"
        root = ET.Element('TransactionLog', attrib={
            'version': '2',
            'store_id': str(store_id),
            'device_id': '1',
            'timestamp': datetime.now().isoformat()
        })
        ET.SubElement(root, 'Transaction', attrib={
            'id': f"TXN{random.randint(100000, 999999)}",
            'type': 'SALE',
            'total': str(round(random.uniform(10, 200), 2)),
            'tax_total': str(round(random.uniform(1, 40), 2)),
            'timestamp': datetime.now().isoformat()
        })

        from xml.dom import minidom
        rough = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough)
        pretty = reparsed.toprettyxml(indent="  ")

        with open(INBOX_DIR / filename, 'w') as f:
            f.write(pretty)
        results["transaction_log"] = filename
    else:
        # JSON v3
        filename = f"TLOG_S{store_id:03d}_{datetime.now().strftime('%Y%m%d%H%M%S')}_v3.json"
        data = {
            "version": "3",
            "store_id": store_id,
            "device_id": 1,
            "timestamp": datetime.now().isoformat(),
            "transactions": [{
                "id": f"TXN{random.randint(100000, 999999)}",
                "type": "SALE",
                "total": round(random.uniform(10, 200), 2),
                "tax_total": round(random.uniform(1, 40), 2),
                "timestamp": datetime.now().isoformat()
            }]
        }
        with open(INBOX_DIR / filename, 'w') as f:
            json.dump(data, f, indent=2)
        results["transaction_log"] = filename

    # Generate random price change requests
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_code, variant_code, price FROM items ORDER BY RANDOM() LIMIT 2")
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        item_code, variant_code, current_price = row
        current = Decimal(current_price)
        adjustment = Decimal(str(random.uniform(-0.10, 0.10)))
        new_price = current * (Decimal('1') + adjustment)
        new_price = str(round(new_price, 2))

        if new_price != current_price:
            change_id = f"STORE{store_id}_CHG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100, 999)}"

            root = ET.Element('PriceChangeRequest', attrib={
                'version': '2',
                'store_id': str(store_id),
                'timestamp': datetime.now().isoformat()
            })
            ET.SubElement(root, 'Change', attrib={
                'change_id': change_id,
                'item_code': item_code,
                'variant_code': variant_code,
                'old_price': current_price,
                'new_price': new_price,
                'reason': 'Store requested price adjustment'
            })

            from xml.dom import minidom
            rough = ET.tostring(root, encoding='unicode')
            reparsed = minidom.parseString(rough)
            pretty = reparsed.toprettyxml(indent="  ")

            filename = f"PRICE_CHANGE_{change_id}.xml"
            with open(INBOX_DIR / filename, 'w') as f:
                f.write(pretty)

            results["price_changes"].append(filename)

    return results