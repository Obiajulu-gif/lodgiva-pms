"""Financial and booking integrity under concurrency - run on a disposable site.

    printf 'from kamra.scripts.integrity_checks import execute\\nexecute()\\nexit\\n' \\
        | bench --site test.localhost console

Builds its own property ("CI Integrity Hotel", 3 rooms) and commits, because
the point is real concurrent transactions on separate connections - what two
front-desk clicks or two gateway retries actually are. Prints one line per
check and "INTEGRITY n/n passed" at the end. Never run it on a live site.
"""

import threading

import frappe
from frappe.utils import add_days

PROP = "CI Integrity Hotel"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
	results.append((name, bool(ok), detail))
	print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def _fixture() -> str:
	import kamra.api

	if not frappe.db.exists("Property", PROP):
		kamra.api.setup_property(payload={
			"property": {"property_name": PROP, "city": "Lagos", "country": "Nigeria", "currency": "NGN"},
			"room_types": [{"code": "STD", "name": "Standard", "base_price": 40000, "adults": 2, "tax_percent": 7.5}],
			"rooms": [{"room_type_code": "STD", "numbers": ["901", "902", "903"]}]})
	frappe.db.commit()
	return frappe.get_all("Room Type", filters={"property": PROP}, pluck="name")[0]


def _threads(n: int, fn) -> list:
	site, barrier, out = frappe.local.site, threading.Barrier(n), []

	def run(i):
		frappe.init(site=site)
		frappe.connect()
		frappe.set_user("Administrator")
		frappe.db.sql("select 1")  # snapshot taken before the race, like a real request
		barrier.wait()
		try:
			for _ in range(6):  # what a client does with a lock-conflict error
				try:
					out.append(("ok", fn(i)))
					frappe.db.commit()
					break
				except frappe.QueryDeadlockError:
					frappe.db.rollback()
			else:
				out.append(("err", "lock conflict x6"))
		except Exception as e:
			frappe.db.rollback()
			out.append(("err", f"{type(e).__name__}: {str(e)[:60]}"))
		finally:
			frappe.destroy()

	ts = [threading.Thread(target=run, args=(i,)) for i in range(n)]
	[t.start() for t in ts]
	[t.join() for t in ts]
	frappe.db.commit()  # end our snapshot so the threads' commits are visible
	return out


def last_room_race(rt: str, offset: int, assign_room: int) -> None:
	import kamra.api
	from kamra.business_date import get_business_date

	d1 = add_days(get_business_date(PROP), offset)
	d2 = add_days(d1, 1)
	rooms = frappe.db.count("Room", {"room_type": rt})
	for i in range(rooms - 1):
		kamra.api.create_booking(property=PROP, room_type=rt, check_in_date=d1, check_out_date=d2,
		                         guest_name=f"Filler {offset}-{i}", phone="+2348000000001")
	frappe.db.commit()
	out = _threads(6, lambda i: kamra.api.create_booking(
		property=PROP, room_type=rt, check_in_date=d1, check_out_date=d2,
		guest_name=f"Racer {offset}-{i}", phone="+2348000000002", assign_room=assign_room)["reservation"])
	live = frappe.db.sql("""select count(*) from tabReservation where room_type=%s and check_in_date=%s
	                        and status in ('Confirmed','Checked In','Held','Pending Payment')""", (rt, d1))[0][0]
	won = sum(1 for s, _ in out if s == "ok")
	check(f"last room-night race (assign_room={assign_room})", won == 1 and live == rooms,
	      f"{won} committed, {live}/{rooms} sold")


def payment_retries(rt: str) -> None:
	import kamra.api
	from kamra.business_date import get_business_date
	from kamra.payments import post_link_payment

	bd = get_business_date(PROP)
	res = kamra.api.create_booking(property=PROP, room_type=rt, check_in_date=bd, check_out_date=add_days(bd, 1),
	                               guest_name="Payment Retry", phone="+2348000000003")["reservation"]
	kamra.api.check_in(res)
	folio = frappe.db.get_value("Folio", {"reservation": res, "folio_type": "Guest"})
	frappe.db.commit()
	ref = f"{folio}-ci{frappe.generate_hash(length=6)}"
	out = _threads(6, lambda i: post_link_payment(folio, 25000, ref))
	rows = frappe.db.sql("select name from `tabFolio Payment` where parent=%s and reference=%s", (folio, ref))
	ledger = frappe.db.count("Folio Ledger Entry", {"source_doctype": "Folio Payment",
	                                                 "source_name": ["in", [r[0] for r in rows] or ["-"]]})
	credited = sum(1 for s, v in out if s == "ok" and v)
	check("concurrent gateway retries credit once", len(rows) == 1 and ledger == 1 and credited == 1,
	      f"{len(rows)} payment row(s), {ledger} ledger row(s), {credited} credited")


def audit_twice() -> None:
	import kamra.folio as F
	from kamra.business_date import get_business_date

	d = str(get_business_date(PROP))
	out = _threads(2, lambda i: F.run_night_audit(PROP, d).get("already_ran", False))
	runs = frappe.db.count("Night Audit Run", {"property": PROP, "business_date": d})
	charges = frappe.db.sql("""select count(*) from `tabFolio Charge` fc join tabFolio f on f.name=fc.parent
	                           where f.property=%s and fc.charge_type='Room' and fc.posting_date=%s""", (PROP, d))[0][0]
	check("two night audits at once run once", runs == 1 and sorted(v for _, v in out) == [False, True]
	      and str(get_business_date(PROP)) == str(add_days(d, 1)),
	      f"{runs} run(s), {charges} room charge(s), date {get_business_date(PROP)}")


