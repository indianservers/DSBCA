import 'dart:async';
import 'media.dart';
import 'dart:convert';
import 'package:share_plus/share_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:video_player/video_player.dart';

class AcademyDetail extends StatefulWidget {
  const AcademyDetail({
    super.key,
    required this.api,
    required this.kind,
    required this.id,
  });
  final ApiClient api;
  final String kind, id;
  @override
  State<AcademyDetail> createState() => _Academy();
}

class _Academy extends State<AcademyDetail> {
  Json? data, state, registration, chapter;
  List<Json> chapters = [];
  String? error;
  bool busy = false;
  VideoPlayerController? video;
  Timer? saver;
  int lastPosition = -1;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    if (mounted) setState(() => error = null);
    saver?.cancel();
    video?.removeListener(refreshVideo);
    await video?.dispose();
    video = null;
    try {
      final resource = await widget.api.get('/${widget.kind}/${widget.id}');
      Json? saved;
      if (widget.api.signedIn) {
        saved = await widget.api.get(
          '/professional/learning/${widget.kind}/${widget.id}/state',
        );
      }
      final parts = widget.kind == 'publications'
          ? (await widget.api.page('/publications/${widget.id}/chapters')).items
          : <Json>[];
      if (widget.kind == 'webinars' && widget.api.signedIn) {
        registration = await widget.api.get(
          '/professional/webinars/${widget.id}/registration',
        );
      }
      if (!mounted) return;
      setState(() {
        data = resource;
        state = saved;
        chapters = parts;
      });
      if (widget.kind == 'videos' && resource['media_url'] != null) {
        final uri = Uri.parse(resource['media_url'] as String);
        if (uri.scheme != 'https') throw StateError('HTTPS media required');
        final controller = VideoPlayerController.networkUrl(uri);
        video = controller;
        await controller.initialize().timeout(const Duration(seconds: 30));
        if (!mounted) return;
        await controller.seekTo(
          Duration(
            seconds: ((saved?['progress'] as Map?)?['position'] as int?) ?? 0,
          ),
        );
        controller.addListener(refreshVideo);
        saver = Timer.periodic(const Duration(seconds: 10), (_) => persist());
        setState(() {});
      }
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  void refreshVideo() {
    if (mounted) setState(() {});
  }

  Future<void> persist({bool complete = false}) async {
    if (!widget.api.signedIn) return;
    final pos = video?.value.position.inSeconds ?? 0;
    if (pos == lastPosition && !complete) return;
    lastPosition = pos;
    try {
      final r = await widget.api.put(
        '/professional/learning/${widget.kind}/${widget.id}/progress',
        {
          'position': pos,
          'completed':
              complete || ((state?['progress'] as Map?)?['completed'] == true),
        },
      );
      if (mounted) setState(() => state = {...state ?? {}, 'progress': r});
    } catch (e) {
      if (mounted) setState(() => error = 'Progress not saved: ${apiError(e)}');
    }
  }

  @override
  void dispose() {
    if (video?.value.isInitialized == true && widget.api.signedIn) {
      unawaited(persist());
    }
    saver?.cancel();
    video?.removeListener(refreshVideo);
    video?.dispose();
    super.dispose();
  }

  Future<void> bookmark() async {
    try {
      final saved = state?['bookmarked'] != true;
      await widget.api.put(
        '/professional/learning/${widget.kind}/${widget.id}/bookmark',
        {'saved': saved},
      );
      if (mounted) {
        setState(() => state = {...state ?? {}, 'bookmarked': saved});
      }
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Future<void> open(String? url) async {
    if (url == null || Uri.tryParse(url)?.scheme != 'https') {
      setState(
        () => error = 'An approved HTTPS resource URL is not configured.',
      );
      return;
    }
    if (!await launchUrl(Uri.parse(url)) && mounted) {
      setState(() => error = 'Unable to open resource.');
    }
  }

  Future<void> eventAction(String action) async {
    setState(() => busy = true);
    try {
      if (action == 'cancel') {
        await widget.api.delete('/professional/webinars/${widget.id}/register');
      } else if (action == 'register') {
        await widget.api.post(
          '/professional/webinars/${widget.id}/register',
          {},
        );
      } else {
        final r = await widget.api.get(
          '/professional/webinars/${widget.id}/join',
        );
        await open(
          r[action == 'recording' ? 'recording_url' : 'join_url'] as String?,
        );
        return;
      }
      registration = await widget.api.get(
        '/professional/webinars/${widget.id}/registration',
      );
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> openAsset(String? id, {String? fallback}) async {
    if (id == null) {
      await open(fallback);
      return;
    }
    try {
      await openPrivateMedia(widget.api, id);
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Widget player() {
    final c = video!;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AspectRatio(aspectRatio: c.value.aspectRatio, child: VideoPlayer(c)),
        VideoProgressIndicator(c, allowScrubbing: true),
        Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            IconButton(
              tooltip: c.value.isPlaying ? 'Pause' : 'Play',
              onPressed: () async {
                if (c.value.isPlaying) {
                  await c.pause();
                  await persist();
                } else {
                  await c.play();
                }
              },
              icon: Icon(c.value.isPlaying ? Icons.pause : Icons.play_arrow),
            ),
            Text(
              '${c.value.position.inSeconds}s / ${c.value.duration.inSeconds}s',
            ),
            DropdownButton<double>(
              value: c.value.playbackSpeed,
              items: [.5, 1.0, 1.5, 2.0]
                  .map((v) => DropdownMenuItem(value: v, child: Text('${v}x')))
                  .toList(),
              onChanged: (v) => c.setPlaybackSpeed(v!),
            ),
            IconButton(
              tooltip: 'Full screen',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  fullscreenDialog: true,
                  builder: (_) => Scaffold(
                    appBar: AppBar(title: const Text('Video playback')),
                    body: Center(
                      child: AspectRatio(
                        aspectRatio: c.value.aspectRatio,
                        child: VideoPlayer(c),
                      ),
                    ),
                  ),
                ),
              ),
              icon: const Icon(Icons.fullscreen),
            ),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final x = data;
    final meta = (x?['metadata_extra'] as Map?) ?? {};
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              IconButton(
                onPressed: () =>
                    context.canPop() ? context.pop() : context.go('/learn'),
                icon: const Icon(Icons.arrow_back),
              ),
              Expanded(
                child: Text(
                  x?['title'] as String? ?? 'Learning resource',
                  style: DSBTypography.heading,
                ),
              ),
              IconButton(
                tooltip: 'My learning',
                onPressed: () => context.push('/learning-library'),
                icon: const Icon(Icons.school_outlined),
              ),
            ],
          ),
          if (error != null) DSBErrorState(error!, onRetry: load),
          if (x == null) const DSBLoadingState(),
          if (x != null) ...[
            const SizedBox(height: 16),
            if (x['demo'] == true)
              const DSBCard(
                color: DSBColors.peach,
                child: Text(
                  'Demonstration material — not verified professional guidance.',
                ),
              ),
            if (widget.kind == 'videos') ...[
              if (video?.value.isInitialized == true)
                player()
              else if (x['media_url'] == null)
                const DSBCard(
                  child: Text(
                    'Playback unavailable: no approved media source is configured.',
                  ),
                )
              else
                const DSBLoadingState(),
              const SizedBox(height: 12),
            ],
            SelectableText(x['body'] as String? ?? ''),
            if (widget.api.signedIn)
              Wrap(
                spacing: 8,
                children: [
                  TextButton.icon(
                    onPressed: bookmark,
                    icon: Icon(
                      state?['bookmarked'] == true
                          ? Icons.bookmark
                          : Icons.bookmark_border,
                    ),
                    label: const Text('Save resource'),
                  ),
                  TextButton.icon(
                    onPressed: () => persist(complete: true),
                    icon: const Icon(Icons.check_circle_outline),
                    label: Text(
                      (state?['progress'] as Map?)?['completed'] == true
                          ? 'Completed'
                          : 'Mark completed',
                    ),
                  ),
                  TextButton.icon(
                    onPressed: () => Clipboard.setData(
                      ClipboardData(
                        text:
                            '${Uri.base.origin}/#/content/${widget.kind}/${widget.id}',
                      ),
                    ),
                    icon: const Icon(Icons.share_outlined),
                    label: const Text('Copy share link'),
                  ),
                ],
              ),
            if (widget.kind == 'publications') ...[
              const SizedBox(height: 16),
              const Text('Chapters', style: DSBTypography.heading),
              ...chapters.map(
                (c) => ListTile(
                  leading: Text('${c['position']}'),
                  title: Text(c['title'] as String),
                  trailing: const Icon(Icons.chevron_right),
                  selected: chapter?['id'] == c['id'],
                  onTap: () async {
                    setState(() => chapter = c);
                    if (widget.api.signedIn) {
                      await widget.api.put(
                        '/professional/learning/chapters/${c['id']}/progress',
                        {'position': 0, 'completed': false},
                      );
                    }
                  },
                ),
              ),
              if (chapter != null)
                DSBCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        chapter!['title'] as String,
                        style: DSBTypography.heading,
                      ),
                      SelectableText(chapter!['body'] as String? ?? ''),
                      TextButton(
                        onPressed: () => openAsset(
                          chapter!['asset_id'] as String?,
                          fallback: chapter!['download_url'] as String?,
                        ),
                        child: const Text('Open authorized PDF'),
                      ),
                      if (widget.api.signedIn)
                        TextButton(
                          onPressed: () async {
                            await widget.api.put(
                              '/professional/learning/chapters/${chapter!['id']}/progress',
                              {
                                'position': chapter!['pages'] ?? 0,
                                'completed': true,
                              },
                            );
                          },
                          child: const Text('Complete chapter'),
                        ),
                    ],
                  ),
                ),
              TextButton(
                onPressed: () => openAsset(
                  meta['asset_id'] as String?,
                  fallback: x['download_url'] as String?,
                ),
                child: const Text('Open publication PDF'),
              ),
            ],
            if (widget.kind == 'chapters')
              TextButton(
                onPressed: () => openAsset(
                  x['asset_id'] as String?,
                  fallback: x['download_url'] as String?,
                ),
                child: const Text('Open authorized PDF'),
              ),
            if (widget.kind == 'updates') ...[
              Text('Verified: ${meta['verified_on'] ?? 'Not recorded'}'),
              TextButton(
                onPressed: () => open(x['source_url'] as String?),
                child: const Text('Open official source'),
              ),
            ],
            if (widget.kind == 'webinars') ...[
              const SizedBox(height: 16),
              Text(
                'Starts: ${DateTime.tryParse('${x['starts_at']}')?.toLocal()} · ${meta['timezone'] ?? 'Asia/Dubai'}',
              ),
              Text('Presenter: ${meta['presenter'] ?? 'To be confirmed'}'),
              Text(
                'Registration: ${registration?['status'] ?? 'Sign in required'}',
              ),
              Wrap(
                spacing: 10,
                children: [
                  DSBPrimaryButton(
                    registration?['status'] == 'registered'
                        ? (meta['join_configured'] == true
                              ? 'Open joining information'
                              : 'Joining link pending')
                        : 'Register',
                    loading: busy,
                    onPressed:
                        !widget.api.signedIn ||
                            (registration?['status'] == 'registered' &&
                                meta['join_configured'] != true)
                        ? null
                        : () => eventAction(
                            registration?['status'] == 'registered'
                                ? 'join'
                                : 'register',
                          ),
                  ),
                  if (registration?['status'] == 'registered') ...[
                    TextButton(
                      onPressed: () => eventAction('cancel'),
                      child: const Text('Cancel registration'),
                    ),
                    if (meta['recording_configured'] == true)
                      TextButton(
                        onPressed: () => eventAction('recording'),
                        child: const Text('Authorized recording'),
                      ),
                  ],
                  TextButton(
                    onPressed: !widget.api.signedIn
                        ? null
                        : () async {
                            final r = await widget.api.dio.get<String>(
                              '/professional/webinars/${widget.id}/calendar',
                            );
                            await SharePlus.instance.share(
                              ShareParams(
                                files: [
                                  XFile.fromData(
                                    utf8.encode(r.data ?? ''),
                                    mimeType: 'text/calendar',
                                  ),
                                ],
                                fileNameOverrides: ['webinar.ics'],
                                sharePositionOrigin: const Rect.fromLTWH(
                                  0,
                                  0,
                                  1,
                                  1,
                                ),
                              ),
                            );
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text(
                                    'Calendar export opened; choose your calendar or save the ICS file.',
                                  ),
                                ),
                              );
                            }
                          },
                    child: const Text('Export calendar (.ics)'),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 16),
            TextButton(
              onPressed: () => context.push('/learning-library'),
              child: const Text('Learning paths, saved and recently viewed'),
            ),
          ],
        ],
      ),
    );
  }
}
