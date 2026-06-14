class Horse {
  final int? id; // pedigree_id post-cutover (was arbitrary local 1-143)
  final String name;
  final String? nickname;
  final String? color;
  final String? sex;
  final String? brand;
  final String? birthYear;
  final String? birthDate;
  final String? eyeColor;
  final String? auctionPrice;
  final String? buybackDonor;
  final String? sire;
  final String? dam;
  final String? herd;
  final String? notes;
  final String? background; // canon narrative (scrape); supersedes the old book_info
  final String? qrVideoUrl;
  final String? qrPedigreeUrl;
  final int? bookPage;

  // --- §5 enrichment (from the website scrape; null until Phase 2) ---
  final int? sireId;
  final int? damId;
  final String? state; // 'VA' | 'MD'
  final String? coatPattern;
  final String? markings;
  final String? genotype;
  final String? birthLocation;
  final String? breeder;
  final String? owner;
  final String? auctionNumber;
  final String? registry;
  final String? registryNumber;
  final String? dscPhotoUrl;

  // Pedigree-chart flag codes (M/B/F/H); ★ full-sibling is derived, not stored.
  final bool mistyDescendant;
  final bool buyback;
  final bool feral;
  final bool halfChincoteague;

  // Dated observational sub-herd (VA only; MD = null). Overlaid at read time
  // from the canon region snapshot + the user's local override — NOT a column
  // on the horse row in horses_data.json (it lives in the regions[] section).
  final String? region; // 'northern' | 'southern' | null

  Horse({
    this.id,
    required this.name,
    this.nickname,
    this.color,
    this.sex,
    this.brand,
    this.birthYear,
    this.birthDate,
    this.eyeColor,
    this.auctionPrice,
    this.buybackDonor,
    this.sire,
    this.dam,
    this.herd,
    this.notes,
    this.background,
    this.qrVideoUrl,
    this.qrPedigreeUrl,
    this.bookPage,
    this.sireId,
    this.damId,
    this.state,
    this.coatPattern,
    this.markings,
    this.genotype,
    this.birthLocation,
    this.breeder,
    this.owner,
    this.auctionNumber,
    this.registry,
    this.registryNumber,
    this.dscPhotoUrl,
    this.mistyDescendant = false,
    this.buyback = false,
    this.feral = false,
    this.halfChincoteague = false,
    this.region,
  });

  /// Tolerant bool parse: the chart flags arrive as null until the scrape, and
  /// may come back as bool, int (0/1), or string ("1"/"true") depending on source.
  static bool _asBool(dynamic v) {
    if (v == null) return false;
    if (v is bool) return v;
    if (v is num) return v != 0;
    final s = v.toString().toLowerCase();
    return s == 'true' || s == '1' || s == 'yes';
  }

  factory Horse.fromMap(Map<String, dynamic> map) {
    return Horse(
      id: map['id'] as int?,
      name: map['name'] as String,
      nickname: map['nickname'] as String?,
      color: map['color'] as String?,
      sex: map['sex'] as String?,
      brand: map['brand'] as String?,
      birthYear: map['birth_year'] as String?,
      birthDate: map['birth_date'] as String?,
      eyeColor: map['eye_color'] as String?,
      auctionPrice: map['auction_price'] as String?,
      buybackDonor: map['buyback_donor'] as String?,
      sire: map['sire'] as String?,
      dam: map['dam'] as String?,
      herd: map['herd'] as String?,
      notes: map['notes'] as String?,
      background: map['background'] as String?,
      qrVideoUrl: map['qr_video_url'] as String?,
      qrPedigreeUrl: map['qr_pedigree_url'] as String?,
      bookPage: map['book_page'] as int?,
      sireId: map['sire_id'] as int?,
      damId: map['dam_id'] as int?,
      state: map['state'] as String?,
      coatPattern: map['coat_pattern'] as String?,
      markings: map['markings'] as String?,
      genotype: map['genotype'] as String?,
      birthLocation: map['birth_location'] as String?,
      breeder: map['breeder'] as String?,
      owner: map['owner'] as String?,
      auctionNumber: map['auction_number'] as String?,
      registry: map['registry'] as String?,
      registryNumber: map['registry_number'] as String?,
      dscPhotoUrl: map['dsc_photo_url'] as String?,
      mistyDescendant: _asBool(map['misty_descendant']),
      buyback: _asBool(map['buyback']),
      feral: _asBool(map['feral']),
      halfChincoteague: _asBool(map['half_chincoteague']),
      region: map['region'] as String?,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'name': name,
      'nickname': nickname,
      'color': color,
      'sex': sex,
      'brand': brand,
      'birth_year': birthYear,
      'birth_date': birthDate,
      'eye_color': eyeColor,
      'auction_price': auctionPrice,
      'buyback_donor': buybackDonor,
      'sire': sire,
      'dam': dam,
      'herd': herd,
      'notes': notes,
      'background': background,
      'qr_video_url': qrVideoUrl,
      'qr_pedigree_url': qrPedigreeUrl,
      'book_page': bookPage,
      'sire_id': sireId,
      'dam_id': damId,
      'state': state,
      'coat_pattern': coatPattern,
      'markings': markings,
      'genotype': genotype,
      'birth_location': birthLocation,
      'breeder': breeder,
      'owner': owner,
      'auction_number': auctionNumber,
      'registry': registry,
      'registry_number': registryNumber,
      'dsc_photo_url': dscPhotoUrl,
      'misty_descendant': mistyDescendant,
      'buyback': buyback,
      'feral': feral,
      'half_chincoteague': halfChincoteague,
      'region': region,
    };
  }

  Horse copyWith({
    int? id,
    String? name,
    String? nickname,
    String? color,
    String? sex,
    String? brand,
    String? birthYear,
    String? birthDate,
    String? eyeColor,
    String? auctionPrice,
    String? buybackDonor,
    String? sire,
    String? dam,
    String? herd,
    String? notes,
    String? background,
    String? qrVideoUrl,
    String? qrPedigreeUrl,
    int? bookPage,
    int? sireId,
    int? damId,
    String? state,
    String? coatPattern,
    String? markings,
    String? genotype,
    String? birthLocation,
    String? breeder,
    String? owner,
    String? auctionNumber,
    String? registry,
    String? registryNumber,
    String? dscPhotoUrl,
    bool? mistyDescendant,
    bool? buyback,
    bool? feral,
    bool? halfChincoteague,
    String? region,
  }) {
    return Horse(
      id: id ?? this.id,
      name: name ?? this.name,
      nickname: nickname ?? this.nickname,
      color: color ?? this.color,
      sex: sex ?? this.sex,
      brand: brand ?? this.brand,
      birthYear: birthYear ?? this.birthYear,
      birthDate: birthDate ?? this.birthDate,
      eyeColor: eyeColor ?? this.eyeColor,
      auctionPrice: auctionPrice ?? this.auctionPrice,
      buybackDonor: buybackDonor ?? this.buybackDonor,
      sire: sire ?? this.sire,
      dam: dam ?? this.dam,
      herd: herd ?? this.herd,
      notes: notes ?? this.notes,
      background: background ?? this.background,
      qrVideoUrl: qrVideoUrl ?? this.qrVideoUrl,
      qrPedigreeUrl: qrPedigreeUrl ?? this.qrPedigreeUrl,
      bookPage: bookPage ?? this.bookPage,
      sireId: sireId ?? this.sireId,
      damId: damId ?? this.damId,
      state: state ?? this.state,
      coatPattern: coatPattern ?? this.coatPattern,
      markings: markings ?? this.markings,
      genotype: genotype ?? this.genotype,
      birthLocation: birthLocation ?? this.birthLocation,
      breeder: breeder ?? this.breeder,
      owner: owner ?? this.owner,
      auctionNumber: auctionNumber ?? this.auctionNumber,
      registry: registry ?? this.registry,
      registryNumber: registryNumber ?? this.registryNumber,
      dscPhotoUrl: dscPhotoUrl ?? this.dscPhotoUrl,
      mistyDescendant: mistyDescendant ?? this.mistyDescendant,
      buyback: buyback ?? this.buyback,
      feral: feral ?? this.feral,
      halfChincoteague: halfChincoteague ?? this.halfChincoteague,
      region: region ?? this.region,
    );
  }
}

class HorsePhoto {
  final int? id;
  final int horseId;
  final String filename;
  final String source; // 'book' (canon) | 'field' (canon, Kristina) | 'user' (local)
  final String? credit; // e.g. 'K. Kent' for field photos

  HorsePhoto({
    this.id,
    required this.horseId,
    required this.filename,
    this.source = 'book',
    this.credit,
  });

  /// Canon = shipped by us (book or harvested field). 'user' = local-only,
  /// not yet harvested — this is what the provenance accent rule marks.
  bool get isCanon => source != 'user';

  factory HorsePhoto.fromMap(Map<String, dynamic> map) {
    return HorsePhoto(
      id: map['id'] as int?,
      horseId: map['horse_id'] as int,
      filename: map['filename'] as String,
      source: map['source'] as String? ?? 'book',
      credit: map['credit'] as String?,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'horse_id': horseId,
      'filename': filename,
      'source': source,
      if (credit != null) 'credit': credit,
    };
  }
}
