import 'dart:convert';
import 'package:share_plus/share_plus.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';

class ProfessionalAdmin extends StatefulWidget {
  const ProfessionalAdmin({super.key, required this.api, this.initialTab = 0});
  final ApiClient api;
  final int initialTab;
  @override
  State<ProfessionalAdmin> createState() => _ProfessionalAdmin();
}

class _ProfessionalAdmin extends State<ProfessionalAdmin> {
  int tab = 0, page = 1, total = 0;
  String kind = 'videos', search = '';
  String? error;
  late Future<Json> future;
  final tabs = [
    'Calculator rules',
    'Learning academy',
    'Compliance rules',
    'Regulatory review',
    'Webinars',
    'Delivery center',
    'Metrics',
  ];
  @override
  void initState() {
    super.initState();
    tab = widget.initialTab;
    load();
  }

  String get path => switch (tab) {
    0 || 2 => '/admin/professional/rules',
    1 =>
      kind == 'video-categories'
          ? '/admin/professional/video-categories'
          : kind == 'learning-paths'
          ? '/admin/professional/learning-paths'
          : '/admin/content/$kind',
    3 => '/admin/updates',
    4 => '/admin/content/webinars',
    5 => '/admin/professional/notifications',
    _ => '/admin/professional/metrics',
  };
  void load() {
    future = widget.api
        .get(
          path,
          query: {
            'page': page,
            'q': search,
            if (tab == 0 || tab == 2)
              'category': tab == 2 ? 'compliance' : 'calculator',
          },
        )
        .then((r) {
          if (mounted) setState(() => total = r['total'] as int? ?? 0);
          return r;
        });
  }

  void refresh() {
    setState(load);
  }

  void fail(Object e) {
    if (mounted) setState(() => error = apiError(e));
  }

