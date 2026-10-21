"""Reviewed reference templates. Drafts only; a second administrator must approve publication."""

VERIFIED = "2026-10-21"


def source(title, url):
    return {
        "title": title,
        "url": url,
        "verified_on": VERIFIED,
        "authority": "Official primary source",
    }


CT = source(
    "FTA Small Business Relief guide / standard CT framework",
    "https://tax.gov.ae/Datafolder/Files/Guides/CT/Small%20Business%20Relief%20Guide%20-%20EN%20-%2029%2008%202023.pdf",
)
LOSSES = source(
    "FTA Determination of Taxable Income guide",
    "https://tax.gov.ae/DataFolder/Files/Pdf/2024/Determination%20of%20Taxable%20Income%20-%2031%2007%202024.pdf",
)
VAT = source(
    "FTA standard VAT rate FAQ",
    "https://tax.gov.ae/en/faq.aspx?keyword=What+is+the+standard+rate+of+VAT+in+the+UAE%3F",
)
QFZP = source(
    "Ministerial Decision 229 of 2025 — Article 3",
    "https://mof.gov.ae/wp-content/uploads/2025/09/EN-Ministerial-Decision-No.-229-of-2025-Regarding-Qualifying-Activities-and-Excluded-Activities.pdf",
)
GRATUITY = source(
    "UAE Government: private-sector end-of-service benefits",
    "https://u.ae/en/information-and-services/jobs/employment-in-the-private-sector/end-of-service-benefits-for-employees-in-the-private-sector",
)
TP = source(
    "FTA Transfer Pricing guide — documentation thresholds",
    "https://tax.gov.ae/Datafolder/Files/Pdf/2023/Transfer%20Pricing%20Guide%20-%20EN%20-%2023%2010%202023.pdf",
)
DMTT = source(
    "Ministry of Finance — UAE Top-up Tax",
    "https://mof.gov.ae/en/public-finance/tax/top-up-tax/",
)
CBCR = source(
    "OECD global minimum tax, January 2026 developments",
    "https://www.oecd.org/en/topics/global-minimum-tax.html",
)
CT_DUE = source(
    "FTA: filing and payment within nine months",
    "https://tax.gov.ae/en/media.centre/News/federal.tax.authority.urges.submission.of.corporate.tax.returns.and.settlement.of.corporate.tax.liabilities.within.nine.months.from.the.end.of.the.tax.period.aspx",
)
VAT_DUE = source(
    "FTA VAT return and payment deadlines",
    "https://tax.gov.ae/en/taxes/Vat/vat.topics/filing.vat.returns.and.making.payments.aspx",
)
PERIOD = {"period_start": "2026-01-01", "period_end": "2026-12-31"}
TEMPLATES = [
    {
        "code": "corporate_tax",
        "valid_from": "2023-06-01",
        "parameters": {
            "zero_band": "375000",
            "rate": ".09",
            "loss_limit": ".75",
            "sbr_revenue": "3000000",
            "sbr_end": "2026-12-31",
        },
        "sources": [CT, LOSSES],
        "validation_cases": [
            {
                "inputs": {**PERIOD, "accounting_profit": "900000"},
                "expected": {"corporate_tax": "47250.00"},
            },
            {
                "inputs": {**PERIOD, "accounting_profit": "375000"},
                "expected": {"corporate_tax": "0.00"},
            },
        ],
    },
    {
        "code": "vat",
        "valid_from": "2018-01-01",
        "parameters": {"standard_rate": ".05"},
        "sources": [VAT],
        "validation_cases": [
            {
                "inputs": {"amount": "105", "inclusive": True},
                "expected": {"output_vat": "5.00"},
            }
        ],
    },
    {
        "code": "qfzp",
        "valid_from": "2023-06-01",
        "parameters": {"percentage": ".05", "cap": "5000000"},
        "sources": [QFZP],
        "validation_cases": [
            {
                "inputs": {
                    **PERIOD,
                    "total_revenue": "20000000",
                    "non_qualifying": "3000000",
                },
                "expected": {"de_minimis_pass": False},
            }
        ],
    },
    {
        "code": "gratuity",
        "valid_from": "2022-02-02",
        "parameters": {"first_days": "21", "later_days": "30", "cap_months": "24"},
        "sources": [GRATUITY],
        "validation_cases": [
            {
                "inputs": {
                    "employment_start": "2020-01-01",
                    "employment_end": "2026-01-01",
                    "monthly_basic": "15000",
                },
                "expected": {"gratuity": "67500.00"},
            }
        ],
    },
    {
        "code": "tp_documentation",
        "valid_from": "2023-06-01",
        "parameters": {"local_revenue": "200000000", "group_revenue": "3150000000"},
        "sources": [TP],
        "validation_cases": [
            {
                "inputs": {**PERIOD, "revenue": "200000000"},
                "expected": {"local_file_threshold_screen": True},
            }
        ],
    },
    {
        "code": "pillar_two",
        "valid_from": "2025-01-01",
        "parameters": {
            "revenue_eur": "750000000",
            "minimum_rate": ".15",
            "cbcr_etr_rates": {"2025": ".16", "2026": ".17", "2027": ".17"},
            "cbcr_revenue_limit": "10000000",
            "cbcr_profit_limit": "1000000",
        },
        "sources": [DMTT, CBCR],
        "validation_cases": [
            {
                "inputs": {
                    **PERIOD,
                    "prior_revenues": ["750000000"] * 4,
                    "mne_group": True,
                    "globe_income": "1000000",
                    "covered_taxes": "100000",
                },
                "expected": {"illustrative_top_up": "50000.00"},
            }
        ],
    },
    {
        "code": "ct_filing",
        "category": "compliance",
        "valid_from": "2023-06-01",
        "parameters": {"months_after": 9},
        "sources": [CT_DUE],
        "validation_cases": [
            {"period_end": "2025-12-31", "expected_due": "2026-09-30"}
        ],
    },
    {
        "code": "vat_filing",
        "category": "compliance",
        "valid_from": "2018-01-01",
        "parameters": {"days_after": 28},
        "sources": [VAT_DUE],
        "validation_cases": [
            {"period_end": "2026-03-31", "expected_due": "2026-04-28"}
        ],
    },
]
for t in TEMPLATES:
    t.update(
        {
            "version": "reference-2026-10-21",
            "category": t.get("category", "calculator"),
            "valid_to": "2026-12-31",
        }
    )
