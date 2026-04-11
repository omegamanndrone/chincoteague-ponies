import 'dart:convert';
import 'dart:html' as html;
import 'dart:typed_data';

void triggerWebDownload(Uint8List bytes, String filename) {
  final base64 = base64Encode(bytes);
  final anchor = html.AnchorElement(
    href: 'data:application/json;base64,$base64',
  )
    ..setAttribute('download', filename)
    ..click();
}
