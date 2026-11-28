"""Pricing module - handles price changes, approvals, and price lists"""
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.db import get_db

router = APIRouter()

# Data package lives at <assignment root>/data_package_extracted/data_package (4 levels up)
DATA_PACKAGE_DIR = Path(__file__).parent.parent.parent.parent / "data_package_extracted" / "data_package"
INBOX_DIR = DATA_PACKAGE_DIR / "inbox"
OUTBOX_DIR = DATA_PACKAGE_DIR / "outbox"


class PriceChangeRequest(BaseModel):
    item_code: str
    variant_code: str
    new_price: str
    reason: str


class PriceChangeResponse(BaseModel):
    change_id: str
    item_code: str
    variant_code: str
    old_price: str
    new_price: str
    status: str
    reason: str
    created_at: str
    processed_at: Optional[str] = None


class PriceListItem(BaseModel):
    item_code: str
    variant_code: str
    description: str
    department_id: int
    department_name: str
    price: str
    tax_group: str
    age_restriction: bool


def generate_change_id() -> str:
    """Generate unique change ID"""
    return f"CHG{datetime.now().strftime('%Y%m%d%H%M%S')}"


@router.get("/price-list", response_model=List[PriceListItem])
async def get_price_list():
    """Get current price list from database"""
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

    return [
        PriceListItem(
            item_code=row[0],
            variant_code=row[1],
            description=row[2],
            department_id=row[3],
            department_name=row[4],
            price=row[5],
            tax_group=row[6],
            age_restriction=bool(row[7])
        )
        for row in rows
    ]


@router.post("/price-changes", response_model=PriceChangeResponse)
async def create_price_change(request: PriceChangeRequest):
    """Create a new price change request"""
    conn = get_db()
    cursor = conn.cursor()

    # Get current price
    cursor.execute("""
        SELECT price FROM items
        WHERE item_code = ? AND variant_code = ?
    """, (request.item_code, request.variant_code))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    old_price = row[0]
    change_id = generate_change_id()

    # Insert price change record
    cursor.execute("""
        INSERT INTO price_changes (change_id, item_code, variant_code, old_price, new_price, status, reason)
        VALUES (?, ?, ?, ?, ?, 'Pending', ?)
    """, (change_id, request.item_code, request.variant_code, old_price, request.new_price, request.reason))
    conn.commit()
    conn.close()

    return PriceChangeResponse(
        change_id=change_id,
        item_code=request.item_code,
        variant_code=request.variant_code,
        old_price=old_price,
        new_price=request.new_price,
        status="Pending",
        reason=request.reason,
        created_at=datetime.now().isoformat()
    )


@router.get("/price-changes", response_model=List[PriceChangeResponse])
async def get_price_changes(
    status: Optional[str] = None
):
    """Get all price changes"""
    conn = get_db()
    cursor = conn.cursor()

    if status:
        cursor.execute("""
            SELECT change_id, item_code, variant_code, old_price, new_price, status, reason, pc_created_at, pc_processed_at
            FROM price_changes
            WHERE status = ?
            ORDER BY pc_created_at DESC
        """, (status,))
    else:
        cursor.execute("""
            SELECT change_id, item_code, variant_code, old_price, new_price, status, reason, pc_created_at, pc_processed_at
            FROM price_changes
            ORDER BY pc_created_at DESC
        """)

    rows = cursor.fetchall()
    conn.close()

    return [
        PriceChangeResponse(
            change_id=row[0],
            item_code=row[1],
            variant_code=row[2],
            old_price=row[3],
            new_price=row[4],
            status=row[5],
            reason=row[6],
            created_at=row[7],
            processed_at=row[8]
        )
        for row in rows
    ]


@router.post("/price-changes/{change_id}/approve")
async def approve_price_change(change_id: str):
    """Approve and apply a price change"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT item_code, variant_code, new_price FROM price_changes WHERE change_id = ?
    """, (change_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Price change not found")

    item_code, variant_code, new_price = row

    # Update item price
    cursor.execute("""
        UPDATE items SET price = ? WHERE item_code = ? AND variant_code = ?
    """, (new_price, item_code, variant_code))

    # Update price change status
    cursor.execute("""
        UPDATE price_changes SET status = 'Applied', pc_processed_at = ? WHERE change_id = ?
    """, (datetime.now().isoformat(), change_id))

    conn.commit()
    conn.close()

    return {"message": "Price change approved and applied", "change_id": change_id}


@router.post("/price-changes/{change_id}/reject")
async def reject_price_change(change_id: str, reason: str = "Rejected"):
    """Reject a price change"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE price_changes SET status = 'Rejected', pc_processed_at = ?, reason = ? WHERE change_id = ?
    """, (datetime.now().isoformat(), reason, change_id))

    conn.commit()
    conn.close()

    return {"message": "Price change rejected", "change_id": change_id}


