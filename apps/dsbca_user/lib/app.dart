import 'dart:async';
import 'dart:convert';
import 'research.dart';
import 'professional.dart';
import 'academy.dart';
import 'compliance.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:design_system/design_system.dart';
import 'package:api_client/api_client.dart';

Json? calculatorPrefill(String? value) {
  if (value == null) return null;
  try {
    final decoded = jsonDecode(value);
    return decoded is Map ? Json.from(decoded) : null;
  } catch (_) {
    return null;
  }
}

final apiProvider = ChangeNotifierProvider((ref) => ApiClient()..restore());
final dashboardProvider = FutureProvider<Json>((ref) async {
  final api = ref.watch(apiProvider);
  return api.signedIn ? api.get('/dashboard') : <String, dynamic>{};
});
final routerProvider = Provider(
  (ref) => GoRouter(
    initialLocation: '/sign-in',
    refreshListenable: ref.read(apiProvider),
    redirect: (_, state) =>
        state.uri.path == '/sign-in' && ref.read(apiProvider).signedIn
        ? '/home'
        : null,
    routes: [
      GoRoute(path: '/sign-in', builder: (_, _) => const SignIn()),
      StatefulShellRoute.indexedStack(
        builder: (_, state, shell) => AppShell(
          path: state.uri.path,
          navigationShell: shell,
          child: shell,
        ),
        branches: [
          StatefulShellBranch(
            routes: [GoRoute(path: '/home', builder: (_, _) => const Home())],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/discuss', builder: (_, _) => const Discuss()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/learn',
                builder: (_, s) => Learn(
                  publications: s.uri.queryParameters['tab'] == 'publications',
                ),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/toolkit', builder: (_, _) => const Toolkit()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/updates', builder: (_, _) => const Updates()),
            ],
          ),
        ],
      ),
      ShellRoute(
        builder: (_, state, child) =>
            AppShell(path: state.uri.path, child: child),
        routes: [
          GoRoute(path: '/reminders', builder: (_, _) => const Reminders()),
          GoRoute(
            path: '/learning-library',
            builder: (_, _) => Consumer(
              builder: (_, ref, _) =>
                  LearningLibrary(api: ref.watch(apiProvider)),
            ),
          ),
          GoRoute(
            path: '/toolkit/:code',
            builder: (_, s) => Consumer(
              builder: (_, ref, _) => ProfessionalToolkit(
                api: ref.watch(apiProvider),
                code: s.pathParameters['code'],
                prefill: calculatorPrefill(s.uri.queryParameters['inputs']),
              ),
            ),
          ),
          GoRoute(
            path: '/delivery-settings',
            builder: (_, _) => Consumer(
              builder: (_, ref, _) =>
                  NotificationStatus(api: ref.watch(apiProvider)),
            ),
          ),
          GoRoute(path: '/notifications', builder: (_, _) => const Alerts()),
          GoRoute(path: '/profile', builder: (_, _) => const Profile()),
          GoRoute(path: '/settings', builder: (_, _) => const Profile()),
          GoRoute(
            path: '/content/:kind/:id',
            builder: (_, s) => Consumer(
              builder: (_, ref, _) => AcademyDetail(
                key: ValueKey(s.uri.path),
                api: ref.watch(apiProvider),
                kind: s.pathParameters['kind']!,
                id: s.pathParameters['id']!,
              ),
            ),
          ),
        ],
      ),
    ],
  ),
);

class UserApp extends ConsumerWidget {
  const UserApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => MaterialApp.router(
    title: 'DSBCA · Tax and Accounting Companion',
    debugShowCheckedModeBanner: false,
    theme: DSBTheme.light,
    routerConfig: ref.watch(routerProvider),
  );
}

void toast(BuildContext context, String text) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
const topics = ['Corporate Tax', 'VAT', 'TP', 'IFRS', 'Pillar Two'];

