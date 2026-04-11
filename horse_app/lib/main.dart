import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'screens/horse_list_screen.dart';
import 'services/data_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await DataService.instance.init();
  runApp(const HorseApp());
}

/// Constrains the app to a phone/tablet portrait shape on desktop.
class PhoneFrame extends StatelessWidget {
  final Widget child;
  const PhoneFrame({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF1A1A1A),
      child: Center(
        child: AspectRatio(
          aspectRatio: 9 / 19.5,
          child: Container(
            constraints: const BoxConstraints(maxWidth: 430),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.5),
                  blurRadius: 30,
                  spreadRadius: 5,
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(24),
              child: child,
            ),
          ),
        ),
      ),
    );
  }
}

class HorseApp extends StatelessWidget {
  const HorseApp({super.key});

  @override
  Widget build(BuildContext context) {
    final app = MaterialApp(
      title: 'Chincoteague Ponies',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF2E7D32),
        useMaterial3: true,
        cardTheme: CardThemeData(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          elevation: 2,
        ),
      ),
      home: const HorseListScreen(),
    );

    // On desktop, wrap the entire app in a phone frame
    if (!kIsWeb && !Platform.isAndroid && !Platform.isIOS) {
      return PhoneFrame(child: app);
    }
    return app;
  }
}
