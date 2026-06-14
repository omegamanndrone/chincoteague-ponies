import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/data_service.dart';
import '../models/horse.dart';
import '../models/band.dart';
import '../theme/provenance.dart';
import 'photo_viewer_screen.dart';

class HorseDetailScreen extends StatefulWidget {
  final Horse horse;

  const HorseDetailScreen({super.key, required this.horse});

  @override
  State<HorseDetailScreen> createState() => _HorseDetailScreenState();
}

class _HorseDetailScreenState extends State<HorseDetailScreen> {
  final _data = DataService.instance;
  late Horse _horse;
  List<HorsePhoto> _photos = [];
  final Map<String, Uint8List> _photoBytes = {};
  List<Map<String, dynamic>> _bandHistory = [];
  List<BandMember> _currentBandMembers = [];
  int? _currentStallionId;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _horse = widget.horse;
    _loadData();
  }

  Future<void> _loadData() async {
    _photos = _data.getPhotosForHorse(_horse.id!);

    // Load photo bytes
    _photoBytes.clear();
    for (final photo in _photos) {
      // Canon photos (book + Kristina's harvested 'field' crops) are bundled in
      // assets; only the user's own on-device photos live in blob storage.
      if (photo.isCanon) {
        try {
          final bytes =
              await rootBundle.load('assets/photos/${photo.filename}');
          _photoBytes[photo.filename] = bytes.buffer.asUint8List();
        } catch (_) {}
      } else {
        final bytes = _data.getUserPhotoBytes(photo.filename);
        if (bytes != null) _photoBytes[photo.filename] = bytes;
      }
    }

    _loadBandData();
    // Refresh horse from data service
    final refreshed = _data.getHorse(_horse.id!);
    if (refreshed != null) _horse = refreshed;
    setState(() => _loading = false);
  }

  void _loadBandData() {
    _bandHistory = _data.getBandHistoryForHorse(_horse.id!);
    if (_bandHistory.isNotEmpty) {
      _currentStallionId = _bandHistory.first['stallion_id'] as int;
      _currentBandMembers = _data.getCurrentBandMembers(_currentStallionId!);
    } else {
      _currentStallionId = null;
      _currentBandMembers = [];
    }
  }

  Future<void> _takePhoto() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.camera);
    if (image == null) return;

    final bytes = await image.readAsBytes();
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final filename = 'user_${_horse.id}_$timestamp.jpg';

    await _data.addUserPhoto(_horse.id!, filename, bytes);
    _loadData();
  }

  Future<void> _pickPhoto() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery);
    if (image == null) return;

    final bytes = await image.readAsBytes();
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final filename = 'user_${_horse.id}_$timestamp.jpg';

    await _data.addUserPhoto(_horse.id!, filename, bytes);
    _loadData();
  }

  Future<void> _setHerd() async {
    final result = await showDialog<String>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Assign Herd'),
        children: [
          SimpleDialogOption(
            child: const Text('Northern Herd'),
            onPressed: () => Navigator.pop(context, 'northern'),
          ),
          SimpleDialogOption(
            child: const Text('Southern Herd'),
            onPressed: () => Navigator.pop(context, 'southern'),
          ),
          SimpleDialogOption(
            child: const Text('Unassigned'),
            onPressed: () => Navigator.pop(context, ''),
          ),
        ],
      ),
    );

    if (result == null) return;

    // N/S is the dated canon `region` now; an edit here is the user's LOCAL
    // override (empty -> clear the override and fall back to the canon value).
    await _data.updateUserData(_horse.id!, region: result);
    final refreshed = _data.getHorse(_horse.id!);
    if (refreshed != null) setState(() => _horse = refreshed);
  }

  Future<void> _editNotes() async {
    final controller = TextEditingController(text: _horse.notes ?? '');
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Your Notes'),
        content: TextField(
          controller: controller,
          maxLines: 6,
          decoration: const InputDecoration(
            hintText: 'Add your observations, sightings, etc...',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (result == null) return;

    if (result.isEmpty) {
      await _data.clearNotes(_horse.id!);
    } else {
      await _data.updateUserData(_horse.id!, notes: result);
    }
    final refreshed = _data.getHorse(_horse.id!);
    if (refreshed != null) setState(() => _horse = refreshed);
  }

  Future<void> _editBand() async {
    final stallions = _data.getStallions();

    if (!mounted) return;

    final stallion = await showDialog<Horse>(
      context: context,
      builder: (context) => _StallionPickerDialog(stallions: stallions),
    );

    if (stallion == null || !mounted) return;

    final existingMembers = _data.getCurrentBandMembers(stallion.id!);
    final existingIds = existingMembers.map((m) => m.horseId).toSet();
    final allHorses = _data.getAllHorses();

    if (!mounted) return;

    final selectedIds = await showDialog<Set<int>>(
      context: context,
      builder: (context) => _BandMemberPickerDialog(
        allHorses: allHorses,
        stallion: stallion,
        preselectedIds: existingIds,
      ),
    );

    if (selectedIds == null || !mounted) return;

    final today = DateTime.now().toIso8601String().substring(0, 10);
    final idsToAdd = {...selectedIds, stallion.id!};
    for (final id in idsToAdd) {
      await _data.addToBand(id, stallion.id!, today);
    }

    // Horses deselected since last time left the band: write a dated departure
    // marker (never the stallion himself) so they drop off the current roster
    // while their history is preserved.
    final removedIds = existingIds.difference(selectedIds)..remove(stallion.id!);
    for (final id in removedIds) {
      await _data.markBandDeparture(id, stallion.id!, today);
    }

    setState(() => _loading = true);
    _loadBandData();
    final refreshed = _data.getHorse(_horse.id!);
    if (refreshed != null) _horse = refreshed;
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_horse.name),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildPhotoGallery(),
                  _buildIdentityCard(),
                  _buildActionBar(),
                  _buildDescriptionCard(),
                  _buildBandCard(),
                  _buildPedigreeCard(),
                  _buildRecordsCard(),
                  if (_horse.background != null && _horse.background!.isNotEmpty)
                    _buildBackgroundCard(),
                  _buildNotesCard(),
                  if (_horse.qrVideoUrl != null ||
                      _horse.qrPedigreeUrl != null ||
                      _horse.dscPhotoUrl != null)
                    _buildLinksCard(),
                  if (_hasLocalData()) Provenance.legend(),
                  const SizedBox(height: 24),
                ],
              ),
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _takePhoto,
        backgroundColor: const Color(0xFF2E7D32),
        child: const Icon(Icons.camera_alt, color: Colors.white),
      ),
    );
  }

  /// Whether this horse carries any of the user's own local data — drives
  /// whether the provenance legend is worth showing.
  bool _hasLocalData() {
    return _horse.notes != null ||
        _data.isRegionUserOverride(_horse.id!) ||
        _photos.any((p) => p.source == 'user') ||
        _bandHistory.any((e) => e['is_local'] == true);
  }

  Widget _buildPhotoGallery() {
    // _photos already arrives field/user-first, book last (DataService priority);
    // use it as-is so Kristina's harvested 'field' crops show and lead.
    final orderedPhotos = _photos;
    final userPhotos = _photos.where((p) => p.source == 'user').toList();

    if (orderedPhotos.isEmpty) {
      return Container(
        height: 200,
        color: Colors.grey[200],
        child: const Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.photo_library, size: 48, color: Colors.grey),
              SizedBox(height: 8),
              Text('No photos yet', style: TextStyle(color: Colors.grey)),
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        SizedBox(
          height: 250,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            itemCount: orderedPhotos.length,
            itemBuilder: (context, index) {
              final photo = orderedPhotos[index];
              final bytes = _photoBytes[photo.filename];

              return GestureDetector(
                onTap: () {
                  if (bytes != null) {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => PhotoViewerScreen(
                          imageBytes: bytes,
                          horseName: _horse.name,
                          source: photo.source,
                        ),
                      ),
                    );
                  }
                },
                onLongPress: photo.source == 'user'
                    ? () => _confirmDeletePhoto(photo)
                    : null,
                child: Container(
                  margin: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    // User's own (not-yet-harvested) photos carry the
                    // provenance accent; canon book/field photos stay clean.
                    border: photo.source == 'user'
                        ? Border.all(color: Provenance.local, width: 2)
                        : null,
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: bytes != null
                        ? Image.memory(bytes,
                            fit: BoxFit.contain, height: 234)
                        : Container(
                            width: 200,
                            color: Colors.grey[300],
                            child: const Center(
                              child: Icon(Icons.broken_image,
                                  color: Colors.grey),
                            ),
                          ),
                  ),
                ),
              );
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Text(
            '${orderedPhotos.length} photo${orderedPhotos.length == 1 ? '' : 's'}'
            '${userPhotos.isNotEmpty ? ' (${userPhotos.length} yours)' : ''}'
            ' \u2014 swipe to see more',
            style: TextStyle(fontSize: 12, color: Colors.grey[500]),
          ),
        ),
      ],
    );
  }

  Widget _buildActionBar() {
    // Region (N/S) is the VA-only sub-herd split; the MD (Assateague) herd isn't
    // subdivided, so MD ponies get no "Assign Herd" button.
    final showHerd = _horse.state != 'MD';
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          if (showHerd) ...[
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _setHerd,
                // Show the canon region (her harvested N/S); accent ONLY when it's
                // her local override of canon, not canon itself.
                style: _data.isRegionUserOverride(_horse.id!)
                    ? OutlinedButton.styleFrom(
                        foregroundColor: Provenance.local,
                        side: const BorderSide(color: Provenance.local))
                    : null,
                icon: const Icon(Icons.location_on),
                label: Text(_horse.region != null
                    ? '${_horse.region![0].toUpperCase()}${_horse.region!.substring(1)} Herd'
                    : 'Assign Herd'),
              ),
            ),
            const SizedBox(width: 8),
          ],
          Expanded(
            child: OutlinedButton.icon(
              onPressed: _pickPhoto,
              icon: const Icon(Icons.photo_library),
              label: const Text('Add Photo'),
            ),
          ),
        ],
      ),
    );
  }

  // --- At-a-glance identity (always open) ---------------------------------
  Widget _buildIdentityCard() {
    // One consistent style across the glance line. Region is intentionally NOT
    // here — it lives on the herd button below, so it isn't duplicated.
    final parts = <String>[];
    if ((_horse.sex ?? '').isNotEmpty) parts.add(_cap(_horse.sex));
    if ((_horse.color ?? '').isNotEmpty) parts.add(_horse.color!);
    final age = _ageString();
    if (age != null) parts.add(age);
    final flags = _flagLabels();

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_horse.nickname != null && _horse.nickname!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text('"${_horse.nickname}"',
                    style: TextStyle(
                        fontSize: 15,
                        fontStyle: FontStyle.italic,
                        color: Colors.grey[700])),
              ),
            Text(parts.join('  ·  '),
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            if (flags.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(flags.join('  ·  ').toUpperCase(),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                    color: Colors.grey[600],
                  )),
            ],
          ],
        ),
      ),
    );
  }

  String _cap(String? s) =>
      (s == null || s.isEmpty) ? '' : '${s[0].toUpperCase()}${s.substring(1)}';

  /// Age is computed live from the birth year; show both, e.g. "14 yrs (b. 2011)".
  String? _ageString() {
    final raw = _horse.birthYear;
    final y = int.tryParse(raw ?? '');
    if (y != null) return '${DateTime.now().year - y} yrs (b. $y)';
    return (raw != null && raw.isNotEmpty) ? 'b. $raw' : null;
  }

  /// Lineage + registry flags as plain metadata words — rendered as one quiet
  /// small-caps line (never as buttons/badges).
  List<String> _flagLabels() => [
        if (_horse.buyback) 'Buyback',
        if (_horse.feral) 'Feral',
        if (_horse.mistyDescendant) 'Misty descendant',
        if (_horse.halfChincoteague) '½ Chincoteague',
        if (_horse.registry != null) '${_horse.registry} registry',
      ];

  // --- Description (always open): the field-ID core ------------------------
  Widget _buildDescriptionCard() {
    // Uniform label-rows so the block reads consistently (markings leads — it's
    // the field-ID core).
    final rows = <Widget>[
      if (_horse.markings != null && _horse.markings!.isNotEmpty)
        _detailRow('Markings', _horse.markings!),
      if (_horse.eyeColor != null) _detailRow('Eyes', _horse.eyeColor!),
      if (_horse.brand != null && _horse.brand!.isNotEmpty)
        _detailRow('Brand', _horse.brand!),
    ];
    if (rows.isEmpty) return const SizedBox.shrink();
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Description',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Divider(),
            ...rows,
          ],
        ),
      ),
    );
  }

  // --- Pedigree / Family (collapsed) --------------------------------------
  Widget _buildPedigreeCard() {
    if (_horse.sire == null && _horse.dam == null) return const SizedBox.shrink();
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ExpansionTile(
        leading: const Icon(Icons.account_tree, color: Color(0xFF2E7D32)),
        title: const Text('Pedigree / Family',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        children: [
          if (_horse.sire != null) _parentRow('Sire', _horse.sire!, _horse.sireId),
          if (_horse.dam != null) _parentRow('Dam', _horse.dam!, _horse.damId),
        ],
      ),
    );
  }

  /// A parent row. Tappable when the parent resolves to a horse in the current
  /// herds (pedigree id present in canon); otherwise a plain name (the tree
  /// dead-ends at ancestors not in the current VA/MD herds, per the plan).
  Widget _parentRow(String label, String name, int? parentId) {
    final target = parentId != null ? _data.getHorse(parentId) : null;
    final tappable = target != null;
    return InkWell(
      onTap: tappable
          ? () => Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (_) => HorseDetailScreen(horse: target)),
              ).then((_) => _loadData())
          : null,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            SizedBox(
              width: 60,
              child: Text(label,
                  style: TextStyle(
                      color: Colors.grey[600], fontWeight: FontWeight.w500)),
            ),
            Expanded(
              child: Text(name,
                  style: TextStyle(
                    color: tappable ? const Color(0xFF2E7D32) : Colors.black87,
                    decoration: tappable ? TextDecoration.underline : null,
                    fontWeight: tappable ? FontWeight.w500 : FontWeight.normal,
                  )),
            ),
            if (tappable)
              const Icon(Icons.chevron_right, size: 18, color: Color(0xFF2E7D32)),
          ],
        ),
      ),
    );
  }

  // --- Records & registry (collapsed) -------------------------------------
  Widget _buildRecordsCard() {
    final rows = <Widget>[
      if (_horse.breeder != null) _detailRow('Breeder', _horse.breeder!),
      if (_horse.owner != null) _detailRow('Owner', _horse.owner!),
      if (_horse.birthDate != null) _detailRow('Born', _horse.birthDate!),
      if (_horse.birthLocation != null)
        _detailRow('Birthplace', _horse.birthLocation!),
      if (_horse.auctionPrice != null)
        _detailRow('Auction Price', _horse.auctionPrice!),
      if (_horse.auctionNumber != null)
        _detailRow('Auction No.', _horse.auctionNumber!),
      if (_horse.buybackDonor != null)
        _detailRow('Buyback Donor', _horse.buybackDonor!),
      if (_horse.registry != null)
        _detailRow('Registry',
            '${_horse.registry}${_horse.registryNumber != null ? ' ${_horse.registryNumber}' : ''}'),
      if (_horse.genotype != null) _detailRow('Genotype', _horse.genotype!),
    ];
    if (rows.isEmpty) return const SizedBox.shrink();
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ExpansionTile(
        leading: const Icon(Icons.assignment, color: Color(0xFF2E7D32)),
        title: const Text('Records & registry',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        children: rows,
      ),
    );
  }

  Widget _buildBandCard() {
    final now = DateTime.now();
    final cutoff = DateTime(now.year - 2, now.month, now.day)
        .toIso8601String()
        .substring(0, 10);

    final recentHistory = _bandHistory
        .where((e) => (e['date_recorded'] as String).compareTo(cutoff) >= 0)
        .toList();

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.groups, size: 20),
                const SizedBox(width: 8),
                const Text('Band',
                    style:
                        TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const Spacer(),
                TextButton.icon(
                  onPressed: _editBand,
                  icon: const Icon(Icons.edit, size: 16),
                  label: const Text('Edit Band'),
                ),
              ],
            ),
            const Divider(),
            if (_currentBandMembers.isNotEmpty) ...[
              Text('Current Band',
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Colors.grey[700])),
              const SizedBox(height: 4),
              ..._currentBandMembers.map((m) => _bandMemberRow(m)),
              const SizedBox(height: 12),
            ],
            if (recentHistory.isNotEmpty) ...[
              Text('History (last 2 years)',
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Colors.grey[700])),
              const SizedBox(height: 4),
              ...recentHistory.map((entry) => Provenance.rule(
                    isLocal: entry['is_local'] == true,
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          Icon(Icons.circle, size: 8, color: Colors.grey[400]),
                          const SizedBox(width: 8),
                          Text(entry['stallion_name'] as String,
                              style:
                                  const TextStyle(fontWeight: FontWeight.w500)),
                          const Spacer(),
                          Text(entry['date_recorded'] as String,
                              style: TextStyle(
                                  fontSize: 12, color: Colors.grey[500])),
                        ],
                      ),
                    ),
                  )),
            ],
            if (_currentBandMembers.isEmpty && recentHistory.isEmpty)
              Text(
                'No band assigned yet. Tap "Edit Band" to link this horse with its current traveling group.',
                style: TextStyle(
                    color: Colors.grey[400], fontStyle: FontStyle.italic),
              ),
          ],
        ),
      ),
    );
  }

  Widget _bandMemberRow(BandMember member) {
    final isCurrentHorse = member.horseId == _horse.id;
    final sexIcon = member.sex == 'stallion'
        ? Icons.star
        : member.sex == 'mare'
            ? Icons.female
            : Icons.child_care;

    return InkWell(
      onTap: isCurrentHorse
          ? null
          : () async {
              final target = _data.getHorse(member.horseId);
              if (target != null && mounted) {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => HorseDetailScreen(horse: target),
                  ),
                ).then((_) => _loadData());
              }
            },
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Icon(sexIcon, size: 16, color: const Color(0xFF2E7D32)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(member.name,
                  style: TextStyle(
                    fontWeight:
                        isCurrentHorse ? FontWeight.bold : FontWeight.normal,
                    color: isCurrentHorse
                        ? Colors.black
                        : const Color(0xFF2E7D32),
                    decoration:
                        isCurrentHorse ? null : TextDecoration.underline,
                  )),
            ),
            Text(member.sex ?? '',
                style: TextStyle(fontSize: 12, color: Colors.grey[500])),
            const SizedBox(width: 8),
            Text(member.dateRecorded,
                style: TextStyle(fontSize: 11, color: Colors.grey[400])),
          ],
        ),
      ),
    );
  }

  // --- Background (collapsed): the canon narrative (replaces "From the Book") -
  Widget _buildBackgroundCard() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ExpansionTile(
        leading: const Icon(Icons.menu_book, color: Color(0xFF2E7D32)),
        title: const Text('Background',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Text(_horse.background!,
                style: const TextStyle(height: 1.4)),
          ),
        ],
      ),
    );
  }

  Widget _buildNotesCard() {
    final hasNotes = _horse.notes != null;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: InkWell(
        onTap: _editNotes,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            // Notes are always the user's own — accent them when present.
            border: hasNotes
                ? const Border(
                    left: BorderSide(color: Provenance.local, width: 3))
                : null,
          ),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(children: [
                Icon(Icons.edit_note, size: 20),
                SizedBox(width: 8),
                Text('Your Notes',
                    style:
                        TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                Spacer(),
                Icon(Icons.edit, size: 16, color: Colors.grey),
              ]),
              const SizedBox(height: 8),
              Text(
                _horse.notes ?? 'Tap to add notes...',
                style: TextStyle(
                  color: _horse.notes != null ? Colors.black87 : Colors.grey[400],
                  fontStyle:
                      _horse.notes != null ? FontStyle.normal : FontStyle.italic,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLinksCard() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Links',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (_horse.qrVideoUrl != null)
              _linkRow(Icons.videocam, 'Video Clip', _horse.qrVideoUrl!),
            if (_horse.qrPedigreeUrl != null)
              _linkRow(Icons.account_tree, 'Pedigree', _horse.qrPedigreeUrl!),
            // Copyrighted DSC gallery — link out only, never rehost (plan §8).
            if (_horse.dscPhotoUrl != null)
              _linkRow(Icons.photo_camera, 'Photos at DSC', _horse.dscPhotoUrl!),
          ],
        ),
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label,
                style: TextStyle(
                    color: Colors.grey[600], fontWeight: FontWeight.w500)),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open: $url')),
      );
    }
  }

  Widget _linkRow(IconData icon, String label, String url) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: InkWell(
        onTap: () => _openUrl(url),
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
          child: Row(
            children: [
              Icon(icon, size: 20, color: const Color(0xFF2E7D32)),
              const SizedBox(width: 8),
              Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
              const Spacer(),
              const Icon(Icons.open_in_new,
                  size: 16, color: Color(0xFF2E7D32)),
            ],
          ),
        ),
      ),
    );
  }

  void _confirmDeletePhoto(HorsePhoto photo) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Photo?'),
        content: const Text('This will permanently remove this photo.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              await _data.deleteUserPhoto(_horse.id!, photo.filename);
              _loadData();
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}

