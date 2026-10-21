from decimal import Decimal as D
import pytest
from app.calculators.engine import calculate

CT = {
    "zero_band": "375000",
    "rate": ".09",
    "loss_limit": ".75",
    "sbr_revenue": "3000000",
    "sbr_end": "2026-12-31",
}
PERIOD = {"period_start": "2026-01-01", "period_end": "2026-12-31"}


@pytest.mark.parametrize(
    "profit,tax",
    [
        ("0", "0.00"),
        ("-100", "0.00"),
        ("375000", "0.00"),
        ("375100", "9.00"),
        ("900000", "47250.00"),
    ],
)
def test_ct_reference_cases(profit, tax):
    assert calculate("corporate_tax", {**PERIOD, "accounting_profit": profit}, CT)[
        "results"
    ]["corporate_tax"] == D(tax)


def test_ct_loss_cap_and_sbr_restrictions():
    result = calculate(
        "corporate_tax",
        {
            **PERIOD,
            "accounting_profit": "1000000",
            "losses_brought_forward": "1000000",
            "losses_requested": "1000000",
        },
        CT,
    )["results"]
    assert result["losses_applied"] == D("750000") and result["taxable_income"] == D(
        "250000"
    )
    with pytest.raises(ValueError, match="eligibility"):
        calculate(
            "corporate_tax",
            {**PERIOD, "accounting_profit": "900000", "sbr_elected": True},
            CT,
        )
    eligible = {
        **PERIOD,
        "accounting_profit": "900000",
        "sbr_elected": True,
        "revenue": "3000000",
        **{
            k: True
            for k in [
                "resident",
                "prior_revenue_eligible",
                "not_qfzp",
                "not_large_mne",
                "sbr_conditions_confirmed",
            ]
        },
    }
    assert calculate("corporate_tax", eligible, CT)["results"]["corporate_tax"] == 0
    with pytest.raises(ValueError):
        calculate("corporate_tax", {**eligible, "period_end": "2027-01-01"}, CT)
    assert (
        calculate("corporate_tax", {**PERIOD, "treatment": "free_zone"}, CT)["status"]
        == "restricted"
    )


@pytest.mark.parametrize(
    "inputs,expected",
    [
        ({"amount": "100", "inclusive": False}, "5.00"),
        ({"amount": "105", "inclusive": True}, "5.00"),
        ({"amount": "0.10"}, "0.01"),
        ({"amount": "100", "treatment": "zero"}, "0.00"),
        ({"amount": "100", "treatment": "exempt"}, "0.00"),
        ({"amount": "100", "treatment": "out_of_scope"}, "0.00"),
    ],
)
def test_vat_treatment_and_rounding(inputs, expected):
    assert calculate("vat", inputs, {"standard_rate": ".05"})["results"][
        "output_vat"
    ] == D(expected)


def test_vat_net_and_recoverability():
    result = calculate(
        "vat",
        {
            "transactions": [
                {"amount": "100", "direction": "output"},
                {"amount": "200", "direction": "input", "recoverable": True},
                {"amount": "100", "direction": "input", "recoverable": False},
            ]
        },
        {"standard_rate": ".05"},
    )["results"]
    assert result["net_vat_payable"] == D("-5.00")
    with pytest.raises(ValueError):
        calculate("vat", {"amount": "-1"}, {"standard_rate": ".05"})


def test_qfzp_boundary_is_not_status_determination():
    params = {"percentage": ".05", "cap": "5000000"}
    result = calculate(
        "qfzp",
        {**PERIOD, "total_revenue": "20000000", "non_qualifying": "1000000"},
        params,
    )
    assert (
        result["results"]["de_minimis_pass"]
        and result["results"]["unverified_conditions"]
    )
    assert not calculate(
        "qfzp",
        {**PERIOD, "total_revenue": "20000000", "non_qualifying": "1000000.01"},
        params,
    )["results"]["de_minimis_pass"]
    with pytest.raises(ValueError):
        calculate("qfzp", {**PERIOD, "total_revenue": "0"}, params)


