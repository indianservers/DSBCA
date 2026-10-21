# Webinars and events

Existing Webinar content stores title/body/category/status/start/join URL; metadata holds presenter, timezone, capacity, registration state, duration, thumbnail, related resources and recording. Starts_at requires a timezone-aware timestamp and metadata timezone must be an IANA identifier. Storage is UTC; the client presents local time alongside the named event zone.

Registration locks the event row, enforces publication, future time, registration state and capacity, and reuses a unique webinar/user registration. Duplicate registration is idempotent. Cancellation releases capacity and cancels that user's pending event jobs. Recording/join data requires current active registration. Public listing/detail responses never include the private join or recording URL; only availability flags are public.

Calendar export returns a UTC ICS with stable UID and escaped text. It contains no private join URL. User export uses the system share/download sheet. Admin registration lists and CSV exports require administrator permission and record an audit event; CSV strings are protected against formula injection. No actual meeting service is provisioned by this implementation.

Local demonstration events have no fabricated joining endpoint or booked presenter. A real meeting/recording URL must be configured before joining/recording playback can be accepted as verified. Capacity, cancellation, URL restriction and timezone export are exercised by integration tests.
