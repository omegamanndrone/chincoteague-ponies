import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/services.dart';
import 'package:hive_flutter/hive_flutter.dart';
import '../models/horse.dart';
import '../models/band.dart';

class DataService {
  static final DataService instance = DataService._();
  DataService._();

  late Box _horsesBox;
  late Box _userDataBox; // notes, herds per horse
  late Box _bandBox;
  late Box _userPhotosBox; // user photo metadata
  late Box _userPhotoBlobsBox; // user photo binary data
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;

    await Hive.initFlutter();
    _horsesBox = await Hive.openBox('horses');
    _userDataBox = await Hive.openBox('userData');
    _bandBox = await Hive.openBox('bands');
    _userPhotosBox = await Hive.openBox('userPhotos');
    _userPhotoBlobsBox = await Hive.openBox('userPhotoBlobs');

    // Load book data on first run
    if (_horsesBox.isEmpty) {
      await _loadBookData();
    }

    _initialized = true;
  }

  Future<void> _loadBookData() async {
    final jsonStr = await rootBundle.loadString('assets/horses_data.json');
    final data = json.decode(jsonStr) as Map<String, dynamic>;

    final horses = data['horses'] as List;
    for (final h in horses) {
      final id = h['id'] as int;
      await _horsesBox.put(id, h);
    }

    // Store photo mappings (book photos)
    final photos = data['photos'] as List;
    for (final p in photos) {
      final key = 'book_${p['id']}';
      await _horsesBox.put('photo_$key', p);
    }

    // Store photo list per horse
    final photosByHorse = <int, List<Map<String, dynamic>>>{};
    for (final p in photos) {
      final horseId = p['horse_id'] as int;
      photosByHorse.putIfAbsent(horseId, () => []);
      photosByHorse[horseId]!.add(Map<String, dynamic>.from(p));
    }
    for (final entry in photosByHorse.entries) {
      await _horsesBox.put('photos_${entry.key}', json.encode(entry.value));
    }
  }

  // --- Horses ---

  List<Horse> getAllHorses() {
    final horses = <Horse>[];
    for (final key in _horsesBox.keys) {
      if (key is int) {
        final map = Map<String, dynamic>.from(_horsesBox.get(key));
        // Overlay user data (notes, herd)
        final userData = _userDataBox.get(key);
        if (userData != null) {
          final ud = Map<String, dynamic>.from(userData);
          map['notes'] = ud['notes'];
          map['herd'] = ud['herd'];
        }
        horses.add(Horse.fromMap(map));
      }
    }
    horses.sort((a, b) => a.name.compareTo(b.name));
    return horses;
  }

  Horse? getHorse(int id) {
    final raw = _horsesBox.get(id);
    if (raw == null) return null;
    final map = Map<String, dynamic>.from(raw);
    final userData = _userDataBox.get(id);
    if (userData != null) {
      final ud = Map<String, dynamic>.from(userData);
      map['notes'] = ud['notes'];
      map['herd'] = ud['herd'];
    }
    return Horse.fromMap(map);
  }

  Future<void> updateUserData(int horseId, {String? notes, String? herd}) async {
    final existing = _userDataBox.get(horseId);
    final data = existing != null ? Map<String, dynamic>.from(existing) : {};
    if (notes != null) data['notes'] = notes;
    if (herd != null) data['herd'] = herd.isEmpty ? null : herd;
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

  // --- Photos ---

  List<HorsePhoto> getPhotosForHorse(int horseId) {
    final photos = <HorsePhoto>[];

    // Book photos
    final bookJson = _horsesBox.get('photos_$horseId');
    if (bookJson != null) {
      final list = json.decode(bookJson) as List;
      for (final p in list) {
        photos.add(HorsePhoto.fromMap(Map<String, dynamic>.from(p)));
      }
    }

    // User photos
    final userPhotosJson = _userPhotosBox.get(horseId);
    if (userPhotosJson != null) {
      final list = json.decode(userPhotosJson) as List;
      for (final p in list) {
        photos.add(HorsePhoto.fromMap(Map<String, dynamic>.from(p)));
      }
    }

    return photos;
  }

  HorsePhoto? getFirstPhotoForHorse(int horseId) {
    final photos = getPhotosForHorse(horseId);
    if (photos.isEmpty) return null;
    // Prefer book photos
    return photos.firstWhere((p) => p.source == 'book',
        orElse: () => photos.first);
  }

  Future<void> addUserPhoto(int horseId, String filename, Uint8List bytes) async {
    // Store the photo bytes
    await _userPhotoBlobsBox.put(filename, bytes);

    // Add to the user photos list for this horse
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
    // Remove bytes
    await _userPhotoBlobsBox.delete(filename);

    // Remove from list
    final existing = _userPhotosBox.get(horseId);
    if (existing != null) {
      final list = (json.decode(existing) as List).cast<Map<String, dynamic>>();
      list.removeWhere((p) => p['filename'] == filename);
      await _userPhotosBox.put(horseId, json.encode(list));
    }
  }

  // --- Bands ---

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
  /// preserved (the prior membership entries stay); getCurrentBandMembers stops
  /// showing the horse because its latest-dated entry is now a 'left' marker.
  Future<void> markBandDeparture(int horseId, int stallionId, String date) async {
    await addToBand(horseId, stallionId, date, status: 'left');
  }

  List<BandMember> getCurrentBandMembers(int stallionId) {
    // First find the latest-dated entry per horse (membership OR departure)...
    final latest = <int, Map<String, dynamic>>{};
    for (final key in _bandBox.keys) {
      final entry = Map<String, dynamic>.from(_bandBox.get(key));
      if (entry['stallion_id'] != stallionId) continue;
      final horseId = entry['horse_id'] as int;
      final date = entry['date_recorded'] as String;
      final prev = latest[horseId];
      if (prev == null || date.compareTo(prev['date_recorded'] as String) > 0) {
        latest[horseId] = entry;
      }
    }

    // ...then include only horses whose latest entry is not a departure.
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

    // Sort: stallions first, then mares, then others
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

    for (final key in _bandBox.keys) {
      final entry = Map<String, dynamic>.from(_bandBox.get(key));
      if (entry['horse_id'] == horseId) {
        final stallion = getHorse(entry['stallion_id'] as int);
        history.add({
          'id': key,
          'stallion_id': entry['stallion_id'],
          'date_recorded': entry['date_recorded'],
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
    // User data (notes, herds)
    final userData = <String, dynamic>{};
    for (final key in _userDataBox.keys) {
      userData[key.toString()] = Map<String, dynamic>.from(_userDataBox.get(key));
    }

    // Band entries
    final bands = <String, dynamic>{};
    for (final key in _bandBox.keys) {
      bands[key.toString()] = Map<String, dynamic>.from(_bandBox.get(key));
    }

    // User photos metadata
    final userPhotoMeta = <String, dynamic>{};
    for (final key in _userPhotosBox.keys) {
      userPhotoMeta[key.toString()] = _userPhotosBox.get(key);
    }

    // User photo blobs as base64
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
    // User data
    final userData = backup['user_data'] as Map<String, dynamic>? ?? {};
    for (final entry in userData.entries) {
      final key = int.tryParse(entry.key) ?? entry.key;
      await _userDataBox.put(key, entry.value);
    }

    // Bands
    final bands = backup['bands'] as Map<String, dynamic>? ?? {};
    for (final entry in bands.entries) {
      await _bandBox.put(entry.key, entry.value);
    }

    // User photo metadata
    final photoMeta = backup['user_photo_meta'] as Map<String, dynamic>? ?? {};
    for (final entry in photoMeta.entries) {
      final key = int.tryParse(entry.key) ?? entry.key;
      await _userPhotosBox.put(key, entry.value);
    }

    // User photo blobs
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
