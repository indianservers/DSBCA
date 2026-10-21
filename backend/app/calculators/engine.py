"""Deterministic Decimal engines. Rates/thresholds arrive only via reviewed rule snapshots."""

from decimal import Decimal, ROUND_HALF_UP, localcontext
from datetime import date
import calendar

D = Decimal
MONEY = D(".01")


def money(n):
    return D(n).quantize(MONEY, rounding=ROUND_HALF_UP)


def number(x, key, default="0", minimum=None, maximum=D("1e15")):
    try:
        v = D(str(x.get(key, default)))
    except Exception:
        raise ValueError(f"{key}: enter a number")
    if not v.is_finite() or abs(v) > maximum or (minimum is not None and v < minimum):
        raise ValueError(f"{key}: outside allowed range")
    return v


def count(x, key, default=12):
    v = number(x, key, default, minimum=D(1), maximum=D(1200))
    if v != int(v):
        raise ValueError(f"{key}: whole number required")
    return int(v)


def dt(x, key):
    try:
        return date.fromisoformat(x[key])
    except Exception:
        raise ValueError(f"{key}: use YYYY-MM-DD")


def period(x):
    a, b = dt(x, "period_start"), dt(x, "period_end")
    if a > b or (b - a).days > 732:
        raise ValueError("Invalid financial period")
    return a, b


def annual_schedule(principal, rate, n, payment=None, advance=False):
    if rate <= -1:
        raise ValueError("Periodic rate must exceed -100%")
    if payment is None:
        payment = (
            principal / n if rate == 0 else principal * rate / (1 - (1 + rate) ** (-n))
        )
    balance = principal
    rows = []
    for i in range(1, n + 1):
        interest = (balance - payment) * rate if advance else balance * rate
        if i < n and payment > balance + interest + D("0.00000001"):
            raise ValueError(
                "Payment repays the balance before the selected final period; shorten the term"
            )
        paid = balance + interest if i == n else payment
        closing = balance + interest - paid
        rows.append(
            {
                "period": i,
                "opening": money(balance),
                "payment": money(paid),
                "interest": money(interest),
                "principal": money(paid - interest),
                "closing": money(closing),
            }
        )
        balance = closing
    return payment, rows


def calculate(code, x, rule=None):
    with localcontext() as ctx:
        ctx.prec = 36
        return _calculate(code, x, rule or {})


