import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:api_client/api_client.dart';

class SessionAdapter implements HttpClientAdapter {
  int rotations = 0;
  bool expired = false;
  bool denyRetry = false;
  final requests = <RequestOptions>[];
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    requests.add(options);
    dynamic data = <String, dynamic>{};
    int status = 200;
    switch (options.path) {
      case '/auth/login':
        data = {'access_token': 'access-1', 'refresh_token': 'refresh-1'};
      case '/auth/refresh':
        rotations++;
        data = {'access_token': 'access-2', 'refresh_token': 'refresh-2'};
      case '/auth/me':
        data = {
          'id': 'account',
          'roles': ['admin'],
          'name': 'Operator',
        };
      case '/private':
        if (expired &&
            (options.headers['Authorization'] != 'Bearer access-2' ||
                denyRetry)) {
          status = 401;
          data = {'detail': 'Expired'};
        } else {
          data = {'ok': true};
        }
    }
    return ResponseBody.fromString(
      jsonEncode(data),
      status,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  test(
    'Authentication, automatic rotation and logout use the shared contract',
    () async {
      final client = ApiClient(persistRefresh: false);
      final adapter = SessionAdapter();
      client.dio.httpClientAdapter = adapter;
      await client.authenticate('operator@example.com', 'a-strong-password');
      expect(client.signedIn, true);
      expect(client.canEdit, true);
      adapter.expired = true;
      expect((await client.get('/private'))['ok'], true);
      expect(adapter.rotations, 1);
      expect(adapter.requests.last.headers['Authorization'], 'Bearer access-2');
      await client.logout();
      expect(client.signedIn, false);
      expect(client.user, isNull);
    },
  );
  test('A failed retry stops rather than refreshing forever', () async {
    final client = ApiClient(persistRefresh: false);
    final adapter = SessionAdapter();
    client.dio.httpClientAdapter = adapter;
    await client.authenticate('operator@example.com', 'a-strong-password');
    adapter.expired = adapter.denyRetry = true;
    await expectLater(client.get('/private'), throwsA(isA<DioException>()));
    expect(adapter.rotations, 1);
    expect(client.signedIn, false);
  });
}
