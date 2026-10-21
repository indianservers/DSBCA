# Release blockers — NO GO

The application has substantially improved local verification, but production release is not approved.

| Gate | Evidence / required action |
|---|---|
| Target database | Supplied Neon is schema 0002, no installed pgvector. Provision an isolated branch, reviewed migration to 0004, vector/index tests and restore rehearsal before any authorized production migration. |
| Live research promise | OpenAI/models absent. Typed tools and controlled providers are tested; natural-language selection, real retrieval recall and professional answer quality are not. Output is deliberately restricted to source excerpts pending evaluated reasoning/entailment policy. |
| Private storage and recovery | Hosted private S3 access, signed delivery, backup/version lifecycle and restore not configured/verified. Local private storage is forbidden in production. |
| Hosting and operations | Vercel projects/token/domains, schedulers/executors, protected environments/reviewers and production alerts unavailable. No hosted deployment or CI run is claimed. |
| Credentials and roles | Rotate previously shared credentials, provision least-privilege runtime/migrator access and approve operator access policies. No remote rotation/role changes performed. |
| Mobile release | No owner signing keystore, no AAB; no macOS/Xcode/Apple signing/device tests. Native launcher/splash artwork, verified HTTPS links, push and store disclosures need approval/testing. |
| Privacy and account lifecycle | Publish approved policy/terms/AI limitations and support information; establish usable export/deletion and object/backups handling. No formal legal compliance is claimed. |
| Final acceptance | Repeat complete manual/invalid-input/authorization workflows on staged services, cross-browser/native accessibility/media/download flows, real provider delivery and final visual approval. Manual browser coverage here is a documented subset. |

Email/push are honestly inactive and may remain disabled if the owner explicitly releases without them. Full special legal/IFRS regimes remain visibly unsupported/preliminary. Those bounded optional limitations do not convert the missing core research/hosting/privacy/mobile validation into a release pass.
