import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:hive_flutter/hive_flutter.dart';
import '../models/horse.dart';
import '../models/band.dart';

class DataService {
  static final DataService instance = DataService._();
  DataService._();

  // --- Data versioning (Phase 1 cutover, IMPLEMENTATION_PLAN.md §4) ---
  //
  // schemaVersion: bump for a STRUCTURAL change (e.g. the one-time local-id ->
  //   pedigree_id cutover). A bump wipes ALL boxes and reloads the bundled
  //   pedigree-keyed canon; the user's local-only NOTES are remapped old->new
  //   id and re-written (everything else returns via canon).
  // contentVersion: bump for every ordinary deploy (new foals, refreshed
  //   fields). A bump reloads the CANON boxes only and leaves the user's boxes
  //   untouched — this is also the fix for the old "updates never reach
  //   existing users" bug (data used to load only when the box was empty).
  static const int _bundledSchemaVersion = 1;
  static const int _bundledContentVersion = 1;

  late Box _meta;
  late Box _horsesBox; // CANON horses (pedigree-keyed) + per-horse photo lists
  late Box _canonBandBox; // CANON bands (shipped), keyed mare_stallion_date
  late Box _canonRegionBox; // CANON region snapshot, keyed by pedigree_id
  late Box _userDataBox; // notes, herd, region override (local-only)
  late Box _bandBox; // user band edits/overrides (additions + 'left' markers)
  late Box _userPhotosBox; // user photo metadata
  late Box _userPhotoBlobsBox; // user photo binary data
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;

    await Hive.initFlutter();
    _meta = await Hive.openBox('_meta');
    _horsesBox = await Hive.openBox('horses');
    _canonBandBox = await Hive.openBox('canonBands');
    _canonRegionBox = await Hive.openBox('canonRegions');
    _userDataBox = await Hive.openBox('userData');
    _bandBox = await Hive.openBox('bands');
    _userPhotosBox = await Hive.openBox('userPhotos');
    _userPhotoBlobsBox = await Hive.openBox('userPhotoBlobs');

    final storedSchema = _meta.get('schemaVersion', defaultValue: 0) as int;
    final storedContent = _meta.get('contentVersion', defaultValue: 0) as int;

    if (storedSchema < _bundledSchemaVersion) {
      // One-time structural cutover (or a brand-new install — same path).
      await _migrateSchema();
    } else if (storedContent < _bundledContentVersion || _horsesBox.isEmpty) {
      // Ordinary content update: refresh canon, keep the user's own data.
      await _reloadCanon();
    }

