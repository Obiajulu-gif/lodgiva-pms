# Copyright (c) 2026, HeyKoala and contributors
# For license information, please see license.txt

"""The night audit closes one day per run. These cover what happens when more
than one day is owed - the case that left a hotel permanently behind."""

from datetime import date, timedelta


def catch_up(business_date: str, today: str, audited: set[str],
             max_days: int = 370) -> list[str]:
    """The loop in kamra.folio.catch_up_night_audit, with the Frappe calls
    replaced by a set of already-audited dates. Returns the dates it ran."""
    ran = []
    for _ in range(max_days):
        if business_date >= today:
            break
        if business_date not in audited:
            audited.add(business_date)
            ran.append(business_date)
        # Whether it audited or found the date already done, the date has to
        # move - an early return used to leave the roll unreached.
        business_date = str(date.fromisoformat(business_date) + timedelta(days=1))
    return ran


def test_single_missed_night_is_the_normal_case():
    assert catch_up("2026-10-28", "2026-10-29", set()) == ["2026-10-28"]


def test_already_at_today_does_nothing():
    assert catch_up("2026-10-29", "2026-10-29", set()) == []


def test_future_business_date_does_not_run_backwards():
    assert catch_up("2026-11-02", "2026-10-29", set()) == []


def test_a_month_of_downtime_is_caught_up_in_one_pass():
    ran = catch_up("2026-09-26", "2026-10-29", set())
    assert len(ran) == 33
    assert ran[0] == "2026-09-26"
    assert ran[-1] == "2026-10-28"


def test_an_already_audited_date_is_stepped_over_not_spun_on():
    # The real run_night_audit returns {"already_ran": True} without rolling,
    # which is exactly how a loop over it would hang.
    ran = catch_up("2026-10-26", "2026-10-29", audited={"2026-10-27"})
    assert ran == ["2026-10-26", "2026-10-28"]


def test_the_cap_bounds_a_nonsense_business_date():
    ran = catch_up("1900-01-01", "2026-10-29", set())
    assert len(ran) == 370
