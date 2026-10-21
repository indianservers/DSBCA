# AI Knowledge Base admin guide

Sign in with an existing authorized administrator. Open **AI Knowledge Base** from the existing Admin navigation.

1. Choose **+ Upload PDF**, select/drop a PDF and enter title, subject, issuer, jurisdiction, language, document type, publication/effective dates, version, applicable periods, description, keywords, scope and notes. Organization/client choices list only your memberships/owned companies. Demonstration Material must use demo scope.
2. Upload creates a pending version and a durable processing job. Run/schedule the authenticated worker. **Processing jobs** shows progress, checkpoint, attempt count and safe error codes. No background browser tab is required.
3. Inspect extracted page previews, original PDF, metadata, date applicability and source authority. Ready means processing succeeded; it does not mean approved. Approve explicitly after review. A failed/OCR-required version cannot be approved.
4. Reject, retry eligible failures, supersede or archive from document/version actions. Replace creates a new immutable version; it retains source scope and old citations. Pending metadata can be edited; approved metadata requires replacement.
5. Super administrators can save an audited assistant configuration version. All users' future requests use the latest configuration; saved answers retain their snapshot. Model IDs must be supported by the configured provider. Changing embedding model requires new document versions/reindexing. Citations remain mandatory; reranking and official verification remain disabled.
6. Analytics shows aggregate questions, subject usage, feedback, indexing failures, tokens/latency and available cost estimates. It does not provide access to private chat contents.

Development demonstration command: from repository root run `scripts/phase2.ps1 -Task seed`, then `-Task worker`. This command safeguards the isolated development database name, creates random local operator/researcher credentials in ignored `.local-phase2-access.json`, uploads only demo scope and does not approve sources. With OpenAI absent the job visibly stops at embeddings; that is expected. Do not repurpose this seed for production or change demonstrations into authoritative law.

Discuss defaults to Approved PDFs with demo excluded. Enable demonstrations explicitly for a demonstration query. Use research period filters for historical questions and inspect evidence limitations. A stopped request remains inspectable in saved history; a retry is a new provider request.
