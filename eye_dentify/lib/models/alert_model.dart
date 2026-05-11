import 'enums.dart';

class AlertModel {
  final int alertId;
  final int detectionId;
  final String? userId;
  final DateTime alertTimestamp;
  final String message;
  final String? aiSummary;
  final AlertStatus status;
  final AlertPriority priority;
  final AlertLevel alertLevel;
  final int sightingsCount;
  final DateTime? firstSeenTime;
  final DateTime? lastSeenTime;
  final double? cameraReliabilityScore;
  final DateTime? readTimestamp;
  final DateTime? acknowledgedTimestamp;
  final DetectionData? detection;

  AlertModel({
    required this.alertId,
    required this.detectionId,
    required this.userId,
    required this.alertTimestamp,
    required this.message,
    this.aiSummary,
    required this.status,
    required this.priority,
    this.alertLevel = AlertLevel.preliminary,
    this.sightingsCount = 1,
    this.firstSeenTime,
    this.lastSeenTime,
    this.cameraReliabilityScore,
    this.readTimestamp,
    this.acknowledgedTimestamp,
    this.detection,
  });

  factory AlertModel.fromJson(Map<String, dynamic> json) {
    int _parseInt(dynamic value, {int fallback = 0}) {
      if (value is int) return value;
      if (value is num) return value.toInt();
      if (value is String) return int.tryParse(value) ?? fallback;
      return fallback;
    }

    String? _parseString(dynamic value) {
      if (value == null) return null;
      return value.toString();
    }

    return AlertModel(
      alertId: _parseInt(json['alert_id'] ?? json['id']),
      detectionId: _parseInt(json['detection_id']),
      userId: _parseString(json['user_id']),
      alertTimestamp: DateTime.parse(
          (json['alert_timestamp'] ?? json['created_at']).toString()),
      message: (json['message'] ?? 'Alert detected').toString(),
      aiSummary: json['ai_summary'] as String?,
      status: AlertStatus.fromString(json['status'] as String),
      priority:
          AlertPriority.fromString((json['priority'] ?? 'medium').toString()),
      alertLevel: json['alert_level'] != null
          ? AlertLevel.fromString(json['alert_level'] as String)
          : AlertLevel.preliminary,
      sightingsCount: json['sightings_count'] as int? ?? 1,
      firstSeenTime: json['first_seen_time'] != null
          ? DateTime.parse(json['first_seen_time'] as String)
          : null,
      lastSeenTime: json['last_seen_time'] != null
          ? DateTime.parse(json['last_seen_time'] as String)
          : null,
      cameraReliabilityScore:
          (json['camera_reliability_score'] as num?)?.toDouble(),
      readTimestamp: (json['read_timestamp'] ?? json['read_at']) != null
          ? DateTime.parse((json['read_timestamp'] ?? json['read_at']).toString())
          : null,
      acknowledgedTimestamp:
          (json['acknowledged_timestamp'] ?? json['acknowledged_at']) != null
          ? DateTime.parse(
              (json['acknowledged_timestamp'] ?? json['acknowledged_at'])
                  .toString())
          : null,
      detection: json['detection'] != null
          ? DetectionData.fromJson(json['detection'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'alert_id': alertId,
      'detection_id': detectionId,
      'user_id': userId,
      'alert_timestamp': alertTimestamp.toIso8601String(),
      'message': message,
      'ai_summary': aiSummary,
      'status': status.name,
      'priority': priority.name,
      'alert_level': alertLevel.name,
      'sightings_count': sightingsCount,
      'first_seen_time': firstSeenTime?.toIso8601String(),
      'last_seen_time': lastSeenTime?.toIso8601String(),
      'camera_reliability_score': cameraReliabilityScore,
      'read_timestamp': readTimestamp?.toIso8601String(),
      'acknowledged_timestamp': acknowledgedTimestamp?.toIso8601String(),
      if (detection != null) 'detection': detection!.toJson(),
    };
  }

  AlertModel copyWith({
    int? alertId,
    int? detectionId,
    String? userId,
    DateTime? alertTimestamp,
    String? message,
    String? aiSummary,
    AlertStatus? status,
    AlertPriority? priority,
    AlertLevel? alertLevel,
    int? sightingsCount,
    DateTime? firstSeenTime,
    DateTime? lastSeenTime,
    double? cameraReliabilityScore,
    DateTime? readTimestamp,
    DateTime? acknowledgedTimestamp,
    DetectionData? detection,
  }) {
    return AlertModel(
      alertId: alertId ?? this.alertId,
      detectionId: detectionId ?? this.detectionId,
      userId: userId ?? this.userId,
      alertTimestamp: alertTimestamp ?? this.alertTimestamp,
      message: message ?? this.message,
      aiSummary: aiSummary ?? this.aiSummary,
      status: status ?? this.status,
      priority: priority ?? this.priority,
      alertLevel: alertLevel ?? this.alertLevel,
      sightingsCount: sightingsCount ?? this.sightingsCount,
      firstSeenTime: firstSeenTime ?? this.firstSeenTime,
      lastSeenTime: lastSeenTime ?? this.lastSeenTime,
      cameraReliabilityScore:
          cameraReliabilityScore ?? this.cameraReliabilityScore,
      readTimestamp: readTimestamp ?? this.readTimestamp,
      acknowledgedTimestamp:
          acknowledgedTimestamp ?? this.acknowledgedTimestamp,
      detection: detection ?? this.detection,
    );
  }
}

class DetectionData {
  final int detectionId;
  final String personName;
  final String cameraLocation;
  final String? cameraId;
  final String? trackId;
  final double? latitude;
  final double? longitude;
  final double faceMatchScore;
  final double? colorMatchScore;
  final double? heightMatchScore;
  final double combinedScore;
  final String? snapshotUrl;
  final String? originalPhotoUrl;
  final bool verified;
  final DateTime detectionTimestamp;

  DetectionData({
    required this.detectionId,
    required this.personName,
    required this.cameraLocation,
    this.cameraId,
    this.trackId,
    this.latitude,
    this.longitude,
    required this.faceMatchScore,
    this.colorMatchScore,
    this.heightMatchScore,
    required this.combinedScore,
    this.snapshotUrl,
    this.originalPhotoUrl,
    this.verified = false,
    required this.detectionTimestamp,
  });

  factory DetectionData.fromJson(Map<String, dynamic> json) {
    return DetectionData(
      detectionId: json['detection_id'] as int,
      personName: json['person_name'] as String,
      cameraLocation: json['camera_location'] as String,
      cameraId: json['camera_id']?.toString(),
      trackId: json['track_id']?.toString(),
      latitude: json['latitude']?.toDouble(),
      longitude: json['longitude']?.toDouble(),
      faceMatchScore: (json['face_match_score'] as num).toDouble(),
      colorMatchScore: json['color_match_score']?.toDouble(),
      heightMatchScore: json['height_match_score']?.toDouble(),
      combinedScore: (json['combined_score'] as num).toDouble(),
      snapshotUrl: json['snapshot_url'] as String?,
      originalPhotoUrl: json['original_photo_url'] as String?,
      verified: json['verified'] as bool? ?? false,
      detectionTimestamp: DateTime.parse(json['detection_timestamp'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'detection_id': detectionId,
      'person_name': personName,
      'camera_location': cameraLocation,
      'camera_id': cameraId,
      'track_id': trackId,
      'latitude': latitude,
      'longitude': longitude,
      'face_match_score': faceMatchScore,
      'color_match_score': colorMatchScore,
      'height_match_score': heightMatchScore,
      'combined_score': combinedScore,
      'snapshot_url': snapshotUrl,
      'original_photo_url': originalPhotoUrl,
      'verified': verified,
      'detection_timestamp': detectionTimestamp.toIso8601String(),
    };
  }
}
