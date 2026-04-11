import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/data_service.dart';
import '../services/backup_service.dart';
import '../models/horse.dart';
import 'horse_detail_screen.dart';

class HorseListScreen extends StatefulWidget {
  const HorseListScreen({super.key});

  @override
  State<HorseListScreen> createState() => _HorseListScreenState();
}

class _HorseListScreenState extends State<HorseListScreen> {
  final _data = DataService.instance;
  List<Horse> _horses = [];
  List<Horse> _filtered = [];
  List<String> _colors = [];
  // Thumbnail cache: horse id -> image bytes
  final Map<int, Uint8List?> _thumbnails = {};
  String? _selectedColor;
  String? _selectedHerd;
  String _searchQuery = '';
  bool _loading = true;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    _horses = _data.getAllHorses();
    _colors = _horses
        .map((h) => h.color)
        .whereType<String>()
        .toSet()
        .toList()
      ..sort();

    // Load thumbnails
    _thumbnails.clear();
    for (final horse in _horses) {
      final photo = _data.getFirstPhotoForHorse(horse.id!);
      if (photo != null) {
        if (photo.source == 'book') {
          try {
            final bytes =
                await rootBundle.load('assets/photos/${photo.filename}');
            _thumbnails[horse.id!] = bytes.buffer.asUint8List();
          } catch (_) {
            _thumbnails[horse.id!] = null;
          }
        } else {
          _thumbnails[horse.id!] = _data.getUserPhotoBytes(photo.filename);
        }
      }
    }

