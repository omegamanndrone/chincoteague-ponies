import 'dart:typed_data';
import 'package:flutter/material.dart';

class PhotoViewerScreen extends StatelessWidget {
  final Uint8List imageBytes;
  final String horseName;
  final String source;

  const PhotoViewerScreen({
    super.key,
    required this.imageBytes,
    required this.horseName,
    required this.source,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(horseName),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Chip(
              label: Text(
                source == 'user'
                    ? 'Your Photo'
                    : source == 'field'
                        ? '© K. Kent'
                        : 'Book Photo',
                style: const TextStyle(fontSize: 12),
              ),
              backgroundColor: source == 'user'
                  ? const Color(0xFF2E7D32)
                  : source == 'field'
                      ? const Color(0xFF1B6B32)
                      : Colors.brown,
              labelStyle: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      body: Center(
        child: InteractiveViewer(
          minScale: 0.5,
          maxScale: 4.0,
          child: Image.memory(imageBytes),
        ),
      ),
    );
  }
}
