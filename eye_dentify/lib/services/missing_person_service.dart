import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:eye_dentify/models/missing_person_model.dart';
import '../core/network/api_client.dart';
import 'package:http_parser/http_parser.dart';

class MissingPersonService {
  final ApiClient _apiClient;

  MissingPersonService(this._apiClient);

  /// Uploads multiple photos and returns a list of their URLs.
  /// Optionally provides upload progress via [onProgress] callback (0.0 - 1.0).
  Future<List<String>> uploadPhotos(
    List<File> photos, {
    Function(double)? onProgress,
  }) async {
    try {
      final List<String> uploadedUrls = [];

      for (int i = 0; i < photos.length; i++) {
        final formData = FormData.fromMap({
          'photo': await MultipartFile.fromFile(
            photos[i].path,
            filename: 'photo_${DateTime.now().millisecondsSinceEpoch}_$i.jpg',
            contentType: MediaType('image', 'jpeg'),
          ),
        });

        final response = await _apiClient.post(
          '/missing-persons/upload-photo',
          data: formData,
        );

        // Expecting the API to return the URL in response.data['url']
        if (response.statusCode == 200 && response.data != null) {
          uploadedUrls.add(response.data['url'] as String);
        } else {
          throw DioException(
            requestOptions:
                RequestOptions(path: '/missing-persons/upload-photo'),
            response: response,
            type: DioExceptionType.badResponse,
            message: response.data?['message'] ?? 'Photo upload failed',
          );
        }

        // Report progress if callback provided
        if (onProgress != null) {
          onProgress((i + 1) / photos.length);
        }
      }

      return uploadedUrls;
    } catch (e) {
      debugPrint('Photo upload error: $e');
      rethrow;
    }
  }

  /// Reports a missing person case with associated photo URLs.
  Future<MissingPersonModel> reportMissingPerson(
    MissingPersonModel missingPerson,
    List<String> photoUrls,
  ) async {
    try {
      // Convert model to JSON and inject photo URLs
      final Map<String, dynamic> personData = missingPerson.toJson();
      personData['photos'] = photoUrls;

      final response = await _apiClient.post(
        '/missing-persons',
        data: personData,
      );

      if (response.statusCode == 201 && response.data != null) {
        return MissingPersonModel.fromJson(response.data);
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/missing-persons'),
          response: response,
          type: DioExceptionType.badResponse,
          message:
              response.data?['message'] ?? 'Failed to report missing person',
        );
      }
    } catch (e) {
      debugPrint('Report missing person error: $e');
      rethrow;
    }
  }

  /// Retrieves the list of cases reported by the current user.
  Future<List<MissingPersonModel>> getMyCases() async {
    try {
      final response = await _apiClient.get('/missing-persons/my');

      if (response.statusCode == 200 && response.data != null) {
        final List<dynamic> data = response.data as List<dynamic>;
        return data.map((item) => MissingPersonModel.fromJson(item)).toList();
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/missing-persons/my'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to fetch your cases',
        );
      }
    } catch (e) {
      debugPrint('Get my cases error: $e');
      rethrow;
    }
  }

  /// Retrieves a single case by its ID.
  Future<MissingPersonModel> getCaseById(int id) async {
    try {
      final response = await _apiClient.get('/missing-persons/$id');

      if (response.statusCode == 200 && response.data != null) {
        return MissingPersonModel.fromJson(response.data);
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/missing-persons/$id'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to fetch case details',
        );
      }
    } catch (e) {
      debugPrint('Get case by ID error: $e');
      rethrow;
    }
  }

  /// Updates an existing missing person case.
  Future<MissingPersonModel> updateCase(
    int id,
    MissingPersonModel updatedCase,
  ) async {
    try {
      final response = await _apiClient.put(
        '/missing-persons/$id',
        data: updatedCase.toJson(),
      );

      if (response.statusCode == 200 && response.data != null) {
        return MissingPersonModel.fromJson(response.data);
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/missing-persons/$id'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to update case',
        );
      }
    } catch (e) {
      debugPrint('Update case error: $e');
      rethrow;
    }
  }

  /// Deletes a missing person case.
  Future<void> deleteCase(int id) async {
    try {
      final response = await _apiClient.delete('/missing-persons/$id');

      if (response.statusCode != 200 && response.statusCode != 204) {
        throw DioException(
          requestOptions: RequestOptions(path: '/missing-persons/$id'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to delete case',
        );
      }
    } catch (e) {
      debugPrint('Delete case error: $e');
      rethrow;
    }
  }

  /// Retrieves all active missing person cases (public view).
  Future<List<MissingPersonModel>> getAllActiveCases() async {
    try {
      final response = await _apiClient.get('/missing-persons?status=active');

      if (response.statusCode == 200 && response.data != null) {
        final List<dynamic> data = response.data as List<dynamic>;
        return data.map((item) => MissingPersonModel.fromJson(item)).toList();
      } else {
        throw DioException(
          requestOptions:
              RequestOptions(path: '/missing-persons?status=active'),
          response: response,
          type: DioExceptionType.badResponse,
          message: response.data?['message'] ?? 'Failed to fetch active cases',
        );
      }
    } catch (e) {
      debugPrint('Get all active cases error: $e');
      rethrow;
    }
  }

  Future<String> generateCaseDescription({
    required String name,
    required String age,
    required String gender,
    required String lastSeenLocation,
    required String lastSeenDate,
    required String clothingDescription,
    required String distinguishingFeatures,
  }) async {
    final response = await _apiClient.post(
      '/missing-persons/generate-description',
      data: {
        'name': name,
        'age': age,
        'gender': gender,
        'last_seen_location': lastSeenLocation,
        'last_seen_date': lastSeenDate,
        'clothing_description': clothingDescription,
        'distinguishing_features': distinguishingFeatures,
      },
    );

    if (response.statusCode == 200 && response.data != null) {
      return (response.data['description'] ?? '').toString();
    }
    throw DioException(
      requestOptions: RequestOptions(path: '/missing-persons/generate-description'),
      response: response,
      type: DioExceptionType.badResponse,
      message: response.data?['message'] ?? 'Failed to generate description',
    );
  }
}
