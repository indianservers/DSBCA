# Citation validation

Every retrieved chunk has a stable UUID tied to an immutable document version. The provider receives only those IDs plus trusted title, type, issuer, heading, page range and passage. Structured output requires evidence IDs and verbatim supporting quotations for each claim.

Server validation rejects unknown IDs, missing/unequal quotation lists, quotations absent from the referenced passage, untrusted generated claim URLs and numerical details missing from supporting quotations. Current access, approval and applicability are rechecked after generation. Invalid output becomes a safe failed message; unvalidated provider text is not streamed to users.

The backend resolves supporting quotations against stored physical page text to select an exact physical page and printed label. Quotations spanning pages preserve the chunk page range. Source URLs are generated from stored version metadata, never accepted from a model. Answer evidence snapshots retain the chunk/version and configuration used.

A user can open the source card, inspect passage text and provenance, load an authenticated single-page PNG, navigate pages and open the short-lived original URL with `#page=N` where the viewer supports it. Page labels and physical page numbers are shown separately. Historical citation content survives replacement/supersession, subject to current access permissions and retention policy.

These checks establish citation identity, quote presence and page provenance. They cannot prove every generated paraphrase is semantically entailed or legally correct; professional applicability review remains necessary. Live model citation quality has not been tested because OpenAI setup was deferred. Fixture tests assert the uploaded bytes produce the cited stored page, reject forged IDs and preserve old versions.
