# AI chatbot architecture

All routes below are under `/api/v1`. Existing bearer authentication/session revocation applies. Flutter never calls OpenAI directly.

## Request flow

1. Validate owner, request identifier, question length, selected subject and complete research period. A year without an explicit period prompts clarification. Entity classification and other missing material facts are delegated to the grounded structured response; there is no separate autonomous legal fact classifier.
2. Lock the user row, reserve a bounded daily token budget, enforce request/rate limits and persist user/assistant messages. Repeated identifiers return the existing assistant; a changed question with the same identifier returns 409.
3. Retrieve accessible, applicable, processed and approved PDF evidence. Unknown applicability is disclosed; explicit historical research requires known applicability dates. No results produces an evidence-gap response, never an assertion that no legal rule exists.
4. Send bounded history and evidence as untrusted data to the configured provider with a strict JSON schema. No web, shell or application tools are exposed to the model.
5. Validate passage IDs, verbatim supporting quotations, numerical claims and trusted page metadata. Recheck source approval and ACL before persisting the answer/evidence snapshot.
6. Stream validated text to Flutter and retain status, usage and configuration version. Structured output is buffered until validation; provider tokens are not streamed before checks. This adds latency but avoids exposing fabricated citations before rejection.

## Provider selection

`ChatModelProvider`, `EmbeddingProvider` and `RerankingProvider` are separate protocols. Actual OpenAI integration uses `AsyncOpenAI.responses.create`, strict JSON schema, `store=False` and no tools. Embeddings use 512 dimensions with a compatible configured model. Temperature is omitted unless its support is explicitly configured. Model names are not defaulted silently. Optional fast model is stored but automatic routing is not enabled. Reranking is rejected until an implementation is configured.

Official references checked during implementation: [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [embeddings](https://developers.openai.com/api/docs/guides/embeddings). Installed SDK request shapes are covered by a mocked SDK test; no live model was called.

## User API

- `GET /ai/capabilities`: provider/storage availability and mode.
- `GET, POST /ai/conversations`; `GET, DELETE /ai/conversations/{id}`; `GET /ai/conversations/{id}/messages`: owner-only paginated history and soft deletion.
- `POST /ai/chat`, `POST /ai/chat/stream`: JSON or SSE orchestration. SSE emits accepted, status, citations, answer_delta and done.
- `POST /ai/messages/{id}/cancel`; `POST /ai/feedback`: owner-only cancellation and feedback.
- `GET /ai/sources/{id}`: trusted source card and passage.
- `GET /ai/documents/{version_id}/pages/{page}` and `/preview`: page text/tables/provenance and an authenticated PNG.
- `GET /ai/documents/{version_id}/download`: authorized short-lived URL or local access ticket.
- `GET /ai/files/{version_id}?ticket=...`: local development original, with session/account/ACL checks and no-store headers.

OpenAPI at `/docs` is the authoritative schema. Cancellation cannot retract an already sent provider request; it prevents the answer from replacing the cancelled state. Retrying creates a new request and may incur another provider charge.
