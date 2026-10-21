import 'dart:async';
import 'dart:convert';
import 'package:share_plus/share_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

class ProfessionalToolkit extends StatefulWidget {
  const ProfessionalToolkit({
    super.key,
    required this.api,
    this.code,
    this.prefill,
  });
  final ApiClient api;
  final String? code;
  final Json? prefill;
  @override
  State<ProfessionalToolkit> createState() => _Toolkit();
}

class _Toolkit extends State<ProfessionalToolkit> {
  List<Json> definitions = [];
  Json? definition, result;
  String? error;
  bool busy = false, auto = false;
  Timer? timer;
  int generation = 0, schedulePage = 0;
  final fields = <String, TextEditingController>{};
  final values = <String, dynamic>{};
  String? rule;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final response = await widget.api.get('/professional/calculators');
      if (!mounted) return;
      setState(
        () => definitions = ((response['items'] as List?) ?? [])
            .map((e) => Json.from(e as Map))
            .toList(),
      );
      if (widget.code != null) {
        final item = definitions
            .where((x) => x['code'] == widget.code)
            .firstOrNull;
        if (item != null) select(item);
      }
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    for (final c in fields.values) {
      c.dispose();
    }
    super.dispose();
  }

  void select(Json item) {
    generation++;
    busy = false;
    timer?.cancel();
    for (final c in fields.values) {
      c.dispose();
    }
    fields.clear();
    values.clear();
    for (final raw in item['fields'] as List) {
      final f = Json.from(raw as Map);
      final key = f['key'] as String;
      final value = widget.prefill?[key] ?? f['default'];
      if (f['type'] == 'bool' || f['type'] == 'select') {
        values[key] = value;
      } else {
        fields[key] = TextEditingController(
          text: value is List || value is Map ? jsonEncode(value) : '$value',
        );
      }
    }
    setState(() {
      definition = item;
      result = null;
      error = null;
      rule = null;
      schedulePage = 0;
    });
  }

  Json inputs() {
    final data = Json.from(values);
    for (final raw in definition!['fields'] as List) {
      final f = Json.from(raw as Map);
      final key = f['key'] as String;
      if (fields.containsKey(key)) {
        final text = fields[key]!.text.trim();
        if (f['type'] == 'json') {
          if (text.isNotEmpty) data[key] = jsonDecode(text);
        } else {
          data[key] = text;
        }
      }
    }
    return data;
  }

  void changed() {
    if (auto) {
      timer?.cancel();
      timer = Timer(const Duration(milliseconds: 600), () => calculate());
    }
  }

  Future<void> calculate({bool save = false}) async {
    if (definition == null) return;
    if (save && !widget.api.signedIn) {
      setState(() => error = 'Sign in to save results.');
      return;
    }
    final current = ++generation;
    setState(() => busy = true);
    try {
      final response = await widget.api.post(
        '/professional/calculators/${definition!['code']}/calculate',
        {
          'inputs': inputs(),
          'rule_id': rule,
          'save': save,
          'title': definition!['title'],
        },
      );
      if (mounted && current == generation) {
        setState(() {
          result = response;
          error = null;
          schedulePage = 0;
        });
      }
    } catch (e) {
      if (mounted && current == generation) {
        setState(
          () => error = e is FormatException
              ? 'Check JSON array syntax.'
              : apiError(e),
        );
      }
    } finally {
      if (mounted && current == generation) setState(() => busy = false);
    }
  }

  Future<void> history() async {
    try {
      final page = await widget.api.page('/professional/calculations');
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => DSBDialog(
          title: 'Calculation history',
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Close'),
            ),
          ],
          child: SizedBox(
            width: 680,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (page.items.isEmpty)
                    const Text('No saved calculations yet.'),
                  ...page.items.map(
                    (x) => ListTile(
                      title: Text('${x['title']}'),
                      subtitle: Text('${x['created_at']}'),
                      onTap: () {
                        Navigator.pop(ctx);
                        final d = definitions
                            .where((r) => r['code'] == x['calculator'])
                            .firstOrNull;
                        if (d != null) {
                          select(d);
                          final saved = Json.from(x['inputs'] as Map);
                          for (final e in saved.entries) {
                            if (fields.containsKey(e.key)) {
                              fields[e.key]!.text = e.value is List
                                  ? jsonEncode(e.value)
                                  : '${e.value}';
                            } else {
                              values[e.key] = e.value;
                            }
                          }
                          setState(
                            () => result = {
                              ...Json.from(x['result'] as Map),
                              'run_id': x['id'],
                            },
                          );
                        }
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Widget input(Json f) {
    final key = f['key'] as String;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: switch (f['type']) {
        'bool' => CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(f['label'] as String),
          value: values[key] == true,
          onChanged: (v) {
            setState(() => values[key] = v);
            changed();
          },
        ),
        'select' => DropdownButtonFormField<String>(
          isExpanded: true,
          initialValue: values[key] as String,
          decoration: InputDecoration(labelText: f['label'] as String),
          items: (f['options'] as List)
              .map((x) => DropdownMenuItem(value: '$x', child: Text('$x')))
              .toList(),
          onChanged: (v) {
            setState(() => values[key] = v);
            changed();
          },
        ),
        _ => TextField(
          controller: fields[key],
          decoration: InputDecoration(
            labelText: f['label'] as String,
            helperText: f['type'] == 'date'
                ? 'YYYY-MM-DD'
                : f['type'] == 'json'
                ? 'JSON array; no sample is treated as a sourced benchmark'
                : null,
          ),
          keyboardType: f['type'] == 'number'
              ? const TextInputType.numberWithOptions(
                  decimal: true,
                  signed: true,
                )
              : TextInputType.text,
          minLines: f['type'] == 'json' ? 2 : 1,
          maxLines: f['type'] == 'json' ? 6 : 1,
          onChanged: (_) => changed(),
        ),
      },
    );
  }

  Widget output() {
    final r = result!;
    final rows = ((r['schedule'] as List?) ?? [])
        .map((x) => Json.from(x as Map))
        .toList();
    final current = rows.skip(schedulePage * 20).take(20).toList();
    final rules = r['rule'] as Map?;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DSBCard(
          color: DSBColors.navy,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${r['status']}'.replaceAll('_', ' ').toUpperCase(),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              ...(r['results'] as Map? ?? {}).entries.map(
                (e) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Text(
                    '${e.key.toString().replaceAll('_', ' ')}: ${e.value}',
                    style: const TextStyle(color: Colors.white),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        ...((r['warnings'] as List?) ?? []).map(
          (x) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: DSBCard(color: DSBColors.peach, child: Text('$x')),
          ),
        ),
        ExpansionTile(
          title: const Text('Formula, rule and assumptions'),
          children: [
            ...((r['formula'] as List?) ?? []).map(
              (x) => ListTile(title: Text('$x')),
            ),
            ListTile(
              title: Text('Rule: ${rules?['version'] ?? 'No published rule'}'),
              subtitle: Text('${r['rounding'] ?? ''}'),
            ),
            for (final source in (rules?['sources'] as List?) ?? [])
              ListTile(
                title: Text('${source['title']}'),
                subtitle: Text('Verified ${source['verified_on']}'),
                trailing: const Icon(Icons.open_in_new),
                onTap: () => launchUrl(Uri.parse(source['url'] as String)),
              ),
          ],
        ),
        if (current.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Text('Detailed schedule', style: DSBTypography.heading),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: current.first.keys
                  .map((k) => DataColumn(label: Text(k.replaceAll('_', ' '))))
                  .toList(),
              rows: current
                  .map(
                    (x) => DataRow(
                      cells: x.values.map((v) => DataCell(Text('$v'))).toList(),
                    ),
                  )
                  .toList(),
            ),
          ),
          Row(
            children: [
              TextButton(
                onPressed: schedulePage > 0
                    ? () => setState(() => schedulePage--)
                    : null,
                child: const Text('Previous'),
              ),
              Text('Page ${schedulePage + 1}'),
              TextButton(
                onPressed: (schedulePage + 1) * 20 < rows.length
                    ? () => setState(() => schedulePage++)
                    : null,
                child: const Text('Next'),
              ),
            ],
          ),
        ],
        Wrap(
          spacing: 8,
          children: [
            TextButton.icon(
              icon: const Icon(Icons.copy),
              label: const Text('Copy summary'),
              onPressed: () => Clipboard.setData(
                ClipboardData(
                  text: const JsonEncoder.withIndent('  ').convert(r),
                ),
              ),
            ),
            TextButton.icon(
              icon: const Icon(Icons.share_outlined),
              label: const Text('Share result'),
              onPressed: () => SharePlus.instance.share(
                ShareParams(
                  text: const JsonEncoder.withIndent('  ').convert(r),
                  sharePositionOrigin: const Rect.fromLTWH(0, 0, 1, 1),
                ),
              ),
            ),
            TextButton.icon(
              icon: const Icon(Icons.save_outlined),
              label: Text(r['run_id'] == null ? 'Save to my account' : 'Saved'),
              onPressed:
                  r['run_id'] == null && r['status'] != 'restricted' && !busy
                  ? () => calculate(save: true)
                  : null,
            ),
          ],
        ),
        const Text(
          'Saved results retain their original inputs, engine and rule snapshot.',
          style: DSBTypography.muted,
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.all(20),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                definition?['title'] as String? ?? 'Toolkit',
                style: DSBTypography.heading,
              ),
            ),
            IconButton(
              tooltip: 'Calculation history',
              onPressed: widget.api.signedIn ? history : null,
              icon: const Icon(Icons.history),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'Versioned rules · precise workings · saved calculations',
          style: DSBTypography.muted,
        ),
        const SizedBox(height: 20),
        if (error != null) DSBErrorState(error!, onRetry: load),
        if (definition == null)
          LayoutBuilder(
            builder: (_, c) => Wrap(
              spacing: 12,
              runSpacing: 12,
              children: definitions
                  .map(
                    (d) => SizedBox(
                      width: c.maxWidth >= 700
                          ? (c.maxWidth - 24) / 3
                          : c.maxWidth >= 450
                          ? (c.maxWidth - 12) / 2
                          : c.maxWidth,
                      child: DSBCard(
                        outlined: true,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              d['group'] as String,
                              style: DSBTypography.muted,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              d['title'] as String,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextButton(
                              onPressed: () => select(d),
                              child: const Text('Open calculator'),
                            ),
                          ],
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
        if (definition != null) ...[
          TextButton(
            onPressed: () => setState(() => definition = null),
            child: const Text('All calculators'),
          ),
          if (definition!['rule_required'] == true)
            DropdownButtonFormField<String>(
              isExpanded: true,
              initialValue: rule,
              decoration: const InputDecoration(
                labelText: 'Applicable reviewed rule',
              ),
              items: [
                const DropdownMenuItem<String>(
                  value: null,
                  child: Text('Select by financial period automatically'),
                ),
                ...((definition!['rules'] as List?) ?? []).map(
                  (r) => DropdownMenuItem(
                    value: r['id'] as String,
                    child: Text('${r['version']} · ${r['valid_from']}'),
                  ),
                ),
              ],
              onChanged: (v) => setState(() => rule = v),
            ),
          const SizedBox(height: 16),
          ...((definition!['fields'] as List).map(
            (f) => input(Json.from(f as Map)),
          )),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              DSBPrimaryButton(
                'Calculate',
                loading: busy,
                onPressed: () => calculate(),
              ),
              OutlinedButton(
                onPressed: () => select(definition!),
                child: const Text('Reset'),
              ),
            ],
          ),
          CheckboxListTile(
            title: const Text('Update results while editing'),
            value: auto,
            onChanged: (v) => setState(() => auto = v ?? false),
          ),
          if (result != null) output(),
        ],
      ],
    ),
  );
}

