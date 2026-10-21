# Controlled AI application tools

The Phase 2 grounded PDF answer flow remains separate from deterministic application results. New tools map fixed names to backend calculators, owner-scoped company data and published learning/update/event searches. They accept bounded structured arguments, enforce current-user authorization and record execution outcome without logging private argument bodies. They expose no SQL, shell, arbitrary database query or model-controlled destination URL.

`POST /professional/ai/tools/execute` is authenticated. ChatInput can contain a typed application_tool request. The server executes it and constructs the numerical answer directly from the deterministic result; a second model cannot change the result. Trusted metadata supplies calculator prefill/navigation or resource/compliance cards. User-selected periods can populate tool arguments. VAT tools require explicit inclusive/exclusive and treatment facts rather than guessing.

An optional official OpenAI Responses function-selection adapter selects at most one whitelisted read-only operation for a natural-language application request. It uses strict function argument schemas, store=False and no parallel tool calls. OpenAI remains unconfigured; natural-language tool selection has not been live-verified. Typed tool/chat integration is covered by actual backend tests.

All writes are excluded from model tools. The assistant may navigate to a populated application form, where the user explicitly confirms the change and the ordinary API enforces authorization/audit. Unknown or write tool names are rejected, even with a supposed confirmation token. This is deliberately more restrictive than exposing direct reminder mutation to a model.

Company tools require an explicit authorized company ID; no company is inferred from another user's data. Published resource searches return titles/links without inventing a legal explanation. PDF legal explanations still require Phase 2 approved evidence/citation validation. Historical conversations are never rewritten by regulatory update publication.
