"""Group dashboard: every property the signed-in user may access, side by side.

Three views, all scoped by my_properties (Frappe User Permissions):

- portfolio:   occupancy, room revenue, ADR, RevPAR, arrivals, departures and
               out-of-service rooms for a date range, per property and total.
               Built from reports._day_stats, the same numbers the property
               reports show, so a group total always equals the sum of the
               property reports.
- daily_close: one row per property - business date, close status, open
               cashier sessions and what still blocks the close, each blocker
               with the screen that resolves it.
- finance:     collections by tender, refunds, outstanding folios, unmatched
               payments and cashier variances, with links to the property
               report and the transactions behind each number.

Anything dated on or after a property's business date has not been through
night audit yet, and is flagged provisional.
"""

import frappe
from frappe.utils import add_days, date_diff, getdate, nowdate

from kamra.authz import require_roles

MAX_DAYS = 92

# How the desk's payment modes roll up into the tenders finance reports on.
TENDERS = {"Cash": "cash", "Bank Transfer": "bank_transfer", "Card": "pos_terminal",
           "POS Terminal": "pos_terminal", "Payment Link": "paystack"}


def _properties(property: str | None = None) -> list[dict]:
	from kamra.api import my_properties
	props = my_properties()
	if property:
		props = [p for p in props if p["name"] == property]
		if not props:
			frappe.throw(f"You don't have access to {property}.", frappe.PermissionError)
	return props


def _range(from_date, to_date) -> tuple[str, str]:
	to_date = str(getdate(to_date or nowdate()))
	from_date = str(getdate(from_date or to_date))
	if date_diff(to_date, from_date) < 0:
		frappe.throw("From date is after to date.")
	if date_diff(to_date, from_date) >= MAX_DAYS:
		frappe.throw(f"Pick a range of at most {MAX_DAYS} days.")
	return from_date, to_date


def _business_date(property: str) -> str:
	from kamra.business_date import get_business_date
	return str(get_business_date(property))


def _ratio(a, b, pct=False):
	if not b:
		return 0
	return round((100 if pct else 1) * a / b, 1 if pct else 0)


@frappe.whitelist()
@require_roles("Finance", "Revenue Manager", "Hotel Admin", "Kamra Agent")
def portfolio(from_date: str | None = None, to_date: str | None = None,
              property: str | None = None) -> dict:
	from kamra.reports import _day_stats

	from_date, to_date = _range(from_date, to_date)
	days = date_diff(to_date, from_date) + 1
	rows = []
	for p in _properties(property):
		name = p["name"]
		rooms = frappe.db.count("Room", {"property": name})
		sold = revenue = 0.0
		for i in range(days):
			s = _day_stats(name, add_days(from_date, i), rooms)
			sold += s["rooms_sold"]
			revenue += s["room_revenue"]
		available = rooms * days
		bd = _business_date(name)
		rows.append({
			"property": name, "property_name": p.get("property_name") or name,
			"rooms": rooms,
			"out_of_service": frappe.db.count(
				"Room", {"property": name, "housekeeping_status": "Out of Order"}),
			"room_nights_sold": int(sold), "room_nights_available": available,
			"occupancy_pct": _ratio(sold, available, pct=True),
			"room_revenue": round(revenue, 2),
			"adr": _ratio(revenue, sold), "revpar": _ratio(revenue, available),
			"arrivals": frappe.db.count("Reservation", {
				"property": name, "check_in_date": ["between", [from_date, to_date]],
				"status": ["in", ["Confirmed", "Checked In", "Checked Out"]]}),
			"departures": frappe.db.count("Reservation", {
				"property": name, "check_out_date": ["between", [from_date, to_date]],
				"status": ["in", ["Checked In", "Checked Out"]]}),
			"business_date": bd,
			"provisional": to_date >= bd,
		})
	t_sold = sum(r["room_nights_sold"] for r in rows)
	t_avail = sum(r["room_nights_available"] for r in rows)
	t_rev = sum(r["room_revenue"] for r in rows)
	return {
		"from_date": from_date, "to_date": to_date, "rows": rows,
		"totals": {
			"properties": len(rows), "rooms": sum(r["rooms"] for r in rows),
			"out_of_service": sum(r["out_of_service"] for r in rows),
			"room_nights_sold": t_sold, "room_nights_available": t_avail,
			"occupancy_pct": _ratio(t_sold, t_avail, pct=True),
			"room_revenue": round(t_rev, 2),
			"adr": _ratio(t_rev, t_sold), "revpar": _ratio(t_rev, t_avail),
			"arrivals": sum(r["arrivals"] for r in rows),
			"departures": sum(r["departures"] for r in rows),
			"provisional": any(r["provisional"] for r in rows),
		},
	}


