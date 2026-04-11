class BandEntry {
  final int? id;
  final int horseId;
  final int stallionId;
  final String dateRecorded;

  BandEntry({
    this.id,
    required this.horseId,
    required this.stallionId,
    required this.dateRecorded,
  });

  factory BandEntry.fromMap(Map<String, dynamic> map) {
    return BandEntry(
      id: map['id'] as int?,
      horseId: map['horse_id'] as int,
      stallionId: map['stallion_id'] as int,
      dateRecorded: map['date_recorded'] as String,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'horse_id': horseId,
      'stallion_id': stallionId,
      'date_recorded': dateRecorded,
    };
  }
}

/// A resolved view of a band member with the horse's name/details.
class BandMember {
  final int horseId;
  final String name;
  final String? sex;
  final String? color;
  final String dateRecorded;

  BandMember({
    required this.horseId,
    required this.name,
    this.sex,
    this.color,
    required this.dateRecorded,
  });
}