class AppShell extends StatelessWidget {
  const AppShell({
    super.key,
    required this.path,
    required this.child,
    this.navigationShell,
  });
  final StatefulNavigationShell? navigationShell;
  final String path;
  final Widget child;
  @override
  Widget build(BuildContext context) {
    final routes = ['/home', '/discuss', '/learn', '/toolkit', '/updates'];
    final index = path.startsWith('/toolkit')
        ? 3
        : path.startsWith('/discuss')
        ? 1
        : path.startsWith('/learn') ||
              [
                '/content/videos',
                '/content/publications',
                '/content/articles',
                '/content/chapters',
              ].any(path.startsWith)
        ? 2
        : path == '/home'
        ? 0
        : 4;
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1024),
            child: child,
          ),
        ),
      ),
      bottomNavigationBar: DSBBottomNavigation(
        index: index < 0 ? 4 : index,
        onTap: (i) {
          if (navigationShell != null) {
            navigationShell!.goBranch(
              i,
              initialLocation: i == navigationShell!.currentIndex,
            );
          } else {
            context.go(routes[i]);
          }
        },
      ),
    );
  }
}

class PageBody extends StatelessWidget {
  const PageBody({super.key, required this.children, this.padding = 20});
  final List<Widget> children;
  final double padding;
  @override
  Widget build(BuildContext context) => ListView(
    padding: EdgeInsets.fromLTRB(padding, 48, padding, 24),
    children: children,
  );
}

class Section extends StatelessWidget {
  const Section(this.title, {super.key, this.action, this.onTap});
  final String title;
  final String? action;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 16, bottom: 10),
    child: Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          ),
        ),
        if (action != null) TextButton(onPressed: onTap, child: Text(action!)),
      ],
    ),
  );
}

class RemoteList extends ConsumerStatefulWidget {
  const RemoteList({
    super.key,
    required this.path,
    required this.builder,
    this.query,
    this.empty = 'Nothing published here yet.',
    this.hideWhenEmpty = false,
  });
  final String path, empty;
  final bool hideWhenEmpty;
  final Json? query;
  final Widget Function(List<Json>) builder;
  @override
  ConsumerState<RemoteList> createState() => _RemoteListState();
}

class _RemoteListState extends ConsumerState<RemoteList> {
  late Future<ApiPage> future;
  void load() =>
      future = ref.read(apiProvider).page(widget.path, query: widget.query);
  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void didUpdateWidget(RemoteList oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.path != widget.path ||
        oldWidget.query.toString() != widget.query.toString()) {
      load();
    }
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<ApiPage>(
    future: future,
    builder: (_, snap) {
      if (snap.hasError) {
        return DSBErrorState(
          apiError(snap.error!),
          onRetry: () => setState(load),
        );
      }
      if (!snap.hasData) return const DSBLoadingState();
      if (snap.data!.items.isEmpty) {
        return widget.hideWhenEmpty
            ? const SizedBox.shrink()
            : DSBEmptyState(widget.empty);
      }
      return widget.builder(snap.data!.items);
    },
  );
}