    _applyFilters();
    setState(() => _loading = false);
  }

  void _applyFilters() {
    var result = _horses;

    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      result = result.where((h) {
        return h.name.toLowerCase().contains(q) ||
            (h.nickname?.toLowerCase().contains(q) ?? false) ||
            (h.color?.toLowerCase().contains(q) ?? false) ||
            (h.brand?.toLowerCase().contains(q) ?? false) ||
            (h.birthYear?.toLowerCase().contains(q) ?? false) ||
            (h.birthDate?.toLowerCase().contains(q) ?? false) ||
            (h.eyeColor?.toLowerCase().contains(q) ?? false) ||
            (h.sex?.toLowerCase().contains(q) ?? false) ||
            (h.sire?.toLowerCase().contains(q) ?? false) ||
            (h.dam?.toLowerCase().contains(q) ?? false) ||
            (h.auctionPrice?.toLowerCase().contains(q) ?? false) ||
            (h.buybackDonor?.toLowerCase().contains(q) ?? false) ||
            (h.herd?.toLowerCase().contains(q) ?? false);
      }).toList();
    }

    if (_selectedColor != null) {
      result = result.where((h) => h.color == _selectedColor).toList();
    }

    if (_selectedHerd != null) {
      result = result.where((h) => h.herd == _selectedHerd).toList();
    }

    setState(() => _filtered = result);
  }

  Color _colorForHorse(String? color) {
    if (color == null) return Colors.grey;
    final c = color.toLowerCase();
    if (c.contains('bay')) return const Color(0xFF8B4513);
    if (c.contains('chestnut')) return const Color(0xFFCD853F);
    if (c.contains('black')) return const Color(0xFF2C2C2C);
    if (c.contains('buckskin')) return const Color(0xFFD2B48C);
    if (c.contains('palomino')) return const Color(0xFFDAA520);
    return Colors.grey;
  }

  Future<void> _showBackupDialog() async {
    final action = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Backup & Restore'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_data.hasUserData())
              const Text(
                  'You have user data (notes, herds, bands, photos) that should be backed up regularly.')
            else
              const Text('No user data to backup yet.'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          OutlinedButton.icon(
            onPressed: () => Navigator.pop(context, 'restore'),
            icon: const Icon(Icons.upload_file),
            label: const Text('Restore'),
          ),
          FilledButton.icon(
            onPressed: _data.hasUserData()
                ? () => Navigator.pop(context, 'backup')
                : null,
            icon: const Icon(Icons.download),
            label: const Text('Backup'),
          ),
        ],
      ),
    );

    if (!mounted || action == null) return;

    if (action == 'backup') {
      final success = await BackupService.instance.saveBackup();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(success ? 'Backup saved!' : 'Backup failed.'),
        ));
      }
    } else if (action == 'restore') {
      final success = await BackupService.instance.restoreBackup();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content:
              Text(success ? 'Data restored!' : 'Restore failed or cancelled.'),
        ));
        if (success) _loadData();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Chincoteague Ponies'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.backup),
            tooltip: 'Backup & Restore',
            onPressed: _showBackupDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search by name, brand, color, year...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          _searchQuery = '';
                          _applyFilters();
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                filled: true,
                fillColor: Colors.grey[100],
              ),
              onChanged: (value) {
                _searchQuery = value;
                _applyFilters();
              },
            ),
          ),

          // Filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                FilterChip(
                  label: Text(_selectedColor ?? 'All Colors'),
                  selected: _selectedColor != null,
                  onSelected: (_) => _showColorPicker(),
                ),
                const SizedBox(width: 8),
                FilterChip(
                  label: Text(_selectedHerd ?? 'All Herds'),
                  selected: _selectedHerd != null,
                  onSelected: (_) => _showHerdPicker(),
                ),
                if (_selectedColor != null || _selectedHerd != null) ...[
                  const SizedBox(width: 8),
                  ActionChip(
                    label: const Text('Clear Filters'),
                    onPressed: () {
                      _selectedColor = null;
                      _selectedHerd = null;
                      _applyFilters();
                    },
                  ),
                ],
              ],
            ),
          ),

          // Count
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '${_filtered.length} ponies',
                style: TextStyle(color: Colors.grey[600], fontSize: 14),
              ),
            ),
          ),

          // Horse list
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : ListView.builder(
                    itemCount: _filtered.length,
                    itemBuilder: (context, index) {
                      final horse = _filtered[index];
                      return _HorseListTile(
                        horse: horse,
                        accentColor: _colorForHorse(horse.color),
                        thumbnailBytes: _thumbnails[horse.id],
                        onTap: () async {
                          await Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => HorseDetailScreen(horse: horse),
                            ),
                          );
                          _loadData();
                        },
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  void _showColorPicker() {
    showModalBottomSheet(
      context: context,
      builder: (context) => ListView(
        children: [
          ListTile(
            title: const Text('All Colors'),
            onTap: () {
              _selectedColor = null;
              _applyFilters();
              Navigator.pop(context);
            },
          ),
          ..._colors.map((color) => ListTile(
                leading: CircleAvatar(
                  backgroundColor: _colorForHorse(color),
                  radius: 12,
                ),
                title: Text(color),
                trailing: Text(
                  '${_horses.where((h) => h.color == color).length}',
                  style: TextStyle(color: Colors.grey[600]),
                ),
                onTap: () {
                  _selectedColor = color;
                  _applyFilters();
                  Navigator.pop(context);
                },
              )),
        ],
      ),
    );
  }

  void _showHerdPicker() {
    showModalBottomSheet(
      context: context,
      builder: (context) => ListView(
        children: [
          ListTile(
            title: const Text('All Herds'),
            onTap: () {
              _selectedHerd = null;
              _applyFilters();
              Navigator.pop(context);
            },
          ),
          ListTile(
            title: const Text('Northern Herd'),
            trailing: Text(
              '${_horses.where((h) => h.herd == 'northern').length}',
              style: TextStyle(color: Colors.grey[600]),
            ),
            onTap: () {
              _selectedHerd = 'northern';
              _applyFilters();
              Navigator.pop(context);
            },
          ),
          ListTile(
            title: const Text('Southern Herd'),
            trailing: Text(
              '${_horses.where((h) => h.herd == 'southern').length}',
              style: TextStyle(color: Colors.grey[600]),
            ),
            onTap: () {
              _selectedHerd = 'southern';
              _applyFilters();
              Navigator.pop(context);
            },
          ),
          ListTile(
            title: const Text('Unassigned'),
            trailing: Text(
              '${_horses.where((h) => h.herd == null).length}',
              style: TextStyle(color: Colors.grey[600]),
            ),
            onTap: () {
              _selectedHerd = null;
              setState(() {
                _filtered = _horses.where((h) => h.herd == null).toList();
              });
              Navigator.pop(context);
            },
          ),
        ],
      ),
    );
  }
}

class _HorseListTile extends StatelessWidget {
  final Horse horse;
  final Color accentColor;
  final Uint8List? thumbnailBytes;
  final VoidCallback onTap;

  const _HorseListTile({
    required this.horse,
    required this.accentColor,
    required this.thumbnailBytes,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: ListTile(
        leading: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircleAvatar(
              backgroundColor: accentColor,
              radius: 18,
              child: Text(
                horse.name[0],
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
            ),
            const SizedBox(width: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: SizedBox(
                width: 36,
                height: 36,
                child: thumbnailBytes != null
                    ? Image.memory(
                        thumbnailBytes!,
                        fit: BoxFit.cover,
                      )
                    : Container(
                        color: accentColor.withValues(alpha: 0.2),
                        child: Icon(Icons.photo, size: 18, color: accentColor),
                      ),
              ),
            ),
          ],
        ),
        title: Text(
          horse.name,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(
          [
            horse.color,
            horse.sex,
            if (horse.herd != null) '${horse.herd} herd',
          ].whereType<String>().join(' - '),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
