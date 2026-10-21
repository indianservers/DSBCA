import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:design_system/design_system.dart';
import 'package:dsbca_user/app.dart';
import 'app_test.dart' show DemoApi;

void main() {
  for (final scale in [1.5, 2.0]) {
    for (final entry in <String, Widget>{
      'sign-in': const SignIn(),
      'home': const Home(),
      'profile': const Profile(),
      'reminders': const Reminders(),
    }.entries) {
      testWidgets('${entry.key} at 360px and text scale $scale', (
        tester,
      ) async {
        tester.view.physicalSize = const Size(360, 900);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          ProviderScope(
            overrides: [apiProvider.overrideWith((ref) => DemoApi())],
            child: MaterialApp(
              theme: DSBTheme.light,
              builder: (context, child) => MediaQuery(
                data: MediaQuery.of(
                  context,
                ).copyWith(textScaler: TextScaler.linear(scale)),
                child: child!,
              ),
              home: Scaffold(body: entry.value),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
  }
}
