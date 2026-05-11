import 'enums.dart';

class UserModel {
  final String userId;
  final String email;
  final String fullName;
  final String? phoneNumber;
  final UserRole role;
  final String? profileImage;
  final DateTime createdAt;
  final DateTime? lastLogin;

  UserModel({
    required this.userId,
    required this.email,
    required this.fullName,
    this.phoneNumber,
    required this.role,
    this.profileImage,
    required this.createdAt,
    this.lastLogin,
  });

  // From JSON
  factory UserModel.fromJson(Map<String, dynamic> json) {
    final rawUserId = json['user_id'] ?? json['id'];
    final rawCreatedAt = json['created_at'];
    final rawLastLogin = json['last_login'];

    return UserModel(
      userId: rawUserId?.toString() ?? '',
      email: (json['email'] ?? '').toString(),
      fullName: (json['full_name'] ?? json['fullName'] ?? '').toString(),
      phoneNumber: json['phone_number'] as String?,
      role: UserRole.fromString((json['role'] ?? 'user').toString()),
      profileImage: json['profile_image'] as String?,
      createdAt: rawCreatedAt != null
          ? DateTime.parse(rawCreatedAt.toString())
          : DateTime.now(),
      lastLogin:
          rawLastLogin != null ? DateTime.parse(rawLastLogin.toString()) : null,
    );
  }

  // To JSON
  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'email': email,
      'full_name': fullName,
      'phone_number': phoneNumber,
      'role': role.name,
      'profile_image': profileImage,
      'created_at': createdAt.toIso8601String(),
      'last_login': lastLogin?.toIso8601String(),
    };
  }

  // Copy with
  UserModel copyWith({
    String? userId,
    String? email,
    String? fullName,
    String? phoneNumber,
    UserRole? role,
    String? profileImage,
    DateTime? createdAt,
    DateTime? lastLogin,
  }) {
    return UserModel(
      userId: userId ?? this.userId,
      email: email ?? this.email,
      fullName: fullName ?? this.fullName,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      role: role ?? this.role,
      profileImage: profileImage ?? this.profileImage,
      createdAt: createdAt ?? this.createdAt,
      lastLogin: lastLogin ?? this.lastLogin,
    );
  }

  @override
  String toString() {
    return 'UserModel(userId: $userId, email: $email, fullName: $fullName, role: ${role.displayName})';
  }
}
