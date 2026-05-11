// User Role Enum
enum UserRole {
  guardian,
  security,
  admin;

  String get displayName {
    switch (this) {
      case UserRole.guardian:
        return 'Guardian';
      case UserRole.security:
        return 'Security Personnel';
      case UserRole.admin:
        return 'Administrator';
    }
  }

  static UserRole fromString(String value) {
    return UserRole.values.firstWhere(
      (role) => role.name == value.toLowerCase(),
      orElse: () => UserRole.guardian,
    );
  }
}

// Case Status Enum
enum CaseStatus {
  active,
  found,
  closed;

  String get displayName {
    switch (this) {
      case CaseStatus.active:
        return 'Active';
      case CaseStatus.found:
        return 'Found';
      case CaseStatus.closed:
        return 'Closed';
    }
  }

  static CaseStatus fromString(String value) {
    return CaseStatus.values.firstWhere(
      (status) => status.name == value.toLowerCase(),
      orElse: () => CaseStatus.active,
    );
  }
}

// Alert Status Enum
enum AlertStatus {
  sent,
  read,
  acknowledged,
  dismissed;

  String get displayName {
    switch (this) {
      case AlertStatus.sent:
        return 'New';
      case AlertStatus.read:
        return 'Read';
      case AlertStatus.acknowledged:
        return 'Acknowledged';
      case AlertStatus.dismissed:
        return 'Dismissed';
    }
  }

  static AlertStatus fromString(String value) {
    return AlertStatus.values.firstWhere(
      (status) => status.name == value.toLowerCase(),
      orElse: () => AlertStatus.sent,
    );
  }
}

// AI Verification State Enum
enum VerificationState {
  preliminary,
  pendingVerification,
  confirmedMatch,
  needsReview,
  rejectedFalseAlarm,
  cloudTimeout;

  String get displayName {
    switch (this) {
      case VerificationState.preliminary:
        return 'Preliminary';
      case VerificationState.pendingVerification:
        return 'Verifying';
      case VerificationState.confirmedMatch:
        return 'Confirmed';
      case VerificationState.needsReview:
        return 'Needs Review';
      case VerificationState.rejectedFalseAlarm:
        return 'Cleared';
      case VerificationState.cloudTimeout:
        return 'Cloud Delay';
    }
  }
}

// System Status Enum
enum SystemStatus {
  operational,
  cloudDelay,
  offline;

  String get displayName {
    switch (this) {
      case SystemStatus.operational:
        return 'Operational';
      case SystemStatus.cloudDelay:
        return 'Cloud Delay';
      case SystemStatus.offline:
        return 'Offline';
    }
  }
}

// Alert Priority Enum
enum AlertPriority {
  critical,
  high,
  medium,
  low;

  String get displayName {
    switch (this) {
      case AlertPriority.critical:
        return 'Critical Priority';
      case AlertPriority.high:
        return 'High Priority';
      case AlertPriority.medium:
        return 'Medium Priority';
      case AlertPriority.low:
        return 'Low Priority';
    }
  }

  static AlertPriority fromString(String value) {
    return AlertPriority.values.firstWhere(
      (priority) => priority.name == value.toLowerCase(),
      orElse: () => AlertPriority.medium,
    );
  }
}

// Alert Escalation Level
enum AlertLevel {
  preliminary,
  tracking,
  strongMatch,
  critical;

  String get displayName {
    switch (this) {
      case AlertLevel.preliminary:
        return 'Preliminary';
      case AlertLevel.tracking:
        return 'Tracking';
      case AlertLevel.strongMatch:
        return 'Strong Match';
      case AlertLevel.critical:
        return 'Critical';
    }
  }

  static AlertLevel fromString(String value) {
    return AlertLevel.values.firstWhere(
      (level) => level.name.toLowerCase() == value.toLowerCase(),
      orElse: () => AlertLevel.preliminary,
    );
  }
}

// Gender Enum
enum Gender {
  male,
  female,
  other;

  String get displayName {
    switch (this) {
      case Gender.male:
        return 'Male';
      case Gender.female:
        return 'Female';
      case Gender.other:
        return 'Other';
    }
  }

  static Gender fromString(String value) {
    return Gender.values.firstWhere(
      (gender) => gender.name == value.toLowerCase(),
      orElse: () => Gender.other,
    );
  }
}
