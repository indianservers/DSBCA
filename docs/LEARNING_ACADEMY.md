# Learning academy

Existing videos, publications, chapters and articles are reused. ContentInput adds visibility, scheduled publication and metadata for subject, kind, thumbnail, order, topics and resources. Published routes enforce scheduled time and authenticated visibility, including chapter endpoints. Learning publication does not approve AI retrieval.

The User player uses the official video_player plugin with HTTPS sources, play/pause, scrubbing, resume, speed and fullscreen. Playback position is saved every ten seconds and on pause; completion can be marked explicitly. Network/player failures show an error rather than fake playback. Published resource progress/bookmarks are owner-specific. Learning paths reference published videos/articles/chapters, track enrollment and compute completion from persisted lesson progress. Saved/recent library links remain subject to current publication visibility.

Publications support body text, chapter navigation, independent chapter progress and authorized PDF opening/downloading. Small private PDF/image uploads reuse the Phase 2 local/S3 adapter; learning assets are distinct from confidential company assets and cannot silently become AI knowledge sources. S3 downloads are short-lived; bounded local downloads use the system share/save sheet. Large videos are external streaming-appropriate URLs, not Neon binaries or API-proxied media.

Admin content forms support metadata, drafts/publication/archive, visibility and scheduled release; chapter ordering uses a transactional reorder endpoint. Paths can be created/edited/archived. No certificates or education credits are generated.

Local seed uses the official Flutter bee player sample, explicitly labeled as a player demonstration rather than Corporate Tax instruction, plus the fictional Phase 2 checklist PDF as a private chapter. Actual professional video/publication content must be supplied and reviewed by the organization. See PHASE3_TEST_RESULTS for actual playback verification rather than interpreting a configured URL as proof of playback.


Direct chapter deep links now enforce the same parent-publication visibility/scheduling rules as the chapter list and private PDF delivery. The final browser workflow resumed a saved demonstration lesson, downloaded the authorized chapter PDF and completed both path items to 100%. Browser preview cache-busting is applied only to ignored build artifacts; release hosts should use the normal Flutter asset caching/version strategy.