def close_blockers(property: str, business_date: str) -> list[dict]:
	"""What stops this property closing its business date, and where to fix it.

	Each item: {kind, count, text, link}. Links are PMS routes.
	"""
	out = []

	def add(kind, count, text, link):
		if count:
			out.append({"kind": kind, "count": count, "text": text, "link": link})

	sessions = frappe.get_all("Cashier Session", filters={"property": property, "status": "Open"},
	                          fields=["name", "user"])
	add("open_cashier", len(sessions),
	    "Open cashier session(s): " + ", ".join(s.user or s.name for s in sessions),
	    "/cashier/sessions")
	overstays = frappe.db.count("Reservation", {
		"property": property, "status": "Checked In", "check_out_date": ["<=", business_date]})
	add("overstay", overstays, "Guest(s) past departure still checked in", "/")
	arrivals = frappe.db.count("Reservation", {
		"property": property, "status": "Confirmed", "check_in_date": ["<", business_date]})
	add("stale_arrival", arrivals,
	    "Arrival(s) from earlier dates never checked in - audit will mark them no-show",
	    "/")
	owing = frappe.db.sql(
		"""select count(*) from `tabFolio` f join `tabReservation` r on r.name = f.reservation
		   where f.property=%s and r.status='Checked Out' and f.status='Open' and f.balance > 0.5""",
		property)[0][0]
	add("unsettled", owing, "Checked-out stay(s) with money still owed", "/billing")
	if frappe.db.exists("DocType", "Payment Match"):
		unmatched = frappe.db.count("Payment Match", {
			"property": property, "status": ["in", ["Unmatched", "Suggested"]]})
		add("unmatched", unmatched, "Payment(s) received but not matched to a folio",
		    "/reconciliation")
	# a channel whose last push failed is selling yesterday's availability
	failing = frappe.get_all("Channel Manager Connection", filters={
		"property": property, "active": 1, "last_push_status": ["like", "FAILED%"]},
		fields=["name", "provider", "last_push_status"])
	add("channel_sync", len(failing),
	    "Channel sync failing: " + "; ".join(f"{c.provider}: {c.last_push_status[8:80]}" for c in failing),
	    "/channel-manager")
	return out


@frappe.whitelist()
@require_roles("Finance", "Front Desk", "Revenue Manager", "Hotel Admin", "Kamra Agent")
def daily_close(property: str | None = None) -> dict:
	from kamra.business_date import property_today

	rows = []
	for p in _properties(property):
		name = p["name"]
		bd = _business_date(name)
		today = property_today(name)
		last = frappe.get_all("Night Audit Run", filters={"property": name},
		                      fields=["name", "business_date", "status", "creation"],
		                      order_by="business_date desc", limit=1)
		blockers = close_blockers(name, bd)
		behind = date_diff(today, bd)
		status = ("Behind" if behind > 0 else "Blocked" if blockers else "Ready")
		from kamra.api import cash_summary
		cash = cash_summary(name, bd)
		rows.append({
			"property": name, "property_name": p.get("property_name") or name,
			"business_date": bd, "today": today, "days_behind": max(behind, 0),
			"status": status,
			"open_cashiers": next((b["count"] for b in blockers if b["kind"] == "open_cashier"), 0),
			"blockers": blockers,
			"last_audit": last[0] if last else None,
			# not through night audit yet, so it can still change
			"provisional": {"collections": cash.get("grand_total", 0)},
		})
	return {"rows": rows,
	        "summary": {s: sum(1 for r in rows if r["status"] == s)
	                    for s in ("Ready", "Blocked", "Behind")}}


@frappe.whitelist()
@require_roles("Finance", "Hotel Admin", "Kamra Agent")
def finance(from_date: str | None = None, to_date: str | None = None,
            property: str | None = None) -> dict:
	from_date, to_date = _range(from_date, to_date)
	rows = []
	for p in _properties(property):
		name = p["name"]
		tenders = {v: 0.0 for v in TENDERS.values()} | {"other": 0.0}
		refunds = 0.0
		for mode, amount in frappe.db.sql(
				"""select fp.mode, fp.amount from `tabFolio Payment` fp
				   join `tabFolio` f on f.name = fp.parent and fp.parenttype = 'Folio'
				   where f.property=%s and fp.posting_date between %s and %s""",
				(name, from_date, to_date)):
			amount = float(amount or 0)
			if amount < 0:
				refunds += -amount
			else:
				tenders[TENDERS.get(mode, "other")] += amount
		outstanding = frappe.db.sql(
			"""select count(*), coalesce(sum(balance), 0) from `tabFolio`
			   where property=%s and status='Open' and balance > 0.5""", name)[0]
		unmatched = (0, 0.0)
		if frappe.db.exists("DocType", "Payment Match"):
			unmatched = frappe.db.sql(
				"""select count(*), coalesce(sum(amount), 0) from `tabPayment Match`
				   where property=%s and status in ('Unmatched', 'Suggested')""", name)[0]
		variances = frappe.get_all(
			"Cashier Session",
			filters={"property": name, "status": "Closed", "variance": ["!=", 0],
			         "business_date": ["between", [from_date, to_date]]},
			fields=["name", "user", "business_date", "variance", "close_notes"])
		bd = _business_date(name)
		rows.append({
			"property": name, "property_name": p.get("property_name") or name,
			"tenders": {k: round(v, 2) for k, v in tenders.items()},
			"collected": round(sum(tenders.values()), 2),
			"refunds": round(refunds, 2),
			"outstanding_folios": int(outstanding[0]), "outstanding": float(outstanding[1]),
			"unmatched_payments": int(unmatched[0]), "unmatched_amount": float(unmatched[1]),
			"cashier_variances": variances,
			"variance_total": round(sum(float(v.variance or 0) for v in variances), 2),
			"provisional": to_date >= bd,
			"links": {"report": "/reports", "transactions": "/folio-history",
			          "outstanding": "/billing", "unmatched": "/reconciliation",
			          "variances": "/cashier/sessions"},
		})
	keys = ["collected", "refunds", "outstanding", "outstanding_folios", "unmatched_payments",
	        "unmatched_amount", "variance_total"]
	totals = {k: round(sum(r[k] for r in rows), 2) for k in keys}
	totals["tenders"] = {k: round(sum(r["tenders"][k] for r in rows), 2)
	                     for k in list(TENDERS.values()) + ["other"]}
	return {"from_date": from_date, "to_date": to_date, "rows": rows, "totals": totals}