    await _meta.put('schemaVersion', _bundledSchemaVersion);
    await _meta.put('contentVersion', _bundledContentVersion);
    _initialized = true;
  }

  // --- Boot-time data loading ---

  /// Structural cutover: preserve the user's local-only notes across a full
  /// wipe by remapping their keys old-local-id -> pedigree_id IN-APP (the id
  /// map is bundled and non-personal; the notes themselves NEVER leave the
  /// device, so nothing private is ever published). Everything else (photos,
  /// bands, region) returns automatically from canon.
  Future<void> _migrateSchema() async {
    final preservedNotes = _snapshotLocalNotes();

    await _horsesBox.clear();
    await _canonBandBox.clear();
    await _canonRegionBox.clear();
    await _userDataBox.clear();
    await _bandBox.clear();
    await _userPhotosBox.clear();
    await _userPhotoBlobsBox.clear();

    await _reloadCanon();
    await _restoreRemappedNotes(preservedNotes);
  }

  /// Notes keyed by the pre-cutover local id (only present on an existing
  /// device mid-cutover; empty on a fresh install).
  Map<int, String> _snapshotLocalNotes() {
    final out = <int, String>{};
    for (final key in _userDataBox.keys) {
      final raw = _userDataBox.get(key);
      if (raw is! Map) continue;
      final note = (Map<String, dynamic>.from(raw))['notes'];
      final id = key is int ? key : int.tryParse(key.toString());
      if (id != null && note is String && note.isNotEmpty) out[id] = note;
    }
    return out;
  }

  Future<void> _restoreRemappedNotes(Map<int, String> notesByLocalId) async {
    if (notesByLocalId.isEmpty) return;
    Map<String, dynamic> remap = {};
    try {
      remap = json.decode(await rootBundle.loadString('assets/id_remap.json'))
          as Map<String, dynamic>;
    } catch (_) {
      // No id map bundled (pre-cutover dev build) — nothing to remap against.
      return;
    }
    for (final entry in notesByLocalId.entries) {
      final pedId = remap[entry.key.toString()];
      if (pedId is int) {
        await _userDataBox.put(pedId, {'notes': entry.value});
      }
    }
  }

  /// Load (or refresh) the canon boxes from the bundled assets. Canon boxes
  /// hold ONLY our shipped data, so clearing + repopulating them is how a
  /// content update adds new horses and drops departed ones without ever
  /// touching the user's local boxes.
  Future<void> _reloadCanon() async {
    final jsonStr = await rootBundle.loadString('assets/horses_data.json');
    final data = json.decode(jsonStr) as Map<String, dynamic>;

    await _horsesBox.clear();
    await _canonBandBox.clear();
    await _canonRegionBox.clear();

    // Horses (pedigree-keyed).
    for (final h in (data['horses'] as List)) {
      await _horsesBox.put(h['id'] as int, Map<String, dynamic>.from(h));
    }

    // Photos -> per-horse list under 'photos_<id>'.
    final photosByHorse = <int, List<Map<String, dynamic>>>{};
    for (final p in (data['photos'] as List? ?? [])) {
      final horseId = p['horse_id'] as int;
      photosByHorse.putIfAbsent(horseId, () => []).add(
          Map<String, dynamic>.from(p));
    }
    for (final entry in photosByHorse.entries) {
      await _horsesBox.put('photos_${entry.key}', json.encode(entry.value));
    }

    // Canon bands (normalized to the same shape the read path expects).
    for (final b in (data['bands'] as List? ?? [])) {
      final mareId = b['mare_id'] as int;
      final stallionId = b['stallion_id'] as int;
      final date = b['date_recorded'] as String;
      await _canonBandBox.put('${mareId}_${stallionId}_$date', {
        'horse_id': mareId,
        'stallion_id': stallionId,
        'date_recorded': date,
        'status': 'present',
      });
    }

    // Canon region snapshot, keyed by pedigree_id.
    for (final r in (data['regions'] as List? ?? [])) {
      await _canonRegionBox.put(r['id'] as int, {
        'region': r['region'],
        'observed': r['observed'],
      });
    }
  }

  // --- Horses ---

  /// Overlay the user's local data (notes, herd, region override) onto a canon
  /// horse map, exactly as the storage split intends: canon underneath, the
  /// user's own edits on top at read time.
  Map<String, dynamic> _withUserOverlay(int id, Map<String, dynamic> canon) {
    final map = Map<String, dynamic>.from(canon);
    final userData = _userDataBox.get(id);
    if (userData != null) {
      final ud = Map<String, dynamic>.from(userData);
      if (ud.containsKey('notes')) map['notes'] = ud['notes'];
      if (ud.containsKey('herd')) map['herd'] = ud['herd'];
    }
    map['region'] = getRegion(id);
    return map;
  }

  List<Horse> getAllHorses() {
    final horses = <Horse>[];
    for (final key in _horsesBox.keys) {
      if (key is int) {
        final canon = Map<String, dynamic>.from(_horsesBox.get(key));
        horses.add(Horse.fromMap(_withUserOverlay(key, canon)));
      }
    }
    horses.sort((a, b) => a.name.compareTo(b.name));
    return horses;
  }

  Horse? getHorse(int id) {
    final raw = _horsesBox.get(id);
    if (raw == null) return null;
    return Horse.fromMap(_withUserOverlay(id, Map<String, dynamic>.from(raw)));
  }

  Future<void> updateUserData(int horseId,
      {String? notes, String? herd, String? region}) async {
    final existing = _userDataBox.get(horseId);
    final data = existing != null ? Map<String, dynamic>.from(existing) : {};
    if (notes != null) data['notes'] = notes;
    if (herd != null) data['herd'] = herd.isEmpty ? null : herd;
    if (region != null) data['region'] = region.isEmpty ? null : region;
    await _userDataBox.put(horseId, data);
  }

  Future<void> clearHerd(int horseId) async {
    final existing = _userDataBox.get(horseId);
    final data = existing != null ? Map<String, dynamic>.from(existing) : {};
    data['herd'] = null;
    await _userDataBox.put(horseId, data);
  }

  Future<void> clearNotes(int horseId) async {
    final existing = _userDataBox.get(horseId);
    final data = existing != null ? Map<String, dynamic>.from(existing) : {};
    data['notes'] = null;
    await _userDataBox.put(horseId, data);
  }

  // --- Regions (canon dated snapshot + local override) ---

  /// Resolve a horse's current region: the user's local override wins; else the
  /// canon snapshot. Returns null for horses with no region (e.g. MD herd).
  String? getRegion(int horseId) {
    final userData = _userDataBox.get(horseId);
    if (userData is Map) {
      final ud = Map<String, dynamic>.from(userData);
      if (ud['region'] != null) return ud['region'] as String?;
    }
    final canon = _canonRegionBox.get(horseId);
    if (canon is Map) return Map<String, dynamic>.from(canon)['region'] as String?;
    return null;
  }

  /// True when the displayed region differs from canon — i.e. it's the user's
  /// own local observation (drives the provenance accent rule).
  bool isRegionUserOverride(int horseId) {
    final userData = _userDataBox.get(horseId);
    if (userData is! Map) return false;
    return Map<String, dynamic>.from(userData)['region'] != null;
  }

  // --- Photos ---

  List<HorsePhoto> getPhotosForHorse(int horseId) {
    final photos = <HorsePhoto>[];

    // Canon photos (book + harvested field).
    final canonJson = _horsesBox.get('photos_$horseId');
    if (canonJson != null) {
      for (final p in (json.decode(canonJson) as List)) {
        photos.add(HorsePhoto.fromMap(Map<String, dynamic>.from(p)));
      }
    }

    // User (local-only) photos.
    final userPhotosJson = _userPhotosBox.get(horseId);
    if (userPhotosJson != null) {
      for (final p in (json.decode(userPhotosJson) as List)) {
        photos.add(HorsePhoto.fromMap(Map<String, dynamic>.from(p)));
      }
    }

    // Field/user photos first, book last (the "slowly replace book" ordering).
    photos.sort((a, b) {
      int rank(HorsePhoto p) => p.source == 'book' ? 1 : 0;
      return rank(a).compareTo(rank(b));
    });
    return photos;
  }

  HorsePhoto? getFirstPhotoForHorse(int horseId) {
    final photos = getPhotosForHorse(horseId);
    if (photos.isEmpty) return null;
    // Prefer a non-book (field/user) photo; getPhotosForHorse already sorts them
    // first, so the head of the list is the right primary image.
    return photos.first;
  }

  Future<void> addUserPhoto(int horseId, String filename, Uint8List bytes) async {
    await _userPhotoBlobsBox.put(filename, bytes);

    final existing = _userPhotosBox.get(horseId);
    final list = existing != null
        ? (json.decode(existing) as List).cast<Map<String, dynamic>>()
        : <Map<String, dynamic>>[];

    list.add({
      'id': DateTime.now().millisecondsSinceEpoch,
      'horse_id': horseId,
      'filename': filename,
      'source': 'user',
    });

    await _userPhotosBox.put(horseId, json.encode(list));
  }

  Uint8List? getUserPhotoBytes(String filename) {
    final data = _userPhotoBlobsBox.get(filename);
    if (data == null) return null;
    if (data is Uint8List) return data;
    if (data is List) return Uint8List.fromList(data.cast<int>());
    return null;
  }

  Future<void> deleteUserPhoto(int horseId, String filename) async {
    await _userPhotoBlobsBox.delete(filename);

    final existing = _userPhotosBox.get(horseId);
    if (existing != null) {
      final list = (json.decode(existing) as List).cast<Map<String, dynamic>>();
      list.removeWhere((p) => p['filename'] == filename);
      await _userPhotosBox.put(horseId, json.encode(list));
    }
  }

  // --- Bands (canon snapshot + local edits, merged at read time) ---

  /// All band entries (canon + user) for a stallion. The user's box overlays
  /// canon: a dated 'left' marker she records suppresses a canon membership,
  /// and a band she adds locally that canon doesn't have still shows.
  Iterable<Map<String, dynamic>> _bandEntries() sync* {
    for (final key in _canonBandBox.keys) {
      yield Map<String, dynamic>.from(_canonBandBox.get(key));
    }
    for (final key in _bandBox.keys) {
      yield Map<String, dynamic>.from(_bandBox.get(key));
    }
  }

  Future<void> addToBand(int horseId, int stallionId, String date,
      {String status = 'present'}) async {
    final key = '${horseId}_${stallionId}_$date';
    await _bandBox.put(key, {
      'horse_id': horseId,
      'stallion_id': stallionId,
      'date_recorded': date,
      'status': status,
    });
  }

  /// Record a dated departure marker for a horse that left the band. History is
  /// preserved (prior memberships, canon included, stay); getCurrentBandMembers
  /// stops showing the horse because its latest-dated entry is now 'left'. As a
  /// user-box entry it survives canon content reloads (the sellable-app promise:
  /// removing a canon-shipped band is a local override that isn't clobbered).
  Future<void> markBandDeparture(int horseId, int stallionId, String date) async {
    await addToBand(horseId, stallionId, date, status: 'left');
  }

  List<BandMember> getCurrentBandMembers(int stallionId) {
    // Latest-dated entry per horse, across canon + user.
    final latest = <int, Map<String, dynamic>>{};
    for (final entry in _bandEntries()) {
      if (entry['stallion_id'] != stallionId) continue;
      final horseId = entry['horse_id'] as int;
      final date = entry['date_recorded'] as String;
      final prev = latest[horseId];
      if (prev == null || date.compareTo(prev['date_recorded'] as String) > 0) {
        latest[horseId] = entry;
      }
    }

    final members = <int, BandMember>{};
    latest.forEach((horseId, entry) {
      if ((entry['status'] ?? 'present') == 'left') return;
      final horse = getHorse(horseId);
      if (horse != null) {
        members[horseId] = BandMember(
          horseId: horseId,
          name: horse.name,
          sex: horse.sex,
          color: horse.color,
          dateRecorded: entry['date_recorded'] as String,
        );
      }
    });

    final sorted = members.values.toList()
      ..sort((a, b) {
        final aOrder = a.sex == 'stallion' ? 0 : a.sex == 'mare' ? 1 : 2;
        final bOrder = b.sex == 'stallion' ? 0 : b.sex == 'mare' ? 1 : 2;
        if (aOrder != bOrder) return aOrder.compareTo(bOrder);
        return a.name.compareTo(b.name);
      });

    return sorted;
  }

  List<Map<String, dynamic>> getBandHistoryForHorse(int horseId) {
    final history = <Map<String, dynamic>>[];

    for (final entry in _bandEntries()) {
      if (entry['horse_id'] == horseId) {
        final stallion = getHorse(entry['stallion_id'] as int);
        history.add({
          'id': '${entry['horse_id']}_${entry['stallion_id']}_${entry['date_recorded']}',
          'stallion_id': entry['stallion_id'],
          'date_recorded': entry['date_recorded'],
          'status': entry['status'] ?? 'present',
          'stallion_name': stallion?.name ?? 'Unknown',
        });
      }
    }

    history.sort((a, b) => (b['date_recorded'] as String)
        .compareTo(a['date_recorded'] as String));
    return history;
  }

  Future<void> removeBandEntry(String key) async {
    await _bandBox.delete(key);
  }

  List<Horse> getStallions() {
    return getAllHorses().where((h) => h.sex == 'stallion').toList();
  }

  // --- Backup & Restore ---

  /// Export all user data as a JSON map.
  Map<String, dynamic> exportUserData() {
    final userData = <String, dynamic>{};
    for (final key in _userDataBox.keys) {
      userData[key.toString()] = Map<String, dynamic>.from(_userDataBox.get(key));
    }

    final bands = <String, dynamic>{};
    for (final key in _bandBox.keys) {
      bands[key.toString()] = Map<String, dynamic>.from(_bandBox.get(key));
    }

    final userPhotoMeta = <String, dynamic>{};
    for (final key in _userPhotosBox.keys) {
      userPhotoMeta[key.toString()] = _userPhotosBox.get(key);
    }

    final userPhotoBlobs = <String, String>{};
    for (final key in _userPhotoBlobsBox.keys) {
      final bytes = getUserPhotoBytes(key as String);
      if (bytes != null) {
        userPhotoBlobs[key] = base64Encode(bytes);
      }
    }

    return {
      'version': 1,
      'exported_at': DateTime.now().toIso8601String(),
      'user_data': userData,
      'bands': bands,
      'user_photo_meta': userPhotoMeta,
      'user_photo_blobs': userPhotoBlobs,
    };
  }

  /// Import user data from a backup JSON map.
  Future<void> importUserData(Map<String, dynamic> backup) async {
    final userData = backup['user_data'] as Map<String, dynamic>? ?? {};
    for (final entry in userData.entries) {
      final key = int.tryParse(entry.key) ?? entry.key;
      await _userDataBox.put(key, entry.value);
    }

    final bands = backup['bands'] as Map<String, dynamic>? ?? {};
    for (final entry in bands.entries) {
      await _bandBox.put(entry.key, entry.value);
    }

    final photoMeta = backup['user_photo_meta'] as Map<String, dynamic>? ?? {};
    for (final entry in photoMeta.entries) {
      final key = int.tryParse(entry.key) ?? entry.key;
      await _userPhotosBox.put(key, entry.value);
    }

    final photoBlobs = backup['user_photo_blobs'] as Map<String, dynamic>? ?? {};
    for (final entry in photoBlobs.entries) {
      final bytes = base64Decode(entry.value as String);
      await _userPhotoBlobsBox.put(entry.key, Uint8List.fromList(bytes));
    }
  }

  /// Check if there's any user data worth backing up.
  bool hasUserData() {
    return _userDataBox.isNotEmpty ||
        _bandBox.isNotEmpty ||
        _userPhotosBox.isNotEmpty;
  }
}
