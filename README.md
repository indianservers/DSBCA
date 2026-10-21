# DSBCA — Tax and Accounting Companion

Phase 1 foundation, Phase 2 PDF research and Phase 3 professional platform: separate Flutter User and Admin apps, shared Dart packages, FastAPI, SQLAlchemy/Alembic and PostgreSQL. The nine original references in `../targetUI` are preserved.

**Current status:** Phase 4 local hardening and QA are complete: 404 automated tests passed, both Flutter analyzers and web builds passed, and both internal QA debug APKs built. **Production recommendation: NO GO.** See [final release report](docs/FINAL_RELEASE_REPORT.md) and [release blockers](docs/RELEASE_BLOCKERS.md). Shared Neon remains unchanged.

Start with [Windows setup](docs/LOCAL_SETUP.md), [architecture](docs/ARCHITECTURE.md), [database schema](docs/DATABASE_SCHEMA.md), and [deployment](docs/VERCEL_DEPLOYMENT.md).

```powershell
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
# Fill database URLs and a random JWT key in backend/.env, then:
./scripts/dev.ps1 -Task install
./scripts/dev.ps1 -Task migrate
./scripts/dev.ps1 -Task seed
# In separate terminals:
./scripts/dev.ps1 -Task api
./scripts/dev.ps1 -Task user
./scripts/dev.ps1 -Task admin
```

API docs: [local OpenAPI](http://localhost:8000/docs). User: [localhost:5183](http://localhost:5183). Admin: [localhost:5184](http://localhost:5184). These are local development addresses, not production deployments. Preview ports differ from the usual 5173 because that port is already used by an unrelated project on this computer.

The configured `backend/.env` already contains the supplied Neon credentials and is ignored by Git. Preserve it. Random demonstration operator/reader login details are stored only in ignored `.local-access.json`. Review all nine screens against the originals in [UI comparison](docs/UI_COMPARISON.html).

Do not embed secrets in Dart defines. Web sessions keep tokens in memory; reloading requires signing in. Mobile refresh tokens use platform secure storage. No privileged accounts are seeded. Register a real operator account, then grant an administrative role with the explicit operator CLI.

Demonstration content is labeled and does not assert verified legislation. Videos/PDFs without configured URLs show an unavailable state. Discuss now integrates approved PDF research through a configurable server-side provider. OpenAI setup is deferred, so live generation is unavailable until configured. The professional toolkit now contains 14 deterministic calculators with explicit coverage limits. Server email/push adapters are implemented; device setup and actual external delivery remain unverified.


Phase 2 implementation and activation status: [report](docs/PHASE2_ARCHITECTURE.md), [tests](docs/PHASE2_TEST_RESULTS.md), [environment](docs/AI_ENV_CONFIGURATION.md), [deployment](docs/PHASE2_DEPLOYMENT.md). Use `scripts/phase2.ps1` for the isolated local development database and API port 8002. Local previews: [User](http://localhost:5193/#/discuss), [Admin](http://localhost:5194/). Phase 2 has not migrated the shared Neon database or been deployed. The live AI acceptance workflow remains pending credentials.


Phase 3: [architecture](docs/PHASE3_ARCHITECTURE.md), [test results and workflows](docs/PHASE3_TEST_RESULTS.md), [calculator coverage](docs/CALCULATOR_VALIDATION.md), [API](docs/PHASE3_API_REFERENCE.md), [deployment](docs/PHASE3_DEPLOYMENT.md). Use `scripts/phase3.ps1` for isolated local migration, fixtures, API, bounded notification worker, tests and web builds. Current previews: [User](http://localhost:5203/) and [Admin](http://localhost:5204/); API: [localhost:8003/docs](http://localhost:8003/docs). Local fixture credentials are in ignored `.local-phase3-access.json`. The seeder simulates two local reviewers; these fixtures are not production professional approval.

Phase 4 previews: User http://localhost:5303/ and Admin http://localhost:5304/; API http://localhost:8004/docs. Run `scripts/phase4.ps1` for isolated QA tasks. Credentials remain in ignored `.local-phase4-access.json`. QA web archives and debug APKs are in `output/release`; hashes are in `docs/phase4/artifacts.json`. These artifacts use local API origins and are not production releases.
