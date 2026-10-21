import 'package:dio/dio.dart';
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
export 'package:shared_models/shared_models.dart';
import 'package:shared_models/shared_models.dart';

class ApiClient extends ChangeNotifier {
  ApiClient({String? baseUrl, bool? persistRefresh})
    : _persistRefresh = persistRefresh ?? !kIsWeb,
      dio = Dio(
        BaseOptions(
          baseUrl:
              '${baseUrl ?? const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000')}/api/v1',
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 20),
        ),
      ) {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (_access != null)
            options.headers['Authorization'] = 'Bearer $_access';
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401 &&
              error.requestOptions.extra['sessionRetried'] != true &&
              _refresh != null &&
              !error.requestOptions.path.startsWith('/auth/')) {
            try {
              await (_refreshing ??= _rotate()).whenComplete(
                () => _refreshing = null,
              );
              error.requestOptions.headers['Authorization'] = 'Bearer $_access';
              error.requestOptions.extra['sessionRetried'] = true;
              return handler.resolve(await dio.fetch(error.requestOptions));
            } catch (_) {
              await clear();
            }
          }
          handler.next(error);
        },
      ),
    );
  }
  final Dio dio;
  final bool _persistRefresh;
  final _storage = const FlutterSecureStorage();
  String? _access, _refresh;
  Future<void>? _refreshing;
  Json? user;
  bool get signedIn => _access != null;
  bool get canEdit => ((user?['roles'] as List?) ?? []).any(
    (e) => ['content_editor', 'admin', 'super_admin'].contains(e),
  );

  Future<void> restore() async {
    // Web tokens remain in memory; mobile refresh tokens use platform secure storage.
    if (_persistRefresh) {
      try {
        _refresh = await _storage.read(key: 'dsbca_refresh');
        if (_refresh != null) {
          await _rotate();
          user = await get('/auth/me');
        }
      } catch (_) {
        _access = _refresh = null;
        user = null;
        try {
          await _storage.delete(key: 'dsbca_refresh');
        } catch (_) {
          /* Device secure storage may be unavailable. */
        }
      }
    }
    notifyListeners();
  }

  Future<void> _rotate() async {
    final response = await dio.post(
      '/auth/refresh',
      data: {'refresh_token': _refresh},
    );
    await _tokens(Json.from(response.data as Map));
  }

  Future<void> _tokens(Json data) async {
    _access = data['access_token'] as String;
    _refresh = data['refresh_token'] as String;
    if (_persistRefresh)
      await _storage.write(key: 'dsbca_refresh', value: _refresh);
  }

  Future<void> authenticate(
    String email,
    String password, {
    String? name,
  }) async {
    final result = await post(name == null ? '/auth/login' : '/auth/register', {
      'email': email,
      'password': password,
      if (name != null) 'name': name,
    });
    await _tokens(result);
    user = await get('/auth/me');
    notifyListeners();
  }

  Future<void> updateProfile(String name) async {
    await patch('/users/me', {'name': name});
    user = await get('/auth/me');
    notifyListeners();
  }

  Future<void> logout() async {
    try {
      if (_refresh != null)
        await post('/auth/logout', {'refresh_token': _refresh});
    } finally {
      await clear();
    }
  }

  Future<void> clear() async {
    _access = _refresh = null;
    user = null;
    if (_persistRefresh) await _storage.delete(key: 'dsbca_refresh');
    notifyListeners();
  }

  Future<Json> get(String path, {Json? query}) async =>
      Json.from((await dio.get(path, queryParameters: query)).data as Map);
  Future<ApiPage> page(String path, {Json? query}) async =>
      ApiPage.fromJson(await get(path, query: query));
  Future<Json> post(String path, Json data) async =>
      Json.from((await dio.post(path, data: data)).data as Map);
  Future<Json> put(String path, Json data) async =>
      Json.from((await dio.put(path, data: data)).data as Map);
  Future<Json> patch(String path, [Json? data]) async =>
      Json.from((await dio.patch(path, data: data)).data as Map);
  Future<void> delete(String path) async {
    await dio.delete(path);
  }

  String absoluteUrl(String path) => '${dio.options.baseUrl}$path';

  Future<Uint8List> bytes(String path) async => Uint8List.fromList(
    (await dio.get<List<int>>(
      path,
      options: Options(responseType: ResponseType.bytes),
    )).data!,
  );

  Future<Json> privateDownload(String assetId) async {
    final response = await dio.get<List<int>>(
      '/professional/media/$assetId/download',
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = Uint8List.fromList(response.data ?? []);
    final mime =
        response.headers.value('content-type')?.split(';').first ??
        'application/octet-stream';
    if (mime == 'application/json')
      return Json.from(jsonDecode(utf8.decode(bytes)) as Map);
    return {'bytes': bytes, 'mime': mime};
  }

  Future<Json> uploadPrivateAsset(
    Uint8List data, {
    required String filename,
    required String mime,
    String? companyId,
  }) async {
    final response = await dio.post(
      '/professional/media',
      data: FormData.fromMap({
        'title': filename,
        if (companyId != null) 'company_id': companyId,
        'file': MultipartFile.fromBytes(
          data,
          filename: filename,
          contentType: DioMediaType.parse(mime),
        ),
      }),
    );
    return Json.from(response.data as Map);
  }

  Future<Json> uploadPdf(
    String path,
    Json metadata,
    Uint8List data, {
    String? documentId,
  }) async {
    if (data.length <= 3000000) {
      final result = await dio.post(
        path,
        data: FormData.fromMap({
          'metadata': jsonEncode(metadata),
          'file': MultipartFile.fromBytes(
            data,
            filename: 'document.pdf',
            contentType: DioMediaType.parse('application/pdf'),
          ),
        }),
      );
      return Json.from(result.data as Map);
    }
    final pending = await post(
      '/admin/ai/uploads${documentId == null ? '' : '?document_id=$documentId'}',
      {
        'metadata': metadata,
        'byte_size': data.length,
        'sha256': sha256.convert(data).toString(),
      },
    );
    final upload = Json.from(pending['upload'] as Map);
    final url = Uri.parse(upload['url'] as String);
    if (url.scheme != 'https')
      throw StateError('Private storage requires HTTPS');
    final request = http.MultipartRequest('POST', url)
      ..fields.addAll(
        (upload['fields'] as Map).map((k, v) => MapEntry('$k', '$v')),
      )
      ..files.add(
        http.MultipartFile.fromBytes('file', data, filename: 'document.pdf'),
      );
    final client = http.Client();
    try {
      final response = await client
          .send(request)
          .timeout(const Duration(seconds: 120));
      await response.stream.drain<void>();
      if (response.statusCode >= 300) throw StateError('Private upload failed');
    } finally {
      client.close();
    }
    return post('/admin/ai/uploads/${pending['version_id']}/complete', {});
  }

  Stream<Json> streamEvents(
    String path,
    Json data,
    RequestCancellation cancellation,
  ) async* {
    final client = http.Client();
    cancellation.client = client;
    try {
      http.StreamedResponse? response;
      for (var attempt = 0; attempt < 2; attempt++) {
        if (cancellation.cancelled) return;
        final request = http.Request('POST', Uri.parse(absoluteUrl(path)))
          ..headers.addAll({
            'Authorization': 'Bearer $_access',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          })
          ..body = jsonEncode(data);
        response = await client
            .send(request)
            .timeout(const Duration(seconds: 60));
        if (response.statusCode != 401 || _refresh == null || attempt > 0)
          break;
        await response.stream.drain<void>();
        await (_refreshing ??= _rotate()).whenComplete(
          () => _refreshing = null,
        );
      }
      if (response!.statusCode != 200) {
        final text = await response.stream.bytesToString();
        final error = jsonDecode(text);
        throw StateError(
          error is Map && error['detail'] is String
              ? error['detail'] as String
              : 'Research request failed',
        );
      }
      var event = '', payload = '';
      await for (final line
          in response.stream
              .transform(utf8.decoder)
              .transform(const LineSplitter())
              .timeout(const Duration(seconds: 90))) {
        if (cancellation.cancelled) return;
        if (line.startsWith('event:')) event = line.substring(6).trim();
        if (line.startsWith('data:')) payload += line.substring(5).trim();
        if (line.isEmpty && payload.isNotEmpty) {
          yield {'event': event, 'data': Json.from(jsonDecode(payload) as Map)};
          event = '';
          payload = '';
        }
      }
    } finally {
      client.close();
      cancellation.client = null;
    }
  }
}

class RequestCancellation {
  http.Client? client;
  bool cancelled = false;
  void cancel() {
    cancelled = true;
    client?.close();
  }
}

String apiError(Object error) {
  if (error is DioException) {
    final detail = error.response?.data;
    if (detail is Map && detail['detail'] is String)
      return detail['detail'] as String;
    if (error.response?.statusCode == 422)
      return 'Please check the form fields and try again.';
    if (error.response == null)
      return 'Cannot reach the API. Check the server and connection.';
  }
  return 'The request could not be completed. Please try again.';
}
