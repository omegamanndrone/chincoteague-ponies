import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:horse_app/services/data_service.dart';

/// Phase 1 cutover verification (IMPLEMENTATION_PLAN.md §4): an existing device
/// upgrading from the old local-id scheme must keep the user's local-only notes
/// (remapped to pedigree ids) while everything else returns from canon.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized(); // for rootBundle asset loads

  // DataService is a singleton; reset its init flag between tests so each one's
  // own temp Hive dir is loaded fresh.
  setUp(() => DataService.instance.resetForTest());

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

    // Canon loaded, pedigree-keyed (Phase 2 roster: 148 VA + 88 MD).
    expect(ds.getAllHorses().length, 236, reason: 'all canon horses loaded');

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

  // Phase 2 content update (IMPLEMENTATION_PLAN.md §4): an existing device on the
  // current schema but an OLDER contentVersion must reload canon (so the new
  // roster + enrichment appear) WITHOUT wiping the user's local boxes.
  test('content update: older contentVersion reloads canon (new horses appear) '
      'but preserves the user\'s local data', () async {
    final dir = await Directory.systemTemp.createTemp('hive_content');
    Hive.init(dir.path);

    // Seed a post-cutover device: schema is current (no structural migration),
    // contentVersion is older than the bundled one -> triggers a content reload.
    // The user has her own local-only data in the user boxes.
    final meta = await Hive.openBox('_meta');
    await meta.put('schemaVersion', 1);
    await meta.put('contentVersion', 1);
    await meta.close();
    final ud = await Hive.openBox('userData');
    await ud.put(3, {'notes': 'my field note', 'region': 'northern'}); // note + region override
    await ud.close();
    final bands = await Hive.openBox('bands');
    await bands.put('3_809_2026-06-20', {
      'horse_id': 3, 'stallion_id': 809,
      'date_recorded': '2026-06-20', 'status': 'present',
    });
    await bands.close();
    await Hive.close();

    await DataService.instance.init(hivePath: dir.path);
    final ds = DataService.instance;

    // Canon reloaded with the new (larger) roster — new ponies now present.
    expect(ds.getAllHorses().length, 236, reason: 'content update loaded the new roster');
    expect(ds.getHorse(6), isNotNull,
        reason: 'a new VA pony (Ace\'s Black Tie Affair) appears after the update');
    expect(ds.getAllHorses().any((h) => h.state == 'MD'), isTrue,
        reason: 'the MD (Assateague) herd loaded');

    // The user's local data was PRESERVED (this is a content update, not a wipe).
    final h3 = ds.getHorse(3);
    expect(h3!.notes, 'my field note', reason: 'local note preserved');
    expect(ds.getRegion(3), 'northern',
        reason: 'local region override preserved + overlays canon (canon = southern)');
    expect(ds.isRegionUserOverride(3), isTrue);
    expect(
        ds.getBandHistoryForHorse(3).any(
            (e) => e['is_local'] == true && e['stallion_id'] == 809),
        isTrue,
        reason: 'local band edit preserved');

    await Hive.close();
    await dir.delete(recursive: true);
  });
}