class Segments extends StatelessWidget {
  const Segments({
    super.key,
    required this.labels,
    required this.index,
    required this.onChanged,
  });
  final List<String> labels;
  final int index;
  final ValueChanged<int> onChanged;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(4),
    decoration: BoxDecoration(
      color: const Color(0xFFEAE4F2),
      borderRadius: BorderRadius.circular(15),
    ),
    child: Row(
      children: List.generate(
        labels.length,
        (i) => Expanded(
          child: InkWell(
            onTap: () => onChanged(i),
            child: Container(
              alignment: Alignment.center,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                color: i == index ? Colors.white : Colors.transparent,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                labels[i],
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

class SignIn extends ConsumerStatefulWidget {
  const SignIn({super.key});
  @override
  ConsumerState<SignIn> createState() => _SignInState();
}

class _SignInState extends ConsumerState<SignIn> {
  final email = TextEditingController(),
      password = TextEditingController(),
      name = TextEditingController(),
      token = TextEditingController();
  bool expanded = false, register = false, reset = false, busy = false;
  String? error;
  @override
  void dispose() {
    for (final c in [email, password, name, token]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> submit() async {
    if (!email.text.contains('@')) {
      setState(() => error = 'Enter a valid email address.');
      return;
    }
    if (!expanded && !reset) {
      setState(() => expanded = true);
      return;
    }
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final api = ref.read(apiProvider);
      if (reset) {
        await api.post(
          token.text.isEmpty
              ? '/auth/request-password-reset'
              : '/auth/reset-password',
          token.text.isEmpty
              ? {'email': email.text}
              : {'token': token.text, 'password': password.text},
        );
        if (mounted) {
          toast(
            context,
            token.text.isEmpty
                ? 'If the account exists, a reset link will be sent.'
                : 'Password updated. Sign in again.',
          );
        }
      } else {
        await api.authenticate(
          email.text.trim(),
          password.text,
          name: register ? name.text : null,
        );
        if (mounted) context.go('/home');
      }
    } catch (e) {
      if (mounted) setState(() => error = apiError(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.white,
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: ListView(
            children: [
              Container(
                padding: const EdgeInsets.fromLTRB(28, 66, 28, 38),
                decoration: const BoxDecoration(
                  color: DSBColors.navy,
                  borderRadius: BorderRadius.vertical(
                    bottom: Radius.circular(32),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'DSB',
                      style: TextStyle(
                        fontSize: 44,
                        color: Color(0xFF9455FF),
                        fontWeight: FontWeight.w800,
                        letterSpacing: 3,
                      ),
                    ),
                    Container(width: 215, height: 5, color: DSBColors.muted),
                    const SizedBox(height: 6),
                    const Text(
                      'CHARTERED ACCOUNTANTS',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        letterSpacing: 1.8,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'UAE | INDIA',
                      style: TextStyle(
                        color: Color(0xFFB69AFF),
                        fontSize: 12,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 28),
                    Text(
                      'DSBCA',
                      style: DSBTypography.heading.copyWith(
                        fontSize: 34,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'UAE tax and IFRS, in your pocket. Ask questions, watch short explainers, run quick calculations.',
                      style: TextStyle(
                        color: Color(0xFFD5CDEB),
                        fontSize: 16,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Wrap(
                      spacing: 7,
                      runSpacing: 7,
                      children:
                          [
                                'Corporate Tax',
                                'VAT',
                                'Transfer Pricing',
                                'IFRS',
                                'Pillar Two',
                              ]
                              .map(
                                (x) => Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 10,
                                    vertical: 7,
                                  ),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF2F2759),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: Text(
                                    x,
                                    style: const TextStyle(
                                      color: Color(0xFFD5CDEB),
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              )
                              .toList(),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('Email or user ID'),
                    const SizedBox(height: 8),
                    DSBTextField(
                      controller: email,
                      hint: 'you@company.com',
                      keyboardType: TextInputType.emailAddress,
                    ),
                    if (expanded || reset) ...[
                      const SizedBox(height: 12),
                      if (register) ...[
                        DSBTextField(controller: name, label: 'Full name'),
                        const SizedBox(height: 12),
                      ],
                      DSBTextField(
                        controller: password,
                        label: 'Password · minimum 12 characters',
                        obscure: true,
                      ),
                      if (reset) ...[
                        const SizedBox(height: 12),
                        DSBTextField(
                          controller: token,
                          label: 'Reset token from email (if received)',
                        ),
                      ],
                    ],
                    if (error != null)
                      Text(error!, style: const TextStyle(color: Colors.red)),
                    const SizedBox(height: 16),
                    DSBPrimaryButton(
                      reset
                          ? 'Send link / reset password'
                          : register
                          ? 'Create account'
                          : 'Continue',
                      loading: busy,
                      onPressed: submit,
                    ),
                    if (expanded)
                      Wrap(
                        alignment: WrapAlignment.center,
                        children: [
                          TextButton(
                            onPressed: () => setState(() {
                              register = !register;
                              reset = false;
                            }),
                            child: Text(
                              register ? 'Sign in' : 'Create account',
                            ),
                          ),
                          TextButton(
                            onPressed: () => setState(() {
                              reset = !reset;
                              register = false;
                            }),
                            child: const Text('Forgot password?'),
                          ),
                        ],
                      ),
                    const SizedBox(height: 16),
                    const Row(
                      children: [
                        Expanded(child: Divider()),
                        Padding(
                          padding: EdgeInsets.symmetric(horizontal: 12),
                          child: Text('or', style: DSBTypography.muted),
                        ),
                        Expanded(child: Divider()),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: ['Google', 'Microsoft']
                          .map(
                            (x) => Expanded(
                              child: Padding(
                                padding: EdgeInsets.only(
                                  right: x == 'Google' ? 10 : 0,
                                ),
                                child: DSBSecondaryButton(
                                  x,
                                  onPressed: () async {
                                    try {
                                      await ref
                                          .read(apiProvider)
                                          .get(
                                            '/auth/oauth/${x.toLowerCase()}',
                                          );
                                    } catch (e) {
                                      if (context.mounted) {
                                        toast(context, apiError(e));
                                      }
                                    }
                                  },
                                ),
                              ),
                            ),
                          )
                          .toList(),
                    ),
                    const SizedBox(height: 16),
                    TextButton(
                      onPressed: () => context.go('/home'),
                      child: const Text(
                        'Explore as guest',
                        style: TextStyle(decoration: TextDecoration.underline),
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Free for every professional. No subscription, no card.\nBy DSB Chartered Accountants · FTA registered tax agency',
                      textAlign: TextAlign.center,
                      style: DSBTypography.muted,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class Home extends ConsumerWidget {
  const Home({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiProvider);
    final dashboard = ref.watch(dashboardProvider);
    return PageBody(
      children: [
        Row(
          children: [
            InkWell(
              onTap: () => context.go('/profile'),
              child: const CircleAvatar(
                backgroundColor: DSBColors.lavender,
                child: Text('DS', style: TextStyle(color: DSBColors.violet)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Good morning', style: DSBTypography.muted),
                  Text(
                    api.user?['name'] as String? ?? 'Welcome, guest',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            Badge(
              isLabelVisible:
                  (dashboard.asData?.value['unread_count'] as int? ?? 0) > 0,
              child: IconButton.filledTonal(
                onPressed: () => context.go('/notifications'),
                icon: const Icon(Icons.notifications_none),
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),
        DSBSearchBar(
          hint: 'Ask about CT, VAT, TP, IFRS...',
          onSubmitted: (_) => context.go('/discuss'),
        ),
        const SizedBox(height: 18),
        if (api.signedIn)
          dashboard.when(
            data: (data) =>
                DeadlineCard(deadline: data['next_deadline'] as Json?),
            error: (error, _) => DSBErrorState(
              apiError(error),
              onRetry: () => ref.invalidate(dashboardProvider),
            ),
            loading: () => const DSBLoadingState(),
          )
        else
          const DeadlineCard(),
        const SizedBox(height: 18),
        LayoutBuilder(
          builder: (_, c) => GridView.count(
            crossAxisCount: c.maxWidth > 600 ? 6 : 3,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio:
                ((c.maxWidth - (c.maxWidth > 600 ? 50 : 20)) /
                    (c.maxWidth > 600 ? 6 : 3)) /
                (104 +
                    (MediaQuery.textScalerOf(context).scale(14) - 14).clamp(
                          0,
                          28,
                        ) *
                        12),
            children: List.generate(6, (i) {
              const labels = [
                'Discuss',
                'Videos',
                'Library',
                'Toolkit',
                'Reminders',
                'Webinars',
              ];
              const icons = [
                Icons.chat_bubble_outline,
                Icons.ondemand_video,
                Icons.menu_book_outlined,
                Icons.calculate_outlined,
                Icons.alarm,
                Icons.calendar_today_outlined,
              ];
              const paths = [
                '/discuss',
                '/learn',
                '/learn?tab=publications',
                '/toolkit',
                '/reminders',
                '/updates',
              ];
              return InkWell(
                onTap: () => context.go(paths[i]),
                child: DSBCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: i == 4 ? DSBColors.peach : DSBColors.lavender,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(
                          icons[i],
                          color: DSBColors.violet,
                          size: 22,
                        ),
                      ),
                      Text(
                        labels[i],
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ),
        ),
        Section(
          'What changed',
          action: 'See all',
          onTap: () => context.go('/updates'),
        ),
        RemoteList(
          path: '/updates',
          builder: (items) => contentCards(context, items, 'updates'),
        ),
      ],
    );
  }
}

class DeadlineCard extends StatelessWidget {
  const DeadlineCard({super.key, this.deadline});
  final Json? deadline;
  @override
  Widget build(BuildContext context) => DSBCard(
    color: DSBColors.navy,
    padding: 18,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'NEXT DEADLINE',
          style: TextStyle(
            color: Color(0xFFB69AFF),
            fontSize: 12,
            letterSpacing: 1,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        Text(
          deadline?['title'] as String? ?? 'Your deadlines, in one place',
          style: DSBTypography.heading.copyWith(
            color: Colors.white,
            fontSize: 22,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          deadline == null
              ? 'Add a company to track renewals and compliance.'
              : 'Due ${deadline!['due_on']}',
          style: const TextStyle(color: Color(0xFFD5CDEB)),
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: DSBPrimaryButton(
                'Open checklist',
                onPressed: () => context.go('/reminders'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF2F2759),
                ),
                onPressed: () => context.go('/reminders'),
                child: const Text('My reminders'),
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

Widget contentCards(BuildContext c, List<Json> items, String kind) => Column(
  children: items
      .map(
        (x) => DSBNotificationTile(
          title: x['title'] as String,
          body: x['demo'] == true
              ? 'Demonstration content · review details'
              : x['body'] as String? ?? '',
          category: kind,
          read: x['read_at'] != null,
          onTap: () => c.go('/content/$kind/${x['id']}'),
        ),
      )
      .toList(),
);

class Discuss extends ConsumerWidget {
  const Discuss({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) =>
      ResearchScreen(api: ref.watch(apiProvider));
}

class Learn extends ConsumerStatefulWidget {
  const Learn({super.key, this.publications = false});
  final bool publications;
  @override
  ConsumerState<Learn> createState() => _LearnState();
}

class _LearnState extends ConsumerState<Learn> {
  String search = '';
  String? category, videoCategory;
  Timer? timer;
  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PageBody(
    children: [
      Align(
        alignment: Alignment.centerRight,
        child: TextButton.icon(
          onPressed: () => context.push('/learning-library'),
          icon: const Icon(Icons.school_outlined),
          label: const Text('My learning paths & saved resources'),
        ),
      ),
      Segments(
        labels: const ['Videos', 'Publications'],
        index: widget.publications ? 1 : 0,
        onChanged: (i) =>
            context.go(i == 0 ? '/learn' : '/learn?tab=publications'),
      ),
      const SizedBox(height: 12),
      DSBSearchBar(
        hint: widget.publications
            ? 'Search articles, books, chapters...'
            : 'Search: CT return, IAS 19, DMTT...',
        onChanged: (q) {
          timer?.cancel();
          timer = Timer(const Duration(milliseconds: 300), () {
            if (mounted) setState(() => search = q);
          });
        },
      ),
      const SizedBox(height: 8),
      RemoteList(
        path: '/categories',
        builder: (items) => SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              DSBCategoryChip(
                'All',
                selected: category == null,
                onTap: () => setState(() {
                  category = null;
                  videoCategory = null;
                }),
              ),
              ...items.map(
                (x) => DSBCategoryChip(
                  x['name'] as String,
                  selected: category == x['id'],
                  onTap: () => setState(() {
                    category = x['id'] as String;
                    videoCategory = null;
                  }),
                ),
              ),
            ],
          ),
        ),
      ),
      if (!widget.publications)
        RemoteList(
          path: '/video-categories',
          hideWhenEmpty: true,
          query: {if (category != null) 'subject_id': category},
          builder: (items) => SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                DSBCategoryChip(
                  'All video topics',
                  selected: videoCategory == null,
                  onTap: () => setState(() => videoCategory = null),
                ),
                ...items.map(
                  (x) => DSBCategoryChip(
                    x['name'] as String,
                    selected: videoCategory == x['id'],
                    onTap: () =>
                        setState(() => videoCategory = x['id'] as String),
                  ),
                ),
              ],
            ),
          ),
        ),
      if (!widget.publications) ...[
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          children:
              ['QFZP', 'Computation', 'CT return', 'Small Business Relief']
                  .map(
                    (x) => ActionChip(
                      label: Text(x, style: const TextStyle(fontSize: 12)),
                      onPressed: () => setState(() => search = x),
                    ),
                  )
                  .toList(),
        ),
        const Section('Video lessons'),
      ] else
        const SizedBox(height: 14),
      RemoteList(
        path: widget.publications ? '/publications' : '/videos',
        query: {
          'q': search,
          if (category != null) 'category_id': category,
          if (!widget.publications && videoCategory != null)
            'video_category_id': videoCategory,
        },
        builder: (items) => Column(
          children: List.generate(items.length, (i) {
            final x = items[i];
            final seconds = x['duration_seconds'] as int? ?? 0;
            return widget.publications
                ? Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Column(
                      children: [
                        DSBPublicationCard(
                          title: x['title'] as String,
                          subtitle: x['demo'] == true
                              ? 'Demonstration publication'
                              : 'Browse chapters and downloads',
                          onTap: () =>
                              context.go('/content/publications/${x['id']}'),
                        ),
                        RemoteList(
                          path: '/publications/${x['id']}/chapters',
                          builder: (chapters) => DSBCard(
                            outlined: true,
                            padding: 0,
                            child: Column(
                              children: chapters
                                  .take(3)
                                  .map(
                                    (chapter) => ListTile(
                                      dense: true,
                                      leading: Text(
                                        '${chapter['position']}'.padLeft(
                                          2,
                                          '0',
                                        ),
                                        style: const TextStyle(
                                          color: DSBColors.violet,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      title: Text(
                                        chapter['title'] as String,
                                        style: const TextStyle(
                                          fontSize: 14,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      subtitle: Text(
                                        'PDF · ${chapter['pages']} pages',
                                        style: DSBTypography.muted,
                                      ),
                                      trailing: IconButton(
                                        tooltip: 'View chapter download',
                                        onPressed: () => context.go(
                                          '/content/publications/${x['id']}',
                                        ),
                                        icon: const Icon(
                                          Icons.download_outlined,
                                          size: 20,
                                          color: DSBColors.violet,
                                        ),
                                      ),
                                    ),
                                  )
                                  .toList(),
                            ),
                          ),
                        ),
                      ],
                    ),
                  )
                : DSBVideoCard(
                    title: x['title'] as String,
                    index: i + 1,
                    demo: x['demo'] == true,
                    duration:
                        '${seconds ~/ 60}:${(seconds % 60).toString().padLeft(2, '0')}',
                    onTap: () => context.go('/content/videos/${x['id']}'),
                  );
          }),
        ),
      ),
      if (widget.publications) ...[
        const Section('From our desk'),
        RemoteList(
          path: '/articles',
          query: {'q': search},
          builder: (items) => Column(
            children: items
                .map(
                  (x) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: DSBCard(
                      padding: 14,
                      child: Row(
                        children: [
                          Expanded(
                            child: InkWell(
                              onTap: () =>
                                  context.go('/content/articles/${x['id']}'),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    x['title'] as String,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    'Article · ${x['reading_minutes']} min read',
                                    style: DSBTypography.muted,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          BookmarkButton(id: x['id'] as String),
                        ],
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ),
      ],
    ],
  );
}

class BookmarkButton extends ConsumerStatefulWidget {
  const BookmarkButton({super.key, required this.id});
  final String id;
  @override
  ConsumerState<BookmarkButton> createState() => _BookmarkState();
}

class _BookmarkState extends ConsumerState<BookmarkButton> {
  bool saved = false;
  @override
  void initState() {
    super.initState();
    if (ref.read(apiProvider).signedIn) {
      ref
          .read(apiProvider)
          .get('/articles/${widget.id}/bookmark')
          .then((x) {
            if (mounted) setState(() => saved = x['bookmarked'] == true);
          })
          .catchError((Object _) {});
    }
  }

  @override
  Widget build(BuildContext context) => IconButton(
    tooltip: 'Bookmark',
    icon: Icon(saved ? Icons.bookmark : Icons.bookmark_border),
    onPressed: () async {
      final api = ref.read(apiProvider);
      if (!api.signedIn) {
        context.go('/sign-in');
        return;
      }
      try {
        if (saved) {
          await api.delete('/articles/${widget.id}/bookmark');
        } else {
          await api.put('/articles/${widget.id}/bookmark', {});
        }
        if (mounted) setState(() => saved = !saved);
      } catch (e) {
        if (context.mounted) toast(context, apiError(e));
      }
    },
  );
}

class Toolkit extends ConsumerWidget {
  const Toolkit({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) =>
      ProfessionalToolkit(api: ref.watch(apiProvider));
}

class Updates extends ConsumerStatefulWidget {
  const Updates({super.key});
  @override
  ConsumerState<Updates> createState() => _UpdatesState();
}

class _UpdatesState extends ConsumerState<Updates> {
  int tab = 0;
  final selected = <String>{};
  @override
  void initState() {
    super.initState();
    if (ref.read(apiProvider).signedIn) {
      ref
          .read(apiProvider)
          .get('/notifications/preferences')
          .then((x) {
            if (mounted) {
              setState(
                () => selected.addAll((x['categories'] as List).cast<String>()),
              );
            }
          })
          .catchError((Object _) {});
    }
  }

  @override
  Widget build(BuildContext context) => PageBody(
    children: [
      Align(
        alignment: Alignment.centerRight,
        child: TextButton.icon(
          onPressed: () => context.push('/delivery-settings'),
          icon: const Icon(Icons.notifications_active_outlined),
          label: const Text('Subscribe to topics'),
        ),
      ),
      const Text('Updates', style: DSBTypography.heading),
      const SizedBox(height: 16),
      Segments(
        labels: const ['Notifications', 'Webinars'],
        index: tab,
        onChanged: (i) => setState(() => tab = i),
      ),
      const SizedBox(height: 14),
      InkWell(
        onTap: () => context.go('/reminders'),
        child: const DSBCard(
          color: DSBColors.navy,
          child: Row(
            children: [
              Icon(Icons.calendar_today_outlined, color: Color(0xFFB69AFF)),
              SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Company reminders',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'Track renewals and deadlines',
                      style: TextStyle(color: Color(0xFFD5CDEB), fontSize: 13),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: Color(0xFFB69AFF)),
            ],
          ),
        ),
      ),
      const SizedBox(height: 12),
      const Text('Notify me about', style: DSBTypography.muted),
      Wrap(
        children: topics
            .map(
              (x) => DSBCategoryChip(
                x,
                multi: true,
                selected: selected.contains(x),
                onTap: () async {
                  final api = ref.read(apiProvider);
                  if (!api.signedIn) {
                    context.go('/sign-in');
                    return;
                  }
                  final previous = Set<String>.from(selected);
                  setState(() {
                    selected.contains(x) ? selected.remove(x) : selected.add(x);
                  });
                  try {
                    await api.put('/notifications/preferences', {
                      'categories': selected.toList(),
                      'in_app': true,
                    });
                  } catch (e) {
                    if (mounted) {
                      setState(() {
                        selected.clear();
                        selected.addAll(previous);
                      });
                      if (context.mounted) toast(context, apiError(e));
                    }
                  }
                },
              ),
            )
            .toList(),
      ),
      const SizedBox(height: 10),
      if (tab == 0 && ref.watch(apiProvider).signedIn)
        RemoteList(
          path: '/notifications',
          builder: (items) =>
              notificationCards(context, ref.read(apiProvider), items),
        ),
      Section(tab == 0 ? 'Regulatory updates' : 'Upcoming webinars'),
      RemoteList(
        path: tab == 0 ? '/updates' : '/webinars',
        builder: (items) =>
            contentCards(context, items, tab == 0 ? 'updates' : 'webinars'),
      ),
    ],
  );
}

Widget notificationCards(BuildContext c, ApiClient api, List<Json> items) =>
    Column(
      children: items
          .map(
            (x) => DSBNotificationTile(
              title: x['title'] as String,
              body: x['body'] as String,
              category: x['category'] as String,
              read: x['read_at'] != null,
              onTap: () async {
                try {
                  await api.patch('/notifications/${x['id']}/read');
                  if (c.mounted) {
                    final path = x['deep_link'] as String? ?? '/updates';
                    final open = await showDialog<bool>(
                      context: c,
                      builder: (ctx) => DSBDialog(
                        title: x['title'] as String,
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(ctx, false),
                            child: const Text('Close'),
                          ),
                          FilledButton(
                            onPressed: () => Navigator.pop(ctx, true),
                            child: const Text('Open related page'),
                          ),
                        ],
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              x['category'] as String,
                              style: const TextStyle(
                                color: DSBColors.violet,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Text(x['body'] as String),
                            if (x['created_at'] != null)
                              Text(
                                '${x['created_at']}',
                                style: DSBTypography.muted,
                              ),
                          ],
                        ),
                      ),
                    );
                    if (c.mounted) {
                      if (open == true) {
                        c.go(
                          path.startsWith('/') &&
                                  !path.startsWith('//') &&
                                  !path.contains(':')
                              ? path
                              : '/updates',
                        );
                      } else {
                        c.go('/updates');
                      }
                    }
                  }
                } catch (e) {
                  if (c.mounted) toast(c, apiError(e));
                }
              },
            ),
          )
          .toList(),
    );

class Alerts extends ConsumerWidget {
  const Alerts({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Container(
    color: DSBColors.navy,
    child: PageBody(
      children: [
        TextButton.icon(
          onPressed: () => context.push('/delivery-settings'),
          icon: const Icon(Icons.tune),
          label: const Text('Delivery preferences & subscriptions'),
        ),
        Text(
          TimeOfDay.now().format(context),
          textAlign: TextAlign.center,
          style: DSBTypography.heading.copyWith(
            color: Colors.white,
            fontSize: 60,
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'How alerts arrive',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        const Text(
          'In-app notifications · device push preview only',
          textAlign: TextAlign.center,
          style: TextStyle(color: Color(0xFFD5CDEB), fontSize: 12),
        ),
        const SizedBox(height: 24),
        if (ref.watch(apiProvider).signedIn)
          RemoteList(
            path: '/notifications',
            builder: (items) =>
                notificationCards(context, ref.read(apiProvider), items),
          )
        else
          DSBCard(
            child: Column(
              children: [
                const Text('Sign in to see your alerts.'),
                TextButton(
                  onPressed: () => context.go('/sign-in'),
                  child: const Text('Sign in'),
                ),
              ],
            ),
          ),
      ],
    ),
  );
}

class Profile extends ConsumerWidget {
  const Profile({super.key});
  Future<void> editName(BuildContext context, ApiClient api) async {
    final controller = TextEditingController(
      text: api.user?['name'] as String? ?? '',
    );
    String? error;
    bool busy = false;
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, change) => AlertDialog(
          title: const Text('Edit profile'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                maxLength: 100,
                decoration: const InputDecoration(labelText: 'Display name'),
              ),
              if (error != null) Text(error!),
            ],
          ),
          actions: [
            TextButton(
              onPressed: busy ? null : () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: busy
                  ? null
                  : () async {
                      if (controller.text.trim().isEmpty) {
                        change(() => error = 'Enter your name.');
                        return;
                      }
                      change(() {
                        busy = true;
                        error = null;
                      });
                      try {
                        await api.updateProfile(controller.text.trim());
                        if (ctx.mounted) Navigator.pop(ctx);
                      } catch (e) {
                        if (ctx.mounted) {
                          change(() {
                            busy = false;
                            error = apiError(e);
                          });
                        }
                      }
                    },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
    controller.dispose();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiProvider);
    return PageBody(
      children: [
        const Text('Profile & settings', style: DSBTypography.heading),
        const SizedBox(height: 24),
        DSBCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                api.user?['name'] as String? ?? 'Guest',
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                api.user?['email'] as String? ??
                    'Sign in to save preferences and reminders.',
              ),
              const SizedBox(height: 16),
              if (api.signedIn)
                TextButton.icon(
                  onPressed: () => editName(context, api),
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Edit profile'),
                ),
              DSBSecondaryButton(
                'Notification preferences',
                onPressed: () => context.go('/delivery-settings'),
              ),
              const SizedBox(height: 12),
              DSBPrimaryButton(
                api.signedIn ? 'Sign out' : 'Sign in',
                onPressed: () async {
                  if (api.signedIn) await api.logout();
                  if (context.mounted) context.go('/sign-in');
                },
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class Reminders extends ConsumerWidget {
  const Reminders({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) =>
      ComplianceWorkspace(api: ref.watch(apiProvider));
}
