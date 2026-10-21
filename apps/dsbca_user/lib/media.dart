import 'package:flutter/material.dart';
import 'package:api_client/api_client.dart';
import 'package:file_picker/file_picker.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

Future<String?> choosePrivateAsset(ApiClient api, {String? companyId}) async {
  final selected = await FilePicker.platform.pickFiles(
    type: FileType.custom,
    allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg', 'webp'],
    withData: true,
  );
  if (selected == null) return null;
  final file = selected.files.single;
  if (file.bytes == null || file.size > 3000000) {
    throw StateError('Choose an attachment up to 3 MB.');
  }
  final ext = (file.extension ?? '').toLowerCase();
  final mime = ext == 'pdf'
      ? 'application/pdf'
      : ext == 'png'
      ? 'image/png'
      : ext == 'webp'
      ? 'image/webp'
      : 'image/jpeg';
  return (await api.uploadPrivateAsset(
        file.bytes!,
        filename: file.name,
        mime: mime,
        companyId: companyId,
      ))['asset_id']
      as String;
}

Future<void> openPrivateMedia(ApiClient api, String id) async {
  final result = await api.privateDownload(id);
  if (result['url'] != null) {
    final uri = Uri.parse(result['url'] as String);
    if (uri.scheme != 'https') throw StateError('Secure storage URL required');
    await launchUrl(uri);
  } else {
    final mime = result['mime'] as String;
    final extension = mime == 'image/png'
        ? 'png'
        : mime == 'image/webp'
        ? 'webp'
        : mime == 'image/jpeg'
        ? 'jpg'
        : 'pdf';
    await SharePlus.instance.share(
      ShareParams(
        files: [XFile.fromData(result['bytes'], mimeType: mime)],
        fileNameOverrides: ['private-document.$extension'],
        sharePositionOrigin: const Rect.fromLTWH(0, 0, 1, 1),
      ),
    );
  }
}
