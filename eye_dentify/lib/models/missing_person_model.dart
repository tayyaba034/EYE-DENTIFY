import 'enums.dart';

class MissingPersonModel {
  final int? missingPersonId;
  final String userId;
  final String fullName;
  final int? age;
  final Gender? gender;
  final double? heightCm;
  final double? heightRangeMin;
  final double? heightRangeMax;
  final String? lastSeenLocation;
  final DateTime? lastSeenDatetime;
  final String? clothingDescription;
  final String? additionalNotes;
  final CaseStatus status;
  final List<String>? photos;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  MissingPersonModel({
    this.missingPersonId,
    required this.userId,
    required this.fullName,
    this.age,
    this.gender,
    this.heightCm,
    this.heightRangeMin,
    this.heightRangeMax,
    this.lastSeenLocation,
    this.lastSeenDatetime,
    this.clothingDescription,
    this.additionalNotes,
    this.status = CaseStatus.active,
    this.photos,
    this.createdAt,
    this.updatedAt,
  });

  factory MissingPersonModel.fromJson(Map<String, dynamic> json) {
    int? _parseNullableInt(dynamic value) {
      if (value == null) return null;
      if (value is int) return value;
      if (value is num) return value.toInt();
      if (value is String) return int.tryParse(value);
      return null;
    }

    return MissingPersonModel(
      missingPersonId: _parseNullableInt(json['missing_person_id'] ?? json['id']),
      userId: (json['user_id'] ?? json['userId'] ?? '').toString(),
      fullName: json['full_name'] as String,
      age: json['age'] as int?,
      gender: json['gender'] != null
          ? Gender.fromString(json['gender'] as String)
          : null,
      heightCm: json['height_cm']?.toDouble(),
      heightRangeMin: json['height_range_min']?.toDouble(),
      heightRangeMax: json['height_range_max']?.toDouble(),
      lastSeenLocation: json['last_seen_location'] as String?,
      lastSeenDatetime: json['last_seen_datetime'] != null
          ? DateTime.parse(json['last_seen_datetime'] as String)
          : null,
      clothingDescription: json['clothing_description'] as String?,
      additionalNotes: json['additional_notes'] as String?,
      status: CaseStatus.fromString(json['status'] as String? ?? 'active'),
      photos: json['photos'] != null
          ? List<String>.from(json['photos'] as List)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (missingPersonId != null) 'missing_person_id': missingPersonId,
      'user_id': userId,
      'full_name': fullName,
      'age': age,
      'gender': gender?.name,
      'height_cm': heightCm,
      'height_range_min': heightRangeMin,
      'height_range_max': heightRangeMax,
      'last_seen_location': lastSeenLocation,
      'last_seen_datetime': lastSeenDatetime?.toIso8601String(),
      'clothing_description': clothingDescription,
      'additional_notes': additionalNotes,
      'status': status.name,
      if (photos != null) 'photos': photos,
    };
  }

  MissingPersonModel copyWith({
    int? missingPersonId,
    String? userId,
    String? fullName,
    int? age,
    Gender? gender,
    double? heightCm,
    double? heightRangeMin,
    double? heightRangeMax,
    String? lastSeenLocation,
    DateTime? lastSeenDatetime,
    String? clothingDescription,
    String? additionalNotes,
    CaseStatus? status,
    List<String>? photos,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return MissingPersonModel(
      missingPersonId: missingPersonId ?? this.missingPersonId,
      userId: userId ?? this.userId,
      fullName: fullName ?? this.fullName,
      age: age ?? this.age,
      gender: gender ?? this.gender,
      heightCm: heightCm ?? this.heightCm,
      heightRangeMin: heightRangeMin ?? this.heightRangeMin,
      heightRangeMax: heightRangeMax ?? this.heightRangeMax,
      lastSeenLocation: lastSeenLocation ?? this.lastSeenLocation,
      lastSeenDatetime: lastSeenDatetime ?? this.lastSeenDatetime,
      clothingDescription: clothingDescription ?? this.clothingDescription,
      additionalNotes: additionalNotes ?? this.additionalNotes,
      status: status ?? this.status,
      photos: photos ?? this.photos,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
