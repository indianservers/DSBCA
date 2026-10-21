# Web and API performance measurements

Environment: Windows, Flutter 3.38.5 / Dart 3.10.4, JavaScript release builds, loopback HTTP, PostgreSQL 17.6 and small fictional QA fixtures. These results do not predict hosted/mobile-network performance.

| Operation | Requests / concurrency | Median ms | p95 ms | Errors |
|---|---:|---:|---:|---:|
| dashboard | 20 / 4 | 96.06 | 127.91 | 0 |
| content_list | 20 / 4 | 32.01 | 47.82 | 0 |
| company_compliance | 20 / 4 | 50.13 | 191.74 | 0 |
| admin_pagination | 20 / 4 | 44.12 | 76.27 | 0 |
| calculator_npv | 10 / 2 | 14.56 | 18.39 | 0 |
| profile_writes | 12 / 2 | 10.31 | 12.53 | 0 |
| private_learning_pdf | 10 / 2 | 30.02 | 36.35 | 0 |

Typed chat SSE: first event 38.94 ms, first validated answer 64.8 ms, total 65.57 ms. This is a deterministic selected application tool, not live model time-to-first-token. PostgreSQL FTS plus explicit QA synthetic exact vectors took median 31.43 ms across five retrievals; no native pgvector/OpenAI latency was measured.

Browser readiness proxy (one sample each): User 3825 ms, Admin 3515 ms, navigation through attachment of Flutter's accessibility activation control. Browser/renderer caches were already warm; each application origin was new. Instrumentation/IPC is included. These are not LCP, cold-cache TTI, mobile-throttled or cross-browser results.

| Build | Main JS bytes | Main JS gzip bytes | All output bytes |
|---|---:|---:|---:|
| dsbca_user | 3,483,019 | 1,026,334 | 33,890,462 |
| dsbca_admin | 3,118,628 | 914,971 | 33,533,910 |

All-output size includes renderer alternatives/assets and is not the initial transfer. Gzip sizes are locally calculated, not a measured Vercel CDN transfer. Tree shaking is enabled. The optional WASM compatibility dry run is disabled because platform plugins are not fully WASM compatible; JavaScript builds are the verified target.

## Measured repair

A fresh Python process with warm filesystem cache imported the API in 4964.34 ms before and 2898.56 ms after lazy imports of optional AI SDK, PDF and S3 dependencies (one paired local sample). Ordinary API startup no longer imports those unused providers. This does not claim a Vercel cold-start result. Runtime/test dependencies were separated and pinned; compatible Linux wheel payload is 58,403,046 bytes compressed and 145,400,973 bytes expanded, excluding platform/runtime build overhead.

Request correlation/duration telemetry, bounded pools/timeouts, no-store private responses and bootstrap no-cache policies were added. Query plans did not justify speculative new indexes on the tiny QA corpus. There is no fabricated pre-change HTTP baseline or claimed statistical improvement from one sample.

Before release, repeat cold/warm browser and API measurements on Vercel/Neon, with representative corpus/company sizes, device/network throttling, CDN headers, real model/storage providers and approved concurrency limits. Full list virtualization, large-account company selection beyond first-page UI, renderer/font transfer, hosted monitoring and native vector plans remain measurement targets.
