# Company compliance workspace

Existing companies, company_people and company_documents are extended rather than duplicated. Profiles include legal/trading names, entity/jurisdiction/zone/licensing facts, licence/incorporation/year-end/TRN/contact/responsible-person fields. People support shareholders, directors, managers, signatories, employees and legacy partner roles.

Documents have category, title, person, issue/expiry details, number, notes, optional private attachment and active/renewed/archived/not-applicable/needs-review state. Editing a changed expiry records the previous snapshot and regenerates future jobs. Archive cancels pending reminders; past deliveries remain auditable. Existing authorized deletion APIs remain available and cancel document jobs. The new primary UI emphasizes renewal/archive to retain history.

The workspace separates recorded expiries from legal rule-derived obligations. It shows expired, due soon, upcoming and explicit review/not-applicable states without asserting that every expired record carries the same legal risk. Company selection, expiry status, document category, person and expiry-date filters are implemented; the compliance API also accepts category/person/from_date/to_date filters.

All company/people/document/attachment routes enforce current ownership. General admin metrics do not expose company details. Private company facts, people details, document details and renewal history use AES-256-GCM with DATA_ENCRYPTION_KEY, separate from JWT signing. New legacy TRN writes are stored in encrypted profile data. Preserve/back up the key securely; losing it makes those records unreadable. Existing Phase 1 plaintext TRNs require an explicitly reviewed operational migration if they are to be encrypted retroactively; Phase 3 does not silently rewrite them.

Attachments are private, hash-checked and MIME/size validated. An attachment must belong to the selected company. General administrators cannot download another owner's company attachment. Learning uploads cannot republish a company-confidential asset.
