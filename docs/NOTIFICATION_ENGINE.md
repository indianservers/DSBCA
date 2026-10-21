# Durable notification engine

notification_jobs stores user, source, channel, due timestamp, status, deduplication key, attempts, lease and safe error code. notification_deliveries records actual attempt outcomes/provider receipts. Existing Notification/NotificationRecipient tables represent in-app availability/read state. Device tokens belong to individual accounts and can be deactivated only by their owner.

Document and obligation schedules use configured days-before values, with 09:00 Asia/Dubai represented as 05:00 UTC. Renewal and preference changes cancel/rebuild unsent jobs. Webinar registration queues an event reminder; cancellation invalidates it. Reviewed published updates queue subscribed users. Admin campaigns require explicit confirmation and target category subscribers. AppSetting stores delivery template definitions without provider secrets.

The bounded worker uses PostgreSQL SKIP LOCKED claims, persisted leases, attempt limits and retries. In-app notification creation and delivered status commit in one transaction with a deterministic notification ID. Repeating the worker does not create duplicate recipients. External requests are outside the original scheduling transaction. Email uses Resend with a stable Idempotency-Key; FCM ambiguous/expired attempts become uncertain and are not automatically replayed as if delivery were known.

Status meanings: planned/retry = queued; blocked = missing provider/device configuration; delivered = in-app inbox record exists; submitted = external provider accepted the request; uncertain = reconciliation required. None of those establish a user read an email or that a device displayed a push.

Provider adapters: [Resend send-email API](https://resend.com/docs/api-reference/emails/send-email), [FCM HTTP v1](https://firebase.google.com/docs/cloud-messaging/send/v1-api). Email bodies/push previews are generic to avoid exposing company facts on external channels. FCM service-account credentials stay server-side. Android/iOS app Firebase registration, APNs credentials/entitlements and real device delivery are not configured or verified. No emails or pushes were sent during local work.

Run `scripts/phase3.ps1 -Task worker` locally or authenticate calls to `/api/v1/internal/professional/notifications/tick` using INDEXING_WORKER_SECRET/CRON_SECRET. Each call processes one bounded job; configure a supported scheduler independently. Vercel Cron/function plan limits and provider costs must be reviewed before activation. No paid service or recurring automation was created.
