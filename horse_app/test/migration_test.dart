import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:horse_app/services/data_service.dart';

/// Phase 1 cutover verification (IMPLEMENTATION_PLAN.md §4): an existing device
/// upgrading from the old local-id scheme must keep the user's local-only notes
/// (remapped to pedigree ids) while everything else returns from canon.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized(); // for rootBundle asset loads

  test('schema cutover: local-keyed note survives, remapped to pedigree id; '
      'canon horses/bands/regions load', () async {
    final dir = await Directory.systemTemp.createTemp('hive_migration');
    Hive.init(dir.path);

    // Seed an "old device": userData keyed by the OLD local id 42 (= pedigree 3,
    // "A Splash of Freckles") with a personal note + a herd value. No _meta box,
    // so schemaVersion defaults to 0 -> the cutover migration must run.
    final ud = await Hive.openBox('userData');
    await ud.put(42, {'notes': 'splash note — local only', 'herd': 'southern'});
    await ud.close();
    await Hive.close();

    await DataService.instance.init(hivePath: dir.path);

    final ds = DataService.instance;

    // Canon loaded, pedigree-keyed.
    expect(ds.getAllHorses().length, 143, reason: 'all canon horses loaded');

    // The note was preserved across the wipe and remapped local 42 -> pedigree 3.
    final splash = ds.getHorse(3);
    expect(splash, isNotNull);
    expect(splash!.name, 'A Splash of Freckles');
    expect(splash.notes, 'splash note — local only',
        reason: 'local note survived the cutover, remapped to pedigree id');

    // Canon bands merged + readable (mare 3 banded with stallion 809).
    expect(ds.getCurrentBandMembers(809).any((m) => m.horseId == 3), isTrue,
        reason: 'canon band membership resolves');

    // Canon region snapshot overlaid (pedigree 3 = southern).
    expect(ds.getRegion(3), 'southern', reason: 'canon region resolves');

    await Hive.close();
    await dir.delete(recursive: true);
  });
}