class LearningLibrary extends StatefulWidget {
  const LearningLibrary({super.key, required this.api});
  final ApiClient api;
  @override
  State<LearningLibrary> createState() => _Library();
}

class _Library extends State<LearningLibrary> {
  String view = 'paths';
  late Future<Json> future;
  @override
  void initState() {
    super.initState();
    load();
  }

  void load() {
    future = widget.api.get(
      view == 'paths'
          ? '/professional/learning/paths'
          : '/professional/learning/library',
      query: {'view': view},
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('My learning')),
    body: Column(
      children: [
        Wrap(
          spacing: 8,
          children: ['paths', 'saved', 'recent']
              .map(
                (v) => ChoiceChip(
                  label: Text(v),
                  selected: view == v,
                  onSelected: (_) => setState(() {
                    view = v;
                    load();
                  }),
                ),
              )
              .toList(),
        ),
        Expanded(
          child: FutureBuilder<Json>(
            future: future,
            key: ValueKey(view),
            builder: (_, s) {
              if (s.hasError) return DSBErrorState(apiError(s.error!));
              if (!s.hasData) return const DSBLoadingState();
              final items = (s.data!['items'] as List?) ?? [];
              if (items.isEmpty) {
                return const Center(
                  child: Text(
                    'No learning records yet. Published content and paths will appear here.',
                  ),
                );
              }
              return ListView(
                children: items.map((raw) {
                  final x = Json.from(raw as Map);
                  return DSBCard(
                    child: Column(
                      children: [
                        ListTile(
                          title: Text('${x['title']}'),
                          subtitle: Text(
                            view == 'paths'
                                ? '${x['progress_percent']}% complete'
                                : 'Last accessed ${x['updated_at']}',
                          ),
                          onTap: view == 'paths'
                              ? null
                              : () => context.push(x['path'] as String),
                        ),
                        if (view == 'paths') ...[
                          LinearProgressIndicator(
                            value: (x['progress_percent'] as num) / 100,
                          ),
                          TextButton(
                            onPressed: x['enrolled'] == true
                                ? null
                                : () async {
                                    await widget.api.post(
                                      '/professional/learning/paths/${x['id']}/enroll',
                                      {},
                                    );
                                    if (mounted) setState(load);
                                  },
                            child: Text(
                              x['enrolled'] == true ? 'Enrolled' : 'Enroll',
                            ),
                          ),
                          ...(x['items'] as List).map(
                            (i) => ListTile(
                              leading: Icon(
                                i['completed'] == true
                                    ? Icons.check_circle
                                    : Icons.play_circle_outline,
                              ),
                              title: Text('${i['title']}'),
                              onTap: () => context.push(
                                '/content/${i['kind']}/${i['resource_id']}',
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  );
                }).toList(),
              );
            },
          ),
        ),
      ],
    ),
  );
}

class NotificationStatus extends StatefulWidget {
  const NotificationStatus({super.key, required this.api});
  final ApiClient api;
  @override
  State<NotificationStatus> createState() => _NotificationStatus();
}

class _NotificationStatus extends State<NotificationStatus> {
  Json? settings;
  List<Json> jobs = [];
  List<String> subscriptions = [];
  String? error;
  final subjects = [
    'Corporate Tax',
    'VAT',
    'Transfer Pricing',
    'Pillar Two',
    'IFRS',
    'Audit',
    'Commercial/Regulatory Compliance',
  ];
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final values = await Future.wait([
        widget.api.get('/professional/notifications/settings'),
        widget.api.get('/professional/notifications/jobs'),
        widget.api.get('/professional/updates/subscriptions'),
      ]);
      if (mounted) {
        setState(() {
          settings = values[0];
          jobs = ((values[1]['items'] as List?) ?? [])
              .map((x) => Json.from(x as Map))
              .toList();
          subscriptions = ((values[2]['subjects'] as List?) ?? [])
              .cast<String>();
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Future<void> channel(String key, bool value) async {
    try {
      await widget.api.put('/professional/notifications/settings', {
        'in_app': key == 'in_app' ? value : settings?['in_app'] == true,
        'email': key == 'email' ? value : settings?['email'] == true,
        'push': key == 'push' ? value : settings?['push'] == true,
      });
      await load();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.all(20),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(
              child: Text(
                'Alerts & subscriptions',
                style: DSBTypography.heading,
              ),
            ),
            IconButton(
              tooltip: 'Refresh delivery state',
              onPressed: load,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        if (error != null) DSBErrorState(error!),
        if (settings == null) const DSBLoadingState(),
        if (settings != null) ...[
          for (final key in ['in_app', 'email', 'push'])
            SwitchListTile(
              title: Text(key.replaceAll('_', ' ')),
              subtitle: Text(
                key == 'in_app'
                    ? 'Available in your signed-in notification inbox'
                    : settings!['${key}_configured'] == true
                    ? 'Provider configured; actual delivery verification is separate'
                    : 'Provider setup pending; no external delivery is claimed',
              ),
              value: settings![key] == true,
              onChanged: (v) => channel(key, v),
            ),
          const Text(
            'Regulatory update subscriptions',
            style: DSBTypography.heading,
          ),
          ...subjects.map(
            (subject) => CheckboxListTile(
              title: Text(subject),
              value: subscriptions.contains(subject),
              onChanged: (enabled) async {
                final next = [...subscriptions];
                if (enabled == true) {
                  next.add(subject);
                } else {
                  next.remove(subject);
                }
                try {
                  await widget.api.put('/professional/updates/subscriptions', {
                    'subjects': next,
                  });
                  await load();
                } catch (e) {
                  if (mounted) setState(() => error = apiError(e));
                }
              },
            ),
          ),
          const Text(
            'Scheduled / recorded delivery',
            style: DSBTypography.heading,
          ),
          if (jobs.isEmpty)
            const Text(
              'No scheduled deliveries yet. Company and event workflows create these records.',
            ),
          ...jobs.map(
            (j) => ListTile(
              title: Text('${j['channel']} · ${j['status']}'),
              subtitle: Text(
                '${j['due_at']}\n${j['status'] == 'submitted'
                    ? 'Provider accepted the request; device/email delivery is unverified'
                    : j['status'] == 'delivered'
                    ? 'Available in the in-app inbox'
                    : j['status'] == 'blocked'
                    ? 'Delivery provider configuration or device registration is required'
                    : 'Pending or recorded workflow state'}',
              ),
            ),
          ),
          const Text(
            'Notifications are processed by the server scheduler. Keeping this screen open is not required.',
            style: DSBTypography.muted,
          ),
        ],
      ],
    ),
  );
}