def audit_resume() -> None:
	from unittest.mock import patch

	import kamra.business_date as BD
	import kamra.folio as F

	import kamra.api

	d = str(BD.get_business_date(PROP))
	rt = frappe.get_all("Room Type", filters={"property": PROP}, pluck="name")[0]
	res = kamra.api.create_booking(property=PROP, room_type=rt, check_in_date=d, check_out_date=add_days(d, 2),
	                               guest_name="Audit Resume Guest", phone="+2348000000005")["reservation"]
	kamra.api.check_in(res)  # in house across the night being audited
	frappe.db.commit()
	real = F.post_room_night

	def crash(res, date, folios=None):
		real(res, date, folios)
		raise RuntimeError("simulated crash mid-audit")

	tomorrow = lambda prop=None: str(add_days(d, 1))  # noqa: E731
	with patch.object(BD, "property_today", tomorrow), patch.object(F, "post_room_night", crash):
		F.nightly_audit_all_properties()
	frappe.db.commit()
	charged = lambda: frappe.db.sql("""select count(*) from `tabFolio Charge` fc join tabFolio f on f.name=fc.parent
	          where f.property=%s and fc.charge_type='Room' and fc.posting_date=%s""", (PROP, d))[0][0]  # noqa: E731
	after_crash = (charged(), frappe.db.count("Night Audit Run", {"property": PROP, "business_date": d}),
	               str(BD.get_business_date(PROP)))
	with patch.object(BD, "property_today", tomorrow):
		F.nightly_audit_all_properties()
		F.nightly_audit_all_properties()
	frappe.db.commit()
	after = (charged(), frappe.db.count("Night Audit Run", {"property": PROP, "business_date": d}),
	         str(BD.get_business_date(PROP)))
	check("audit crash leaves nothing half-posted", after_crash == (0, 0, d), str(after_crash))
	check("audit resumes once, rolls the date once", after[1] == 1 and after[0] >= 1 and after[2] == str(add_days(d, 1)),
	      str(after))


def corrections_and_tax(rt: str) -> None:
	import kamra.api
	import kamra.folio as F
	from kamra.business_date import get_business_date
	from kamra.payments import post_link_payment

	bd = get_business_date(PROP)
	res = kamra.api.create_booking(property=PROP, room_type=rt, check_in_date=bd, check_out_date=add_days(bd, 1),
	                               guest_name="Correction Guest", phone="+2348000000004")["reservation"]
	kamra.api.check_in(res)
	folio = frappe.db.get_value("Folio", {"reservation": res, "folio_type": "Guest"})
	kamra.api.add_folio_charge(folio, "Minibar", "CI minibar", 5000, 7.5)
	row = frappe.get_doc("Folio", folio).charges[-1].name
	orig = frappe.db.get_value("Folio Ledger Entry", {"source_name": row, "reversal_of": ["in", ["", None]]})
	kamra.api.void_folio_charge(folio, row, reason="CI: wrong room")
	check("void links back to the original ledger entry",
	      bool(orig) and frappe.db.count("Folio Ledger Entry", {"reversal_of": orig}) == 1)

	F.post_room_night(frappe.get_doc("Reservation", res), bd)
	doc = frappe.get_doc("Folio", folio)
	post_link_payment(folio, float(doc.balance), f"CASH-{res}", mode="Cash")
	F.close_folio(folio)
	snap = lambda: [(c.amount, c.gst_rate, c.gst_amount) for c in frappe.get_doc("Folio", folio).charges] + [  # noqa: E731
		frappe.db.get_value("Folio", folio, "grand_total")]
	before = snap()
	old = frappe.db.get_value("Room Type", rt, "tax_percent")
	frappe.db.set_value("Room Type", rt, "tax_percent", 15)
	again = frappe.get_doc("Folio", folio)
	F._recalculate(again)
	again.save(ignore_permissions=True)
	after = snap()
	frappe.db.set_value("Room Type", rt, "tax_percent", old)
	try:
		kamra.api.add_folio_charge(folio, "Laundry", "after close", 1000, 7.5)
		refused = False
	except Exception:
		frappe.db.rollback()
		refused = True
	check("tax change leaves an issued invoice intact", before == after and refused,
	      f"total {before[-1]} -> {after[-1]}, late charge refused={refused}")
	frappe.db.commit()


def execute():
	results.clear()
	frappe.set_user("Administrator")
	from unittest.mock import patch

	rt = _fixture()
	with patch("frappe.enqueue", lambda *a, **k: None):  # no channel/WhatsApp jobs from the fixture
		last_room_race(rt, 40, 1)
		last_room_race(rt, 45, 0)
		payment_retries(rt)
		corrections_and_tax(rt)
		audit_twice()
		audit_resume()
	passed = sum(1 for _, ok, _ in results if ok)
	print(f"INTEGRITY {passed}/{len(results)} passed")
	return passed == len(results)
