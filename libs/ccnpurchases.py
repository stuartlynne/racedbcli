"""Reconcile Uplifter product receipts without guessing who in a family bought an item."""

import csv
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation


def receipt_id(value):
    match = re.search(r"(?:^|/)receipt/(\d+)(?:[/?#]|$)", value or "")
    return match.group(1) if match else None


def read_purchases(path):
    with open(path, newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        required = {'Product Name', 'Quantity', 'Receipt Link'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Purchase report must contain Product Name, Quantity and Receipt Link")
        for row in reader:
            # Uplifter appends blank lines and a report-description/filter trailer.
            if not row.get('Product Name'):
                continue
            receipt = receipt_id(row.get('Receipt Link'))
            if not receipt:
                raise ValueError("Purchase row has an invalid receipt link")
            try:
                quantity = Decimal(row['Quantity'])
            except (InvalidOperation, TypeError):
                raise ValueError("Purchase row has an invalid quantity") from None
            if not quantity.is_finite() or quantity <= 0:
                raise ValueError("Purchase quantity must be positive")
            yield {'receipt': receipt, 'product': row['Product Name'].strip(),
                   'quantity': quantity}


def match_purchases(registrations, purchases):
    """Return notes by Reg ID and diagnostics; never count race entries as people."""
    by_receipt = defaultdict(list)
    for row in registrations:
        receipt = receipt_id(row.get('Receipt'))
        if receipt and row.get('Reg ID'):
            by_receipt[receipt].append(row)
    notes = defaultdict(list)
    diagnostics = []
    for purchase in purchases:
        receipt = purchase['receipt']
        candidates = by_receipt.get(receipt, [])
        identities = {
            row.get('Identity ID') or (
                row.get('First Name', '').strip().casefold(),
                row.get('Last Name', '').strip().casefold(),
                row.get('Date of Birth') or row.get('DOB'),
            ) for row in candidates
        }
        quantity = format(Decimal(str(purchase['quantity'])).normalize(), 'f')
        item = f"({quantity}) {purchase['product']}"
        if not candidates:
            diagnostics.append(f"Unmatched purchase: receipt {receipt}: {item}")
            continue
        if len(identities) > 1:
            names = sorted({f"{r['First Name']} {r['Last Name']}" for r in candidates})
            note = (f"PURCHASE NEEDS CONFIRMATION: {item}; shared receipt {receipt}; "
                    f"rider not determined ({', '.join(names)})")
            diagnostics.append(note)
        else:
            note = f"PURCHASED: {item} (receipt {receipt})"
        for reg_id in {row['Reg ID'] for row in candidates}:
            notes[reg_id].append(note)
    return dict(notes), diagnostics
