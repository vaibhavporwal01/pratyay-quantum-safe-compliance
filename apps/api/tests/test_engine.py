"""P5 engine: the worked example, refer on a missing fact, stage and date filtering."""

from datetime import date

from app.rules.engine import evaluate_application
from tests.rule_fixtures import ISSUED, REKHA, add_rule_set

ON = date(2026, 11, 25)  # a Wednesday


async def test_worked_example_app_2026_0142(session) -> None:
    await add_rule_set(session)
    ev = await evaluate_application(session, REKHA, ON)

    assert ev.outcome == "fail"
    assert ev.microfinance is True
    mf02 = ev.result("MF-02")
    assert mf02.status == "fail"
    assert mf02.anchor == "CF para 55"
    assert "50 per cent" in mf02.para_text
    assert mf02.values["monthly_income"] == "₹22,000"
    assert mf02.values["new_emi"] == "₹4,230"
    assert mf02.values["repayments"] == "₹11,730"
    assert mf02.values["ratio_percent"] == "53.3"
    assert mf02.values["e_max"] == "₹3,500"
    assert mf02.values["l_max"] == "₹66,198.74"
    assert ev.result("MF-01").status == "pass"

    offer = ev.offer
    assert offer["amount_paise"] == 66_000_00
    assert offer["emi_paise"] == 3_489_00
    assert offer["ratio_percent"] == "49.95"
    assert offer["e_max_paise"] == 3_500_00
    assert offer["outcome"] == "pass"

    kfs = ev.kfs
    assert kfs["emi_paise"] == 4_230_00
    assert kfs["fees_total_paise"] == 800_00
    assert kfs["net_disbursal_paise"] == 79_200_00
    assert kfs["apr_percent"] == "25.07"
    assert kfs["total_payable_paise"] == 24 * 4_230_00
    assert kfs["rate_year_percent"] == "24.00"
    assert kfs["valid_until"] == "2026-11-30"  # Wed + 3 working days, over a weekend
    assert kfs["validity_working_days"] == 3
    assert kfs["fees"][0]["assumed"] is True
    assert offer["kfs"]["apr_percent"] == "25.07"
    assert offer["kfs"]["fees_total_paise"] == 660_00
    assert offer["kfs"]["emi_paise"] == 3_489_00
    assert offer["kfs"]["net_disbursal_paise"] == 65_340_00
    assert offer["kfs"]["total_payable_paise"] == 83_736_00
    assert offer["kfs"]["total_interest_paise"] == 17_736_00
    assert offer["kfs"]["monthly_irr_percent"] == "2.089"

    used = {r["code"]: r["version"] for r in ev.rules_used}
    assert used["MF-02"] == 1 and len(used) == 8


async def test_missing_fact_refers_never_passes(session) -> None:
    await add_rule_set(session)
    ev = await evaluate_application(
        session, {**REKHA, "household_income_annual_paise": None}, ON
    )
    assert ev.outcome == "refer"
    assert ev.result("MF-01").status == "refer"
    assert ev.result("MF-02").status == "refer"
    assert ev.result("MF-02").missing == ["household_income_annual_paise"]
    assert ev.microfinance is None
    assert ev.offer is None

    ev = await evaluate_application(session, {**REKHA, "amount_paise": None}, ON)
    assert ev.kfs is None
    assert ev.result("KF-01").status == "refer"
    assert ev.result("KF-03").status == "refer"


async def test_stage_filtering(session) -> None:
    rules = await add_rule_set(session)
    ev = await evaluate_application(session, REKHA, ON)
    assert ev.result("MF-05").status == "not_checked"  # recovery
    assert ev.result("MF-06").status == "not_checked"  # servicing
    assert ev.result("KF-02").status == "not_checked"  # servicing
    assert "recovery" in ev.result("MF-05").message

    rules["MF-02"].stage = "servicing"
    await session.flush()
    ev = await evaluate_application(session, REKHA, ON)
    assert ev.result("MF-02").status == "not_checked"
    assert ev.outcome == "pass"


async def test_date_filtering(session) -> None:
    rules = await add_rule_set(session)
    before = await evaluate_application(session, REKHA, date(2025, 11, 27))
    assert before.results == [] and before.outcome == "pass" and before.kfs["valid_until"] is None

    rules["MF-02"].effective_to = ON  # effective_to is exclusive
    rules["MF-04"].status = "draft"
    await session.flush()
    ev = await evaluate_application(session, REKHA, ON)
    codes = {r.code for r in ev.results}
    assert "MF-02" not in codes and "MF-04" not in codes
    assert ev.outcome == "pass"
    ev = await evaluate_application(session, REKHA, date(2026, 11, 24))
    assert ev.result("MF-02").status == "fail"
    assert ISSUED <= ON


async def test_not_microfinance_and_secured(session) -> None:
    await add_rule_set(session)
    ev = await evaluate_application(session, {**REKHA, "product_category": "general",
                                              "collateral": True}, ON)
    assert ev.result("MF-02").status == "not_applicable"
    assert ev.result("MF-01").status == "not_applicable"
    assert ev.outcome == "pass"

    ev = await evaluate_application(
        session, {**REKHA, "household_income_annual_paise": 3_60_000_00}, ON
    )
    assert ev.result("MF-01").status == "fail"
    assert ev.result("MF-02").status == "not_applicable"


async def test_no_offer_when_nothing_fits(session) -> None:
    await add_rule_set(session)
    ev = await evaluate_application(
        session, {**REKHA, "household_income_annual_paise": 1_20_000_00,
                  "existing_monthly_repayments_paise": 6_000_00}, ON
    )
    assert ev.result("MF-02").status == "fail"
    assert ev.result("MF-02").values["e_max"] == "₹0"
    assert ev.offer is None


async def test_prepayment_charge_fails_mf04(session) -> None:
    await add_rule_set(session)
    ev = await evaluate_application(session, {**REKHA, "amount_paise": 50_000_00,
                                              "prepayment_charge_paise": 500_00}, ON)
    assert ev.result("MF-04").status == "fail"
