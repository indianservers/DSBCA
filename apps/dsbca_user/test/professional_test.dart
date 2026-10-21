import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:dsbca_user/professional.dart';
import 'package:dsbca_user/compliance.dart';
import 'package:dsbca_user/academy.dart';

class ProfessionalApi extends ApiClient {
  @override
  bool get signedIn => true;
  @override
  Future<Json> get(String path, {Json? query}) async {
    if (path == '/professional/calculators') {
      return Json.from(
        jsonDecode(File('test/fixtures/calculators.json').readAsStringSync())
            as Map,
      );
    }
    if (path.endsWith('/compliance')) {
      return {
        'company': {'id': 'company', 'name': 'UI test company'},
        'documents': [
          {
            'id': 'doc',
            'title': 'Trade Licence',
            'category': 'Trade Licence',
            'expires_on': '2026-11-20',
            'expiry_status': 'due_soon',
            'days_remaining': 30,
            'status': 'active',
            'details': {},
          },
        ],
        'obligations': [],
        'history': [],
      };
    }
    if (path.endsWith('/state')) {
      return {
        'bookmarked': false,
        'progress': {'position': 0, 'completed': false},
      };
    }
    if (path.endsWith('/settings')) {
      return {
        'in_app': true,
        'email': false,
        'push': false,
        'email_configured': false,
        'push_configured': false,
      };
    }
    if (path.endsWith('/subscriptions')) return {'subjects': []};
    if (path.startsWith('/videos/') ||
        path.startsWith('/publications/') ||
        path.startsWith('/articles/') ||
        path.startsWith('/updates/') ||
        path.startsWith('/webinars/')) {
      return {
        'title': 'Controlled UI resource',
        'body': 'Fictional interface fixture; not professional guidance.',
        'metadata_extra': {},
        'media_url': null,
      };
    }
    return {'items': [], 'total': 0, 'page': 1, 'page_size': 20};
  }

  @override
  Future<ApiPage> page(String path, {Json? query}) async => path == '/companies'
      ? const ApiPage([
          {'id': 'company', 'name': 'UI test company', 'profile_data': {}},
        ], 1)
      : const ApiPage([], 0);
  @override
  Future<Json> post(String path, Json body) async => {
    'status': 'calculated',
    'calculator': 'npv',
    'inputs': body['inputs'],
    'results': {'npv': '0.00'},
    'warnings': ['Controlled UI fixture'],
    'formula': ['Known example: −100 + 110/1.1 = 0'],
    'schedule': [],
    'rule': {'version': 'fixture', 'sources': []},
    if (body['save'] == true) 'run_id': 'saved',
  };
  @override
  Future<Json> put(String path, Json body) async => body;
}

void main() {
  final catalogue = Json.from(
    jsonDecode(File('test/fixtures/calculators.json').readAsStringSync())
        as Map,
  );
  for (final width in [360, 390, 430, 768, 1024, 1440]) {
    for (final raw in catalogue['items'] as List) {
      final code = (raw as Map)['code'] as String;
      testWidgets('$code form at $width px', (tester) async {
        tester.view.physicalSize = Size(width.toDouble(), 1000);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          MaterialApp(
            theme: DSBTheme.light,
            home: Scaffold(
              body: ProfessionalToolkit(api: ProfessionalApi(), code: code),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text(raw['title'] as String), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
    for (final kind in ['videos', 'publications', 'updates', 'webinars']) {
      testWidgets('$kind detail at $width px', (tester) async {
        tester.view.physicalSize = Size(width.toDouble(), 1000);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          MaterialApp(
            theme: DSBTheme.light,
            home: Scaffold(
              body: AcademyDetail(
                api: ProfessionalApi(),
                kind: kind,
                id: 'fixture',
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
    testWidgets('Company compliance at $width px', (tester) async {
      tester.view.physicalSize = Size(width.toDouble(), 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        MaterialApp(
          theme: DSBTheme.light,
          home: Scaffold(body: ComplianceWorkspace(api: ProfessionalApi())),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Trade Licence'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
    testWidgets('Delivery settings at $width px', (tester) async {
      tester.view.physicalSize = Size(width.toDouble(), 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        MaterialApp(
          theme: DSBTheme.light,
          home: Scaffold(body: NotificationStatus(api: ProfessionalApi())),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('Calculation output saves and reset preserves editable form', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DSBTheme.light,
        home: Scaffold(
          body: ProfessionalToolkit(api: ProfessionalApi(), code: 'npv'),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Calculate'));
    await tester.tap(find.text('Calculate'));
    await tester.pumpAndSettle();
    expect(find.textContaining('npv: 0.00'), findsOneWidget);
    await tester.ensureVisible(find.text('Save to my account'));
    await tester.tap(find.text('Save to my account'));
    await tester.pumpAndSettle();
    expect(find.text('Saved'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
