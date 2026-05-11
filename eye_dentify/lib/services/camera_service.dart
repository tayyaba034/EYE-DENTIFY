import 'package:dio/dio.dart';
import '../core/network/api_client.dart';
import '../models/camera_model.dart';

class CameraService {
  final ApiClient _apiClient;

  CameraService(this._apiClient);

  Future<List<CameraModel>> getCameras() async {
    final response = await _apiClient.get('/cameras');
    if (response.statusCode == 200 && response.data != null) {
      final List<dynamic> data = response.data;
      return data.map((json) => CameraModel.fromJson(json)).toList();
    }
    _throwCameraError('/cameras', response);
  }

  Future<CameraModel> getCameraById(String id) async {
    final response = await _apiClient.get('/cameras/$id');
    if (response.statusCode == 200 && response.data != null) {
      return CameraModel.fromJson(response.data);
    }
    _throwCameraError('/cameras/$id', response);
  }

  Future<CameraModel> createCamera(Map<String, dynamic> payload) async {
    final response = await _apiClient.post('/cameras', data: payload);
    if ((response.statusCode == 200 || response.statusCode == 201) &&
        response.data != null) {
      return CameraModel.fromJson(response.data);
    }
    _throwCameraError('/cameras', response);
  }

  Future<CameraModel> updateCamera(String id, Map<String, dynamic> payload) async {
    final response = await _apiClient.put('/cameras/$id', data: payload);
    if (response.statusCode == 200 && response.data != null) {
      return CameraModel.fromJson(response.data);
    }
    _throwCameraError('/cameras/$id', response);
  }

  Future<void> deleteCamera(String id) async {
    final response = await _apiClient.delete('/cameras/$id');
    if (response.statusCode == 200 || response.statusCode == 204) return;
    _throwCameraError('/cameras/$id', response);
  }

  Never _throwCameraError(String path, Response response) {
    if (response.statusCode == 403) {
      throw DioException(
        requestOptions: RequestOptions(path: path),
        response: response,
        type: DioExceptionType.badResponse,
        message: 'Insufficient role for camera operation (403).',
      );
    }
    throw DioException(
      requestOptions: RequestOptions(path: path),
      response: response,
      type: DioExceptionType.badResponse,
      message: response.data?['message'] ?? 'Camera API request failed',
    );
  }
}