class _StallionPickerDialog extends StatelessWidget {
  final List<Horse> stallions;
  const _StallionPickerDialog({required this.stallions});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Select Band Stallion'),
      content: SizedBox(
        width: double.maxFinite,
        height: 400,
        child: ListView.builder(
          itemCount: stallions.length,
          itemBuilder: (context, index) {
            final s = stallions[index];
            return ListTile(
              leading: const Icon(Icons.star, color: Color(0xFF2E7D32)),
              title: Text(s.name),
              subtitle: Text(s.color ?? ''),
              onTap: () => Navigator.pop(context, s),
            );
          },
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
      ],
    );
  }
}

class _BandMemberPickerDialog extends StatefulWidget {
  final List<Horse> allHorses;
  final Horse stallion;
  final Set<int> preselectedIds;

  const _BandMemberPickerDialog({
    required this.allHorses,
    required this.stallion,
    required this.preselectedIds,
  });

  @override
  State<_BandMemberPickerDialog> createState() =>
      _BandMemberPickerDialogState();
}

class _BandMemberPickerDialogState extends State<_BandMemberPickerDialog> {
  late Set<int> _selected;
  String _search = '';

  @override
  void initState() {
    super.initState();
    _selected = {...widget.preselectedIds};
  }

  @override
  Widget build(BuildContext context) {
    var horses =
        widget.allHorses.where((h) => h.id != widget.stallion.id).toList();

    if (_search.isNotEmpty) {
      final q = _search.toLowerCase();
      horses = horses
          .where((h) =>
              h.name.toLowerCase().contains(q) ||
              (h.color?.toLowerCase().contains(q) ?? false) ||
              (h.brand?.toLowerCase().contains(q) ?? false))
          .toList();
    }

    return AlertDialog(
      title: Text("${widget.stallion.name}'s Band"),
      content: SizedBox(
        width: double.maxFinite,
        height: 500,
        child: Column(
          children: [
            TextField(
              decoration: InputDecoration(
                hintText: 'Search horses...',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8)),
                isDense: true,
              ),
              onChanged: (v) => setState(() => _search = v),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                itemCount: horses.length,
                itemBuilder: (context, index) {
                  final h = horses[index];
                  final selected = _selected.contains(h.id);
                  return CheckboxListTile(
                    value: selected,
                    onChanged: (val) {
                      setState(() {
                        if (val == true) {
                          _selected.add(h.id!);
                        } else {
                          _selected.remove(h.id!);
                        }
                      });
                    },
                    title: Text(h.name),
                    subtitle: Text('${h.color ?? ''} - ${h.sex ?? ''}'),
                    dense: true,
                  );
                },
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, _selected),
          child: Text('Save (${_selected.length} members)'),
        ),
      ],
    );
  }
}
