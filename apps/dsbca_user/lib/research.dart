import 'dart:math';
import 'dart:convert';
import 'package:go_router/go_router.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:url_launcher/url_launcher.dart';

const researchSubjects = [
  'Corporate Tax',
  'VAT',
  'Transfer Pricing',
  'Pillar Two',
  'IFRS',
  'Audit',
];
const starters = {
  'Corporate Tax': [
    'Does the QFZP de minimis condition apply to my business?',
    'How is taxable income computed?',
    'What happens when a company makes a tax loss?',
  ],
  'VAT': [
    'When is UAE VAT registration required?',
    'When can input VAT be recovered?',
  ],
  'Transfer Pricing': [
    "How is the arm’s length principle applied?",
    'When is transfer pricing documentation required?',
  ],
  'Pillar Two': ['Which entities may fall within the UAE DMTT regime?'],
  'IFRS': ['How should a lease be accounted for under IFRS 16?'],
  'Audit': ['What evidence is generally relevant for revenue testing?'],
};

class ResearchScreen extends StatefulWidget {
  const ResearchScreen({super.key, required this.api});
  final ApiClient api;
  @override
  State<ResearchScreen> createState() => _ResearchState();
}

class _ResearchState extends State<ResearchScreen> {
  final composer = TextEditingController(), scroll = ScrollController();
  List<Json> conversations = [], messages = [], sources = [];
  String? conversation, error, messageId;
  String subject = 'Corporate Tax', stage = '', partial = '';
  String? periodStart, periodEnd;
  bool busy = false, includeDemo = false;
  int historyPage = 1, historyTotal = 0, messagePage = 1;
  bool hasOlderMessages = false;
  RequestCancellation? cancellation;
  Json? capabilities;
  @override
  void initState() {
    super.initState();
    if (widget.api.signedIn) {
      loadHistory();
      widget.api
          .get('/ai/capabilities')
          .then((value) {
            if (mounted) setState(() => capabilities = value);
          })
          .catchError((Object _) {});
    }
  }

  @override
  void dispose() {
    cancellation?.cancel();
    composer.dispose();
    scroll.dispose();
    super.dispose();
  }

  void fail(Object e) {
    if (mounted) {
      setState(() => error = e is StateError ? e.message : apiError(e));
    }
  }

  void latest() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (scroll.hasClients) {
        scroll.animateTo(
          scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> loadHistory({bool more = false}) async {
    if (!more) historyPage = 1;
    try {
      final page = await widget.api.page(
        '/ai/conversations',
        query: {'page': historyPage},
      );
      if (mounted) {
        setState(() {
          conversations = more ? [...conversations, ...page.items] : page.items;
          historyTotal = page.total;
        });
      }
    } catch (e) {
      fail(e);
    }
  }

  Future<void> resume(Json row) async {
    if (busy) return;
    try {
      final page = await widget.api.page(
        '/ai/conversations/${row['id']}/messages',
      );
      if (mounted) {
        setState(() {
          conversation = row['id'] as String;
          messages = page.items;
          messagePage = 1;
          hasOlderMessages = page.total > page.items.length;
          sources = [];
          partial = '';
          error = null;
        });
      }
      latest();
    } catch (e) {
      fail(e);
    }
  }

  Future<void> olderMessages() async {
    if (conversation == null) return;
    try {
      final next = messagePage + 1;
      final page = await widget.api.page(
        '/ai/conversations/$conversation/messages',
        query: {'page': next},
      );
      if (mounted) {
        setState(() {
          messages = [...page.items, ...messages];
          messagePage = next;
          hasOlderMessages = next * 50 < page.total;
        });
      }
    } catch (e) {
      fail(e);
    }
  }

  Future<void> remove(Json row) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => DSBDialog(
        title: 'Delete conversation?',
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
        child: const Text(
          'This conversation will be hidden immediately and removed according to the retention policy.',
        ),
      ),
    );
    if (yes != true) return;
    try {
      await widget.api.delete('/ai/conversations/${row['id']}');
      if (conversation == row['id']) newResearch();
      await loadHistory();
    } catch (e) {
      fail(e);
    }
  }

  void newResearch() {
    if (busy) return;
    setState(() {
      conversation = null;
      messages = [];
      messagePage = 1;
      hasOlderMessages = false;
      sources = [];
      partial = '';
      error = null;
    });
  }

