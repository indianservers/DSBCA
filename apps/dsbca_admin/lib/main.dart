import 'dart:ui' as ui;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  FlutterError.onError = (details) {
    debugPrint('DSBCA flutter_failure type=${details.exception.runtimeType}');
    if (kDebugMode) FlutterError.presentError(details);
  };
  ui.PlatformDispatcher.instance.onError = (error, stack) {
    debugPrint('DSBCA async_failure type=${error.runtimeType}');
    return true;
  };
  runApp(const ProviderScope(child: AdminApp()));
}
