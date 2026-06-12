import 'package:flutter/material.dart';

/// Provenance accent (IMPLEMENTATION_PLAN.md §10): ONE reserved color that marks
/// the user's own *local* annotations — their notes, their own photos, and any
/// band/herd/region they've edited — as distinct from the canon data we ship.
///
/// Used ONLY for this, app-wide (notes card, photo borders, band rows), so the
/// cue stays legible. A thin left rule is the primary treatment; for photo tiles
/// (a horizontal strip) the same color is applied as a full border instead.
class Provenance {
  const Provenance._();

  /// Reserved "this is yours / local-only" accent. Teal — deliberately distinct
  /// from the app's green (canon/interactive) and brown (book), and not a
  /// warning/error red.
  static const Color local = Color(0xFF00897B);

  /// Thin left accent rule applied to a content block when [isLocal] is true;
  /// otherwise the child is returned unchanged.
  static Widget rule(Widget child, {required bool isLocal}) {
    if (!isLocal) return child;
    return Container(
      decoration: const BoxDecoration(
        border: Border(left: BorderSide(color: local, width: 3)),
      ),
      padding: const EdgeInsets.only(left: 10),
      child: child,
    );
  }

  /// One-line legend so the accent is learnable once.
  static Widget legend() => Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Row(
          children: [
            Container(width: 3, height: 14, color: local),
            const SizedBox(width: 8),
            Text('marks your own notes, photos & edits',
                style: TextStyle(fontSize: 12, color: Colors.grey[600])),
          ],
        ),
      );
}
