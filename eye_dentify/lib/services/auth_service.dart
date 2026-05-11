import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:eye_dentify/models/user_model.dart';
import '../core/network/api_client.dart';
import 'storage_service.dart';

class AuthService {
  final ApiClient _apiClient;
  final StorageService _storageService;

  AuthService(this._apiClient, this._storageService);

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _apiClient.post(
      '/auth/login',
      data: {
        'email': email,
        'password': password,
      },
    );

    if (response.statusCode == 200 && response.data != null) {
      final userData = response.data['user'] as Map<String, dynamic>;
      final accessToken = response.data['access_token'] as String?;
      final refreshToken = response.data['refresh_token'] as String?;
      if (accessToken == null || refreshToken == null) {
        throw DioException(
          requestOptions: RequestOptions(path: '/auth/login'),
          response: response,
          type: DioExceptionType.badResponse,
          message: 'Missing access_token/refresh_token',
        );
      }
      await _storageService.saveToken(accessToken);
      await _storageService.saveRefreshToken(refreshToken);
      await _storageService.saveUserData(userData);
      return {
        'user': UserModel.fromJson(userData),
        'token': accessToken,
        'refresh_token': refreshToken,
      };
    }

    throw DioException(
      requestOptions: RequestOptions(path: '/auth/login'),
      response: response,
      type: DioExceptionType.badResponse,
      message: response.data?['message'] ?? 'Login failed. Please try again.',
    );
  }

  Future<Map<String, dynamic>> register(
    String email,
    String password,
    String fullName,
    String role, {
    String? phoneNumber,
  }) async {
    final response = await _apiClient.post(
      '/auth/register',
      data: {
        'email': email,
        'password': password,
        'full_name': fullName,
        'role': role,
        if (phoneNumber != null) 'phone_number': phoneNumber,
      },
    );

    if ((response.statusCode == 200 || response.statusCode == 201) &&
        response.data != null) {
      final userData = (response.data['user'] as Map?)?.cast<String, dynamic>();
      final accessToken = response.data['access_token'] as String?;
      final refreshToken = response.data['refresh_token'] as String?;

      if (accessToken != null) {
        await _storageService.saveToken(accessToken);
      }
      if (refreshToken != null) {
        await _storageService.saveRefreshToken(refreshToken);
      }
      if (userData != null) {
        await _storageService.saveUserData(userData);
      }

      if (userData == null) {
        throw DioException(
          requestOptions: RequestOptions(path: '/auth/register'),
          response: response,
          type: DioExceptionType.badResponse,
          message: 'Registration succeeded but no user profile returned.',
        );
      }

      return {
        'user': UserModel.fromJson(userData),
        'token': accessToken,
        'refresh_token': refreshToken,
      };
    }

    throw DioException(
      requestOptions: RequestOptions(path: '/auth/register'),
      response: response,
      type: DioExceptionType.badResponse,
      message:
          response.data?['message'] ?? 'Registration failed. Please try again.',
    );
  }

  Future<void> logout() async {
    try {
      await _apiClient.post('/auth/logout');
    } catch (e) {
      debugPrint('Logout API warning: $e');
    } finally {
      await _storageService.clearAll();
    }
  }

  Future<UserModel?> getCurrentUser() async {
    try {
      return await getMe();
    } catch (e) {
      await _storageService.clearAll();
      debugPrint('Error fetching current user: $e');
      return null;
    }
  }

  Future<UserModel> getMe() async {
    final response = await _apiClient.get('/auth/me');
    if (response.statusCode == 200 && response.data != null) {
      final data = (response.data as Map).cast<String, dynamic>();
      await _storageService.saveUserData(data);
      return UserModel.fromJson(data);
    }
    throw DioException(
      requestOptions: RequestOptions(path: '/auth/me'),
      response: response,
      type: DioExceptionType.badResponse,
      message: response.data?['message'] ?? 'Failed to load current user.',
    );
  }

  Future<String?> refreshToken() async {
    final refreshToken = await _storageService.getRefreshToken();
    if (refreshToken == null) return null;

    final response = await _apiClient.post(
      '/auth/refresh',
      data: {'refresh_token': refreshToken},
    );

    if (response.statusCode == 200 && response.data != null) {
      final accessToken = response.data['access_token'] as String?;
      final nextRefresh = response.data['refresh_token'] as String?;
      if (accessToken != null) {
        await _storageService.saveToken(accessToken);
      }
      if (nextRefresh != null) {
        await _storageService.saveRefreshToken(nextRefresh);
      }
      return accessToken;
    }
    await logout();
    return null;
  }

  Future<void> forgotPassword(String email) async {
    final response = await _apiClient.post(
      '/auth/forgot-password',
      data: {'email': email},
    );

    if (response.statusCode != 200) {
      throw DioException(
        requestOptions: RequestOptions(path: '/auth/forgot-password'),
        response: response,
        type: DioExceptionType.badResponse,
        message: response.data?['message'] ??
            'Failed to send password reset email.',
      );
    }
  }
}