def _calculate(code, x, p):
    warnings = []
    work = []
    result = {}
    schedule = []
    if code == "corporate_tax":
        period(x)
        if x.get("treatment", "standard") != "standard":
            return {
                "status": "restricted",
                "warnings": [
                    "Free Zone, exempt persons, tax groups and special regimes require separate analysis."
                ],
                "results": {},
            }
        profit = number(x, "accounting_profit")
        exempt = number(x, "exempt_income", minimum=D(0))
        disallowed = number(x, "non_deductible", minimum=D(0))
        adjust = number(x, "adjustments")
        before = max(D(0), profit - exempt + disallowed + adjust)
        losses = number(x, "losses_brought_forward", minimum=D(0))
        requested = number(x, "losses_requested", minimum=D(0))
        if requested > losses:
            raise ValueError("Requested losses exceed brought-forward losses")
        applied = min(requested, before * D(p["loss_limit"]))
        taxable = before - applied
        relief = False
        if x.get("sbr_elected"):
            conditions = [
                "resident",
                "prior_revenue_eligible",
                "not_qfzp",
                "not_large_mne",
                "sbr_conditions_confirmed",
            ]
            eligible = (
                all(x.get(k) is True for k in conditions)
                and number(x, "revenue", minimum=D(0)) <= D(p["sbr_revenue"])
                and dt(x, "period_end") <= date.fromisoformat(p["sbr_end"])
            )
            if not eligible:
                raise ValueError(
                    "Small Business Relief eligibility/effective period is not established"
                )
            relief = True
            applied = D(0)
            taxable = D(0)
        tax = max(D(0), taxable - D(p["zero_band"])) * D(p["rate"])
        result = {
            "accounting_income": profit,
            "exempt_income": exempt,
            "non_deductible": disallowed,
            "adjustments": adjust,
            "income_before_losses": before,
            "losses_applied": applied,
            "losses_remaining": losses - applied,
            "taxable_income": taxable,
            "small_business_relief": relief,
            "corporate_tax": money(tax),
        }
        work = [
            "Adjusted income = accounting profit − exempt income + non-deductible expenses + signed adjustments.",
            "Eligible losses limited by the selected rule and taxpayer confirmations.",
            "Tax = max(0, taxable income − zero-rate band) × rate.",
        ]
        warnings = [
            "Standard taxable-person arithmetic only; exempt-income and loss eligibility are user-confirmed, not independently assessed. Interest limitation, credits, restructuring, foreign PE and other special adjustments are outside this engine."
        ]
    elif code == "vat":
        rows = x.get("transactions") or [
            {
                "amount": x.get("amount", "0"),
                "treatment": x.get("treatment", "standard"),
                "direction": x.get("direction", "output"),
                "inclusive": x.get("inclusive", False),
                "recoverable": x.get("recoverable", True),
            }
        ]
        if not 1 <= len(rows) <= 500:
            raise ValueError("Provide 1–500 transactions")
        output = input_vat = D(0)
        net = gross = D(0)
        for i, t in enumerate(rows):
            amount = number(t, "amount", minimum=D(0))
            treatment = t.get("treatment", "standard")
            if treatment not in ["standard", "zero", "exempt", "out_of_scope"]:
                raise ValueError("Unknown VAT treatment")
            rate = D(p["standard_rate"]) if treatment == "standard" else D(0)
            tax = (
                money(amount - amount / (1 + rate))
                if t.get("inclusive")
                else money(amount * rate)
            )
            base = amount - tax if t.get("inclusive") else amount
            direction = t.get("direction", "output")
            if direction not in ["input", "output"]:
                raise ValueError("Choose input/output VAT")
            if direction == "output":
                output += tax
            elif t.get("recoverable") is True:
                input_vat += tax
            schedule.append(
                {
                    "transaction": i + 1,
                    "treatment": treatment,
                    "net": money(base),
                    "vat": tax,
                    "gross": money(base + tax),
                    "direction": direction,
                    "recoverable": t.get("recoverable", False),
                }
            )
            net += base
            gross += base + tax
        result = {
            "net_amount": money(net),
            "gross_amount": money(gross),
            "output_vat": output,
            "recoverable_input_vat": input_vat,
            "net_vat_payable": money(output - input_vat),
        }
        work = [
            "Exclusive: VAT = net × rate. Inclusive: VAT = gross − gross/(1 + rate).",
            "Round each transaction VAT to 2 decimals, half up; sum rounded tax amounts.",
        ]
        warnings = [
            "Classification and recoverability require confirmation; reverse charge, partial exemption and special schemes are not inferred. Negative payable denotes an arithmetic refund position, not an approved refund."
        ]
    elif code == "qfzp":
        period(x)
        total = number(x, "total_revenue", minimum=D(0))
        removed = number(x, "excluded_from_denominator", minimum=D(0))
        nonqual = number(x, "non_qualifying", minimum=D(0))
        excluded = number(x, "excluded_activity", minimum=D(0))
        qual = number(x, "qualifying_income", minimum=D(0))
        denominator = total - removed
        if denominator <= 0 or nonqual + excluded > denominator:
            raise ValueError(
                "Adjusted revenue must be positive and cover non-qualifying categories"
            )
        threshold = min(denominator * D(p["percentage"]), D(p["cap"]))
        numerator = nonqual + excluded
        checks = [
            "adequate_substance",
            "qualifying_activities",
            "transfer_pricing_compliance",
            "audited_financials",
            "no_standard_election",
            "revenue_classification_verified",
        ]
        missing = [k for k in checks if x.get(k) is not True]
        result = {
            "adjusted_total_revenue": denominator,
            "non_qualifying_revenue": numerator,
            "de_minimis_threshold": money(threshold),
            "de_minimis_pass": numerator <= threshold,
            "reported_qualifying_income": qual,
            "unverified_conditions": missing,
            "assessment": (
                "Conditions require review"
                if missing
                else "Screening only; professional validation required"
            ),
        }
        warnings = [
            "De minimis alone does not establish QFZP status. Non-qualifying and excluded activity inputs must be disjoint. Statutory denominator/numerator exclusions must be classified and verified separately. This does not calculate Free Zone tax."
        ]
        work = [
            "Threshold = lower of adjusted revenue × percentage and cap. Compare aggregate non-qualifying revenue with threshold."
        ]
    elif code == "gratuity":
        a, b = dt(x, "employment_start"), dt(x, "employment_end")
        salary = number(x, "monthly_basic", minimum=D(0))
        unpaid = number(x, "unpaid_days", minimum=D(0))
        if b < a:
            raise ValueError("Employment end precedes start")
        if (
            x.get("regime", "federal") != "federal"
            or x.get("arrangement", "full_time") != "full_time"
            or x.get("worker", "foreign") != "foreign"
        ):
            return {
                "status": "restricted",
                "warnings": [
                    "Only federal full-time foreign-worker gratuity is implemented. DIFC, ADGM, nationals, part-time and alternative savings schemes need separate rules."
                ],
                "results": {},
            }
        days = D((b - a).days) - unpaid
        if days < 0:
            raise ValueError("Unpaid days exceed service")

        # Anniversary-based full years, with actual days in the remaining anniversary year.
        def anniversary(year):
            return date(
                year, a.month, min(a.day, calendar.monthrange(year, a.month)[1])
            )

        years = max(0, b.year - a.year - (b < anniversary(b.year)))
        anchor = anniversary(a.year + years)
        next_anchor = anniversary(a.year + years + 1)
        service = max(
            D(0),
            D(years)
            + D((b - anchor).days) / D((next_anchor - anchor).days)
            - unpaid / D(365),
        )
        first = min(service, D(5))
        later = max(D(0), service - D(5))
        daily = salary / D(30)
        gross = (
            (first * D(p["first_days"]) + later * D(p["later_days"])) * daily
            if service >= 1
            else D(0)
        )
        cap = number(x, "monthly_total_wage", default=str(salary), minimum=salary) * D(
            p["cap_months"]
        )
        result = {
            "service_days": days,
            "service_years": service.quantize(D(".000001")),
            "daily_basic_wage": money(daily),
            "first_band_days": first * D(p["first_days"]) if service >= 1 else D(0),
            "later_band_days": later * D(p["later_days"]) if service >= 1 else D(0),
            "gross_gratuity": money(gross),
            "cap": money(cap),
            "gratuity": money(min(gross, cap)),
        }
        work = [
            "Full anniversary years plus actual-day fractional year; unpaid leave deducted using 365-day convention.",
            "Daily basic = monthly basic / 30. First five years and later years use selected statutory bands.",
        ]
        warnings = [
            "Estimate before employer debt deductions; unpaid-leave day-count convention must be checked for the specific employment contract."
        ]
    elif code == "tp_range":
        observations = x.get("observations", [])
        if not 2 <= len(observations) <= 1000:
            raise ValueError("Provide 2–1000 observations")
        values = []
        for item in observations:
            if isinstance(item, dict):
                if item.get("selected", True):
                    values.append(number(item, "value"))
            else:
                values.append(number({"v": item}, "v"))
        values.sort()
        if len(values) < 2:
            raise ValueError("Select at least two observations")
        method = x.get("method", "inclusive")
        if method not in ["inclusive", "exclusive"]:
            raise ValueError("Choose inclusive/exclusive percentile")

        def percentile(q):
            h = (
                (len(values) - 1) * q
                if method == "inclusive"
                else (len(values) + 1) * q - 1
            )
            if h < 0 or h > len(values) - 1:
                raise ValueError("Exclusive quartile requires more observations")
            lo = int(h)
            hi = min(lo + 1, len(values) - 1)
            return values[lo] + (values[hi] - values[lo]) * (h - lo)

        q1, q2, q3 = [percentile(q) for q in [D(".25"), D(".5"), D(".75")]]
        tested = number(x, "tested_party")
        result = {
            "minimum": values[0],
            "lower_quartile": q1,
            "median": q2,
            "upper_quartile": q3,
            "maximum": values[-1],
            "observations": len(values),
            "tested_party": tested,
            "position": (
                "below" if tested < q1 else "above" if tested > q3 else "within"
            ),
            "method": method,
            "financial_metric": str(x.get("metric", "User-selected metric"))[:180],
        }
        work = [
            "Inclusive rank = (n−1) × p; exclusive rank = (n+1) × p−1, zero-indexed. Linear interpolation between adjacent sorted observations."
        ]
        warnings = [
            "Only selected observations are included; no automatic outlier removal or comparability assertion. Multi-year observations are separate unless the user aggregates them before entry."
        ]
    elif code in ["loan", "lease", "effective_interest", "interest_benchmark"]:
        principal = number(x, "principal", minimum=D(0))
        n = count(x, "periods")
        frequency = count(x, "periods_per_year", 12)
        annual = number(x, "annual_rate", minimum=D(0), maximum=D(10))
        rate = annual / frequency
        if code == "interest_benchmark":
            annual = number(x, "benchmark_rate", minimum=D(0), maximum=D(10)) + number(
                x, "spread", maximum=D(10)
            )
            rate = annual / frequency
            if annual < 0:
                raise ValueError("Combined interest rate must be non-negative")
            lo = number(x, "range_low", minimum=D(0))
            hi = number(x, "range_high", minimum=lo)
            result.update(
                {
                    "annualized_rate": annual,
                    "benchmark_position": (
                        "below" if annual < lo else "above" if annual > hi else "within"
                    ),
                    "currency": str(x.get("currency", "AED"))[:8],
                    "loan_date": dt(x, "loan_date").isoformat(),
                }
            )
        if code == "lease":
            payment = number(x, "payment", minimum=D(0))
            advance = x.get("timing", "arrears") == "advance"
            principal = (
                payment * D(n)
                if rate == 0
                else payment * (1 - (1 + rate) ** (-n)) / rate
            )
            if advance:
                principal *= 1 + rate
            # Advance schedule: interest accrues after beginning-of-period payment.
            actual, schedule = annual_schedule(principal, rate, n, payment, advance)
        elif code == "effective_interest":
            cash = number(x, "cash_payment", minimum=D(0))
            actual, schedule = annual_schedule(principal, rate, n, cash)
            warnings.append(
                "Effective rate is supplied by the user; this engine does not solve an ambiguous IRR. Final payment is the balancing cash flow."
            )
        elif x.get("repayment_profile") == "bullet":
            payment = principal * rate
            schedule = [
                {
                    "period": i,
                    "opening": money(principal),
                    "interest": money(payment),
                    "principal": money(principal if i == n else 0),
                    "payment": money(payment + (principal if i == n else 0)),
                    "closing": money(0 if i == n else principal),
                }
                for i in range(1, n + 1)
            ]
            actual = payment
        else:
            actual, schedule = annual_schedule(principal, rate, n)
        result.update(
            {
                "initial_liability": money(principal),
                "periodic_rate": rate,
                "regular_payment": money(actual),
                "total_interest": sum(r["interest"] for r in schedule),
                "final_balance": schedule[-1]["closing"],
            }
        )
        work = [
            "Periodic rate = nominal annual rate / periods per year. Level payment = PV × r/(1−(1+r)^−n); zero-rate payment = PV/n.",
            "Schedules retain high precision internally and display half-up cents; final payment balances the liability.",
        ]
        if code == "lease":
            warnings.append(
                "Fixed payments only; excludes variable/index changes, incentives, modifications, ROU asset costs, tax and reassessment. This is a lease-liability schedule, not full IFRS 16 accounting."
            )
        if code == "interest_benchmark":
            warnings.append(
                "Benchmark and spread are user supplied. No market rate or arm’s length conclusion is inferred."
            )
    elif code == "npv":
        rate = number(x, "discount_rate", minimum=D("-.99"), maximum=D(10))
        flows = x.get("cashflows", [])
        if not 1 <= len(flows) <= 1201:
            raise ValueError("Provide 1–1201 cash flows including time zero")
        total = D(0)
        for i, value in enumerate(flows):
            amount = number({"amount": value}, "amount")
            pv = amount / (1 + rate) ** i
            total += pv
            schedule.append(
                {"period": i, "cashflow": amount, "present_value": money(pv)}
            )
        result = {"npv": money(total)}
        work = [
            "NPV = Σ cash flow[t] / (1+r)^t, including time zero. Equal periods assumed."
        ]
    elif code == "depreciation":
        cost = number(x, "cost", minimum=D(0))
        residual = number(x, "residual", minimum=D(0))
        n = count(x, "periods")
        if residual > cost:
            raise ValueError("Residual exceeds cost")
        method = x.get("method", "straight_line")
        rate = number(x, "reducing_rate", default=".2", minimum=D(0), maximum=D(1))
        balance = cost
        if method not in ["straight_line", "reducing_balance"]:
            raise ValueError("Unsupported depreciation method")
        for i in range(1, n + 1):
            depreciation = min(
                balance - residual,
                (cost - residual) / n if method == "straight_line" else balance * rate,
            )
            close = balance - depreciation
            schedule.append(
                {
                    "period": i,
                    "opening": money(balance),
                    "depreciation": money(depreciation),
                    "closing": money(close),
                }
            )
            balance = close
        result = {
            "depreciable_amount": cost - residual,
            "closing_carrying_value": money(balance),
        }
        work = [
            "Straight line = (cost−residual)/life. Reducing balance = opening × supplied rate, floored at residual."
        ]
        warnings = [
            "Full equal periods; residual and useful life require review. No automatic forced write-off in reducing-balance method."
        ]
    elif code == "impairment":
        carrying = number(x, "carrying", minimum=D(0))
        fv = number(x, "fair_value_less_costs", minimum=D(0))
        viu = number(x, "value_in_use", minimum=D(0))
        sensitivity = number(x, "sensitivity", default=".1", minimum=D(0), maximum=D(1))
        recoverable = max(fv, viu)
        result = {
            "recoverable_amount": recoverable,
            "impairment": max(D(0), carrying - recoverable),
            "viu_downside": money(viu * (1 - sensitivity)),
            "downside_impairment": money(
                max(D(0), carrying - max(fv, viu * (1 - sensitivity)))
            ),
        }
        work = [
            "Recoverable amount = max(FVLCD, VIU). Impairment = max(0, carrying−recoverable)."
        ]
        warnings = [
            "User-supplied valuations; no CGU allocation, goodwill or reversal assessment."
        ]
    elif code == "tp_documentation":
        period(x)
        revenue = number(x, "revenue", minimum=D(0))
        group = number(x, "group_revenue", minimum=D(0))
        scope = revenue >= D(p["local_revenue"]) or (
            x.get("mne_member") is True and group >= D(p["group_revenue"])
        )
        result = {
            "local_file_threshold_screen": scope,
            "master_file_threshold_screen": scope and x.get("mne_member") is True,
            "related_party_transactions": number(
                x, "related_transactions", minimum=D(0)
            ),
            "connected_person_payments": number(x, "connected_payments", minimum=D(0)),
            "assessment": "Documentation screening; assess transaction exclusions and disclosure separately",
        }
        warnings = [
            "Arm’s length obligations can apply below documentation thresholds. Disclosure thresholds/exemptions are not concluded by this screen. Verify all statutory exclusions and connected-person rules."
        ]
        work = [
            "Compare entity and MNE group revenue with the selected period-specific documentation thresholds."
        ]
    elif code == "pillar_two":
        period(x)
        revenues = x.get("prior_revenues", [])
        if len(revenues) != 4:
            raise ValueError("Four preceding-year group revenues in EUR are required")
        scope = (
            sum(
                number({"r": r}, "r", minimum=D(0)) >= D(p["revenue_eur"])
                for r in revenues
            )
            >= 2
            and x.get("mne_group") is True
        )
        income = number(x, "globe_income")
        tax = number(x, "covered_taxes", minimum=D(0))
        deferred = number(x, "deferred_tax")
        substance = number(x, "substance_exclusion", minimum=D(0))
        etr = (tax + deferred) / income if income > 0 else None
        exposure = (
            max(D(0), D(p["minimum_rate"]) - etr) * max(D(0), income - substance)
            if etr is not None and scope
            else D(0)
        )
        result = {
            "revenue_scope_screen": scope,
            "simplified_etr": etr,
            "illustrative_top_up": money(exposure),
            "globe_loss": income <= 0,
            "safe_harbour": "Not established; CbCR quality, thresholds, eligibility and elections need verification",
            "adjustment_flags": x.get("adjustment_flags", []),
        }
        if x.get("cbcr_data_qualified") is True and str(
            dt(x, "period_start").year
        ) in p.get("cbcr_etr_rates", {}):
            cbcr_profit = number(x, "cbcr_profit")
            cbcr_tax = number(x, "cbcr_simplified_taxes", minimum=D(0))
            cbcr_etr = cbcr_tax / cbcr_profit if cbcr_profit > 0 else None
            transition_rate = D(p["cbcr_etr_rates"][str(dt(x, "period_start").year)])
            result["safe_harbour_screen"] = {
                "de_minimis": number(x, "cbcr_average_revenue", minimum=D(0))
                < D(p["cbcr_revenue_limit"])
                and number(x, "cbcr_average_profit") < D(p["cbcr_profit_limit"]),
                "simplified_etr": cbcr_etr is not None and cbcr_etr >= transition_rate,
                "routine_profits": cbcr_profit
                <= number(x, "cbcr_substance_exclusion", minimum=D(0)),
                "transition_rate": transition_rate,
                "eligibility": "Numeric tests only; qualified data, once-out-always-out and jurisdictional DMTT adoption/exclusions remain to be validated",
            }
        warnings = [
            "Preliminary assessment — not a complete DMTT calculation. Simplified ETR is not the definitive GloBE ETR. Deferred tax eligibility/recapture, allocations, elections, safe harbours and substance exclusion must be independently validated."
        ]
        work = [
            "Revenue screen: at least two of four preceding years meet the EUR threshold for an MNE. Illustrative exposure = max(0, minimum rate−simplified ETR) × max(0, income−supplied substance exclusion)."
        ]
    else:
        raise ValueError("Unknown calculator")
    return {
        "status": (
            "screening"
            if code in ["qfzp", "tp_documentation", "pillar_two"]
            else "calculated"
        ),
        "results": result,
        "schedule": schedule,
        "formula": work,
        "warnings": warnings,
        "engine_version": "3.0.0",
        "rounding": "Decimal precision 36; displayed currency half-up to 2 decimals",
    }
