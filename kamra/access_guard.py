"""What a restricted subscription stops this hotel doing.

The control plane writes `lodgiva_access_mode` into this site's config. This
module is the only thing that reads it, and the only thing that acts on it.

The rule is deliberately narrow: **a restricted hotel cannot take new
business, but can finish serving the guests already in it.**

A hotel is not a web app. When a subscription lapses there are people
physically in the building, mid-stay, who will try to check out in the
morning. Blocking that would strand them at the desk over an unpaid invoice
and turn a billing problem into a guest-safety one. So restriction blocks
*inserts of revenue documents* and nothing else: updates still work, folio
payments still work, housekeeping still works.

The pain is commercial. It is never operational.
"""

import frappe

#: Creating one of these is taking new business, which a restricted hotel
#: may not do. Folio Payment is deliberately absent: it is how a guest
#: already in the hotel settles up and leaves.
BLOCKED_ON_INSERT = (
    "Reservation",
    "POS Order",
    "Venue Booking",
    "Group Booking",
    "Folio Charge",
)

MESSAGE = (
    "This hotel's Lodgiva subscription is restricted, so new {what} cannot be "
    "created right now. You can still check out guests already in the hotel, "
    "take folio payments and update existing records. Nothing has been lost - "
    "settle the subscription and everything returns immediately."
)


def access_mode() -> str:
    """This site's access mode.

    Absent means full. A site the sweep has never reached is not a site that
    stopped paying, and defaulting the other way would lock out every hotel
    the moment this app shipped.
    """
    return frappe.conf.get("lodgiva_access_mode") or "full"


def enforce_access_mode(doc, method=None) -> None:
    """Refuse to create new revenue documents while restricted."""
    if access_mode() != "read_only":
        return

    if doc.doctype not in BLOCKED_ON_INSERT:
        return

    # Updates are always allowed: checking a guest out is an update.
    if getattr(doc, "name", None) and not doc.get("__islocal", True):
        return

    frappe.throw(
        MESSAGE.format(what=doc.doctype.lower() + "s"),
        title="Subscription restricted",
    )
