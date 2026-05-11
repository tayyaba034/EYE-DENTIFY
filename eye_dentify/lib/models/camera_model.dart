class CameraModel {
  final String id;
  final String location;
  final String status;
  final double latitude;
  final double longitude;
  final String type;
  final String? name;

  CameraModel({
    required this.id,
    required this.location,
    required this.status,
    required this.latitude,
    required this.longitude,
    required this.type,
    this.name,
  });

  factory CameraModel.fromJson(Map<String, dynamic> json) {
    return CameraModel(
      id: json['id'].toString(),
      location: (json['location'] ?? 'Unknown').toString(),
      status: (json['status'] ?? 'inactive').toString(),
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0,
      type: (json['type'] ?? json['name'] ?? 'Camera').toString(),
      name: json['name']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'location': location,
      'status': status,
      'latitude': latitude,
      'longitude': longitude,
      'type': type,
      'name': name,
    };
  }
}
