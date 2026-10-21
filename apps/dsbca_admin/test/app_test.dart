import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:dsbca_admin/app.dart';

class AdminApi extends ApiClient {
  AdminApi() {
    user = {
      'name': 'Demo Administrator',
      'roles': ['super_admin'],
    };
  }
  @override
  bool get signedIn => true;
  @override
  Future<Json> get(String path, {Json? query}) async =>
      path == '/admin/ai/documents'
      ? {'items': [], 'total': 0, 'page': 1, 'page_size': 20}
      : {
          'users': 12,
          'videos': 5,
          'publications': 2,
          'updates': 3,
          'webinars': 2,
          'companies': 4,
          'recent_activity': [],
        };
  @override
  Future<ApiPage> page(String path, {Json? query}) async =>
      const ApiPage([], 0);
}

void main() {
  for (final width in [360, 390, 430, 768, 1024, 1440]) {
    for (final section in sections) {
      testWidgets('Admin $section at $width px', (tester) async {
        tester.view.physicalSize = Size(width.toDouble(), 900);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          ProviderScope(
            overrides: [apiProvider.overrideWith((ref) => AdminApi())],
            child: MaterialApp(
              theme: DSBTheme.light,
              home: AdminShell(section: section),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
  }
  testWidgets('Admin login is the initial guarded route', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: AdminApp()));
    await tester.pumpAndSettle();
    expect(find.text('Administration'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
  });
}
