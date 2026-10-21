# Calculator validation and reference sources

The test suite covers exact threshold boundaries, rounding, losses, unsupported regimes, finite-value validation, anniversary service, percentile methods, zero rates, amortization and deterministic saved results. Reference tests are in tests/test_calculators.py and tests/test_professional.py.

Examples: standard adjusted taxable income AED 900,000 with no relief/loss gives (900,000 − 375,000) × 9% = AED 47,250; VAT-inclusive AED 105 at 5% extracts AED 5; a zero-rate AED 1,200 loan over 12 payments gives AED 100 per payment; NPV of −100 at time zero and 110 after one period at 10% is zero. These examples apply only under the explicit selected assumptions and rule version.

## Primary references checked on 21 October 2026

- [FTA Small Business Relief guide](https://tax.gov.ae/Datafolder/Files/Guides/CT/Small%20Business%20Relief%20Guide%20-%20EN%20-%2029%2008%202023.pdf): standard bands and bounded SBR eligibility.
- [FTA taxable income guide](https://tax.gov.ae/DataFolder/Files/Pdf/2024/Determination%20of%20Taxable%20Income%20-%2031%2007%202024.pdf): loss-relief context.
- [FTA standard VAT rate FAQ](https://tax.gov.ae/en/faq.aspx?keyword=What+is+the+standard+rate+of+VAT+in+the+UAE%3F).
- [Ministerial Decision 229 of 2025](https://mof.gov.ae/wp-content/uploads/2025/09/EN-Ministerial-Decision-No.-229-of-2025-Regarding-Qualifying-Activities-and-Excluded-Activities.pdf): Article 3 de minimis; Article 7 applies from 1 June 2023. It repeals MD265; the engine does not classify every qualifying/excluded activity.
- [UAE Government gratuity guidance](https://u.ae/en/information-and-services/jobs/employment-in-the-private-sector/end-of-service-benefits-for-employees-in-the-private-sector).
- [FTA Transfer Pricing guide](https://tax.gov.ae/Datafolder/Files/Pdf/2023/Transfer%20Pricing%20Guide%20-%20EN%20-%2023%2010%202023.pdf): documentation revenue screening, including the distinction for non-MNE UAE groups.
- [MoF UAE Top-up Tax](https://mof.gov.ae/en/public-finance/tax/top-up-tax/) and [OECD global minimum tax developments](https://www.oecd.org/en/topics/global-minimum-tax.html): scope and current safe-harbour developments. Numeric CbCR tests remain preliminary and need qualified data, elections and jurisdictional eligibility checks.

No arbitrary market rate is seeded as approved. Financial-model rates/valuations are editable illustrative/user inputs, not fetched market observations. Legal templates require validation and a second reviewer. No source text is copied as a pretend professional certificate or authoritative internal publication.

Future validation should add approved customer/regime-specific cases, complex table/user data quality, live professional review and larger regression sets before production legal reliance.
