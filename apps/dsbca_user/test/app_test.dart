import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:shared_utils/shared_utils.dart';
import 'package:dsbca_user/app.dart';

class DemoApi extends ApiClient {
  DemoApi({this.authenticated = true}) {
    user = {
      'id': 'demo',
      'name': 'Rahul',
      'email': 'demo@example.com',
      'roles': ['user'],
    };
  }
  @override
  bool get signedIn => authenticated;
  final bool authenticated;
  @override
  Future<Json> get(String path, {Json? query}) async {
    if (path == '/professional/calculators') {
      return Json.from(
        jsonDecode(File('test/fixtures/calculators.json').readAsStringSync())
            as Map,
      );
    }
    if (path == '/dashboard') {
      return {
        'next_deadline': {
          'title': 'VAT return · Jul–Sep quarter',
          'due_on': '2026-10-28',
        },
      };
    }
    if (path.contains('preferences')) {
      return {
        'categories': ['Corporate Tax', 'VAT', 'TP'],
        'in_app': true,
      };
    }
    return {'bookmarked': false};
  }

  @override
  Future<ApiPage> page(String path, {Json? query}) async {
    List<Json> rows = [];
    if (path == '/categories') {
      rows = [
        for (var i = 0; i < topics.length; i++) {'id': '$i', 'name': topics[i]},
      ];
    }
    if (path == '/videos') {
      rows = [
        for (final (i, title) in [
          'QFZP: the conditions, end to end',
          'From accounting profit to taxable income',
          'Filing the CT return on EmaraTax',
          'Small Business Relief: who can elect',
        ].indexed)
          {'id': '$i', 'title': title, 'duration_seconds': 1330, 'demo': true},
      ];
    }
    if (path == '/publications') {
      rows = [
        {
          'id': 'book',
          'title': 'UAE Corporate Tax, chapter by chapter',
          'demo': true,
        },
      ];
    }
    if (path.endsWith('/chapters')) {
      rows = [
        for (final (i, title) in [
          'Who is a taxable person',
          'Free zone persons and QFZP',
          'From accounting profit to taxable income',
        ].indexed)
          {'id': '$i', 'title': title, 'position': i + 1, 'pages': 16 + i * 4},
      ];
    }
    if (path == '/articles') {
      rows = [
        for (final (i, title) in [
          'Small Business Relief after 2026: what comes next',
          'When a free zone company loses QFZP status',
        ].indexed)
          {
            'id': '$i',
            'title': title,
            'body': 'Demonstration article',
            'reading_minutes': 4,
          },
      ];
    }
    if (path == '/updates' || path == '/notifications') {
      rows = [
        {
          'id': 'alert',
          'title': 'VAT return due in 10 days',
          'body': 'Demonstration · review your actual deadline.',
          'category': 'Deadline',
          'demo': true,
        },
        {
          'id': 'alert2',
          'title': 'Law change affects a saved answer',
          'body': 'Demonstration · review the source update.',
          'category': 'Update',
          'demo': true,
        },
      ];
    }
    if (path == '/companies') {
      rows = [
        {'id': 'company', 'name': 'Demonstration Trading LLC'},
      ];
    }
    if (path.endsWith('/documents')) {
      rows = [
        for (final (i, title) in [
          'Trade licence',
          'Passport',
          'Tenancy contract',
          'Emirates ID',
          'Residence visa',
        ].indexed)
          {
            'id': '$i',
            'title': title,
            'category': title,
            'expires_on': DateTime.now()
                .add(Duration(days: 18 + i * 20))
                .toIso8601String()
                .substring(0, 10),
          },
      ];
    }
    return ApiPage(rows, rows.length);
  }
}

