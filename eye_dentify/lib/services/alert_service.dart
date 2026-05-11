import 'package:dio/dio.dart';
import '../core/network/api_client.dart';
import '../models/alert_model.dart';

class AlertService {
  final ApiClient _apiClient;

  AlertService(this._apiClient);

  /// Retrieves a list of alerts for the current user.
  Future<List<AlertModel>> getMyAlerts() async {
    try {
      final response = await _apiClient.get('/alerts/my');

      if (response.statusCode == 200 && response.data != null) {
        final List<dynamic> data = response.data;
        return data.map((item) => AlertModel.fromJson(item)).toList();
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/alerts/my'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to retrieve alerts.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Marks a specific alert as read.
  Future<AlertModel> markAsRead(int alertId) async {
    try {
      final response = await _apiClient.patch('/alerts/$alertId/read');

      if (response.statusCode == 200 && response.data != null) {
        return AlertModel.fromJson(response.data);
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/alerts/$alertId/read'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to mark alert as read.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Acknowledges an alert.
  Future<AlertModel> acknowledgeAlert(int alertId) async {
    try {
      final response = await _apiClient.patch('/alerts/$alertId/acknowledge');

      if (response.statusCode == 200 && response.data != null) {
        return AlertModel.fromJson(response.data);
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/alerts/$alertId/acknowledge'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to acknowledge alert.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Dismisses an alert (marks as false alarm).
  Future<AlertModel> dismissAlert(int alertId) async {
    try {
      final response = await _apiClient.patch('/alerts/$alertId/dismiss');

      if (response.statusCode == 200 && response.data != null) {
        return AlertModel.fromJson(response.data);
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/alerts/$alertId/dismiss'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to dismiss alert.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Retrieves details for a specific alert by its ID.
  Future<AlertModel> getAlertById(int id) async {
    try {
      final response = await _apiClient.get('/alerts/$id');

      if (response.statusCode == 200 && response.data != null) {
        return AlertModel.fromJson(response.data);
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/alerts/$id'),
          response: response,
          type: DioExceptionType.badResponse,
          message:
              response.data?['message'] ?? 'Failed to retrieve alert details.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Retrieves a ground-truth snapshot of alerts for reconciliation.
  Future<List<AlertModel>> getAlertsSnapshot() async {
    try {
      final response = await _apiClient.get('/alerts/snapshot');
      if (response.statusCode == 200 && response.data != null) {
        final List<dynamic> data = response.data as List<dynamic>;
        return data.map((item) => AlertModel.fromJson(item)).toList();
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/alerts/snapshot'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ??
              'Failed to retrieve alerts snapshot.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }
}
