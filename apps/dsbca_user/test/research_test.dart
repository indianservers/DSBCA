import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:dsbca_user/research.dart';

class ResearchApi extends ApiClient {
  final saved = <Json>[];
  bool stopped = false;
  @override
  bool get signedIn => true;
  @override
  Future<Json> get(String path, {Json? query}) async {
    if (path == '/ai/capabilities') return {'openai_configured': false};
    return {
      'text': 'DEMONSTRATION ONLY — NOT UAE LAW. Review the trial balance.',
      'physical_page': 1,
      'printed_label': 'i',
      'page_count': 2,
      'preview_path': '/preview',
      'provenance': 'UI test fixture',
    };
  }

  @override
  Future<ApiPage> page(String path, {Json? query}) async =>
      path.contains('/messages')
      ? ApiPage(saved, saved.length)
      : const ApiPage([
          {
            'id': 'conversation',
            'title': 'UI fixture research',
            'message_count': 2,
          },
        ], 1);
  @override
  Future<Json> post(String path, Json data) async {
    if (path.contains('/cancel')) stopped = true;
    return {'id': 'conversation', 'saved': true};
  }

  @override
  Future<Uint8List> bytes(String path) async => base64Decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==',
  );
  @override
  Stream<Json> streamEvents(
    String path,
    Json data,
    RequestCancellation cancellation,
  ) async* {
    yield {
      'event': 'accepted',
      'data': {'message_id': 'answer'},
    };
    await Future<void>.delayed(const Duration(milliseconds: 100));
    if (cancellation.cancelled) return;
    final source = {
      'id': 'chunk',
      'title': 'Demonstration review checklist',
      'version_id': 'version',
      'version': 'v1',
      'issuer': 'DSBCA test fixture',
      'document_type': 'Demonstration Material',
      'physical_page': 1,
      'page_end': 1,
      'passage': 'Review the trial balance. DEMONSTRATION ONLY — NOT UAE LAW.',
      'demo': true,
    };
    final message = {
      'id': 'answer',
      'role': 'assistant',
      'text':
          '**UI fixture — not AI output**\n\nReview the trial balance. [1]\n\n| Evidence | Status |\n| --- | --- |\n| Trial balance | Requested |',
      'status': 'completed',
      'citations': [source],
    };
    yield {
      'event': 'citations',
      'data': {
        'citations': [source],
      },
    };
    yield {
      'event': 'answer_delta',
      'data': {'text': message['text']},
    };
    yield {'event': 'done', 'data': message};
    saved.add(message);
  }
}

void main() {
  setUpAll(() async {
    final icons = FontLoader('MaterialIcons')
      ..addFont(
        Future.value(
          ByteData.sublistView(
            File(
              '${File(Platform.resolvedExecutable).parent.parent.parent.path}/material_fonts/MaterialIcons-Regular.otf',
            ).readAsBytesSync(),
          ),
        ),
      );
    await icons.load();
    final body = FontLoader('packages/design_system/DSBBody')
      ..addFont(
        Future.value(
          ByteData.sublistView(
            File(
              '../../packages/design_system/assets/fonts/Lato-Regular.ttf',
            ).readAsBytesSync(),
          ),
        ),
      );
    await body.load();
    final serif = FontLoader('packages/design_system/DSBSerif')
      ..addFont(
        Future.value(
          ByteData.sublistView(
            File(
              '../../packages/design_system/assets/fonts/LibreBaskerville.ttf',
            ).readAsBytesSync(),
          ),
        ),
      );
    await serif.load();
  });
  for (final width in [360, 390, 430, 768, 1024, 1440]) {
    testWidgets('Research streams tables and opens source at $width px', (
      tester,
    ) async {
      tester.view.physicalSize = Size(width.toDouble(), 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final boundary = GlobalKey();
      await tester.pumpWidget(
        MaterialApp(
          theme: DSBTheme.light,
          home: Scaffold(
            body: RepaintBoundary(
              key: boundary,
              child: ColoredBox(
                color: DSBColors.background,
                child: ResearchScreen(api: ResearchApi()),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byType(TextField).last,
        'Which evidence should I review?',
      );
      await tester.tap(find.byTooltip('Send question'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Review the trial balance'), findsWidgets);
      expect(tester.takeException(), isNull);
      if (width == 390 || width == 1440) {
        await tester.runAsync(() async {
          final image =
              await (boundary.currentContext!.findRenderObject()!
                      as RenderRepaintBoundary)
                  .toImage();
          final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
          final file = File('../../docs/phase2/research-$width.png');
          await file.parent.create(recursive: true);
          await file.writeAsBytes(bytes!.buffer.asUint8List());
          image.dispose();
        });
      }
      await tester.tap(find.text('[1] PDF 1 · v1').first);
      await tester.pumpAndSettle();
      expect(find.text('Physical PDF page 1 · printed i'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.byTooltip('Close source'));
      await tester.pumpAndSettle();
    });
  }
  testWidgets('Stop uses the cancellation API', (tester) async {
    final api = ResearchApi();
    await tester.pumpWidget(
      MaterialApp(
        theme: DSBTheme.light,
        home: Scaffold(body: ResearchScreen(api: api)),
      ),
    );
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'Review evidence');
    await tester.tap(find.byTooltip('Send question'));
    await tester.pump();
    await tester.tap(find.byTooltip('Stop generation'));
    await tester.pumpAndSettle();
    expect(api.stopped, true);
  });
}
