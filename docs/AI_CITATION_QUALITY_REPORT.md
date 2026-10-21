# AI evidence and citation quality

The local suite executes real PDF parsing, page previews, chunking, PostgreSQL FTS, controlled vector fixtures, access filters, applicability/version selection, citation storage and streamed delivery. The QA dataset contains approved, rejected and superseded demonstration documents. No live OpenAI generation/embedding run occurred; the user deferred configuration.

## Defect and bounded repair

Finding: a valid substring quote and matching numbers could accompany a reversed or overbroad qualitative claim. Quote existence does not prove entailment. A scanner or second unvalidated model would not establish it either.

The server now permits complete verbatim source excerpts/sentences only: claim text equals its supporting quote, the quote exists in the supplied passage, and clipped sentence prefixes or paraphrases fail closed. Output labels excerpts as source material, not a professional conclusion. Uncited generated limitation prose is not emitted. Citations are server-built with known version/page/passage metadata; model-supplied URLs/foreign IDs and unsupported numbers are rejected. The complete sentence on page two of a cross-page chunk still maps to page two.

This is a deliberate capability restriction, not a semantic verifier. A sentence can still need adjacent exceptions/context, and an approved source can itself be wrong or outdated. The system must not be marketed as independently validating all legal reasoning. A professional synthesis mode requires a separately evaluated entailment/context policy and human source/rule review before activation.

## Executed negatives and controls

Tests cover no sources, inaccessible/foreign sources, historical/current applicability and supersession, invalid pages/quotes, invented citations, reversed negation/conditions, truncated qualifiers, conflicting/unavailable evidence, prompt-injection strings, model/provider outage, cancellation and timeout while preserving questions. Source/history text is labeled untrusted in the provider contract. The generative provider has no network/database tools. Application tool selection is separately constrained to authenticated read-only allowlists; numeric results come from Decimal engines and owner data queries are server-authorized. Write requests have no enabled execution path.

An overall 35s chat await budget bounds provider chains below the prepared function duration. Hidden SDK retries were removed; durable indexing jobs control explicit retry/checkpoint state and user retries retain request-id behavior. Actual configured-provider token billing/timeout/disconnect behavior must still be measured.

Live natural-language selection, professional answer quality, real embedding recall, native pgvector ranking, adversarial PDF/model evaluation and hosted source downloads remain release gates. Typed tools and controlled providers are never presented as proof of live GPT acceptance.
