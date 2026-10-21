# Calculator accuracy and coverage

Fourteen Decimal engines and stored rule-case validation were inspected and re-executed through the backend suite. Formula/rate changes were not made to disguise a failed expected result. Monetary rounding is explicit half-up; schedules and supported input bounds remain documented in CALCULATOR_RULE_ENGINE.md and CALCULATOR_VALIDATION.md.

| Engine | Checked scope / important limit |
|---|---|
| Corporate Tax | Standard taxable-income adjustments, exempt/non-deductible amounts, 75% loss cap, bands and explicit SBR facts/period; special regimes restricted. |
| VAT | Inclusive/exclusive, standard/zero/exempt/out-of-scope, per-line rounding, recoverable input/output/net; classification supplied by user. |
| QFZP | Adjusted denominator/exclusions, lower-of de minimis threshold, separate conditions/missing facts; screening only. |
| Gratuity | Eligible federal foreign full-time framework, actual anniversary fractions, unpaid convention, 21/30-day bands and wage cap; other employment regimes unsupported. |
| TP range | Selected comparable data and inclusive/exclusive percentile interpolation; no automatic comparable selection or arm's-length opinion. |
| TP interest | User-supplied currency/date/benchmark/spread/range and repayment convention; no invented market rate. |
| TP documentation | Revenue/group thresholds as a preliminary obligation screen; not full disclosure/legal classification. |
| Pillar Two | Group scope/two-of-four screen, simplified ETR/loss/top-up and qualified-data safe-harbour screens; not a complete GloBE return. |
| Lease | Fixed-payment PV/amortization, advance/arrears and supplied discount rate; not full variable-payment/modification accounting. |
| Effective interest | Supplied yield/cash flows and reconciliation; not an unsupervised fair-value/yield judgment. |
| NPV | Equal-period discounted cash flows including time zero and zero-rate case. |
| Depreciation | Supported straight-line/reducing methods, residual/useful-life bounds; no automatic policy judgment. |
| Impairment | Simplified VIU/FVLCD and sensitivity with user assumptions; not a full allocation/disclosure opinion. |
| Loan | Annuity/bullet/fixed principal, zero rate, final reconciliation and early-repayment validation. |

The suite contains 29 pure calculator tests plus API/rule/template/tool cases. Eight draft source-backed templates have stored expected cases and date windows. Local QA simulates independent review for testing only. Approved versions are immutable through lifecycle transitions; superseded rules cannot be republished. New professional approval requires a new version and explicit applicability review. Saved inputs/results and rule snapshots reproduce historical runs; foreign histories are inaccessible. Typed chat results match the same engine exactly.

The demonstrated CT case is AED 47,250 for AED 900,000 supplied accounting profit in the supported 2026 standard scenario. This is a test fixture, not advice for a real entity. Production activation requires qualified review of source versions, legal facts, edge conditions and any unsupported scenarios. The existing coverage warnings must remain visible.
