"""Form contracts shared by REST clients and whitelisted AI tools."""


def field(key, label, default="", kind="number", options=None):
    return {
        "key": key,
        "label": label,
        "default": default,
        "type": kind,
        **({"options": options} if options else {}),
    }


F = field
PERIOD = [
    F("period_start", "Financial period start", "2026-01-01", "date"),
    F("period_end", "Financial period end", "2026-12-31", "date"),
]
FINANCE = [
    F("principal", "Principal / carrying amount", "100000"),
    F("annual_rate", "Nominal annual rate (decimal)", "0.06"),
    F("periods", "Number of payments", "36"),
    F("periods_per_year", "Payments per year", "12"),
]
CATALOGUE = {
    "corporate_tax": {
        "title": "UAE Corporate Tax",
        "group": "Tax",
        "rule_required": True,
        "fields": PERIOD
        + [
            F("accounting_profit", "Accounting profit / loss", "900000"),
            F("exempt_income", "Exempt income", "0"),
            F("non_deductible", "Non-deductible expenses", "0"),
            F("adjustments", "Signed taxable adjustments", "0"),
            F("losses_brought_forward", "Eligible losses brought forward", "0"),
            F("losses_requested", "Eligible losses to use", "0"),
            F(
                "treatment",
                "Tax treatment",
                "standard",
                "select",
                ["standard", "free_zone", "special"],
            ),
            F("sbr_elected", "Elect Small Business Relief", False, "bool"),
            F("revenue", "Current period revenue", "0"),
        ]
        + [
            F(k, t, False, "bool")
            for k, t in [
                ("resident", "UAE resident person"),
                (
                    "prior_revenue_eligible",
                    "All relevant prior revenues meet SBR limit",
                ),
                ("not_qfzp", "Not a QFZP"),
                ("not_large_mne", "Not an excluded large MNE member"),
                ("sbr_conditions_confirmed", "All other SBR conditions verified"),
            ]
        ],
    },
    "vat": {
        "title": "UAE VAT",
        "group": "Tax",
        "rule_required": True,
        "fields": PERIOD
        + [
            F("amount", "Transaction amount (AED)", "10000"),
            F(
                "treatment",
                "Treatment",
                "standard",
                "select",
                ["standard", "zero", "exempt", "out_of_scope"],
            ),
            F("inclusive", "Amount includes VAT", False, "bool"),
            F("direction", "Direction", "output", "select", ["output", "input"]),
            F("recoverable", "Input VAT recoverable", True, "bool"),
            F(
                "transactions",
                "Optional transaction array (overrides single amount)",
                "",
                "json",
            ),
        ],
    },
    "qfzp": {
        "title": "QFZP assessment studio",
        "group": "Tax",
        "rule_required": True,
        "fields": PERIOD
        + [
            F("total_revenue", "Total revenue", "20000000"),
            F(
                "non_qualifying",
                "Non-qualifying revenue excluding next field",
                "3000000",
            ),
            F(
                "excluded_activity",
                "Excluded-activity revenue (no double counting)",
                "0",
            ),
            F(
                "excluded_from_denominator",
                "Verified statutory revenue exclusions",
                "0",
            ),
            F("qualifying_income", "Reported qualifying income", "0"),
        ]
        + [
            F(k, k.replace("_", " ").capitalize(), False, "bool")
            for k in [
                "adequate_substance",
                "qualifying_activities",
                "transfer_pricing_compliance",
                "audited_financials",
                "no_standard_election",
                "revenue_classification_verified",
            ]
        ],
    },
    "gratuity": {
        "title": "UAE end-of-service gratuity",
        "group": "Employment",
        "rule_required": True,
        "fields": [
            F("employment_start", "Employment start", "2020-01-01", "date"),
            F("employment_end", "Employment end", "2026-01-01", "date"),
            F("monthly_basic", "Monthly basic salary", "15000"),
            F("monthly_total_wage", "Monthly total wage for statutory cap", "15000"),
            F("unpaid_days", "Unpaid absence days", "0"),
            F(
                "regime",
                "Legal regime",
                "federal",
                "select",
                ["federal", "DIFC", "ADGM", "other"],
            ),
            F(
                "arrangement",
                "Employment arrangement",
                "full_time",
                "select",
                ["full_time", "part_time", "savings_scheme"],
            ),
            F(
                "worker",
                "Worker classification",
                "foreign",
                "select",
                ["foreign", "national"],
            ),
        ],
    },
    "tp_range": {
        "title": "Arm’s length range",
        "group": "Transfer Pricing",
        "fields": [
            F("metric", "Financial metric and unit", "Operating margin (%)", "text"),
            F(
                "observations",
                "Comparable observations (JSON array)",
                "[2,4,6,8,10]",
                "json",
            ),
            F("tested_party", "Tested party result", "5"),
            F(
                "method",
                "Percentile interpolation",
                "inclusive",
                "select",
                ["inclusive", "exclusive"],
            ),
        ],
    },
    "interest_benchmark": {
        "title": "Interest rate benchmarking",
        "group": "Transfer Pricing",
        "fields": [f for f in FINANCE if f["key"] != "annual_rate"]
        + [
            F("currency", "Currency", "AED", "text"),
            F("loan_date", "Loan date", "2026-01-01", "date"),
            F("benchmark_rate", "User-supplied reference rate (decimal)", ""),
            F("spread", "Spread (decimal)", "0.02"),
            F("range_low", "Approved range lower rate", ""),
            F("range_high", "Approved range upper rate", ""),
            F(
                "repayment_profile",
                "Repayment profile",
                "amortizing",
                "select",
                ["amortizing", "bullet"],
            ),
        ],
    },
    "tp_documentation": {
        "title": "TP documentation assessment",
        "group": "Transfer Pricing",
        "rule_required": True,
        "fields": PERIOD
        + [
            F("revenue", "Entity revenue", "0"),
            F("group_revenue", "Consolidated MNE revenue (AED)", "0"),
            F("mne_member", "Member of an MNE group", False, "bool"),
            F("related_transactions", "Related-party transaction value", "0"),
            F("connected_payments", "Connected-person payments", "0"),
        ],
    },
    "pillar_two": {
        "title": "Pillar Two / UAE DMTT screening",
        "group": "Pillar Two",
        "rule_required": True,
        "fields": PERIOD
        + [
            F(
                "prior_revenues",
                "Four prior-year group revenues in EUR",
                "[0,0,0,0]",
                "json",
            ),
            F("mne_group", "Multinational enterprise group", False, "bool"),
            F("globe_income", "Jurisdictional GloBE income / loss", "0"),
            F("covered_taxes", "Adjusted covered taxes", "0"),
            F("deferred_tax", "Eligible deferred tax adjustment", "0"),
            F("substance_exclusion", "Verified substance-based exclusion", "0"),
            F(
                "adjustment_flags",
                "Outstanding elections / adjustment flags",
                "[]",
                "json",
            ),
            F(
                "cbcr_data_qualified",
                "Qualified CbCR data and eligibility verified",
                False,
                "bool",
            ),
            F("cbcr_average_revenue", "Three-year average CbCR revenue (EUR)", "0"),
            F(
                "cbcr_average_profit",
                "Three-year average CbCR profit / loss (EUR)",
                "0",
            ),
            F("cbcr_profit", "CbCR current profit / loss (EUR)", "0"),
            F("cbcr_simplified_taxes", "Simplified covered taxes (EUR)", "0"),
            F(
                "cbcr_substance_exclusion",
                "Verified CbCR substance exclusion (EUR)",
                "0",
            ),
        ],
    },
    "lease": {
        "title": "IFRS 16 lease liability",
        "group": "IFRS",
        "fields": [f for f in FINANCE if f["key"] != "principal"]
        + [
            F("payment", "Fixed periodic lease payment", "3000"),
            F("timing", "Payment timing", "arrears", "select", ["arrears", "advance"]),
        ],
    },
    "effective_interest": {
        "title": "Effective interest method",
        "group": "IFRS",
        "fields": FINANCE
        + [F("cash_payment", "Periodic contractual cash payment", "3000")],
    },
    "npv": {
        "title": "Present value / NPV",
        "group": "IFRS",
        "fields": [
            F("discount_rate", "Rate per cash-flow period (decimal)", "0.08"),
            F(
                "cashflows",
                "Equal-period cash flows including time zero",
                "[-100000,40000,40000,40000]",
                "json",
            ),
        ],
    },
    "depreciation": {
        "title": "Depreciation schedule",
        "group": "IFRS",
        "fields": [
            F("cost", "Asset cost", "100000"),
            F("residual", "Residual value", "10000"),
            F("periods", "Useful life in periods", "5"),
            F(
                "method",
                "Method",
                "straight_line",
                "select",
                ["straight_line", "reducing_balance"],
            ),
            F("reducing_rate", "Reducing-balance rate (decimal)", "0.2"),
        ],
    },
    "impairment": {
        "title": "Asset impairment sensitivity",
        "group": "IFRS",
        "fields": [
            F("carrying", "Carrying amount", "100000"),
            F("fair_value_less_costs", "Fair value less costs of disposal", "80000"),
            F("value_in_use", "Value in use", "90000"),
            F("sensitivity", "Downside VIU reduction (decimal)", "0.1"),
        ],
    },
    "loan": {"title": "Loan amortization", "group": "IFRS", "fields": FINANCE},
}