@router.post("/export-price-list")
async def export_price_list():
    """Export current price list to XML v2 format for hub"""
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

    # Create XML
    root = ET.Element('PriceList', attrib={
        'version': '2',
        'export_time': datetime.now().isoformat(),
        'source': 'Brightleaf Retail Platform'
    })

    # Group by department
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

    # Pretty print
    from xml.dom import minidom
    rough_string = ET.tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # Save to outbox
    filename = f"PRICELIST_BRIGHTLEAF_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
    filepath = OUTBOX_DIR / filename
    with open(filepath, 'w') as f:
        f.write(pretty_xml)

    return {"message": "Price list exported", "filename": filename, "path": str(filepath)}


@router.post("/process-inbox-price-changes")
async def process_inbox_price_changes():
    """Process price change files from inbox"""
    results = []

    for filepath in INBOX_DIR.glob("PRICE_CHANGE_*.xml"):
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            for change_elem in root.findall('Change'):
                item_code = change_elem.get('item_code')
                variant_code = change_elem.get('variant_code')
                new_price = change_elem.get('new_price')
                reason = change_elem.get('reason', 'Price update from hub')

                # Create price change request
                conn = get_db()
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT price FROM items
                    WHERE item_code = ? AND variant_code = ?
                """, (item_code, variant_code))
                row = cursor.fetchone()

                if row:
                    old_price = row[0]
                    change_id = generate_change_id()

                    cursor.execute("""
                        INSERT INTO price_changes (change_id, item_code, variant_code, old_price, new_price, status, reason)
                        VALUES (?, ?, ?, ?, ?, 'Pending', ?)
                    """, (change_id, item_code, variant_code, old_price, new_price, reason))
                    conn.commit()

                    results.append({
                        "change_id": change_id,
                        "item_code": item_code,
                        "variant_code": variant_code,
                        "old_price": old_price,
                        "new_price": new_price,
                        "status": "Pending",
                        "source_file": filepath.name
                    })
                else:
                    results.append({
                        "item_code": item_code,
                        "variant_code": variant_code,
                        "status": "Error",
                        "reason": "Item not found",
                        "source_file": filepath.name
                    })

                conn.close()

            # Move processed file to archive
            archive_name = f"PROCESSED_{filepath.name}"
            filepath.rename(INBOX_DIR / archive_name)

        except Exception as e:
            results.append({
                "file": filepath.name,
                "status": "Error",
                "reason": str(e)
            })

    return {"results": results}


@router.post("/send-ack/{change_id}")
async def send_acknowledgement(change_id: str, status: str = "APPLIED"):
    """Send ACK/REJ file to outbox for hub"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT item_code, variant_code, old_price, new_price, status as pc_status, reason
        FROM price_changes WHERE change_id = ?
    """, (change_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Price change not found")

    item_code, variant_code, old_price, new_price, pc_status, reason = row

    if status == "APPLIED":
        # Create ACK XML
        root = ET.Element('Acknowledgement', attrib={
            'change_id': change_id,
            'status': 'APPLIED',
            'timestamp': datetime.now().isoformat()
        })
        ET.SubElement(root, 'Item', attrib={
            'item_code': item_code,
            'variant_code': variant_code,
            'old_price': old_price,
            'new_price': new_price
        })
        filename = f"ACK_{change_id}.xml"
    else:
        # Create REJ XML
        root = ET.Element('Rejection', attrib={
            'change_id': change_id,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        ET.SubElement(root, 'Item', attrib={
            'item_code': item_code,
            'variant_code': variant_code,
            'requested_price': new_price
        })
        filename = f"REJ_{change_id}.xml"

    from xml.dom import minidom
    rough_string = ET.tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    filepath = OUTBOX_DIR / filename
    with open(filepath, 'w') as f:
        f.write(pretty_xml)

    return {"message": f"{status} file created", "filename": filename}