  Future<void> attachAsset(
    Map<String, TextEditingController> controllers,
    void Function(void Function()) change,
  ) async {
    try {
      final files = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg', 'webp'],
        withData: true,
      );
      if (files == null) return;
      final file = files.files.single;
      if (file.bytes == null || file.size > 3000000) {
        throw StateError('Choose a file up to 3 MB');
      }
      final ext = file.extension;
      final mime = ext == 'pdf'
          ? 'application/pdf'
          : ext == 'png'
          ? 'image/png'
          : ext == 'webp'
          ? 'image/webp'
          : 'image/jpeg';
      final result = await widget.api.uploadPrivateAsset(
        file.bytes!,
        filename: file.name,
        mime: mime,
      );
      change(() {
        if (controllers.containsKey('asset_id')) {
          controllers['asset_id']!.text = result['asset_id'] as String;
        } else {
          final metadata = Json.from(
            jsonDecode(controllers['metadata_extra']!.text) as Map,
          );
          metadata['asset_id'] = result['asset_id'];
          controllers['metadata_extra']!.text = const JsonEncoder.withIndent(
            '  ',
          ).convert(metadata);
        }
      });
    } catch (e) {
      fail(e);
    }
  }

  Future<Json?> form(
    String title,
    Json initial, {
    Set<String> jsonFields = const {},
    Set<String> numberFields = const {},
  }) async {
    final controllers = {
      for (final e in initial.entries)
        e.key: TextEditingController(
          text: jsonFields.contains(e.key)
              ? const JsonEncoder.withIndent('  ').convert(e.value)
              : '${e.value ?? ''}',
        ),
    };
    String? issue;
    final result = await showDialog<Json>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, change) => DSBDialog(
          title: title,
          actions: [
            if (controllers.containsKey('metadata_extra') ||
                controllers.containsKey('asset_id'))
              TextButton.icon(
                onPressed: () => attachAsset(controllers, change),
                icon: const Icon(Icons.upload_file),
                label: const Text('Attach private file'),
              ),
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                try {
                  Navigator.pop(ctx, {
                    for (final e in controllers.entries)
                      e.key: jsonFields.contains(e.key)
                          ? jsonDecode(e.value.text)
                          : numberFields.contains(e.key)
                          ? int.parse(e.value.text)
                          : e.value.text,
                  });
                } catch (_) {
                  change(() => issue = 'Check JSON and numeric fields.');
                }
              },
              child: const Text('Confirm & save'),
            ),
          ],
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              ...controllers.entries.map(
                (e) => Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: TextField(
                    controller: e.value,
                    decoration: InputDecoration(
                      labelText: e.key.replaceAll('_', ' '),
                    ),
                    minLines:
                        jsonFields.contains(e.key) ||
                            ['body', 'description'].contains(e.key)
                        ? 3
                        : 1,
                    maxLines: jsonFields.contains(e.key)
                        ? 12
                        : ['body', 'description'].contains(e.key)
                        ? 8
                        : 1,
                  ),
                ),
              ),
              if (issue != null) DSBErrorState(issue!),
            ],
          ),
        ),
      ),
    );
    for (final c in controllers.values) {
      c.dispose();
    }
    return result;
  }

  Future<void> action(String url, {Json data = const {}}) async {
    try {
      await widget.api.post(url, data);
      refresh();
    } catch (e) {
      fail(e);
    }
  }

  Future<void> inspect(Json item) async {
    await showDialog<void>(
      context: context,
      builder: (ctx) => DSBDialog(
        title: 'Recorded details',
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
        ],
        child: SelectableText(const JsonEncoder.withIndent('  ').convert(item)),
      ),
    );
  }

  Future<void> templateRules() async {
    try {
      final response = await widget.api.get(
        '/admin/professional/rule-templates',
      );
      if (!mounted) return;
      final templates = (response['items'] as List).where(
        (x) => tab == 2
            ? x['category'] == 'compliance'
            : x['category'] == 'calculator',
      );
      await showDialog<void>(
        context: context,
        builder: (ctx) => DSBDialog(
          title: 'Reviewed source templates',
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Close'),
            ),
          ],
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Templates create drafts. Validate all reference cases, then ask a different administrator to publish.',
              ),
              ...templates.map(
                (t) => ListTile(
                  title: Text('${t['code']}'),
                  subtitle: Text('${t['valid_from']} – ${t['valid_to']}'),
                  trailing: const Icon(Icons.add),
                  onTap: () {
                    Navigator.pop(ctx);
                    editRule(Json.from(t as Map));
                  },
                ),
              ),
            ],
          ),
        ),
      );
    } catch (e) {
      fail(e);
    }
  }

  Future<void> editRule(Json data) async {
    final value = await form(
      'New immutable rule version',
      {
        'code': data['code'] ?? '',
        'version': data['version'] ?? '',
        'category':
            data['category'] ?? (tab == 2 ? 'compliance' : 'calculator'),
        'valid_from': data['valid_from'] ?? '',
        'valid_to': data['valid_to'] ?? '',
        'parameters': data['parameters'] ?? {},
        'sources': data['sources'] ?? [],
        'validation_cases': data['validation_cases'] ?? [],
      },
      jsonFields: {'parameters', 'sources', 'validation_cases'},
    );
    if (value == null) return;
    if (value['valid_to'] == '') value['valid_to'] = null;
    await action('/admin/professional/rules', data: value);
  }

  Future<void> editContent([Json? item]) async {
    final type = tab == 4
        ? 'webinars'
        : tab == 3
        ? 'updates'
        : kind;
    Json initial;
    Set<String> jsonFields = {'metadata_extra'};
    Set<String> numberFields = {};
    if (type == 'video-categories') {
      initial = {
        'name': item?['name'] ?? '',
        'subject_id': item?['subject_id'] ?? '',
      };
      jsonFields = {};
    } else if (type == 'categories') {
      initial = {'name': item?['name'] ?? ''};
      jsonFields = {};
    } else if (type == 'chapters') {
      initial = {
        'publication_id': item?['publication_id'] ?? '',
        'title': item?['title'] ?? '',
        'position': item?['position'] ?? 1,
        'pages': item?['pages'] ?? 0,
        'body': item?['body'] ?? '',
        'download_url': item?['download_url'] ?? '',
        'asset_id': item?['asset_id'] ?? '',
      };
      jsonFields = {};
      numberFields = {'position', 'pages'};
    } else if (type == 'learning-paths') {
      initial = {
        'title': item?['title'] ?? '',
        'description': item?['description'] ?? '',
        'subject': item?['subject'] ?? 'Corporate Tax',
        'status': item?['status'] ?? 'draft',
        'items': item?['items'] ?? [],
      };
      jsonFields = {'items'};
    } else {
      initial = {
        'title': item?['title'] ?? '',
        'body': item?['body'] ?? '',
        'status': item?['status'] ?? 'draft',
        'visibility': item?['visibility'] ?? 'public',
        'publish_at': item?['publish_at'] ?? '',
        'category_id': item?['category_id'] ?? '',
        'metadata_extra':
            item?['metadata_extra'] ??
            {
              'subject': 'Corporate Tax',
              'thumbnail_url': '',
              'display_order': 0,
              ...(type == 'webinars'
                  ? {
                      'presenter': '',
                      'timezone': 'Asia/Dubai',
                      'capacity': 100,
                      'registration_open': true,
                      'duration_minutes': 60,
                      'recording_url': '',
                    }
                  : {}),
            },
        if (type == 'videos') 'media_url': item?['media_url'] ?? '',
        if (type == 'videos')
          'video_category_id': item?['video_category_id'] ?? '',
        if (type == 'videos')
          'duration_seconds': item?['duration_seconds'] ?? 0,
        if (type == 'publications') 'download_url': item?['download_url'] ?? '',
        if (type == 'updates') 'source_url': item?['source_url'] ?? '',
        if (type == 'webinars') 'starts_at': item?['starts_at'] ?? '',
        if (type == 'webinars') 'join_url': item?['join_url'] ?? '',
      };
      numberFields = {'duration_seconds'};
    }
    final value = await form(
      '${item == null ? 'Create' : 'Edit'} $type',
      initial,
      jsonFields: jsonFields,
      numberFields: numberFields,
    );
    if (value == null) return;
    for (final key in [
      'publish_at',
      'category_id',
      'media_url',
      'download_url',
      'source_url',
      'starts_at',
      'join_url',
      'asset_id',
      'video_category_id',
    ]) {
      if (value[key] == '') value[key] = null;
    }
    try {
      final endpoint = type == 'video-categories'
          ? '/admin/professional/video-categories'
          : type == 'learning-paths'
          ? '/admin/professional/learning-paths'
          : type == 'updates'
          ? '/admin/updates'
          : '/admin/content/$type';
      if (item == null) {
        await widget.api.post(endpoint, value);
      } else {
        await widget.api.put('$endpoint/${item['id']}', value);
      }
      refresh();
    } catch (e) {
      fail(e);
    }
  }

  Future<void> campaign() async {
    final value = await form('Queue a targeted in-app campaign', {
      'title': '',
      'body': '',
      'subject': 'Corporate Tax',
      'scheduled_at': DateTime.now().toUtc().toIso8601String(),
    });
    if (value == null) return;
    await action(
      '/admin/professional/notifications/campaigns',
      data: {...value, 'confirmed': true},
    );
  }

  Future<void> notificationTemplate() async {
    try {
      final settings = await widget.api.page('/admin/settings');
      final entries = settings.items.where(
        (x) => x['key'] == 'notification_template.renewal',
      );
      final current = entries.isEmpty
          ? <String, dynamic>{}
          : Json.from(entries.first['value'] as Map);
      final value = await form('In-app renewal template (new/replanned jobs)', {
        'title': current['title'] ?? 'Document renewal reminder',
        'body': current['body'] ?? 'Review your recorded expiry in DSBCA.',
      });
      if (value == null) return;
      await widget.api.put('/admin/settings', {
        'key': 'notification_template.renewal',
        'value': value,
      });
      refresh();
    } catch (e) {
      fail(e);
    }
  }

  Future<void> registrations(Json event) async {
    try {
      final result = await widget.api.get(
        '/admin/professional/webinars/${event['id']}/registrations',
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => DSBDialog(
          title: 'Authorized registrations',
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Close'),
            ),
            TextButton(
              onPressed: () async {
                final response = await widget.api.dio.get<String>(
                  '/admin/professional/webinars/${event['id']}/attendees.csv',
                );
                await SharePlus.instance.share(
                  ShareParams(
                    files: [
                      XFile.fromData(
                        utf8.encode(response.data ?? ''),
                        mimeType: 'text/csv',
                      ),
                    ],
                    fileNameOverrides: ['attendees.csv'],
                    sharePositionOrigin: const Rect.fromLTWH(0, 0, 1, 1),
                  ),
                );
              },
              child: const Text('Export attendee CSV'),
            ),
          ],
          child: SelectableText(
            const JsonEncoder.withIndent('  ').convert(result),
          ),
        ),
      );
    } catch (e) {
      fail(e);
    }
  }

  Future<void> affectedSources(Json record) async {
    final data = await form(
      'Flag affected source versions',
      {
        'knowledge_version_ids': [],
        'learning_resource_ids': [],
        'effective_on': '',
      },
      jsonFields: {'knowledge_version_ids', 'learning_resource_ids'},
    );
    if (data == null) return;
    if (data['effective_on'] == '') data['effective_on'] = null;
    await action(
      '/admin/professional/updates/${record['id']}/workflow',
      data: {...data, 'action': 'flag_sources'},
    );
  }

  Future<void> archiveContent(Json record) async {
    final permanent =
        tab == 1 &&
        ['chapters', 'categories', 'video-categories'].contains(kind);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => DSBDialog(
        title: permanent
            ? 'Delete this structural record?'
            : 'Archive this resource?',
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(permanent ? 'Delete permanently' : 'Archive'),
          ),
        ],
        child: Text(
          permanent
              ? 'This permanently deletes the structural record. Referenced records cannot be deleted. Check linked chapters and content first.'
              : 'The resource will be removed from published listings. Existing private progress and audit history are retained.',
        ),
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.api.delete('$path/${record['id']}');
      refresh();
    } catch (e) {
      fail(e);
    }
  }

  Future<void> chapterOrder(Json chapter) async {
    try {
      final page = await widget.api.page(
        '/publications/${chapter['publication_id']}/chapters',
      );
      final values = await form(
        'Reorder publication chapters',
        {'chapter_ids': page.items.map((x) => x['id']).toList()},
        jsonFields: {'chapter_ids'},
      );
      if (values == null) return;
      await widget.api.put(
        '/admin/professional/publications/${chapter['publication_id']}/chapter-order',
        values,
      );
      refresh();
    } catch (e) {
      fail(e);
    }
  }

  Widget rowActions(Json x) => Wrap(
    spacing: 4,
    children: [
      IconButton(
        tooltip: 'Inspect record',
        onPressed: () => inspect(x),
        icon: const Icon(Icons.info_outline),
      ),
      if (tab == 0 || tab == 2) ...[
        TextButton(
          onPressed: x['status'] == 'draft'
              ? () => action('/admin/professional/rules/${x['id']}/validate')
              : null,
          child: const Text('Validate'),
        ),
        TextButton(
          onPressed:
              x['status'] == 'draft' &&
                  x['validated_at'] != null &&
                  x['author_id'] != widget.api.user?['id']
              ? () => action('/admin/professional/rules/${x['id']}/publish')
              : null,
          child: const Text('Publish reviewed'),
        ),
        TextButton(
          onPressed: x['status'] == 'published'
              ? () => action('/admin/professional/rules/${x['id']}/supersede')
              : null,
          child: const Text('Supersede'),
        ),
        TextButton(
          onPressed: () =>
              editRule({...x, 'version': '${x['version']}-revision'}),
          child: const Text('New version'),
        ),
      ],
      if (tab == 1 || tab == 3 || tab == 4)
        IconButton(
          tooltip: 'Edit',
          onPressed: () => editContent(x),
          icon: const Icon(Icons.edit_outlined),
        ),
      if (tab == 3)
        for (final actionName in [
          'review',
          'approve',
          'publish',
          'supersede',
          'archive',
        ])
          TextButton(
            onPressed:
                ({
                          'review': 'draft',
                          'approve': 'review',
                          'publish': 'approved',
                          'supersede': 'published',
                        }[actionName] ==
                        x['status'] ||
                    actionName == 'archive')
                ? () => action(
                    '/admin/professional/updates/${x['id']}/workflow',
                    data: {'action': actionName},
                  )
                : null,
            child: Text(actionName),
          ),
      if (tab == 3)
        TextButton(
          onPressed: () => affectedSources(x),
          child: const Text('Affected AI / learning sources'),
        ),
      if (tab == 1 || tab == 4)
        TextButton(
          onPressed: () => archiveContent(x),
          child: const Text('Archive'),
        ),
      if (tab == 1 && kind == 'chapters')
        TextButton(
          onPressed: () => chapterOrder(x),
          child: const Text('Reorder chapters'),
        ),
      if (tab == 4)
        TextButton(
          onPressed: () => registrations(x),
          child: const Text('Registrations'),
        ),
      if (tab == 5 && ['failed', 'blocked'].contains(x['status']))
        TextButton(
          onPressed: () =>
              action('/admin/professional/notifications/${x['id']}/retry'),
          child: const Text('Retry'),
        ),
    ],
  );
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      const Text('Professional administration', style: DSBTypography.heading),
      const SizedBox(height: 12),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: List.generate(
            tabs.length,
            (i) => Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(tabs[i]),
                selected: tab == i,
                onSelected: (_) => setState(() {
                  tab = i;
                  page = 1;
                  error = null;
                  load();
                }),
              ),
            ),
          ),
        ),
      ),
      const SizedBox(height: 12),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          if (tab == 0 || tab == 2) ...[
            FilledButton(
              onPressed: templateRules,
              child: const Text('Create rule from source template'),
            ),
            OutlinedButton(
              onPressed: () => editRule({}),
              child: const Text('New rule version'),
            ),
          ],
          if (tab == 1) ...[
            DropdownButton<String>(
              value: kind,
              items: [
                'videos',
                'publications',
                'articles',
                'chapters',
                'learning-paths',
                'categories',
                'video-categories',
              ].map((k) => DropdownMenuItem(value: k, child: Text(k))).toList(),
              onChanged: (v) => setState(() {
                kind = v!;
                page = 1;
                load();
              }),
            ),
            FilledButton(
              onPressed: () => editContent(),
              child: const Text('Create learning content'),
            ),
          ],
          if (tab == 3 || tab == 4)
            FilledButton(
              onPressed: () => editContent(),
              child: Text(
                tab == 3 ? 'Draft regulatory update' : 'Create webinar',
              ),
            ),
          if (tab == 5) ...[
            FilledButton(
              onPressed: campaign,
              child: const Text('Queue in-app campaign'),
            ),
            OutlinedButton(
              onPressed: notificationTemplate,
              child: const Text('Save delivery template'),
            ),
          ],
          IconButton(
            tooltip: 'Refresh',
            onPressed: refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      const SizedBox(height: 10),
      if (tab != 6)
        TextField(
          decoration: const InputDecoration(labelText: 'Search records'),
          onSubmitted: (value) => setState(() {
            search = value;
            page = 1;
            load();
          }),
        ),
      if (error != null) DSBErrorState(error!),
      const SizedBox(height: 12),
      if (tab == 5)
        const Text(
          'Delivered means in-app availability. Submitted means external provider acceptance; email or device delivery is not asserted.',
          style: DSBTypography.muted,
        ),
      Expanded(
        child: FutureBuilder<Json>(
          key: ValueKey('$tab-$kind'),
          future: future,
          builder: (_, s) {
            if (s.hasError) {
              return DSBErrorState(apiError(s.error!), onRetry: refresh);
            }
            if (!s.hasData) return const DSBLoadingState();
            if (tab == 6) {
              return ListView(
                children: s.data!.entries
                    .map(
                      (e) => ListTile(
                        title: Text(e.key.replaceAll('_', ' ')),
                        trailing: Text(
                          '${e.value}',
                          style: DSBTypography.heading,
                        ),
                      ),
                    )
                    .toList(),
              );
            }
            var items = ((s.data!['items'] as List?) ?? [])
                .map((x) => Json.from(x as Map))
                .toList();
            if (tab == 0 || tab == 2) {
              items = items
                  .where(
                    (x) =>
                        x['category'] ==
                        (tab == 2 ? 'compliance' : 'calculator'),
                  )
                  .toList();
            }
            if (items.isEmpty) {
              return const Center(
                child: Text('No records yet. Create a draft to begin.'),
              );
            }
            if (MediaQuery.sizeOf(context).width >= 1024) {
              return SingleChildScrollView(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    columns: const [
                      DataColumn(label: Text('Record')),
                      DataColumn(label: Text('Status / version')),
                      DataColumn(label: Text('Actions')),
                    ],
                    rows: items
                        .map(
                          (x) => DataRow(
                            cells: [
                              DataCell(
                                SizedBox(
                                  width: 230,
                                  child: Text(
                                    '${x['title'] ?? x['name'] ?? x['code'] ?? x['channel'] ?? 'Delivery'}',
                                    maxLines: 3,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ),
                              DataCell(
                                Text(
                                  '${x['status'] ?? ''} ${x['version'] ?? ''} ${x['error_code'] ?? ''}',
                                ),
                              ),
                              DataCell(
                                SizedBox(
                                  width: 460,
                                  child: SingleChildScrollView(
                                    scrollDirection: Axis.horizontal,
                                    child: rowActions(x),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )
                        .toList(),
                  ),
                ),
              );
            }
            return ListView(
              children: items
                  .map(
                    (x) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: DSBCard(
                        outlined: true,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text(
                              '${x['title'] ?? x['name'] ?? x['code'] ?? x['channel'] ?? 'Delivery'}',
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              '${x['status'] ?? ''} ${x['version'] ?? ''} ${x['error_code'] ?? ''}',
                              style: DSBTypography.muted,
                            ),
                            rowActions(x),
                          ],
                        ),
                      ),
                    ),
                  )
                  .toList(),
            );
          },
        ),
      ),
      Row(
        children: [
          TextButton(
            onPressed: page > 1
                ? () => setState(() {
                    page--;
                    load();
                  })
                : null,
            child: const Text('Previous'),
          ),
          Text('Page $page'),
          TextButton(
            onPressed: page * 20 < total
                ? () => setState(() {
                    page++;
                    load();
                  })
                : null,
            child: const Text('Next'),
          ),
        ],
      ),
    ],
  );
}
