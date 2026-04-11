import 'dart:convert';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'data_service.dart';
import 'web_download_stub.dart' if (dart.library.html) 'web_download.dart';

class BackupService {
  static final BackupService instance = BackupService._();
  BackupService._();

  final _data = DataService.instance;

  /// Create a backup and return the bytes + suggested filename.
  (Uint8List bytes, String filename) createBackup() {
    final backup = _data.exportUserData();
    final jsonStr = const JsonEncoder.withIndent('  ').convert(backup);
    final bytes = Uint8List.fromList(utf8.encode(jsonStr));
    final date = DateTime.now().toIso8601String().substring(0, 10);
    final filename = 'chincoteague_backup_$date.json';
    return (bytes, filename);
  }

  /// Save a backup file.
  Future<bool> saveBackup() async {
    final (bytes, filename) = createBackup();

    try {
      if (kIsWeb) {
        triggerWebDownload(bytes, filename);
        return true;
      }

      final result = await FilePicker.saveFile(
        dialogTitle: 'Save Backup',
        fileName: filename,
        type: FileType.custom,
        allowedExtensions: ['json'],
        bytes: bytes,
      );

      return result != null;
    } catch (e) {
      debugPrint('Backup save error: $e');
      return false;
    }
  }

  /// Pick and restore a backup file.
  Future<bool> restoreBackup() async {
    try {
      final result = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) return false;

      final bytes = result.files.first.bytes;
      if (bytes == null) return false;

      final jsonStr = utf8.decode(bytes);
      final backup = json.decode(jsonStr) as Map<String, dynamic>;

      if (!backup.containsKey('version') || !backup.containsKey('user_data')) {
        return false;
      }

      await _data.importUserData(backup);
      return true;
    } catch (e) {
      debugPrint('Backup restore error: $e');
      return false;
    }
  }
}
