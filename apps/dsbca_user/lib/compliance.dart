import 'package:flutter/material.dart';
import 'media.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';

class ComplianceWorkspace extends StatefulWidget {
  const ComplianceWorkspace({super.key, required this.api});
  final ApiClient api;
  @override
  State<ComplianceWorkspace> createState() => _Compliance();
}

class _Compliance extends State<ComplianceWorkspace> {
  List<Json> companies = [], people = [];
  Json? workspace;
  String? selected, error;
  bool loading = true;
  String filter = 'all',
      categoryFilter = 'all',
      personFilter = 'all',
      dateFrom = '',
      dateTo = '';
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    if (!widget.api.signedIn) {
      setState(() => loading = false);
      return;
    }
    try {
      final cs = (await widget.api.page('/companies')).items;
      selected = cs.any((x) => x['id'] == selected)
          ? selected
          : cs.firstOrNull?['id'] as String?;
      Json? detail;
      List<Json> ps = [];
      if (selected != null) {
        detail = await widget.api.get(
          '/professional/companies/$selected/compliance',
        );
        ps = (await widget.api.page('/companies/$selected/people')).items;
      }
      if (mounted) {
        setState(() {
          companies = cs;
          workspace = detail;
          people = ps;
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

  Future<Json?> form(
    String title,
    Json fields, {
    Map<String, List<String>> choices = const {},
    Map<String, bool> bools = const {},
  }) async {
    final controllers = {
      for (final e in fields.entries)
        e.key: TextEditingController(text: '${e.value ?? ''}'),
    };
    final flags = Map<String, bool>.from(bools);
    final result = await showDialog<Json>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, change) => DSBDialog(
          title: title,
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, {
                for (final e in controllers.entries) e.key: e.value.text,
                ...flags,
              }),
              child: const Text('Confirm & save'),
            ),
          ],
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final e in controllers.entries)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: choices[e.key] == null
                      ? TextField(
                          controller: e.value,
                          decoration: InputDecoration(
                            labelText: e.key.replaceAll('_', ' '),
                          ),
                        )
                      : DropdownButtonFormField<String>(
                          isExpanded: true,
                          initialValue: e.value.text,
                          decoration: InputDecoration(
                            labelText: e.key.replaceAll('_', ' '),
                          ),
                          items: choices[e.key]!
                              .map(
                                (v) =>
                                    DropdownMenuItem(value: v, child: Text(v)),
                              )
                              .toList(),
                          onChanged: (v) => e.value.text = v!,
                        ),
                ),
              for (final e in flags.entries)
                CheckboxListTile(
                  title: Text(e.key.replaceAll('_', ' ')),
                  value: e.value,
                  onChanged: (v) => change(() => flags[e.key] = v ?? false),
                ),
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

