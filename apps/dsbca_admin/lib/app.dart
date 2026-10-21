import 'knowledge.dart';
import 'professional.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';

final apiProvider = ChangeNotifierProvider((ref) => ApiClient()..restore());
final routesProvider = Provider((ref) {
  final api = ref.read(apiProvider);
  return GoRouter(
    initialLocation: '/login',
    refreshListenable: api,
    redirect: (_, s) =>
        s.uri.path != '/login' && (!api.signedIn || !api.canEdit)
        ? '/login'
        : s.uri.path == '/login' && api.signedIn && api.canEdit
        ? '/dashboard'
        : null,
    routes: [
      GoRoute(path: '/login', builder: (_, _) => const AdminLogin()),
      GoRoute(
        path: '/:section',
        builder: (_, s) => AdminShell(section: s.pathParameters['section']!),
      ),
    ],
  );
});

class AdminApp extends ConsumerWidget {
  const AdminApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => MaterialApp.router(
    title: 'DSBCA Administration',
    debugShowCheckedModeBanner: false,
    theme: DSBTheme.light,
    routerConfig: ref.watch(routesProvider),
  );
}

class AdminLogin extends ConsumerStatefulWidget {
  const AdminLogin({super.key});
  @override
  ConsumerState<AdminLogin> createState() => _AdminLoginState();
}