void main() {
  test('Muted body text meets contrast on the shared light surfaces', () {
    for (final surface in [
      Colors.white,
      DSBColors.background,
      DSBColors.lavender,
      DSBColors.peach,
    ]) {
      final a = DSBColors.muted.computeLuminance(),
          b = surface.computeLuminance();
      expect((b + .05) / (a + .05), greaterThanOrEqualTo(4.5));
    }
  });
  setUpAll(() async {
    final loader = FontLoader('packages/design_system/DSBSerif');
    loader.addFont(
      Future.value(
        ByteData.sublistView(
          File(
            '../../packages/design_system/assets/fonts/LibreBaskerville.ttf',
          ).readAsBytesSync(),
        ),
      ),
    );
    await loader.load();
    final body = FontLoader('packages/design_system/DSBBody');
    body.addFont(
      Future.value(
        ByteData.sublistView(
          File(
            '../../packages/design_system/assets/fonts/Lato-Regular.ttf',
          ).readAsBytesSync(),
        ),
      ),
    );
    await body.load();
    final icons = FontLoader('MaterialIcons');
    icons.addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
  });
  test('Gratuity eligibility, tiers, cap and invalid input', () {
    expect(calculateGratuity(15000, 7).total, 82500);
    expect(calculateGratuity(15000, .99).total, 0);
    expect(calculateGratuity(15000, 1).total, 10500);
    expect(calculateGratuity(15000, 5).total, 52500);
    expect(calculateGratuity(15000, 40).total, 360000);
    expect(() => calculateGratuity(-1, 7), throwsArgumentError);
    expect(() => calculateGratuity(double.nan, 7), throwsArgumentError);
  });
  final screens = <String, Widget>{
    '01-sign-in': const SignIn(),
    '02-home': const Home(),
    '03-discuss': const Discuss(),
    '04-videos': const Learn(),
    '05-toolkit': const Toolkit(),
    '06-updates': const Updates(),
    '07-publications': const Learn(publications: true),
    '08-reminders': const Reminders(),
    '09-alerts': const Alerts(),
  };
  for (final width in [360, 390, 430, 768, 1024, 1440]) {
    for (final entry in screens.entries) {
      testWidgets('${entry.key} at ${width}px has no layout exceptions', (
        tester,
      ) async {
        tester.view.physicalSize = Size(width.toDouble(), 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final boundary = GlobalKey();
        await tester.pumpWidget(
          ProviderScope(
            overrides: [apiProvider.overrideWith((ref) => DemoApi())],
            child: MaterialApp(
              theme: DSBTheme.light,
              home: RepaintBoundary(
                key: boundary,
                child: entry.key == '01-sign-in'
                    ? entry.value
                    : Scaffold(
                        body: SafeArea(
                          child: Center(
                            child: ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 1024),
                              child: entry.value,
                            ),
                          ),
                        ),
                        bottomNavigationBar: DSBBottomNavigation(
                          index: entry.key.contains('discuss')
                              ? 1
                              : entry.key.contains('videos') ||
                                    entry.key.contains('publications')
                              ? 2
                              : entry.key.contains('toolkit')
                              ? 3
                              : entry.key.contains('home')
                              ? 0
                              : 4,
                          onTap: (_) {},
                        ),
                      ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        if (true) {
          await tester.runAsync(() async {
            final image =
                await (boundary.currentContext!.findRenderObject()!
                        as RenderRepaintBoundary)
                    .toImage();
            final bytes = await image.toByteData(
              format: ui.ImageByteFormat.png,
            );
            final out = File(
              '../../docs/phase4/screenshots/$width/${entry.key}.png',
            );
            await out.parent.create(recursive: true);
            await out.writeAsBytes(bytes!.buffer.asUint8List());
            image.dispose();
          });
        }
      });
    }
  }
  testWidgets('Guest navigation reaches home and toolkit', (tester) async {
    tester.view.physicalSize = const Size(390, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiProvider.overrideWith((ref) => DemoApi(authenticated: false)),
        ],
        child: const UserApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Explore as guest'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Explore as guest'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Toolkit').last);
    await tester.pumpAndSettle(const Duration(milliseconds: 100));
    expect(find.text('Toolkit'), findsWidgets);
    expect(
      find.text('Versioned rules · precise workings · saved calculations'),
      findsOneWidget,
    );
  });
}
