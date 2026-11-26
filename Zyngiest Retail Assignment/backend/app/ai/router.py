"""AI module - handles invoice processing and OCR"""
import os
import json
import base64
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel

from database.db import get_db

router = APIRouter()

INBOX_DIR = Path(__file__).parent.parent.parent.parent / "inbox"
OUTBOX_DIR = Path(__file__).parent.parent.parent.parent / "outbox"


class InvoiceItem(BaseModel):
    line_number: int
    description: str
    quantity: float
    unit_price: str
    line_total: str
    tax_group: str
    tax_amount: str
    department: str


class InvoiceData(BaseModel):
    invoice_number: str
    supplier: str
    invoice_date: str
    due_date: str
    subtotal: str
    tax_total: str
    grand_total: str
    currency: str
    items: List[InvoiceItem]
    raw_text: Optional[str] = None


class InvoiceProcessingResult(BaseModel):
    invoice_id: str
    status: str
    extracted_data: Optional[InvoiceData] = None
    errors: List[str] = []
    confidence: float = 0.0


# Mock AI processing - in production, this would use actual OCR/ML models
def mock_extract_invoice_data(file_content: bytes, filename: str) -> InvoiceProcessingResult:
    """Mock invoice extraction - simulates AI/OCR processing"""
    import random

    # Simulate processing delay
    invoice_id = f"INV_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

    # Simulate different extraction results based on filename
    if 'pdf' in filename.lower():
        # Simulate PDF processing
        mock_items = [
            InvoiceItem(
                line_number=1,
                description="Premium Coffee Beans 1kg",
                quantity=10.0,
                unit_price="12.50",
                line_total="125.00",
                tax_group="STANDARD",
                tax_amount="25.00",
                department="Food & Beverage"
            ),
            InvoiceItem(
                line_number=2,
                description="Organic Green Tea 100g",
                quantity=20.0,
                unit_price="8.75",
                line_total="175.00",
                tax_group="STANDARD",
                tax_amount="35.00",
                department="Food & Beverage"
            ),
            InvoiceItem(
                line_number=3,
                description="Artisan Bread Loaf",
                quantity=15.0,
                unit_price="3.20",
                line_total="48.00",
                tax_group="REDUCED",
                tax_amount="2.40",
                department="Bakery"
            )
        ]

        extracted = InvoiceData(
            invoice_number=f"SUP-{random.randint(10000, 99999)}",
            supplier="Brightleaf Wholesale Co.",
            invoice_date=datetime.now().strftime('%Y-%m-%d'),
            due_date=datetime.now().strftime('%Y-%m-%d'),
            subtotal="348.00",
            tax_total="62.40",
            grand_total="410.40",
            currency="GBP",
            items=mock_items,
            raw_text="Mock OCR extracted text from PDF invoice"
        )

        return InvoiceProcessingResult(
            invoice_id=invoice_id,
            status="completed",
            extracted_data=extracted,
            confidence=0.92
        )

    elif 'xml' in filename.lower():
        # Try to parse actual XML
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(file_content.decode('utf-8'))
            # Extract from XML structure
            items = []
            for i, item_elem in enumerate(root.findall('.//Item'), 1):
                items.append(InvoiceItem(
                    line_number=i,
                    description=item_elem.get('description', 'Unknown'),
                    quantity=float(item_elem.get('quantity', 1)),
                    unit_price=item_elem.get('unit_price', '0.00'),
                    line_total=item_elem.get('line_total', '0.00'),
                    tax_group=item_elem.get('tax_group', 'STANDARD'),
                    tax_amount=item_elem.get('tax_amount', '0.00'),
                    department=item_elem.get('department', 'General')
                ))

            extracted = InvoiceData(
                invoice_number=root.get('invoice_number', f'XML-{invoice_id}'),
                supplier=root.get('supplier', 'Unknown Supplier'),
                invoice_date=root.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
                due_date=root.get('due_date', datetime.now().strftime('%Y-%m-%d')),
                subtotal=root.get('subtotal', '0.00'),
                tax_total=root.get('tax_total', '0.00'),
                grand_total=root.get('grand_total', '0.00'),
                currency=root.get('currency', 'GBP'),
                items=items,
                raw_text=file_content.decode('utf-8')[:500]
            )

            return InvoiceProcessingResult(
                invoice_id=invoice_id,
                status="completed",
                extracted_data=extracted,
                confidence=0.95
            )
        except Exception as e:
            return InvoiceProcessingResult(
                invoice_id=invoice_id,
                status="failed",
                errors=[f"XML parsing error: {str(e)}"],
                confidence=0.0
            )

    else:
        # Default mock for image files
        return InvoiceProcessingResult(
            invoice_id=invoice_id,
            status="completed",
            extracted_data=InvoiceData(
                invoice_number=f"IMG-{random.randint(10000, 99999)}",
                supplier="Image Supplier",
                invoice_date=datetime.now().strftime('%Y-%m-%d'),
                due_date=datetime.now().strftime('%Y-%m-%d'),
                subtotal="100.00",
                tax_total="20.00",
                grand_total="120.00",
                currency="GBP",
                items=[
                    InvoiceItem(
                        line_number=1,
                        description="Image extracted item",
                        quantity=5.0,
                        unit_price="20.00",
                        line_total="100.00",
                        tax_group="STANDARD",
                        tax_amount="20.00",
                        department="General"
                    )
                ],
                raw_text="Mock OCR text from image"
            ),
            confidence=0.75
        )


