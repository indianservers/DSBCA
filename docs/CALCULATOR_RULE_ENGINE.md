# Calculator rule engine

Financial arithmetic lives in backend/app/calculators/engine.py, outside Flutter. Decimal precision is 36; currency is displayed using ROUND_HALF_UP to 2 decimals. Input values must be finite and bounded. Schedules are bounded at 1,200 periods, observations at 1,000 and VAT transactions at 500. Flutter uses the catalogue's field contract, editable inputs and backend results; it does not simulate tax outputs.

## Rule publication

Statutory engines require exactly one published rule covering the complete supplied period. Zero/multiple matches return a restricted state. Rule versions have code, category, immutable parameters, official sources, applicability, reference cases, validation timestamp, author and independent publisher. New versions are drafts. All supplied reference cases must pass before publication, and a different administrator must publish. Published windows cannot overlap. Superseding an old version does not mutate saved calculation snapshots.

Source domains are restricted to official UAE authorities, OECD and IFRS sources. Each source requires title and verification date. Reference templates are not automatically published in production or added to the AI knowledge base. Source validity and a passing case are not a complete legal review: the reviewer must assess completeness, regime and dates.

## Implemented coverage

| Engine | Coverage |
|---|---|
| Corporate Tax | Standard taxable-person arithmetic, signed adjustments, user-confirmed exempt income and eligible losses, rule-controlled loss cap/rates, explicit SBR conditions and expiry |
| VAT | Inclusive/exclusive, per-transaction classifications, recoverable input/output and net arithmetic; half-up transaction tax |
| QFZP | Adjusted de minimis screen plus independent condition checklist; no definitive status or Free Zone tax computation |
| Gratuity | Federal full-time foreign-worker bands, anniversary service/fractions, unpaid-leave convention and total-wage cap; unsupported regimes restricted |
| TP range | Selected observations, inclusive/exclusive linearly interpolated quartiles and tested-party placement; no automatic outlier removal |
| Interest benchmarking | User-supplied reference/spread/range, currency/date and amortizing/bullet schedules; no market rate feed |
| TP documentation | Entity/MNE revenue threshold screen; disclosure thresholds and transaction exclusions require separate review |
| Pillar Two | Four-prior-year MNE revenue screen, simplified ETR/loss/top-up sensitivity, supplied deferred tax/SBIE and qualified-data CbCR numeric screens |
| IFRS 16 | Fixed-payment lease liability/arrears-or-advance schedule; no complete ROU accounting or modifications |
| Effective interest | Supplied effective yield and cash payment schedule; no automatic IRR solution |
| NPV | Equal-period cash flows including time zero |
| Depreciation | Straight-line or supplied reducing-balance rate, residual floor |
| Impairment | Supplied VIU/FVLCD sensitivity; no CGU/goodwill allocation or reversal assessment |
| Loan | Nominal-rate equal-period amortization with final balancing payment |

Unknown special regimes, insufficient eligibility or absent rules do not produce a supported tax conclusion. The DMTT result always states: Preliminary assessment — not a complete DMTT calculation. CbCR screening does not establish eligibility or UAE adoption of every OECD simplification. Reference templates deliberately stop at 31 December 2026; a later period needs a reviewed version.

Saved runs retain original inputs, result, rule snapshot and engine version. History and JSON export are owner-only. Copy/share returns those actual workings. PDF result export is optional and is not implemented; authorized JSON export is available.