class _AdminLoginState extends ConsumerState<AdminLogin> {
  final email = TextEditingController(), password = TextEditingController();
  String? error;
  bool busy = false;
  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: DSBCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'DSB',
                  style: TextStyle(
                    fontSize: 42,
                    fontWeight: FontWeight.w800,
                    color: DSBColors.violet,
                  ),
                ),
                const Text('Administration', style: DSBTypography.heading),
                const SizedBox(height: 8),
                const Text(
                  'Content, people and professional learning.',
                  style: DSBTypography.muted,
                ),
                const SizedBox(height: 28),
                DSBTextField(controller: email, label: 'Work email'),
                const SizedBox(height: 12),
                DSBTextField(
                  controller: password,
                  label: 'Password',
                  obscure: true,
                ),
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Text(
                      error!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                const SizedBox(height: 20),
                DSBPrimaryButton(
                  'Sign in',
                  loading: busy,
                  onPressed: () async {
                    setState(() {
                      busy = true;
                      error = null;
                    });
                    try {
                      final api = ref.read(apiProvider);
                      await api.authenticate(email.text, password.text);
                      if (!api.canEdit) {
                        await api.logout();
                        throw StateError('No administrative role');
                      }
                      if (context.mounted) context.go('/dashboard');
                    } catch (e) {
                      if (mounted) {
                        setState(
                          () => error = e is StateError
                              ? 'This account has no administrative role.'
                              : apiError(e),
                        );
                      }
                    } finally {
                      if (mounted) setState(() => busy = false);
                    }
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

const sections = [
  'dashboard',
  'users',
  'content',
  'updates',
  'notifications',
  'compliance',
  'settings',
  'audit-logs',
  'ai',
  'professional',
];
const labels = [
  'Overview',
  'Users',
  'Learning content',
  'Regulatory updates',
  'Notifications',
  'Compliance overview',
  'Settings',
  'Audit logs',
  'AI Knowledge Base',
  'Professional platform',
];
const navIcons = [
  Icons.grid_view,
  Icons.people_outline,
  Icons.menu_book_outlined,
  Icons.newspaper,
  Icons.notifications_none,
  Icons.business_outlined,
  Icons.settings_outlined,
  Icons.history,
  Icons.auto_awesome_outlined,
  Icons.workspaces_outline,
];

class AdminShell extends ConsumerWidget {
  const AdminShell({super.key, required this.section});
  final String section;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final index = sections.indexOf(section);
    final title = index < 0 ? 'Administration' : labels[index];
    Widget navigation() => Container(
      color: DSBColors.navy,
      width: 240,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Padding(
              padding: EdgeInsets.all(26),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'DSB',
                    style: TextStyle(
                      color: Color(0xFFAB7BFF),
                      fontSize: 36,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  Text(
                    'ADMINISTRATION',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      letterSpacing: 1.5,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                children: List.generate(
                  sections.length,
                  (i) => ListTile(
                    selected: index == i,
                    selectedTileColor: const Color(0xFF302459),
                    leading: Icon(navIcons[i], color: const Color(0xFFB69AFF)),
                    title: Text(
                      labels[i],
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                    ),
                    onTap: () {
                      if (MediaQuery.sizeOf(context).width < 900) {
                        Navigator.pop(context);
                      }
                      context.go('/${sections[i]}');
                    },
                  ),
                ),
              ),
            ),
            TextButton(
              onPressed: () async {
                await ref.read(apiProvider).logout();
                if (context.mounted) context.go('/login');
              },
              child: const Text(
                'Sign out',
                style: TextStyle(color: Colors.white),
              ),
            ),
          ],
        ),
      ),
    );
    final wide = MediaQuery.sizeOf(context).width >= 900;
    return Scaffold(
      appBar: AppBar(
        title: Text(title, style: DSBTypography.heading.copyWith(fontSize: 23)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 20),
            child: Center(
              child: Text(
                ref.watch(apiProvider).user?['name'] as String? ??
                    'Administrator',
                style: DSBTypography.muted,
              ),
            ),
          ),
        ],
      ),
      drawer: wide ? null : Drawer(child: navigation()),
      body: Row(
        children: [
          if (wide) navigation(),
          Expanded(
            child: Padding(
              padding: EdgeInsets.all(wide ? 28 : 16),
              child: switch (section) {
                'dashboard' => AdminDashboard(
                  compliance: section == 'compliance',
                ),
                'compliance' => ProfessionalAdmin(
                  key: ValueKey(section),
                  api: ref.watch(apiProvider),
                  initialTab: 2,
                ),
                'users' => const UserManagement(),
                'content' => ProfessionalAdmin(
                  key: ValueKey(section),
                  api: ref.watch(apiProvider),
                  initialTab: 1,
                ),
                'updates' => ProfessionalAdmin(
                  key: ValueKey(section),
                  api: ref.watch(apiProvider),
                  initialTab: 3,
                ),
                'notifications' => ProfessionalAdmin(
                  key: ValueKey(section),
                  api: ref.watch(apiProvider),
                  initialTab: 5,
                ),
                'settings' => const SettingsPanel(),
                'audit-logs' => const ResourceTable(
                  path: '/admin/audit-logs',
                  kind: 'audit-logs',
                  readOnly: true,
                ),
                'professional' => ProfessionalAdmin(
                  key: ValueKey(section),
                  api: ref.watch(apiProvider),
                ),
                'ai' => KnowledgeWorkspace(api: ref.watch(apiProvider)),
                _ => const DSBEmptyState('Choose a section.'),
              },
            ),
          ),
        ],
      ),
    );
  }
}

class AdminDashboard extends ConsumerStatefulWidget {
  const AdminDashboard({super.key, this.compliance = false});
  final bool compliance;
  @override
  ConsumerState<AdminDashboard> createState() => _DashboardState();
}

