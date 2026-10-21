import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:api_client/api_client.dart';
import 'package:design_system/design_system.dart';
import 'package:dsbca_admin/knowledge.dart';

class KnowledgeApi extends ApiClient {
  @override
  Future<Json> get(String path, {Json? query}) async {
    if (path.endsWith('/settings')) {
      return {
        'version_id': 'fixture-v1',
        'configuration': {
          'name': 'DSBCA Research',
          'system_instructions': 'Use approved evidence only.',
          'chat_model': '',
          'embedding_model': '',
          'retrieval_top_k': 8,
          'max_output_tokens': 1800,
          'minimum_evidence_score': 0.25,
          'history_window': 8,
          'feedback_enabled': true,
        },
        'providers': {'chat': false},
        'history': [],
      };
    }
    if (path.endsWith('/analytics')) {
      return {
        'conversations': 12,
        'requests': 20,
        'estimated_cost': null,
        'cost_note': 'Pricing is not configured',
        'questions_per_subject': {'Corporate Tax': 10},
      };
    }
    if (path.endsWith('/processing-jobs')) {
      return {
        'items': [
          {
            'status': 'failed',
            'checkpoint': 'embeddings',
            'progress': 60,
            'attempts': 1,
            'error_code': 'PROVIDER_NOT_CONFIGURED',
            'events': [
              {
                'message': 'Provider configuration required',
                'created_at': '2026-10-21',
              },
            ],
          },
        ],
        'total': 1,
      };
    }
    return {'items': [], 'total': 0};
  }

  @override
  Future<ApiPage> page(String path, {Json? query}) async =>
      const ApiPage([], 0);
}

void main() {
  for (final width in [360, 390, 430, 768, 1024, 1440]) {
    testWidgets('Knowledge tabs and upload dialog at $width px', (
      tester,
    ) async {
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
              child: KnowledgeWorkspace(api: KnowledgeApi()),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      for (final name in [
        'Processing jobs',
        'Assistant settings',
        'Analytics',
        'Documents',
      ]) {
        await tester.ensureVisible(find.text(name));
        await tester.tap(find.text(name));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull, reason: name);
      }
      await tester.tap(find.text('+ Upload PDF'));
      await tester.pumpAndSettle();
      expect(find.byType(KnowledgeUpload), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
    });
  }
}
