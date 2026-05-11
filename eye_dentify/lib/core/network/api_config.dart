import 'package:flutter/foundation.dart';

class ApiConfig {
  static String get baseUrl {
    const envBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (envBaseUrl.isNotEmpty) return envBaseUrl;
    if (kDebugMode) return 'http://10.0.2.2:5001/api';
    return 'https://api.eye-dentify.pk/v1';
  }

  static String get webSocketUrl {
    const envWsUrl = String.fromEnvironment('WS_BASE_URL', defaultValue: '');
    if (envWsUrl.isNotEmpty) return envWsUrl;
    if (kDebugMode) return 'ws://10.0.2.2:5001/ws';
    return 'wss://api.eye-dentify.pk/ws';
  }
}