class _DashboardState extends ConsumerState<AdminDashboard> {
  late final future = ref.read(apiProvider).get('/admin/dashboard');
  @override
  Widget build(BuildContext context) => FutureBuilder<Json>(
    future: future,
    builder: (_, s) {
      if (s.hasError) return DSBErrorState(apiError(s.error!));
      if (!s.hasData) return const DSBLoadingState();
      final data = s.data!;
      return ListView(
        children: [
          const Text(
            'Your practice, at a glance',
            style: DSBTypography.heading,
          ),
          const SizedBox(height: 8),
          const Text(
            'A shared source of truth for DSBCA.',
            style: DSBTypography.muted,
          ),
          const SizedBox(height: 24),
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children:
                (widget.compliance
                        ? ['companies']
                        : [
                            'users',
                            'videos',
                            'publications',
                            'updates',
                            'webinars',
                            'companies',
                          ])
                    .map(
                      (x) => SizedBox(
                        width: 210,
                        child: DSBCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(x.toUpperCase(), style: DSBTypography.muted),
                              const SizedBox(height: 12),
                              Text(
                                '${data[x]}',
                                style: DSBTypography.heading.copyWith(
                                  fontSize: 36,
                                  color: DSBColors.violet,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    )
                    .toList(),
          ),
          const SizedBox(height: 24),
          if (widget.compliance)
            const DSBCard(
              child: Text(
                'Aggregate metrics only. Client identity records and company documents remain private to their owners.',
              ),
            )
          else ...[
            const Text(
              'Recent administrative activity',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            ...((data['recent_activity'] as List?) ?? []).map(
              (x) => ListTile(
                leading: const Icon(Icons.history),
                title: Text('${x['action']}'),
                subtitle: Text('${x['created_at']}'),
              ),
            ),
          ],
        ],
      );
    },
  );
}

class ContentManagement extends StatefulWidget {
  const ContentManagement({super.key});
  @override
  State<ContentManagement> createState() => _ContentState();
}

class _ContentState extends State<ContentManagement> {
  String kind = 'videos';
  @override
  Widget build(BuildContext context) => Column(
    children: [
      DropdownButtonFormField<String>(
        initialValue: kind,
        items: [
          'categories',
          'videos',
          'publications',
          'chapters',
          'articles',
          'webinars',
        ].map((x) => DropdownMenuItem(value: x, child: Text(x))).toList(),
        onChanged: (v) => setState(() => kind = v!),
      ),
      const SizedBox(height: 20),
      Expanded(
        child: ResourceTable(
          key: ValueKey(kind),
          path: '/admin/content/$kind',
          kind: kind,
        ),
      ),
    ],
  );
}

class ResourceTable extends ConsumerStatefulWidget {
  const ResourceTable({
    super.key,
    required this.path,
    required this.kind,
    this.readOnly = false,
  });
  final String path, kind;
  final bool readOnly;
  @override
  ConsumerState<ResourceTable> createState() => _ResourceState();
}

class _ResourceState extends ConsumerState<ResourceTable> {
  int page = 1;
  String search = '';
  late Future<ApiPage> future;
  void load() => future = ref
      .read(apiProvider)
      .page(widget.path, query: {'page': page, 'page_size': 20, 'q': search});
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> edit([Json? row]) async {
    final kind = widget.kind;
    List<Json> choices = [];
    if (kind != 'categories' && kind != 'notifications') {
      try {
        choices =
            (await ref
                    .read(apiProvider)
                    .page(
                      kind == 'chapters'
                          ? '/admin/content/publications'
                          : '/categories',
                      query: {'page_size': 100},
                    ))
                .items;
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text(apiError(e))));
        }
        return;
      }
      if (!mounted) return;
    }
    final fields = kind == 'categories'
        ? ['name']
        : kind == 'chapters'
        ? ['title', 'publication_id', 'position', 'pages', 'download_url']
        : kind == 'notifications'
        ? ['title', 'body', 'category', 'deep_link']
        : [
            'title',
            'body',
            'category_id',
            if (kind == 'videos') ...['duration_seconds', 'media_url'],
            if (kind == 'publications') 'download_url',
            if (kind == 'articles') 'reading_minutes',
            if (kind == 'updates') 'source_url',
            if (kind == 'webinars') ...['starts_at', 'join_url'],
          ];
    final controllers = {
      for (final f in fields)
        f: TextEditingController(
          text:
              '${row?[f] ?? (f == 'deep_link'
                      ? '/updates'
                      : f == 'position' || f == 'reading_minutes'
                      ? '1'
                      : f == 'pages' || f == 'duration_seconds'
                      ? '0'
                      : '')}',
        ),
    };
    String status = row?['status'] as String? ?? 'draft';
    bool demo = row?['demo'] == true, busy = false;
    String? error;
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, change) => DSBDialog(
          title: '${row == null ? 'Create' : 'Edit'} $kind',
          actions: [
            TextButton(
              onPressed: busy ? null : () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: busy
                  ? null
                  : () async {
                      final data = <String, dynamic>{};
                      for (final f in fields) {
                        final value = controllers[f]!.text.trim();
                        data[f] =
                            [
                              'position',
                              'pages',
                              'duration_seconds',
                              'reading_minutes',
                            ].contains(f)
                            ? int.tryParse(value)
                            : value.isEmpty &&
                                  ![
                                    'title',
                                    'name',
                                    'body',
                                    'category',
                                    'publication_id',
                                  ].contains(f)
                            ? null
                            : value;
                      }
                      if (kind != 'categories' && kind != 'chapters') {
                        data['status'] = status;
                        data['demo'] = demo;
                      }
                      change(() {
                        busy = true;
                        error = null;
                      });
                      try {
                        final api = ref.read(apiProvider);
                        if (row == null) {
                          await api.post(widget.path, data);
                        } else {
                          await api.put('${widget.path}/${row['id']}', data);
                        }
                        if (ctx.mounted) Navigator.pop(ctx, true);
                      } catch (e) {
                        change(() {
                          error = apiError(e);
                          busy = false;
                        });
                      }
                    },
              child: Text(status == 'published' ? 'Save & publish' : 'Save'),
            ),
          ],
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final f in fields)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: f == 'category_id' || f == 'publication_id'
                      ? DropdownButtonFormField<String>(
                          initialValue: controllers[f]!.text.isEmpty
                              ? ''
                              : controllers[f]!.text,
                          isExpanded: true,
                          decoration: InputDecoration(
                            labelText: f == 'category_id'
                                ? 'Subject'
                                : 'Publication',
                          ),
                          items: [
                            const DropdownMenuItem(
                              value: '',
                              child: Text('Select a subject or publication'),
                            ),
                            ...choices.map(
                              (x) => DropdownMenuItem(
                                value: x['id'] as String,
                                child: Text(
                                  '${x['title'] ?? x['name']}',
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ),
                          ],
                          onChanged: (value) =>
                              controllers[f]!.text = value ?? '',
                        )
                      : TextField(
                          controller: controllers[f],
                          onChanged: (_) => change(() {}),
                          maxLines: f == 'body' ? 5 : 1,
                          decoration: InputDecoration(
                            labelText: f.replaceAll('_', ' '),
                          ),
                        ),
                ),
              if (kind != 'categories' && kind != 'chapters') ...[
                DropdownButtonFormField<String>(
                  initialValue: status,
                  items:
                      [
                            'draft',
                            'published',
                            if (kind != 'notifications') 'archived',
                          ]
                          .map(
                            (x) => DropdownMenuItem(value: x, child: Text(x)),
                          )
                          .toList(),
                  onChanged: (v) => status = v!,
                ),
                CheckboxListTile(
                  title: const Text('Demonstration content'),
                  value: demo,
                  onChanged: (v) => change(() => demo = v!),
                ),
              ],
              if (error != null)
                Text(error!, style: const TextStyle(color: Colors.red)),
              if (kind == 'notifications')
                DSBNotificationTile(
                  title: controllers['title']!.text,
                  body: controllers['body']!.text,
                  category: controllers['category']!.text,
                ),
            ],
          ),
        ),
      ),
    );
    for (final c in controllers.values) {
      c.dispose();
    }
    if (saved == true) setState(load);
  }

  Future<void> remove(Json row) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => DSBDialog(
        title: 'Remove ${widget.kind}?',
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Remove'),
          ),
        ],
        child: const Text(
          'Content is archived; structural records are deleted when unreferenced.',
        ),
      ),
    );
    if (yes != true) return;
    try {
      await ref.read(apiProvider).delete('${widget.path}/${row['id']}');
      setState(load);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(apiError(e))));
      }
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Row(
        children: [
          Expanded(
            child: DSBSearchBar(
              hint: 'Search ${widget.kind}',
              onSubmitted: (q) => setState(() {
                search = q;
                page = 1;
                load();
              }),
            ),
          ),
          if (!widget.readOnly) ...[
            const SizedBox(width: 12),
            DSBPrimaryButton('+ Create', onPressed: edit),
          ],
        ],
      ),
      const SizedBox(height: 16),
      Expanded(
        child: FutureBuilder<ApiPage>(
          future: future,
          builder: (_, s) {
            if (s.hasError) {
              return DSBErrorState(
                apiError(s.error!),
                onRetry: () => setState(load),
              );
            }
            if (!s.hasData) return const DSBLoadingState();
            final data = s.data!;
            return Column(
              children: [
                Expanded(
                  child: data.items.isEmpty
                      ? const DSBEmptyState('No records found.')
                      : LayoutBuilder(
                          builder: (_, c) => SingleChildScrollView(
                            child: SingleChildScrollView(
                              scrollDirection: Axis.horizontal,
                              child: ConstrainedBox(
                                constraints: BoxConstraints(
                                  minWidth: c.maxWidth,
                                ),
                                child: DataTable(
                                  columns: [
                                    const DataColumn(
                                      label: Text('Title / action'),
                                    ),
                                    const DataColumn(
                                      label: Text('Status / date'),
                                    ),
                                    if (!widget.readOnly)
                                      const DataColumn(label: Text('Actions')),
                                  ],
                                  rows: data.items
                                      .map(
                                        (x) => DataRow(
                                          cells: [
                                            DataCell(
                                              SizedBox(
                                                width: c.maxWidth < 600
                                                    ? 180
                                                    : 340,
                                                child: Text(
                                                  '${x['title'] ?? x['name'] ?? x['action']}',
                                                  maxLines: 2,
                                                  overflow:
                                                      TextOverflow.ellipsis,
                                                ),
                                              ),
                                            ),
                                            DataCell(
                                              Text(
                                                '${x['status'] ?? x['created_at']}',
                                              ),
                                            ),
                                            if (!widget.readOnly)
                                              DataCell(
                                                Row(
                                                  children: [
                                                    IconButton(
                                                      tooltip: 'Edit',
                                                      onPressed: () => edit(x),
                                                      icon: const Icon(
                                                        Icons.edit_outlined,
                                                      ),
                                                    ),
                                                    IconButton(
                                                      tooltip: 'Remove',
                                                      onPressed: () =>
                                                          remove(x),
                                                      icon: const Icon(
                                                        Icons.delete_outline,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                          ],
                                        ),
                                      )
                                      .toList(),
                                ),
                              ),
                            ),
                          ),
                        ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Flexible(
                      child: Text(
                        '${data.total} records Â· Page $page',
                        style: DSBTypography.muted,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Previous page',
                      onPressed: page <= 1
                          ? null
                          : () => setState(() {
                              page--;
                              load();
                            }),
                      icon: const Icon(Icons.chevron_left),
                    ),
                    IconButton(
                      tooltip: 'Next page',
                      onPressed: page * 20 >= data.total
                          ? null
                          : () => setState(() {
                              page++;
                              load();
                            }),
                      icon: const Icon(Icons.chevron_right),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    ],
  );
}

class UserManagement extends ConsumerStatefulWidget {
  const UserManagement({super.key});
  @override
  ConsumerState<UserManagement> createState() => _UsersState();
}

class _UsersState extends ConsumerState<UserManagement> {
  int page = 1;
  String q = '';
  late Future<ApiPage> future;
  void load() => future = ref
      .read(apiProvider)
      .page('/admin/users', query: {'q': q, 'page': page});
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> edit(Json user) async {
    String status = user['status'] as String;
    final roles = (user['roles'] as List).cast<String>().toSet();
    String? error;
    final yes = await showDialog<bool>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, change) => DSBDialog(
          title: user['email'] as String,
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () async {
                try {
                  await ref.read(apiProvider).put(
                    '/admin/users/${user['id']}',
                    {'status': status, 'roles': roles.toList()},
                  );
                  if (ctx.mounted) Navigator.pop(ctx, true);
                } catch (e) {
                  change(() => error = apiError(e));
                }
              },
              child: const Text('Save'),
            ),
          ],
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('User ID: ${user['id']}', style: DSBTypography.muted),
              DropdownButtonFormField<String>(
                initialValue: status,
                items: ['active', 'suspended']
                    .map((x) => DropdownMenuItem(value: x, child: Text(x)))
                    .toList(),
                onChanged: (v) => status = v!,
              ),
              ...['user', 'content_editor', 'admin', 'super_admin'].map(
                (r) => CheckboxListTile(
                  title: Text(r),
                  value: roles.contains(r),
                  onChanged: (v) => change(() {
                    v! ? roles.add(r) : roles.remove(r);
                  }),
                ),
              ),
              const Text(
                'Role changes require a super administrator.',
                style: DSBTypography.muted,
              ),
              if (error != null)
                Text(error!, style: const TextStyle(color: Colors.red)),
            ],
          ),
        ),
      ),
    );
    if (yes == true) setState(load);
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      DSBSearchBar(
        hint: 'Search users by email',
        onSubmitted: (s) => setState(() {
          q = s;
          page = 1;
          load();
        }),
      ),
      const SizedBox(height: 16),
      Expanded(
        child: FutureBuilder<ApiPage>(
          future: future,
          builder: (_, s) {
            if (s.hasError) return DSBErrorState(apiError(s.error!));
            if (!s.hasData) return const DSBLoadingState();
            return Column(
              children: [
                Expanded(
                  child: ListView(
                    children: s.data!.items
                        .map(
                          (x) => Card(
                            child: ListTile(
                              title: Text(x['email'] as String),
                              subtitle: Text(
                                '${x['status']} Â· ${(x['roles'] as List).join(', ')}',
                              ),
                              trailing: IconButton(
                                tooltip: 'Edit account',
                                onPressed: () => edit(x),
                                icon: const Icon(Icons.edit_outlined),
                              ),
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Text('Page $page · ${s.data!.total} users'),
                    ),
                    IconButton(
                      onPressed: page == 1
                          ? null
                          : () => setState(() {
                              page--;
                              load();
                            }),
                      icon: const Icon(Icons.chevron_left),
                    ),
                    IconButton(
                      onPressed: page * 20 >= s.data!.total
                          ? null
                          : () => setState(() {
                              page++;
                              load();
                            }),
                      icon: const Icon(Icons.chevron_right),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    ],
  );
}

class SettingsPanel extends ConsumerStatefulWidget {
  const SettingsPanel({super.key});
  @override
  ConsumerState<SettingsPanel> createState() => _SettingsState();
}

class _SettingsState extends ConsumerState<SettingsPanel> {
  final name = TextEditingController();
  String? error;
  @override
  void initState() {
    super.initState();
    ref
        .read(apiProvider)
        .page('/admin/settings')
        .then((p) {
          final item = p.items.where((x) => x['key'] == 'identity').firstOrNull;
          if (mounted) {
            setState(
              () => name.text = item?['value']?['name'] as String? ?? 'DSBCA',
            );
          }
        })
        .catchError((Object e) {
          if (mounted) setState(() => error = apiError(e));
        });
  }

  @override
  void dispose() {
    name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListView(
    children: [
      DSBCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Application identity', style: DSBTypography.heading),
            const SizedBox(height: 20),
            DSBTextField(controller: name, label: 'Application name'),
            const SizedBox(height: 16),
            if (error != null)
              Text(error!, style: const TextStyle(color: Colors.red)),
            DSBPrimaryButton(
              'Save settings',
              onPressed: () async {
                try {
                  await ref.read(apiProvider).put('/admin/settings', {
                    'key': 'identity',
                    'value': {'name': name.text},
                  });
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Settings saved')),
                    );
                  }
                } catch (e) {
                  if (mounted) setState(() => error = apiError(e));
                }
              },
            ),
          ],
        ),
      ),
    ],
  );
}
