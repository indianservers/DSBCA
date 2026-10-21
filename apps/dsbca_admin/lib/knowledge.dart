import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:desktop_drop/desktop_drop.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:url_launcher/url_launcher.dart';

const subjects = [
  'Corporate Tax',
  'VAT',
  'Transfer Pricing',
  'Pillar Two',
  'IFRS',
  'Audit',
];
const documentTypes = [
  'Legislation',
  'Cabinet Decision',
  'Ministerial Decision',
  'Official Tax Guidance',
  'Public Clarification',
  'IFRS Standard',
  'Audit Standard',
  'Internal Technical Note',
  'Professional Interpretation',
  'Demonstration Material',
  'Other',
];

class KnowledgeWorkspace extends StatefulWidget {
  const KnowledgeWorkspace({super.key, required this.api});
  final ApiClient api;
  @override
  State<KnowledgeWorkspace> createState() => _KnowledgeState();
}

class _KnowledgeState extends State<KnowledgeWorkspace> {
  int tab = 0, page = 1;
  String query = '', subject = '', status = '', approval = '';
  late Future<Json> future;
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  void load() {
    future = widget.api.get(
      [
        '/admin/ai/documents',
        '/admin/ai/processing-jobs',
        '/admin/ai/settings',
        '/admin/ai/analytics',
      ][tab],
      query: tab == 0
          ? {
              'page': page,
              'q': query,
              if (subject.isNotEmpty) 'subject': subject,
              if (status.isNotEmpty) 'status': status,
              if (approval.isNotEmpty) 'approval': approval,
            }
          : tab == 1
          ? {'page': page}
          : null,
    );
  }

  void refresh() {
    setState(load);
  }

  void fail(Object e) {
    if (mounted) setState(() => error = apiError(e));
  }

  Future<void> upload({Json? document, bool edit = false}) async {
    try {
      final companies = (await widget.api.page(
        '/companies',
        query: {'page_size': 100},
      )).items;
      final orgs = (await widget.api.page(
        '/admin/ai/organizations',
        query: {'page_size': 100},
      )).items;
      if (!mounted) return;
      final done = await showDialog<bool>(
        context: context,
        builder: (_) => KnowledgeUpload(
          api: widget.api,
          document: document,
          edit: edit,
          companies: companies,
          organizations: orgs,
        ),
      );
      if (done == true) refresh();
    } catch (e) {
      fail(e);
    }
  }