  Future<void> stop() async {
    cancellation?.cancel();
    if (messageId != null) {
      try {
        await widget.api.post('/ai/messages/$messageId/cancel', {});
      } catch (_) {}
    }
    if (mounted) {
      setState(() {
        busy = false;
        stage = 'Stopped. Resume history to inspect the saved state.';
      });
    }
  }

  Future<void> send([String? retry]) async {
    final question = retry ?? composer.text.trim();
    if (question.isEmpty || busy) return;
    if (!widget.api.signedIn) {
      setState(
        () => error = 'Sign in to use private research and save conversations.',
      );
      return;
    }
    setState(() {
      busy = true;
      error = null;
      partial = '';
      stage = 'Preparing research';
      sources = [];
      messageId = null;
    });
    final activeCancellation = RequestCancellation();
    cancellation = activeCancellation;
    final id =
        'r${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 30)}';
    try {
      conversation ??=
          (await widget.api.post('/ai/conversations', {
                'title': 'New research',
              }))['id']
              as String;
      if (!mounted || activeCancellation.cancelled) return;
      setState(
        () => messages.add({
          'request_id': id,
          'role': 'user',
          'text': question,
          'status': 'completed',
        }),
      );
      composer.clear();
      latest();
      await for (final event in widget.api.streamEvents('/ai/chat/stream', {
        'conversation_id': conversation,
        'request_id': id,
        'question': question,
        'subject': subject,
        'include_demo': includeDemo,
        if (periodStart != null) 'period_start': periodStart,
        if (periodEnd != null) 'period_end': periodEnd,
      }, activeCancellation)) {
        if (!mounted ||
            activeCancellation.cancelled ||
            cancellation != activeCancellation) {
          return;
        }
        final data = Json.from(event['data'] as Map);
        setState(() {
          switch (event['event']) {
            case 'accepted':
              messageId = data['message_id'] as String?;
            case 'status':
              stage = 'Searching approved evidence';
            case 'citations':
              sources = (data['citations'] as List)
                  .map((x) => Json.from(x as Map))
                  .toList();
            case 'answer_delta':
              partial += data['text'] as String;
              stage = 'Receiving validated answer';
            case 'done':
              messages.add(data);
              partial = '';
              stage = data['status'] == 'failed'
                  ? 'Provider or evidence check failed'
                  : 'Approved PDFs · independent official-source verification not performed';
          }
        });
        latest();
      }
      await loadHistory();
    } catch (e) {
      if (!activeCancellation.cancelled && cancellation == activeCancellation) {
        fail(e);
      }
    } finally {
      if (mounted && cancellation == activeCancellation) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> filters() async {
    final start = TextEditingController(text: periodStart),
        end = TextEditingController(text: periodEnd);
    String? issue;
    await showDialog<void>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, change) => DSBDialog(
          title: 'Research period',
          actions: [
            TextButton(
              onPressed: () {
                setState(() {
                  periodStart = periodEnd = null;
                });
                Navigator.pop(ctx);
              },
              child: const Text('Clear'),
            ),
            FilledButton(
              onPressed: () {
                if (DateTime.tryParse(start.text) == null ||
                    DateTime.tryParse(end.text) == null ||
                    DateTime.parse(
                      start.text,
                    ).isAfter(DateTime.parse(end.text))) {
                  change(() => issue = 'Enter a valid date range.');
                  return;
                }
                setState(() {
                  periodStart = start.text;
                  periodEnd = end.text;
                });
                Navigator.pop(ctx);
              },
              child: const Text('Apply'),
            ),
          ],
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Set exact dates for historical research. A publication date alone does not establish applicability.',
                style: DSBTypography.muted,
              ),
              const SizedBox(height: 12),
              DSBTextField(controller: start, label: 'From · YYYY-MM-DD'),
              const SizedBox(height: 12),
              DSBTextField(controller: end, label: 'To · YYYY-MM-DD'),
              if (issue != null)
                Text(issue!, style: const TextStyle(color: Colors.red)),
            ],
          ),
        ),
      ),
    );
    start.dispose();
    end.dispose();
  }

  Widget historyPanel() => Container(
    color: Colors.white,
    padding: const EdgeInsets.all(16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Research history',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
        ),
        const SizedBox(height: 16),
        DSBPrimaryButton(
          '+ New research',
          onPressed: busy ? null : newResearch,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView(
            children: [
              ...conversations.map(
                (c) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  selected: c['id'] == conversation,
                  title: Text(
                    c['title'] as String,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  subtitle: Text(
                    '${c['message_count']} messages',
                    style: DSBTypography.muted,
                  ),
                  onTap: () => resume(c),
                  trailing: IconButton(
                    tooltip: 'Delete conversation',
                    onPressed: busy ? null : () => remove(c),
                    icon: const Icon(Icons.delete_outline, size: 18),
                  ),
                ),
              ),
              if (conversations.length < historyTotal)
                TextButton(
                  onPressed: () {
                    historyPage++;
                    loadHistory(more: true);
                  },
                  child: const Text('Load more'),
                ),
            ],
          ),
        ),
      ],
    ),
  );
  Future<void> historySheet() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => SizedBox(
        height: MediaQuery.sizeOf(context).height * .8,
        child: historyPanel(),
      ),
    );
  }

  Future<void> showSource(Json source) async {
    await showDialog<void>(
      context: context,
      builder: (_) => SourceViewer(api: widget.api, source: source),
    );
  }

  Widget sourcesPanel() => Container(
    color: Colors.white,
    padding: const EdgeInsets.all(16),
    child: ListView(
      children: [
        const Text(
          'Supporting sources',
          style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        if (sources.isEmpty)
          const DSBEmptyState('Verified passages will appear here.'),
        ...sources.map(
          (s) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: InkWell(
              onTap: () => showSource(s),
              child: DSBCard(
                outlined: true,
                padding: 12,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      s['title'] as String,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    Text(
                      'PDF ${s['physical_page']} · ${s['version']}',
                      style: DSBTypography.muted,
                    ),
                    Text(
                      s['document_type'] as String,
                      style: const TextStyle(
                        color: DSBColors.violet,
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      s['passage'] as String,
                      maxLines: 5,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    ),
  );
  Widget applicationCards(Json data) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      if (data['path'] is String)
        TextButton.icon(
          icon: const Icon(Icons.open_in_new),
          label: Text(
            data['kind'] == 'calculation'
                ? 'Open populated calculator'
                : 'Open company compliance',
          ),
          onPressed: () {
            final path = data['path'] as String;
            context.push(
              data['prefill'] == null
                  ? path
                  : '$path?inputs=${Uri.encodeComponent(jsonEncode(data['prefill']))}',
            );
          },
        ),
      if (data['kind'] == 'resources')
        ...((data['items'] as List?) ?? []).map(
          (item) => ListTile(
            title: Text('${item['title']}'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(item['path'] as String),
          ),
        ),
      if (data['kind'] == 'compliance')
        ...(((data['data'] as Map?)?['documents'] as List?) ?? []).map(
          (doc) => Text(
            '${doc['title']}: ${doc['expires_on']} (${doc['expiry_status']})',
          ),
        ),
    ],
  );

  Widget bubble(Json m) {
    final own = m['role'] == 'user';
    final citations = ((m['citations'] as List?) ?? [])
        .map((x) => Json.from(x as Map))
        .toList();
    return Align(
      alignment: own ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: EdgeInsets.only(
          left: own ? 32 : 0,
          right: own ? 0 : 12,
          bottom: 14,
        ),
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: own ? DSBColors.violet : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: own ? null : Border.all(color: DSBColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!own)
              const Padding(
                padding: EdgeInsets.only(bottom: 10),
                child: Text(
                  'DSBCA · PDF research',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            if (!own && (m['metadata'] as Map?)?['application_result'] is Map)
              applicationCards(
                Json.from((m['metadata'] as Map)['application_result'] as Map),
              ),
            SelectionArea(
              child: MarkdownBody(
                imageBuilder: (_, _, alt) => Text(alt ?? '[Image omitted]'),
                data: m['text'] as String? ?? '',
                selectable: false,
                styleSheet: MarkdownStyleSheet(
                  p: TextStyle(
                    color: own ? Colors.white : DSBColors.text,
                    fontSize: 15,
                    height: 1.5,
                  ),
                  tableBody: const TextStyle(fontSize: 12),
                  tableColumnWidth: const IntrinsicColumnWidth(),
                  tableBorder: TableBorder.all(color: DSBColors.border),
                ),
                onTapLink: (_, _, _) {},
              ),
            ),
            if (!own) ...[
              Wrap(
                spacing: 6,
                children: List.generate(
                  citations.length,
                  (i) => ActionChip(
                    label: Text(
                      '[${i + 1}] PDF ${citations[i]['physical_page']} · ${citations[i]['version']}',
                      style: const TextStyle(fontSize: 11),
                    ),
                    onPressed: () {
                      setState(() => sources = citations);
                      showSource(citations[i]);
                    },
                  ),
                ),
              ),
              Wrap(
                children: [
                  IconButton(
                    tooltip: 'Copy answer',
                    icon: const Icon(Icons.copy_outlined, size: 18),
                    onPressed: () => Clipboard.setData(
                      ClipboardData(text: m['text'] as String? ?? ''),
                    ),
                  ),
                  if (m['id'] != null) ...[
                    IconButton(
                      tooltip: 'Helpful',
                      icon: const Icon(Icons.thumb_up_outlined, size: 18),
                      onPressed: () => feedback(m, 1),
                    ),
                    IconButton(
                      tooltip: 'Needs review',
                      icon: const Icon(Icons.thumb_down_outlined, size: 18),
                      onPressed: () => feedback(m, -1),
                    ),
                  ],
                  if (m['status'] == 'failed' || m['status'] == 'cancelled')
                    TextButton(
                      onPressed: busy
                          ? null
                          : () {
                              final q =
                                  messages
                                          .where(
                                            (x) =>
                                                x['role'] == 'user' &&
                                                (m['request_id'] == null ||
                                                    x['request_id'] ==
                                                        m['request_id']),
                                          )
                                          .lastOrNull?['text']
                                      as String?;
                              if (q != null) send(q);
                            },
                      child: const Text('Retry'),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> feedback(Json m, int rating) async {
    try {
      await widget.api.post('/ai/feedback', {
        'message_id': m['id'],
        'rating': rating,
      });
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Feedback saved')));
      }
    } catch (e) {
      fail(e);
    }
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (_, constraints) {
      final desktop = constraints.maxWidth >= 960;
      final three = constraints.maxWidth >= 1250;
      return Row(
        children: [
          if (desktop) SizedBox(width: 230, child: historyPanel()),
          Expanded(
            child: Column(
              children: [
                Container(
                  color: Colors.white,
                  padding: const EdgeInsets.fromLTRB(20, 32, 16, 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Expanded(
                            child: Text(
                              'Discuss',
                              style: DSBTypography.heading,
                            ),
                          ),
                          IconButton(
                            tooltip: 'Research period',
                            onPressed: busy ? null : filters,
                            icon: const Icon(Icons.filter_list),
                          ),
                          IconButton(
                            tooltip: 'Conversation history',
                            onPressed: historySheet,
                            icon: const Icon(Icons.history),
                          ),
                          IconButton(
                            tooltip: 'New conversation',
                            onPressed: busy ? null : newResearch,
                            icon: const Icon(Icons.add),
                          ),
                        ],
                      ),
                      Text(
                        periodStart == null
                            ? 'Approved PDFs · citations required'
                            : 'Period: $periodStart to $periodEnd',
                        style: const TextStyle(
                          color: Color(0xFF288452),
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: researchSubjects
                              .map(
                                (s) => DSBCategoryChip(
                                  s,
                                  selected: subject == s,
                                  onTap: busy
                                      ? null
                                      : () => setState(() => subject = s),
                                ),
                              )
                              .toList(),
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: ListView(
                    controller: scroll,
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (!widget.api.signedIn)
                        const DSBCard(
                          child: Text(
                            'Sign in from Profile to save research and access the assistant.',
                          ),
                        ),
                      if (capabilities?['openai_configured'] == false)
                        const Padding(
                          padding: EdgeInsets.only(bottom: 12),
                          child: DSBCard(
                            color: DSBColors.peach,
                            child: Text(
                              'OpenAI activation is pending. PDF administration and saved conversations are available; live evidence-grounded generation will be available after provider configuration.',
                            ),
                          ),
                        ),
                      if (messages.isEmpty) ...[
                        const DSBCard(
                          outlined: true,
                          child: Text(
                            'Ask a question of your approved PDF library. Sources may not exist for every starter question. The assistant will identify evidence gaps.',
                          ),
                        ),
                        const SizedBox(height: 12),
                        ...starters[subject]!.map(
                          (q) => Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: ActionChip(
                              label: Text(q),
                              onPressed: () => composer.text = q,
                            ),
                          ),
                        ),
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text(
                            'Include demonstration material',
                            style: TextStyle(fontSize: 13),
                          ),
                          subtitle: const Text(
                            'Demo content is never authoritative law.',
                            style: DSBTypography.muted,
                          ),
                          value: includeDemo,
                          onChanged: busy
                              ? null
                              : (v) => setState(() => includeDemo = v!),
                        ),
                      ],
                      if (hasOlderMessages)
                        TextButton(
                          onPressed: olderMessages,
                          child: const Text('Load earlier messages'),
                        ),
                      ...messages.map(bubble),
                      if (partial.isNotEmpty)
                        bubble({'role': 'assistant', 'text': partial}),
                      if (busy) const LinearProgressIndicator(),
                      if (stage.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Text(stage, style: DSBTypography.muted),
                        ),
                      if (error != null) DSBErrorState(error!),
                      if (!three && sources.isNotEmpty)
                        TextButton.icon(
                          onPressed: () => showSource(sources.first),
                          icon: const Icon(Icons.menu_book_outlined),
                          label: Text(
                            'View ${sources.length} verified sources',
                          ),
                        ),
                    ],
                  ),
                ),
                Container(
                  color: Colors.white,
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: composer,
                          minLines: 1,
                          maxLines: 4,
                          maxLength: 6000,
                          decoration: const InputDecoration(
                            hintText: 'Ask about CT, VAT, TP, IFRS...',
                            counterText: '',
                          ),
                          onSubmitted: (_) => send(),
                        ),
                      ),
                      const SizedBox(width: 10),
                      IconButton.filled(
                        tooltip: busy ? 'Stop generation' : 'Send question',
                        onPressed: busy ? stop : () => send(),
                        icon: Icon(busy ? Icons.stop : Icons.arrow_upward),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (three) SizedBox(width: 285, child: sourcesPanel()),
        ],
      );
    },
  );
}

class SourceViewer extends StatefulWidget {
  const SourceViewer({super.key, required this.api, required this.source});
  final ApiClient api;
  final Json source;
  @override
  State<SourceViewer> createState() => _SourceState();
}

class _SourceState extends State<SourceViewer> {
  Json? page;
  Uint8List? preview;
  String? error;
  bool loading = true;
  late int number;
  @override
  void initState() {
    super.initState();
    number = widget.source['physical_page'] as int;
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
      preview = null;
    });
    try {
      final result = await widget.api.get(
        '/ai/documents/${widget.source['version_id']}/pages/$number',
      );
      final bytes = await widget.api.bytes(result['preview_path'] as String);
      if (mounted) {
        setState(() {
          page = result;
          preview = bytes;
          loading = false;
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

  Future<void> original() async {
    try {
      final result = await widget.api.get(
        '/ai/documents/${widget.source['version_id']}/download',
      );
      final url =
          result['url'] as String? ??
          widget.api.absoluteUrl(result['path'] as String);
      await launchUrl(Uri.parse('$url#page=$number'));
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  @override
  Widget build(BuildContext context) => Dialog(
    child: ConstrainedBox(
      constraints: BoxConstraints(
        maxWidth: 850,
        maxHeight: MediaQuery.sizeOf(context).height * .88,
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    widget.source['title'] as String,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                IconButton(
                  tooltip: 'Close source',
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    '${widget.source['issuer']} · ${widget.source['document_type']} · version ${widget.source['version']}',
                    style: DSBTypography.muted,
                  ),
                  if (widget.source['demo'] == true)
                    const Text(
                      'DEMONSTRATION ONLY — NOT UAE LAW',
                      style: TextStyle(
                        color: DSBColors.violet,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  const SizedBox(height: 12),
                  DSBCard(
                    color: DSBColors.lavender,
                    child: SelectableText(widget.source['passage'] as String),
                  ),
                  const SizedBox(height: 12),
                  if (loading)
                    const DSBLoadingState()
                  else if (error != null)
                    DSBErrorState(error!, onRetry: load)
                  else ...[
                    Text(
                      'Physical PDF page $number · printed ${page?['printed_label']}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    Text('${page?['provenance']}', style: DSBTypography.muted),
                    if (preview != null)
                      Image.memory(preview!, fit: BoxFit.contain),
                    ExpansionTile(
                      title: const Text('Extracted page text'),
                      children: [
                        SelectableText(page?['text'] as String? ?? ''),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 10,
              children: [
                IconButton(
                  tooltip: 'Previous page',
                  onPressed: number <= 1 || loading
                      ? null
                      : () {
                          number--;
                          load();
                        },
                  icon: const Icon(Icons.chevron_left),
                ),
                Text('Page $number / ${page?['page_count'] ?? '—'}'),
                IconButton(
                  tooltip: 'Next page',
                  onPressed:
                      loading ||
                          number >= (page?['page_count'] as int? ?? number)
                      ? null
                      : () {
                          number++;
                          load();
                        },
                  icon: const Icon(Icons.chevron_right),
                ),
                TextButton(
                  onPressed: original,
                  child: const Text('Open original PDF'),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
