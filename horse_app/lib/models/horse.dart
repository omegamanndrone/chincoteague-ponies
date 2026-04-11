class Horse {
  final int? id;
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
  final String? bookInfo;
  final String? qrVideoUrl;
  final String? qrPedigreeUrl;
  final int? bookPage;

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
    this.bookInfo,
    this.qrVideoUrl,
    this.qrPedigreeUrl,
    this.bookPage,
  });

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
      bookInfo: map['book_info'] as String?,
      qrVideoUrl: map['qr_video_url'] as String?,
      qrPedigreeUrl: map['qr_pedigree_url'] as String?,
      bookPage: map['book_page'] as int?,
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
      'book_info': bookInfo,
      'qr_video_url': qrVideoUrl,
      'qr_pedigree_url': qrPedigreeUrl,
      'book_page': bookPage,
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
    String? bookInfo,
    String? qrVideoUrl,
    String? qrPedigreeUrl,
    int? bookPage,
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
      bookInfo: bookInfo ?? this.bookInfo,
      qrVideoUrl: qrVideoUrl ?? this.qrVideoUrl,
      qrPedigreeUrl: qrPedigreeUrl ?? this.qrPedigreeUrl,
      bookPage: bookPage ?? this.bookPage,
    );
  }
}

class HorsePhoto {
  final int? id;
  final int horseId;
  final String filename;
  final String source; // 'book' or 'user'

  HorsePhoto({
    this.id,
    required this.horseId,
    required this.filename,
    this.source = 'book',
  });

  factory HorsePhoto.fromMap(Map<String, dynamic> map) {
    return HorsePhoto(
      id: map['id'] as int?,
      horseId: map['horse_id'] as int,
      filename: map['filename'] as String,
      source: map['source'] as String? ?? 'book',
    );
  }

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'horse_id': horseId,
      'filename': filename,
      'source': source,
    };
  }
}