  Future<void> action(Json doc, String action, {String? version}) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => DSBDialog(
        title: '${action[0].toUpperCase()}${action.substring(1)} source?',
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Confirm'),
          ),
        ],
        child: Text(
          action == 'approve'
              ? 'Confirm the extraction, source authority, applicability dates and access scope have been reviewed. Approval makes this processed version eligible for retrieval.'
              : 'This action is versioned and audited. Historical evidence is retained under the source access policy.',
        ),
      ),
    );
    if (yes != true) return;
    try {
      await widget.api.post(
        '/admin/ai/documents/${doc['id']}/$action${version == null ? '' : '?version_id=$version'}',
        {},
      );
      refresh();
    } catch (e) {
      fail(e);
    }
  }

  Future<void> details(Json doc) async {
    await showDialog<void>(
      context: context,
      builder: (ctx) => DSBDialog(
        title: doc['title'] as String,
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
        ],
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${doc['issuer']} · ${doc['jurisdiction']} · ${doc['scope']}',
              style: DSBTypography.muted,
            ),
            const SizedBox(height: 12),
            Text(doc['description'] as String? ?? ''),
            const SizedBox(height: 16),
            const Text(
              'Immutable version history',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            ...((doc['versions'] as List?) ?? []).map((raw) {
              final v = Json.from(raw as Map);
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: DSBCard(
                  outlined: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Version ${v['version']}',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        '${v['processing_status']} · ${v['approval_status']} · ${v['page_count']} pages',
                      ),
                      Text(
                        'Effective: ${v['effective_from'] ?? 'unknown'} to ${v['effective_to'] ?? 'open / unknown'}',
                        style: DSBTypography.muted,
                      ),
                      SelectableText(
                        'SHA-256 ${v['sha256']}',
                        style: DSBTypography.muted,
                      ),
                      if (v['failure_code'] != null)
                        Text(
                          '${v['failure_code']}',
                          style: const TextStyle(color: Colors.red),
                        ),
                      Wrap(
                        children: [
                          TextButton(
                            onPressed: () => preview(v),
                            child: const Text('Preview PDF'),
                          ),
                          if (v['processing_status'] == 'ready')
                            TextButton(
                              onPressed: () {
                                Navigator.pop(ctx);
                                action(
                                  doc,
                                  'approve',
                                  version: v['id'] as String,
                                );
                              },
                              child: const Text('Approve'),
                            ),
                          TextButton(
                            onPressed: () {
                              Navigator.pop(ctx);
                              action(doc, 'reject', version: v['id'] as String);
                            },
                            child: const Text('Reject'),
                          ),
                          if (v['processing_status'] == 'ready')
                            TextButton(
                              onPressed: () {
                                Navigator.pop(ctx);
                                action(
                                  doc,
                                  'supersede',
                                  version: v['id'] as String,
                                );
                              },
                              child: const Text('Supersede'),
                            ),
                          if (v['processing_status'] == 'failed')
                            TextButton(
                              onPressed: () {
                                Navigator.pop(ctx);
                                action(
                                  doc,
                                  'retry',
                                  version: v['id'] as String,
                                );
                              },
                              child: const Text('Retry indexing'),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Future<void> preview(Json version) async {
    await showDialog<void>(
      context: context,
      builder: (_) => KnowledgePreview(api: widget.api, version: version),
    );
  }

  Widget filter(
    String hint,
    String value,
    List<String> options,
    ValueChanged<String> onChanged,
  ) => SizedBox(
    width: 190,
    child: DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: hint),
      items: ['', ...options]
          .map(
            (x) => DropdownMenuItem(
              value: x,
              child: Text(
                x.isEmpty ? 'All' : x,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          )
          .toList(),
      onChanged: (v) {
        onChanged(v!);
        page = 1;
        refresh();
      },
    ),
  );
  Widget documents(Json data) {
    final items = (data['items'] as List)
        .map((x) => Json.from(x as Map))
        .toList();
    return Column(
      children: [
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            SizedBox(
              width: 270,
              child: DSBSearchBar(
                hint: 'Search approved and pending PDFs',
                onSubmitted: (v) {
                  query = v;
                  page = 1;
                  refresh();
                },
              ),
            ),
            filter('Subject', subject, subjects, (v) => subject = v),
            filter('Processing', status, [
              'draft',
              'processing',
              'ready',
              'failed',
              'superseded',
              'archived',
            ], (v) => status = v),
            filter('Approval', approval, [
              'pending',
              'approved',
              'rejected',
            ], (v) => approval = v),
            DSBPrimaryButton('+ Upload PDF', onPressed: () => upload()),
          ],
        ),
        const SizedBox(height: 16),
        Expanded(
          child: items.isEmpty
              ? const DSBEmptyState(
                  'Upload your first private PDF. No documents are approved automatically.',
                )
              : LayoutBuilder(
                  builder: (_, c) => SingleChildScrollView(
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: ConstrainedBox(
                        constraints: BoxConstraints(minWidth: c.maxWidth),
                        child: DataTable(
                          columns: const [
                            DataColumn(label: Text('Document')),
                            DataColumn(label: Text('Subject / scope')),
                            DataColumn(label: Text('Version / processing')),
                            DataColumn(label: Text('Approval')),
                            DataColumn(label: Text('Actions')),
                          ],
                          rows: items.map((d) {
                            final versions = d['versions'] as List;
                            final v = versions.isEmpty
                                ? <String, dynamic>{}
                                : Json.from(versions.first as Map);
                            return DataRow(
                              cells: [
                                DataCell(
                                  SizedBox(
                                    width: 240,
                                    child: Text(
                                      d['title'] as String,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  onTap: () => details(d),
                                ),
                                DataCell(
                                  Text('${d['subject']}\n${d['scope']}'),
                                ),
                                DataCell(
                                  Text(
                                    '${v['version'] ?? '—'} · ${v['processing_status'] ?? 'draft'}',
                                  ),
                                ),
                                DataCell(
                                  Text(
                                    '${v['approval_status'] ?? 'pending'}',
                                    style: TextStyle(
                                      color: v['approval_status'] == 'approved'
                                          ? const Color(0xFF288452)
                                          : DSBColors.muted,
                                    ),
                                  ),
                                ),
                                DataCell(
                                  PopupMenuButton<String>(
                                    tooltip: 'Document actions',
                                    onSelected: (a) {
                                      if (a == 'view') {
                                        details(d);
                                      } else if (a == 'replace') {
                                        upload(document: d);
                                      } else if (a == 'edit') {
                                        upload(document: d, edit: true);
                                      } else {
                                        action(d, a);
                                      }
                                    },
                                    itemBuilder: (_) => [
                                      for (final a in [
                                        'view',
                                        'edit',
                                        'replace',
                                        'archive',
                                      ])
                                        PopupMenuItem(
                                          value: a,
                                          child: Text(
                                            a[0].toUpperCase() + a.substring(1),
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                              ],
                            );
                          }).toList(),
                        ),
                      ),
                    ),
                  ),
                ),
        ),
        pagination(data),
      ],
    );
  }

  Widget pagination(Json d) => Row(
    mainAxisAlignment: MainAxisAlignment.end,
    children: [
      Flexible(
        child: Text(
          '${d['total']} records · Page $page',
          style: DSBTypography.muted,
        ),
      ),
      IconButton(
        tooltip: 'Previous',
        onPressed: page <= 1
            ? null
            : () {
                page--;
                refresh();
              },
        icon: const Icon(Icons.chevron_left),
      ),
      IconButton(
        tooltip: 'Next',
        onPressed: page * 20 >= (d['total'] as int)
            ? null
            : () {
                page++;
                refresh();
              },
        icon: const Icon(Icons.chevron_right),
      ),
    ],
  );
  Widget jobs(Json data) => Column(
    children: [
      const DSBCard(
        child: Text(
          'Indexing runs in the durable checkpoint worker. Refresh to see committed progress. Configure the production dispatcher or run the local worker command from the deployment guide.',
        ),
      ),
      const SizedBox(height: 16),
      Expanded(
        child: ListView(
          children: (data['items'] as List).map((raw) {
            final j = Json.from(raw as Map);
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: DSBCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${j['status']} · ${j['checkpoint']}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    LinearProgressIndicator(
                      value: (j['progress'] as num) / 100,
                    ),
                    Text(
                      '${j['progress']}% · attempts ${j['attempts']}',
                      style: DSBTypography.muted,
                    ),
                    if (j['error_code'] != null)
                      Text(
                        '${j['error_code']}',
                        style: const TextStyle(color: Colors.red),
                      ),
                    ExpansionTile(
                      title: const Text('Processing log'),
                      children: (j['events'] as List)
                          .map(
                            (e) => ListTile(
                              dense: true,
                              title: Text('${e['message']}'),
                              subtitle: Text('${e['created_at']}'),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ),
      pagination(data),
    ],
  );
  Widget analytics(Json data) => ListView(
    children: [
      const Text('Recorded AI activity', style: DSBTypography.heading),
      const SizedBox(height: 12),
      const Text(
        'Aggregate metrics only. Private conversation contents are not exposed.',
        style: DSBTypography.muted,
      ),
      const SizedBox(height: 20),
      Wrap(
        spacing: 12,
        runSpacing: 12,
        children: data.entries
            .where((e) => e.value is num || e.value == null)
            .map(
              (e) => SizedBox(
                width: 220,
                child: DSBCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        e.key.replaceAll('_', ' '),
                        style: DSBTypography.muted,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        e.value == null ? 'Unavailable' : '${e.value}',
                        style: DSBTypography.heading.copyWith(fontSize: 25),
                      ),
                    ],
                  ),
                ),
              ),
            )
            .toList(),
      ),
      const SizedBox(height: 16),
      Text('${data['cost_note']}', style: DSBTypography.muted),
      const SizedBox(height: 16),
      Text('Questions per subject: ${data['questions_per_subject']}'),
    ],
  );
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          const Text('AI Knowledge Base', style: DSBTypography.heading),
          IconButton(
            tooltip: 'Refresh workspace',
            onPressed: refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      const SizedBox(height: 8),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: List.generate(
            4,
            (i) => DSBCategoryChip(
              [
                'Documents',
                'Processing jobs',
                'Assistant settings',
                'Analytics',
              ][i],
              selected: tab == i,
              onTap: () {
                setState(() {
                  tab = i;
                  page = 1;
                  error = null;
                  load();
                });
              },
            ),
          ),
        ),
      ),
      const SizedBox(height: 16),
      if (error != null)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: DSBErrorState(error!),
        ),
      Expanded(
        child: FutureBuilder<Json>(
          key: ValueKey(tab),
          future: future,
          builder: (_, s) {
            if (s.hasError) {
              return DSBErrorState(apiError(s.error!), onRetry: refresh);
            }
            if (!s.hasData) return const DSBLoadingState();
            return switch (tab) {
              0 => documents(s.data!),
              1 => jobs(s.data!),
              2 => AssistantSettings(
                key: ValueKey(s.data!['version_id']),
                api: widget.api,
                data: s.data!,
                onSaved: refresh,
              ),
              _ => analytics(s.data!),
            };
          },
        ),
      ),
    ],
  );
}

class KnowledgeUpload extends StatefulWidget {
  const KnowledgeUpload({
    super.key,
    required this.api,
    this.document,
    this.edit = false,
    required this.companies,
    required this.organizations,
  });
  final ApiClient api;
  final Json? document;
  final bool edit;
  final List<Json> companies, organizations;
  @override
  State<KnowledgeUpload> createState() => _UploadState();
}

class _UploadState extends State<KnowledgeUpload> {
  late Map<String, TextEditingController> fields;
  String subject = 'Corporate Tax', type = 'Other', scope = 'shared';
  String? organization, company, error;
  Uint8List? bytes;
  String filename = '';
  bool busy = false, drag = false;
  @override
  void initState() {
    super.initState();
    final d = widget.document;
    final vs = d?['versions'] as List?;
    final v = vs?.isNotEmpty == true
        ? Json.from(vs!.first as Map)
        : <String, dynamic>{};
    final source = widget.edit
        ? Json.from(v['source_metadata'] as Map? ?? {})
        : d ?? {};
    fields = {
      for (final key in [
        'title',
        'issuer',
        'jurisdiction',
        'language',
        'version',
        'publication_date',
        'effective_from',
        'effective_to',
        'applicable_periods',
        'description',
        'keywords',
        'internal_notes',
      ])
        key: TextEditingController(
          text: key == 'keywords' && source[key] is List
              ? (source[key] as List).join(', ')
              : '${source[key] ?? (key == 'jurisdiction'
                        ? 'UAE'
                        : key == 'language'
                        ? 'en'
                        : key == 'version'
                        ? '1'
                        : '')}',
        ),
    };
    subject = d?['subject'] as String? ?? subject;
    type = d?['document_type'] as String? ?? type;
    scope = d?['scope'] as String? ?? scope;
    organization = d?['organization_id'] as String?;
    company = d?['company_id'] as String?;
  }

  @override
  void dispose() {
    for (final c in fields.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> choose() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      withData: true,
    );
    if (result?.files.single.bytes != null && mounted) {
      setState(() {
        bytes = result!.files.single.bytes;
        filename = result.files.single.name;
      });
    }
  }

  Future<void> save() async {
    if (!widget.edit && bytes == null) {
      setState(() => error = 'Select a PDF file.');
      return;
    }
    final data = <String, dynamic>{
      for (final e in fields.entries) e.key: e.value.text.trim(),
      'subject': subject,
      'document_type': type,
      'scope': scope,
      'organization_id': scope == 'organization' ? organization : null,
      'company_id': scope == 'client' ? company : null,
    };
    for (final key in ['publication_date', 'effective_from', 'effective_to']) {
      if (data[key] == '') data[key] = null;
    }
    data['keywords'] = fields['keywords']!.text
        .split(',')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
    setState(() {
      busy = true;
      error = null;
    });
    try {
      if (widget.edit) {
        await widget.api.patch(
          '/admin/ai/documents/${widget.document!['id']}',
          data,
        );
      } else {
        await widget.api.uploadPdf(
          widget.document == null
              ? '/admin/ai/documents'
              : '/admin/ai/documents/${widget.document!['id']}/replace',
          data,
          bytes!,
          documentId: widget.document?['id'] as String?,
        );
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Widget select(
    String label,
    String value,
    List<String> options,
    ValueChanged<String> changed,
  ) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label),
      items: options
          .map(
            (x) => DropdownMenuItem(
              value: x,
              child: Text(x, overflow: TextOverflow.ellipsis),
            ),
          )
          .toList(),
      onChanged: busy ? null : (v) => changed(v!),
    ),
  );
  @override
  Widget build(BuildContext context) => DSBDialog(
    title: widget.edit
        ? 'Edit pending metadata'
        : widget.document == null
        ? 'Upload private PDF'
        : 'Add immutable version',
    actions: [
      TextButton(
        onPressed: busy ? null : () => Navigator.pop(context, false),
        child: const Text('Cancel'),
      ),
      DSBPrimaryButton(
        widget.edit ? 'Save metadata' : 'Upload & queue indexing',
        loading: busy,
        onPressed: save,
      ),
    ],
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (!widget.edit)
          DropTarget(
            onDragEntered: (_) => setState(() => drag = true),
            onDragExited: (_) => setState(() => drag = false),
            onDragDone: (detail) async {
              if (detail.files.isEmpty) return;
              final f = detail.files.first;
              final data = await f.readAsBytes();
              if (mounted) {
                setState(() {
                  bytes = data;
                  filename = f.name;
                  drag = false;
                });
              }
            },
            child: InkWell(
              onTap: busy ? null : choose,
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: drag ? DSBColors.lavender : DSBColors.background,
                  border: Border.all(color: DSBColors.violet),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    const Icon(
                      Icons.upload_file,
                      color: DSBColors.violet,
                      size: 34,
                    ),
                    Text(
                      filename.isEmpty
                          ? 'Drop a PDF or choose a file'
                          : filename,
                      textAlign: TextAlign.center,
                    ),
                    const Text(
                      'Private storage · verified hash · no automatic approval',
                      style: DSBTypography.muted,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ...['title', 'issuer', 'jurisdiction', 'language', 'version'].map(
          (key) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: DSBTextField(
              controller: fields[key],
              label: key.replaceAll('_', ' '),
            ),
          ),
        ),
        select(
          'Subject',
          subject,
          subjects,
          (v) => setState(() => subject = v),
        ),
        select(
          'Document type',
          type,
          documentTypes,
          (v) => setState(() {
            type = v;
            if (v == 'Demonstration Material') scope = 'demo';
          }),
        ),
        select('Access scope', scope, [
          'shared',
          'organization',
          'client',
          'private',
          'demo',
        ], (v) => setState(() => scope = v)),
        if (scope == 'organization')
          DropdownButtonFormField<String>(
            initialValue: organization,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'Organization membership',
            ),
            items: widget.organizations
                .map(
                  (x) => DropdownMenuItem(
                    value: x['id'] as String,
                    child: Text(x['name'] as String),
                  ),
                )
                .toList(),
            onChanged: (v) => organization = v,
          ),
        if (scope == 'client')
          DropdownButtonFormField<String>(
            initialValue: company,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Owned company'),
            items: widget.companies
                .map(
                  (x) => DropdownMenuItem(
                    value: x['id'] as String,
                    child: Text(x['name'] as String),
                  ),
                )
                .toList(),
            onChanged: (v) => company = v,
          ),
        ...[
          'publication_date',
          'effective_from',
          'effective_to',
          'applicable_periods',
          'description',
          'keywords',
          'internal_notes',
        ].map(
          (key) => Padding(
            padding: const EdgeInsets.only(top: 12),
            child: DSBTextField(
              controller: fields[key],
              label: key.contains('date') || key.startsWith('effective')
                  ? '${key.replaceAll('_', ' ')} · YYYY-MM-DD'
                  : key.replaceAll('_', ' '),
            ),
          ),
        ),
        if (error != null)
          Text(error!, style: const TextStyle(color: Colors.red)),
      ],
    ),
  );
}

class KnowledgePreview extends StatefulWidget {
  const KnowledgePreview({super.key, required this.api, required this.version});
  final ApiClient api;
  final Json version;
  @override
  State<KnowledgePreview> createState() => _PreviewState();
}

class _PreviewState extends State<KnowledgePreview> {
  int page = 1;
  Uint8List? bytes;
  String? error;
  bool loading = true;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() => loading = true);
    try {
      final b = await widget.api.bytes(
        '/ai/documents/${widget.version['id']}/pages/$page/preview',
      );
      if (mounted) {
        setState(() {
          bytes = b;
          loading = false;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          error = apiError(e);
          loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => DSBDialog(
    title: 'PDF version ${widget.version['version']} · page $page',
    actions: [
      IconButton(
        tooltip: 'Previous page',
        onPressed: page <= 1
            ? null
            : () {
                page--;
                load();
              },
        icon: const Icon(Icons.chevron_left),
      ),
      IconButton(
        tooltip: 'Next page',
        onPressed: page >= (widget.version['page_count'] as int? ?? 0)
            ? null
            : () {
                page++;
                load();
              },
        icon: const Icon(Icons.chevron_right),
      ),
      TextButton(
        onPressed: () async {
          try {
            final r = await widget.api.get(
              '/ai/documents/${widget.version['id']}/download',
            );
            await launchUrl(
              Uri.parse(
                '${r['url'] ?? widget.api.absoluteUrl(r['path'] as String)}#page=$page',
              ),
            );
          } catch (e) {
            if (mounted) setState(() => error = apiError(e));
          }
        },
        child: const Text('Open original'),
      ),
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Close'),
      ),
    ],
    child: loading
        ? const DSBLoadingState()
        : error != null
        ? DSBErrorState(error!)
        : Image.memory(bytes!, fit: BoxFit.contain),
  );
}

class AssistantSettings extends StatefulWidget {
  const AssistantSettings({
    super.key,
    required this.api,
    required this.data,
    required this.onSaved,
  });
  final ApiClient api;
  final Json data;
  final VoidCallback onSaved;
  @override
  State<AssistantSettings> createState() => _SettingsState();
}

class _SettingsState extends State<AssistantSettings> {
  late Json config;
  late Map<String, TextEditingController> fields;
  String? error;
  bool busy = false;
  @override
  void initState() {
    super.initState();
    config = Json.from(widget.data['configuration'] as Map);
    fields = {
      for (final key in [
        'name',
        'system_instructions',
        'chat_model',
        'fast_model',
        'embedding_model',
        'retrieval_top_k',
        'max_output_tokens',
        'minimum_evidence_score',
        'history_window',
      ])
        key: TextEditingController(text: '${config[key] ?? ''}'),
    };
  }

  @override
  void dispose() {
    for (final c in fields.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> save() async {
    setState(() => busy = true);
    try {
      for (final e in fields.entries) {
        config[e.key] =
            [
              'retrieval_top_k',
              'max_output_tokens',
              'history_window',
            ].contains(e.key)
            ? int.tryParse(e.value.text)
            : e.key == 'minimum_evidence_score'
            ? double.tryParse(e.value.text)
            : e.value.text;
      }
      await widget.api.patch('/admin/ai/settings', config);
      widget.onSaved();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    children: [
      DSBCard(
        child: Text(
          'Configuration version: ${widget.data['version_id'] ?? 'built-in defaults'}\n${jsonEncode(widget.data['providers'])}',
          style: DSBTypography.muted,
        ),
      ),
      const SizedBox(height: 16),
      const Text(
        'OpenAI credentials remain server-side. Select model IDs supported by your account; configuring a name does not activate a provider.',
      ),
      const SizedBox(height: 16),
      ...fields.entries.map(
        (e) => Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: TextField(
            controller: e.value,
            minLines: e.key == 'system_instructions' ? 7 : 1,
            maxLines: e.key == 'system_instructions' ? 14 : 1,
            decoration: InputDecoration(labelText: e.key.replaceAll('_', ' ')),
          ),
        ),
      ),
      const Text(
        'Approved PDFs is the active mode. Citations are mandatory. Official-source verification and reranking are not enabled.',
        style: DSBTypography.muted,
      ),
      CheckboxListTile(
        title: const Text('Collect answer feedback'),
        value: config['feedback_enabled'] == true,
        onChanged: (v) => setState(() => config['feedback_enabled'] = v),
      ),
      if (error != null) DSBErrorState(error!),
      DSBPrimaryButton(
        'Save new audited configuration version',
        loading: busy,
        onPressed: save,
      ),
      const SizedBox(height: 20),
      const Text(
        'Configuration history',
        style: TextStyle(fontWeight: FontWeight.bold),
      ),
      ...((widget.data['history'] as List?) ?? []).map(
        (h) => ListTile(
          title: Text('${h['created_at']}'),
          subtitle: Text('${h['id']}'),
        ),
      ),
    ],
  );
}
