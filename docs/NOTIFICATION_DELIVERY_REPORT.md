# Notification delivery verification

In-app scheduling and delivery were executed using fictional local accounts. The live HTTP acceptance path published an independently reviewed update to a subscriber, ran the durable worker and verified a notification/recipient record. This proves in-app availability, not an email inbox or device receipt.

Database jobs include dedupe/source/user/channel/due state, bounded leases/attempts and delivery logs. Renewal/preferences cancel or replan future jobs; document/obligation ownership and state are rechecked. Regulatory subscription/publication and webinar registration/publication are rechecked before delivery. Source cancellation, retry limits, preference opt-in, device removal, ambiguous delivery and duplicate prevention are covered by API/integration tests. Scheduling uses documented Dubai conventions; uncertain legal calendar cases await confirmation rather than inventing a deadline.

| Channel | Actual status |
|---|---|
| In-app | Executed with real database delivery transaction; read/unread and preferences tested. |
| Resend email | Adapter/state/idempotency tests with controlled responses only. API key and verified sender absent; no real inbox delivery. Provider acceptance is labeled submitted, not delivered. |
| Android push | Server adapter and device-token lifecycle tests only. Firebase client/service credentials and device acceptance absent. |
| iOS push | Unconfigured APNs/Firebase/signing and no physical-device test. |

An ambiguous push result is not blindly replayed. Email retry windows and provider idempotency semantics must be checked against configured service behavior. External channels are off without consent/configuration. A hosted scheduler/worker is not provisioned; CLI QA worker execution is not evidence that production scheduling exists.

Before launch: configure sender/storage/device projects and secret mounts, test lead times/timezones/renewal races with real providers, verify receipts and failure-token removal, and configure operator alerts for blocked/failed/uncertain jobs. Never relabel planned/submitted records as successful device/email delivery.