@router.post("/process-invoice", response_model=InvoiceProcessingResult)
async def process_invoice(
    file: UploadFile = File(...),
    supplier_hint: Optional[str] = Form(None)
):
    """Process an invoice file (PDF, XML, or image) using AI/OCR"""
    file_content = await file.read()

    result = mock_extract_invoice_data(file_content, file.filename)

    # Save processed result to outbox
    output_filename = f"PROCESSED_{result.invoice_id}_{file.filename}.json"
    output_path = OUTBOX_DIR / output_filename

    with open(output_path, 'w') as f:
        json.dump(result.model_dump(), f, indent=2)

    return result


@router.post("/process-inbox-invoices")
async def process_inbox_invoices():
    """Process all invoice files in the inbox directory"""
    results = []

    # Supported invoice file extensions
    extensions = ['*.pdf', '*.xml', '*.png', '*.jpg', '*.jpeg', '*.tiff']

    for ext in extensions:
        for filepath in INBOX_DIR.glob(ext):
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()

                result = mock_extract_invoice_data(content, filepath.name)
                result.invoice_id = f"INBOX_{result.invoice_id}"

                # Save result
                output_filename = f"PROCESSED_{result.invoice_id}_{filepath.name}.json"
                output_path = OUTBOX_DIR / output_filename
                with open(output_path, 'w') as f:
                    json.dump(result.model_dump(), f, indent=2)

                results.append({
                    "source_file": filepath.name,
                    "invoice_id": result.invoice_id,
                    "status": result.status,
                    "confidence": result.confidence,
                    "output_file": output_filename
                })

                # Move to archive
                archive_name = f"PROCESSED_{filepath.name}"
                filepath.rename(INBOX_DIR / archive_name)

            except Exception as e:
                results.append({
                    "source_file": filepath.name,
                    "status": "error",
                    "reason": str(e)
                })

    return {"results": results}


@router.post("/match-invoice-to-po")
async def match_invoice_to_po(invoice_id: str, po_number: str):
    """Match processed invoice to purchase order"""
    # In real implementation, this would do 3-way matching
    # PO -> Goods Receipt -> Invoice

    conn = get_db()
    cursor = conn.cursor()

    # Check if PO exists in business_accounts or a POs table
    cursor.execute("""
        SELECT id, name FROM business_accounts WHERE id = ?
    """, (po_number,))
    po = cursor.fetchone()
    conn.close()

    if po:
        return {
            "invoice_id": invoice_id,
            "po_number": po_number,
            "po_name": po[1],
            "match_status": "matched",
            "match_type": "3-way"
        }
    else:
        return {
            "invoice_id": invoice_id,
            "po_number": po_number,
            "match_status": "no_match",
            "reason": "PO not found"
        }


@router.get("/invoice-status/{invoice_id}")
async def get_invoice_status(invoice_id: str):
    """Get status of a processed invoice"""
    # Look for processed invoice in outbox
    for filepath in OUTBOX_DIR.glob(f"*{invoice_id}*.json"):
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data

    raise HTTPException(status_code=404, detail="Invoice not found")


@router.get("/extracted-data/{invoice_id}")
async def get_extracted_data(invoice_id: str):
    """Get extracted invoice data for review"""
    for filepath in OUTBOX_DIR.glob(f"*{invoice_id}*.json"):
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data.get('extracted_data')

    raise HTTPException(status_code=404, detail="Invoice data not found")


@router.post("/create-goods-receipt")
async def create_goods_receipt(invoice_id: str, received_items: List[Dict[str, Any]]):
    """Create goods receipt from matched invoice"""
    # This would integrate with inventory/stock management
    receipt_id = f"GR_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    conn = get_db()
    cursor = conn.cursor()

    # Update stock levels for each received item
    for item in received_items:
        item_code = item.get('item_code')
        variant_code = item.get('variant_code', 'DEFAULT')
        quantity = item.get('quantity', 0)

        cursor.execute("""
            UPDATE items
            SET stock_level = COALESCE(stock_level, 0) + ?
            WHERE item_code = ? AND variant_code = ?
        """, (quantity, item_code, variant_code))

    conn.commit()
    conn.close()

    return {
        "receipt_id": receipt_id,
        "invoice_id": invoice_id,
        "items_processed": len(received_items),
        "status": "created"
    }