"""Make synthesized document values coherent for the demo.

The training-data synthesizer only needs schema-valid values, so receipts can have more tax
than total and free text is lorem-ipsum. The demo should look like real paperwork: amounts add
up, due dates follow invoice dates, and notes read like notes.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

_ITEMS = [
    "Oat latte",
    "Blueberry muffin",
    "Sparkling water",
    "Turkey sandwich",
    "Garden salad",
    "Printer paper",
    "Ballpoint pens",
    "USB-C cable",
    "Notebook",
    "Hand soap",
    "Batteries (AA)",
    "Greeting cards",
    "Tote bag",
    "Coffee beans",
    "Paperback novel",
]
_CONNECTION_NOTES = [
    "Interested in joining a small group.",
    "New to the area, moved here last month.",
    "Would like information about volunteering.",
    "Came with a friend; wants to hear about the kids ministry.",
    "Please send the newsletter by email.",
    "Looking for a mid-week service.",
]
_PRAYER_REQUESTS = [
    "Please pray for my mother's recovery after surgery.",
    "Praying for guidance with a job decision this month.",
    "Thankful for a safe trip; asking prayer for our family's travels ahead.",
    "Please remember our neighbor who is going through a hard season.",
]
_NOTES = [
    "Call the contractor about the quote by Friday.",
    "Pick up prescription, then groceries: eggs, rice, spinach.",
    "Meeting recap: ship the draft Tuesday, review with Priya on Wednesday.",
    "Ideas for the workshop: hands-on demo, short Q&A, printed handouts.",
]
_FORM_CONTENT = [
    "Requesting a transfer of records to the new address effective next month.",
    "Annual membership renewal. No changes to contact details this year.",
    "Volunteer sign-up for the spring cleanup, Saturday morning shift.",
]
_FLYER_BLURBS = [
    "Live music, food trucks and activities for the whole family. Free admission.",
    "An evening talk followed by an open Q&A. Light refreshments provided.",
    "Join us for a community potluck. Bring a dish to share.",
]
_FUNDS = ["general", "missions", "building"]
_MEMOS = ["Monthly tithe", "Building fund", "Missions offering", "Thank-you gift"]
_TERMS = ["Net 30", "Net 15", "Due on receipt", "Net 45"]
_TAX_RATE = 0.0825


def _money(x: float) -> str:
    return f"${x:,.2f}"


def _parse(d: str | None) -> datetime:
    try:
        return datetime.strptime(d or "", "%m/%d/%Y")
    except ValueError:
        return datetime.now() - timedelta(days=10)


def polish(doc_type: str, labels: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """Return `labels` with coherent amounts, dates and free text for the document type."""
    out = dict(labels)

    if doc_type == "receipt":
        total = round(rng.uniform(6.0, 210.0), 2)
        tax = round(total * _TAX_RATE / (1 + _TAX_RATE), 2)
        out["total_amount"] = _money(total)
        out["tax_amount"] = _money(tax)
        out["items_summary"] = ", ".join(rng.sample(_ITEMS, rng.randint(2, 4)))

    elif doc_type == "invoice":
        subtotal = round(rng.uniform(400.0, 9500.0), 2)
        tax = round(subtotal * _TAX_RATE, 2)
        issued = _parse(out.get("invoice_date"))
        terms = rng.choice(_TERMS)
        days = {"Net 30": 30, "Net 15": 15, "Net 45": 45}.get(terms, 0)
        out["invoice_number"] = f"INV-{issued.year}-{rng.randint(100, 9999):04d}"
        out["subtotal"] = _money(subtotal)
        out["tax_amount"] = _money(tax)
        out["total_due"] = _money(subtotal + tax)
        out["due_date"] = (issued + timedelta(days=days)).strftime("%m/%d/%Y")
        out["payment_terms"] = terms

    elif doc_type == "giving_envelope":
        out["amount"] = _money(float(rng.choice([20, 25, 50, 75, 100, 150, 250, 500])))
        out["memo"] = rng.choice(_MEMOS)
        out["fund"] = rng.choice(_FUNDS)

    elif doc_type == "connection_card":
        out["notes"] = rng.choice(_CONNECTION_NOTES)

    elif doc_type == "prayer_request":
        out["request_text"] = rng.choice(_PRAYER_REQUESTS)

    elif doc_type == "handwritten_note":
        out["note_text"] = rng.choice(_NOTES)

    elif doc_type == "generic_form":
        out["form_content"] = rng.choice(_FORM_CONTENT)

    elif doc_type == "event_flyer":
        out["description"] = rng.choice(_FLYER_BLURBS)

    return out
