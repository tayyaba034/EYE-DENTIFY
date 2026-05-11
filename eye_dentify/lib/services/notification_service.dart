import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../core/network/api_client.dart';

class NotificationService {
  final ApiClient _apiClient;

  NotificationService(this._apiClient);

  Future<void> registerDeviceToken(String token) async {
    try {
      await _apiClient.post(
        '/notifications/device-token',
        data: {'token': token},
      );
    } catch (e) {
      debugPrint('Error registering device token: $e');
    }
  }

  Future<List<Map<String, dynamic>>> getNotifications() async {
    final response = await _apiClient.get('/notifications');
    if (response.statusCode == 200 && response.data != null) {
      return (response.data as List<dynamic>)
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
    }
    throw DioException(
      requestOptions: RequestOptions(path: '/notifications'),
      response: response,
      type: DioExceptionType.badResponse,
      message: response.data?['message'] ?? 'Failed to fetch notifications',
    );
  }

  Future<Map<String, dynamic>> markAsRead(String notificationId) async {
    final response = await _apiClient.patch('/notifications/$notificationId/read');
    if (response.statusCode == 200 && response.data != null) {
      return Map<String, dynamic>.from(response.data as Map);
    }
    throw DioException(
      requestOptions: RequestOptions(path: '/notifications/$notificationId/read'),
      response: response,
      type: DioExceptionType.badResponse,
      message: response.data?['message'] ?? 'Failed to mark notification read',
    );
  }
}
