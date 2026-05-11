import 'package:dio/dio.dart';
import 'package:eye_dentify/models/alert_model.dart'; // DetectionData is nested within AlertModel
import '../core/network/api_client.dart';

class DetectionService {
  final ApiClient _apiClient;

  DetectionService(this._apiClient);

  /// Retrieves details for a specific detection by its ID.
  Future<DetectionData> getDetectionById(int id) async {
    try {
      // Assuming an endpoint like /detections/{id} that returns DetectionData
      final response = await _apiClient.get('/detections/$id');

      if (response.statusCode == 200 && response.data != null) {
        // The API should return DetectionData directly or within a structure
        // For this example, we assume it returns DetectionData directly.
        // If DetectionData is nested, adjust accordingly.
        return DetectionData.fromJson(response.data);
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/detections/$id'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ??
              'Failed to retrieve detection details.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Marks a detection as verified or a false positive.
  /// `verified` should be true for verification, false for marking as false positive.
  Future<void> verifyDetection(int detectionId, bool verified) async {
    try {
      // Assuming an endpoint like /detections/{id}/verify
      final response = await _apiClient.post(
        '/detections/$detectionId/verify',
        data: {'verified': verified},
      );

      if (response.statusCode != 200) {
        throw DioException(
          requestOptions:
              RequestOptions(path: '/detections/$detectionId/verify'),
          response: response,
          type: DioExceptionType.badResponse,
          message:
              response.data?['message'] ?? 'Failed to update detection status.',
        );
      }
      // Success, no data to return
    } catch (e) {
      rethrow;
    }
  }

  /// Retrieves all detections associated with a specific missing person case.
  Future<List<DetectionData>> getDetectionsByCase(int missingPersonId) async {
    try {
      // Assuming an endpoint like /missing-persons/{id}/detections
      final response =
          await _apiClient.get('/missing-persons/$missingPersonId/detections');

      if (response.statusCode == 200 && response.data != null) {
        final List<dynamic> data = response.data;
        // Assuming each item in the list is a DetectionData
        return data.map((item) => DetectionData.fromJson(item)).toList();
      } else {
        throw DioException(
          requestOptions: RequestOptions(
              path: '/missing-persons/$missingPersonId/detections'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ??
              'Failed to retrieve detections for the case.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Confirms an alert match after human verification.
  Future<void> confirmMatch(int alertId,
      {Map<String, dynamic>? decisionPayload}) async {
    try {
      final response = await _apiClient.post(
        '/alerts/$alertId/confirm-match',
        data: decisionPayload,
      );
      if (response.statusCode != 200 && response.statusCode != 204) {
        throw DioException(
          requestOptions: RequestOptions(path: '/alerts/$alertId/confirm-match'),
          response: response,
          type: DioExceptionType.badResponse,
          message:
              response.data?['message'] ?? 'Failed to confirm alert match.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Rejects an alert as a false alarm.
  Future<void> rejectMatch(int alertId,
      {Map<String, dynamic>? decisionPayload}) async {
    try {
      final response = await _apiClient.post(
        '/alerts/$alertId/reject-match',
        data: decisionPayload,
      );
      if (response.statusCode != 200 && response.statusCode != 204) {
        throw DioException(
          requestOptions: RequestOptions(path: '/alerts/$alertId/reject-match'),
          response: response,
          type: DioExceptionType.badResponse,
          message:
              response.data?['message'] ?? 'Failed to reject alert match.',
        );
      }
    } catch (e) {
      rethrow;
    }
  }
}