@pytest.mark.parametrize(
    "end,expected",
    [
        ("2020-12-31", "0.00"),
        ("2021-01-01", "10500.00"),
        ("2025-01-01", "52500.00"),
        ("2026-01-01", "67500.00"),
    ],
)
def test_gratuity_anniversary_bands(end, expected):
    result = calculate(
        "gratuity",
        {
            "employment_start": "2020-01-01",
            "employment_end": end,
            "monthly_basic": "15000",
        },
        {"first_days": "21", "later_days": "30", "cap_months": "24"},
    )
    assert result["results"]["gratuity"] == D(expected)


def test_gratuity_unsupported_and_unpaid():
    assert (
        calculate(
            "gratuity",
            {
                "employment_start": "2020-01-01",
                "employment_end": "2026-01-01",
                "regime": "DIFC",
            },
            {},
        )["status"]
        == "restricted"
    )
    with pytest.raises(ValueError):
        calculate(
            "gratuity",
            {"employment_start": "2026-01-01", "employment_end": "2020-01-01"},
            {},
        )


@pytest.mark.parametrize(
    "method,q1,q3", [("inclusive", "3", "7"), ("exclusive", "2.5", "7.5")]
)
def test_range_interpolation(method, q1, q3):
    result = calculate(
        "tp_range",
        {"observations": list(range(1, 10)), "tested_party": "5", "method": method},
    )["results"]
    assert (
        result["lower_quartile"] == D(q1)
        and result["upper_quartile"] == D(q3)
        and result["median"] == 5
    )


def test_financial_schedules_and_zero_rates():
    result = calculate(
        "loan",
        {
            "principal": "1200",
            "annual_rate": "0",
            "periods": 12,
            "periods_per_year": 12,
        },
    )
    assert (
        result["results"]["regular_payment"] == D("100.00")
        and result["schedule"][-1]["closing"] == 0
    )
    assert sum(r["principal"] for r in result["schedule"]) == 1200
    lease = calculate(
        "lease",
        {"payment": "1000", "annual_rate": "0", "periods": 12, "periods_per_year": 12},
    )
    assert lease["results"]["initial_liability"] == 12000
    assert (
        calculate("npv", {"cashflows": ["-100", "110"], "discount_rate": ".1"})[
            "results"
        ]["npv"]
        == 0
    )
    dep = calculate("depreciation", {"cost": "1000", "residual": "100", "periods": 3})
    assert [r["depreciation"] for r in dep["schedule"]] == [D("300")] * 3
    assert (
        calculate(
            "impairment",
            {"carrying": "100", "fair_value_less_costs": "80", "value_in_use": "90"},
        )["results"]["impairment"]
        == 10
    )


@pytest.mark.parametrize(
    "code,inputs",
    [
        ("loan", {"principal": "NaN"}),
        ("loan", {"principal": "Infinity"}),
        ("loan", {"periods": "1.5"}),
        ("npv", {"cashflows": []}),
        ("depreciation", {"cost": "1", "residual": "2"}),
        ("tp_range", {"observations": [1]}),
    ],
)
def test_invalid_inputs(code, inputs):
    with pytest.raises(ValueError):
        calculate(code, inputs)


def test_pillar_two_is_preliminary_and_handles_loss():
    result = calculate(
        "pillar_two",
        {
            **PERIOD,
            "prior_revenues": ["750000000"] * 4,
            "mne_group": True,
            "globe_income": "-10",
        },
        {"revenue_eur": "750000000", "minimum_rate": ".15"},
    )
    assert (
        result["results"]["revenue_scope_screen"]
        and result["results"]["globe_loss"]
        and result["results"]["simplified_etr"] is None
    )
    assert "Preliminary assessment" in result["warnings"][0]
