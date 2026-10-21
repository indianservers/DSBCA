import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:dsbca_admin/professional.dart';

class PlatformApi extends ApiClient {
  @override
  Future<Json> get(String path, {Json? query}) async =>
      path.endsWith('/metrics')
      ? {'calculator_runs': 3, 'notification_failures': 0}
      : {'items': [], 'total': 0, 'page': 1, 'page_size': 20};
}

void main() {
  for (final width in [360, 390, 430, 768, 1024, 1440]) {
    for (var tab = 0; tab < 7; tab++) {
      testWidgets('Professional admin tab $tab at $width px', (tester) async {
        tester.view.physicalSize = Size(width.toDouble(), 1000);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          MaterialApp(
            theme: DSBTheme.light,
            home: Scaffold(
              body: Padding(
                padding: const EdgeInsets.all(16),
                child: ProfessionalAdmin(api: PlatformApi(), initialTab: tab),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
  }
}
