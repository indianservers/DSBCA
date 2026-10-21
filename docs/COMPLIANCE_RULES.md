# Compliance rules and deadlines

RuleVersion category compliance reuses the reviewed/versioned publication system. Implemented formulas are CT filing at nine calendar months after period end and VAT filing at 28 days after period end. These are bounded general formulas, not a complete registration/licensing/legal calendar.

A derived obligation requires a published applicable rule, complete start/end dates, confirmed registration and explicit absence of unhandled exceptions. Missing facts produce awaiting_confirmation with no asserted due date. Weekend dates remain awaiting confirmation unless the user has checked the calendar exception. Holidays, FTA extensions, special taxpayer regimes and registration-specific deadlines require confirmation; they are not invented.

Each derived record stores rule/version, period, sources, validation timestamp, confirmed facts and calculation basis. Manual reminders are a separate origin. Status history records completion, needs review, not applicable and supersession. Company facts can be corrected independently; replace/supersede affected obligations rather than silently rewriting historical records.

Primary references: [FTA CT filing reminder](https://tax.gov.ae/en/media.centre/News/federal.tax.authority.urges.submission.of.corporate.tax.returns.and.settlement.of.corporate.tax.liabilities.within.nine.months.from.the.end.of.the.tax.period.aspx) and [FTA VAT return/payment deadlines](https://tax.gov.ae/en/taxes/Vat/vat.topics/filing.vat.returns.and.making.payments.aspx). Licensing/document renewals use recorded dates; no universal licensing deadline is inferred.

Notification timing is independently configurable and persisted. Completion/archive/supersession cancels future unsent work; changing facts requires explicit regeneration/review. An authenticated external scheduler drives delivery, not a Flutter timer.