  Future<void> company([Json? record]) async {
    final profile = Json.from(record?['profile_data'] as Map? ?? {});
    final fields = {
      'name': record?['name'] ?? '',
      'trn': record?['trn'] ?? '',
      for (final k in [
        'trading_name',
        'entity_type',
        'jurisdiction',
        'zone',
        'licensing_authority',
        'trade_licence_number',
        'incorporation_date',
        'financial_year_end',
        'corporate_tax_trn',
        'vat_trn',
        'contact_email',
        'contact_phone',
        'responsible_person',
      ])
        k: profile[k] ?? '',
    };
    final result = await form(
      record == null ? 'Add company' : 'Edit company',
      fields,
    );
    if (result == null) return;
    try {
      final data = {
        'name': result['name'],
        'trn': result['trn'] == '' ? null : result['trn'],
        'profile_data': {
          for (final e in result.entries)
            if (e.key != 'name' && e.key != 'trn') e.key: e.value,
        },
      };
      if (record == null) {
        final created = await widget.api.post('/companies', data);
        selected = created['id'] as String;
      } else {
        await widget.api.put('/companies/${record['id']}', data);
      }
      await load();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Future<void> person([Json? record]) async {
    final details = Json.from(record?["details"] as Map? ?? {});
    final result = await form(
      'Add person',
      {
        'name': record?['name'] ?? '',
        'role': record?['role'] ?? 'director',
        'email': details['email'] ?? '',
        'notes': details['notes'] ?? '',
      },
      choices: {
        'role': [
          'partner',
          'shareholder',
          'director',
          'manager',
          'signatory',
          'employee',
        ],
      },
    );
    if (result == null) return;
    try {
      final body = {
        'name': result['name'],
        'role': result['role'],
        'details': {'email': result['email'], 'notes': result['notes']},
      };
      if (record == null) {
        await widget.api.post('/companies/$selected/people', body);
      } else {
        await widget.api.put(
          '/companies/$selected/people/${record['id']}',
          body,
        );
      }
      await load();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Future<void> removeRecord(
    String path,
    String label, {
    bool companyRecord = false,
  }) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Delete $label?'),
        content: const Text(
          'This permanently removes the record. Archive documents instead when renewal history should be retained. Company deletion also removes its people, documents and compliance history.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete permanently'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.api.delete(path);
      if (companyRecord) selected = null;
      categoryFilter = 'all';
      personFilter = 'all';
      await load();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Future<void> attachDocument(Json doc) async {
    try {
      final asset = await choosePrivateAsset(widget.api, companyId: selected);
      if (asset == null) return;
      await widget.api.put(
        '/professional/companies/$selected/documents/${doc['id']}',
        {
          'title': doc['title'],
          'category': doc['category'],
          'expires_on': doc['expires_on'],
          'person_id': doc['person_id'],
          'status': doc['status'],
          'details': {
            ...Json.from(doc['details'] as Map? ?? {}),
            'asset_id': asset,
          },
        },
      );
      await load();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Widget documentActions(Json doc) => PopupMenuButton<String>(
    tooltip: 'Document actions',
    onSelected: (action) async {
      if (action == 'renew') {
        await document(doc);
      } else if (action == 'delete') {
        await removeRecord(
          '/companies/$selected/documents/${doc['id']}',
          'document',
        );
      } else if (action == 'upload') {
        await attachDocument(doc);
      } else {
        try {
          await openPrivateMedia(
            widget.api,
            (doc['details'] as Map)['asset_id'] as String,
          );
        } catch (e) {
          if (mounted) setState(() => error = apiError(e));
        }
      }
    },
    itemBuilder: (_) => [
      const PopupMenuItem(
        value: 'renew',
        child: Text('Edit / renew / archive'),
      ),
      const PopupMenuItem(
        value: 'upload',
        child: Text('Attach private PDF or image'),
      ),
      const PopupMenuItem(value: 'delete', child: Text('Delete document')),
      if ((doc['details'] as Map?)?['asset_id'] != null)
        const PopupMenuItem(value: 'open', child: Text('Open attachment')),
    ],
  );

  Future<void> document([Json? record]) async {
    final personLabels = {
      for (final entry in people.indexed)
        entry.$2['id'] as String:
            '${entry.$2['name']} (${entry.$2['role']}) #${entry.$1 + 1}',
    };
    final details = Json.from(record?['details'] as Map? ?? {});
    final result = await form(
      record == null ? 'Add expiry document' : 'Edit / renew document',
      {
        'title': record?['title'] ?? 'Trade Licence',
        'category': record?['category'] ?? 'Trade Licence',
        'expires_on': record?['expires_on'] ?? '',
        'issue_date': details['issue_date'] ?? '',
        'document_number': details['document_number'] ?? '',
        'person': personLabels[record?['person_id']] ?? 'None',
        'notes': details['notes'] ?? '',
        'status': record?['status'] ?? 'active',
      },
      choices: {
        'person': ['None', ...personLabels.values],
        'status': [
          'active',
          'renewed',
          'archived',
          'not_applicable',
          'needs_review',
        ],
      },
    );
    if (result == null) return;
    try {
      final body = {
        'title': result['title'],
        'category': result['category'],
        'expires_on': result['expires_on'],
        'person_id': personLabels.entries
            .where((e) => e.value == result['person'])
            .firstOrNull
            ?.key,
        'details': {
          ...details,
          'issue_date': result['issue_date'],
          'document_number': result['document_number'],
          'notes': result['notes'],
        },
        'status': result['status'],
      };
      if (record == null) {
        await widget.api.post(
          '/professional/companies/$selected/documents',
          body,
        );
      } else {
        await widget.api.put(
          '/professional/companies/$selected/documents/${record['id']}',
          body,
        );
      }
      await load();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Future<void> obligation() async {
    List<Json> rules = [];
    try {
      rules =
          ((await widget.api.get('/professional/compliance-rules'))['items']
                  as List)
              .map((x) => Json.from(x as Map))
              .toList();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
      return;
    }
    final labels = {
      for (final r in rules) '${r['code']} · ${r['version']}': r['id'],
    };
    final result = await form(
      'Create obligation / manual reminder',
      {
        'title': '',
        'period_start': '',
        'period_end': '',
        'due_on': '',
        'rule': 'Manual reminder',
      },
      choices: {
        'rule': ['Manual reminder', ...labels.keys],
      },
      bools: {
        'calendar_exception_verified': false,
        'facts_confirmed': false,
        'registered': false,
        'no_exceptions': false,
      },
    );
    if (result == null) return;
    try {
      await widget.api.post('/professional/companies/$selected/obligations', {
        'title': result['title'],
        'period_start': result['period_start'] == ''
            ? null
            : result['period_start'],
        'period_end': result['period_end'] == '' ? null : result['period_end'],
        'due_on': result['due_on'] == '' ? null : result['due_on'],
        'rule_id': labels[result['rule']],
        'facts_confirmed': result['facts_confirmed'],
        'facts': {
          'registered': result['registered'],
          'exceptions': result['no_exceptions'] != true,
          'calendar_exception_verified': result['calendar_exception_verified'],
        },
      });
      await load();
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  Future<void> preferences() async {
    try {
      final current = await widget.api.get('/professional/reminder-settings');
      final result = await form(
        'Reminder schedule',
        {'days_before': (current['days'] as List).join(',')},
        bools: {
          'enabled': current['enabled'] == true,
          'in_app': (current['channels'] as List).contains('in_app'),
          'email': (current['channels'] as List).contains('email'),
          'push': (current['channels'] as List).contains('push'),
        },
      );
      if (result == null) return;
      await widget.api.put('/professional/notifications/settings', {
        'in_app': result['in_app'],
        'email': result['email'],
        'push': result['push'],
      });
      await widget.api.put('/professional/reminder-settings', {
        'days': (result['days_before'] as String)
            .split(',')
            .map((v) => int.parse(v.trim()))
            .toList(),
        'enabled': result['enabled'],
        'channels': [
          for (final key in ['in_app', 'email', 'push'])
            if (result[key] == true) key,
        ],
      });
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final docs = ((workspace?['documents'] as List?) ?? [])
        .map((x) => Json.from(x as Map))
        .where(
          (x) =>
              (filter == 'all' || x['expiry_status'] == filter) &&
              (categoryFilter == 'all' || x['category'] == categoryFilter) &&
              (personFilter == 'all' || x['person_id'] == personFilter) &&
              (dateFrom.isEmpty ||
                  DateTime.tryParse(dateFrom) == null ||
                  DateTime.parse(x['expires_on'] as String).isAfter(
                    DateTime.parse(dateFrom).subtract(const Duration(days: 1)),
                  )) &&
              (dateTo.isEmpty ||
                  DateTime.tryParse(dateTo) == null ||
                  DateTime.parse(x['expires_on'] as String).isBefore(
                    DateTime.parse(dateTo).add(const Duration(days: 1)),
                  )),
        );
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text('Company compliance', style: DSBTypography.heading),
              ),
              IconButton(
                tooltip: 'Reminder schedule',
                onPressed: widget.api.signedIn ? preferences : null,
                icon: const Icon(Icons.notifications_active_outlined),
              ),
              IconButton(
                tooltip: 'Refresh',
                onPressed: load,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
          const Text(
            'Recorded expiries, supported deadlines and renewal history',
            style: DSBTypography.muted,
          ),
          if (error != null) DSBErrorState(error!, onRetry: load),
          if (!widget.api.signedIn)
            const DSBCard(
              child: Text('Sign in to manage your private company records.'),
            ),
          if (loading) const DSBLoadingState(),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              TextButton.icon(
                onPressed: widget.api.signedIn ? () => company() : null,
                icon: const Icon(Icons.add_business),
                label: const Text('Add company'),
              ),
              if (selected != null) ...[
                TextButton(
                  onPressed: () =>
                      company(companies.firstWhere((x) => x['id'] == selected)),
                  child: const Text('Edit profile'),
                ),
                TextButton(
                  onPressed: () => removeRecord(
                    '/companies/$selected',
                    'company',
                    companyRecord: true,
                  ),
                  child: const Text('Delete company'),
                ),
                TextButton(
                  onPressed: () => person(),
                  child: const Text('Add person'),
                ),
                TextButton(
                  onPressed: () => document(),
                  child: const Text('Add document'),
                ),
                TextButton(
                  onPressed: obligation,
                  child: const Text('Add obligation'),
                ),
              ],
            ],
          ),
          if (companies.isNotEmpty)
            DropdownButtonFormField<String>(
              isExpanded: true,
              initialValue: selected,
              key: ValueKey(selected),
              decoration: const InputDecoration(labelText: 'Company'),
              items: companies
                  .map(
                    (c) => DropdownMenuItem(
                      value: c['id'] as String,
                      child: Text(c['name'] as String),
                    ),
                  )
                  .toList(),
              onChanged: (v) {
                selected = v;
                categoryFilter = "all";
                personFilter = "all";
                load();
              },
            ),
          ExpansionTile(
            title: const Text('Filter documents'),
            children: [
              const SizedBox(height: 14),
              Wrap(
                spacing: 6,
                children:
                    [
                          'all',
                          'expired',
                          'due_soon',
                          'upcoming',
                          'needs_review',
                          'not_applicable',
                          'archived',
                        ]
                        .map(
                          (v) => ChoiceChip(
                            label: Text(v.replaceAll('_', ' ')),
                            selected: filter == v,
                            onSelected: (_) => setState(() => filter = v),
                          ),
                        )
                        .toList(),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 12,
                children: [
                  SizedBox(
                    width: 220,
                    child: DropdownButtonFormField<String>(
                      isExpanded: true,
                      initialValue: categoryFilter,
                      decoration: const InputDecoration(
                        labelText: 'Document category',
                      ),
                      items: [
                        const DropdownMenuItem(
                          value: 'all',
                          child: Text('All categories'),
                        ),
                        ...{
                          for (final raw
                              in (workspace?['documents'] as List?) ?? [])
                            raw['category'] as String,
                        }.map(
                          (value) => DropdownMenuItem(
                            value: value,
                            child: Text(value),
                          ),
                        ),
                      ],
                      onChanged: (v) => setState(() => categoryFilter = v!),
                    ),
                  ),
                  SizedBox(
                    width: 220,
                    child: DropdownButtonFormField<String>(
                      isExpanded: true,
                      initialValue: personFilter,
                      decoration: const InputDecoration(labelText: 'Person'),
                      items: [
                        const DropdownMenuItem(
                          value: 'all',
                          child: Text('All people'),
                        ),
                        ...people.map(
                          (p) => DropdownMenuItem(
                            value: p['id'] as String,
                            child: Text(p['name'] as String),
                          ),
                        ),
                      ],
                      onChanged: (v) => setState(() => personFilter = v!),
                    ),
                  ),
                  SizedBox(
                    width: 220,
                    child: TextField(
                      decoration: const InputDecoration(
                        labelText: 'Expiry from (YYYY-MM-DD)',
                      ),
                      onChanged: (v) => setState(() => dateFrom = v),
                    ),
                  ),
                  SizedBox(
                    width: 220,
                    child: TextField(
                      decoration: const InputDecoration(
                        labelText: 'Expiry to (YYYY-MM-DD)',
                      ),
                      onChanged: (v) => setState(() => dateTo = v),
                    ),
                  ),
                ],
              ),
            ],
          ),
          ...docs.map(
            (d) => Padding(
              padding: const EdgeInsets.only(top: 10),
              child: DSBCard(
                outlined: true,
                child: ListTile(
                  title: Text('${d['title']}'),
                  subtitle: Text(
                    '${d['category']} · ${d['expires_on']}\n${d['expiry_status']} · ${d['days_remaining']} days',
                  ),
                  trailing: documentActions(d),
                ),
              ),
            ),
          ),
          if (selected != null) ...[
            const SizedBox(height: 20),
            const Text('People', style: DSBTypography.heading),
            ...people.map(
              (p) => ListTile(
                title: Text('${p['name']}'),
                subtitle: Text('${p['role']}'),
                onTap: () => person(p),
                trailing: IconButton(
                  tooltip: 'Delete person',
                  onPressed: () => removeRecord(
                    '/companies/$selected/people/${p['id']}',
                    'person',
                  ),
                  icon: const Icon(Icons.delete_outline),
                ),
              ),
            ),
            const Text('Compliance timeline', style: DSBTypography.heading),
            ...((workspace?['obligations'] as List?) ?? []).map(
              (o) => DSBCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${o['title']}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    Text(
                      '${o['due_on'] ?? 'Awaiting facts'} · ${o['origin']} · ${o['status']}',
                    ),
                    Text('Basis: ${o['basis']}'),
                    Wrap(
                      children: [
                        for (final status in [
                          'completed',
                          'not_applicable',
                          'needs_review',
                          'superseded',
                        ])
                          TextButton(
                            onPressed: () async {
                              try {
                                await widget.api.patch(
                                  '/professional/companies/$selected/obligations/${o['id']}',
                                  {'status': status},
                                );
                                await load();
                              } catch (e) {
                                if (mounted) {
                                  setState(() => error = apiError(e));
                                }
                              }
                            },
                            child: Text(status.replaceAll('_', ' ')),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            ExpansionTile(
              title: const Text('Renewal / status history'),
              children: ((workspace?['history'] as List?) ?? [])
                  .map<Widget>(
                    (h) => ListTile(
                      title: Text('${h['action']}'),
                      subtitle: Text('${h['created_at']}'),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}
