import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../core/network/api_config.dart';
import '../core/network/websocket_client.dart';
import '../models/missing_person_model.dart';
import '../services/missing_person_service.dart';

class MissingPersonProvider extends ChangeNotifier {
  final MissingPersonService _missingPersonService;
  final WebSocketClient _webSocketClient;
  StreamSubscription<dynamic>? _socketSubscription;
  bool _realtimeInitialized = false;

  MissingPersonProvider(this._missingPersonService,
      {WebSocketClient? webSocketClient})
      : _webSocketClient =
            webSocketClient ?? WebSocketClient(ApiConfig.webSocketUrl);

  // State variables
  List<MissingPersonModel> _myCases = [];
  List<MissingPersonModel> _activeCases = [];
  MissingPersonModel? _selectedCase;
  bool _isLoading = false;
  String? _errorMessage;
  double _uploadProgress = 0.0;

  // Getters
  List<MissingPersonModel> get myCases => _myCases;
  List<MissingPersonModel> get activeCases => _activeCases;
  MissingPersonModel? get selectedCase => _selectedCase;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  double get uploadProgress => _uploadProgress;

  // Fetch cases reported by the current user
  Future<void> fetchMyCases() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _myCases = await _missingPersonService.getMyCases();
    } catch (e) {
      _errorMessage = 'Failed to load your cases: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Fetch all active public cases (Help Someone feature)
  Future<void> fetchActiveCases() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _activeCases = await _missingPersonService.getAllActiveCases();
    } catch (e) {
      _errorMessage = 'Failed to load active cases: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void initializeRealtime() {
    if (_realtimeInitialized) return;
    _realtimeInitialized = true;
    _webSocketClient.connect();
    _socketSubscription = _webSocketClient.stream.listen(
      _handleSocketMessage,
      onError: (error) {
        debugPrint('Case socket error: $error');
      },
      onDone: () {
        debugPrint('Case socket disconnected.');
      },
    );
  }

  void _handleSocketMessage(dynamic data) {
    try {
      dynamic decoded = data;
      if (data is String) {
        decoded = jsonDecode(data);
      }

      if (decoded is Map<String, dynamic>) {
        final type = decoded['type'];
        final payload = decoded['payload'];

        if (type == 'case_created' || type == 'case_updated') {
          final caseJson = payload is Map<String, dynamic>
              ? payload['case'] ?? payload
              : null;
          if (caseJson is Map<String, dynamic>) {
            _upsertCase(MissingPersonModel.fromJson(caseJson));
          }
        } else if (type == 'case_deleted') {
          final caseId = payload is Map<String, dynamic>
              ? payload['missing_person_id']
              : decoded['missing_person_id'];
          if (caseId is int) {
            _removeCase(caseId);
          }
        }
      }
    } catch (e) {
      debugPrint('Case socket parse error: $e');
    }
  }

  void _upsertCase(MissingPersonModel updatedCase) {
    final index = _myCases
        .indexWhere((c) => c.missingPersonId == updatedCase.missingPersonId);
    if (index == -1) {
      _myCases.insert(0, updatedCase);
    } else {
      _myCases[index] = updatedCase;
    }

    final activeIndex = _activeCases.indexWhere(
        (c) => c.missingPersonId == updatedCase.missingPersonId);
    if (updatedCase.status.name == 'active') {
      if (activeIndex == -1) {
        _activeCases.insert(0, updatedCase);
      } else {
        _activeCases[activeIndex] = updatedCase;
      }
    } else if (activeIndex != -1) {
      _activeCases.removeAt(activeIndex);
    }

    notifyListeners();
  }

  void _removeCase(int caseId) {
    _myCases.removeWhere((c) => c.missingPersonId == caseId);
    _activeCases.removeWhere((c) => c.missingPersonId == caseId);
    notifyListeners();
  }

  // Fetch a single case by its ID
  Future<void> fetchCaseById(int id) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _selectedCase = await _missingPersonService.getCaseById(id);
    } catch (e) {
      _errorMessage = 'Failed to load case details: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Report a new missing person case
  Future<bool> reportMissingPerson({
    required MissingPersonModel missingPerson,
    required List<File> photos,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    _uploadProgress = 0.0;
    notifyListeners();

    try {
      // Upload photos and get their URLs
      final photoUrls = await _missingPersonService.uploadPhotos(
        photos,
        onProgress: (progress) {
          _uploadProgress = progress;
          notifyListeners();
        },
      );

      // Create the case with the uploaded photo URLs
      final createdCase = await _missingPersonService.reportMissingPerson(
        missingPerson,
        photoUrls,
      );

      // Add the new case to the local list
      _myCases.insert(0, createdCase);
      _isLoading = false;
      _uploadProgress = 0.0;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      _uploadProgress = 0.0;
      _errorMessage = 'Failed to report missing person: $e';
      notifyListeners();
      return false;
    }
  }

  // Update an existing case
  Future<bool> updateCase(int id, MissingPersonModel updatedCase) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final updated = await _missingPersonService.updateCase(id, updatedCase);
      // Update local list
      final index = _myCases.indexWhere((c) => c.missingPersonId == id);
      if (index != -1) {
        _myCases[index] = updated;
      }
      _selectedCase = updated;
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'Failed to update case: $e';
      notifyListeners();
      return false;
    }
  }

  // Delete a case
  Future<bool> deleteCase(int id) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _missingPersonService.deleteCase(id);
      _myCases.removeWhere((c) => c.missingPersonId == id);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'Failed to delete case: $e';
      notifyListeners();
      return false;
    }
  }

  // Clear any error message
  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  // Clear the selected case
  void clearSelectedCase() {
    _selectedCase = null;
    notifyListeners();
  }

  Future<String?> generateCaseDescription({
    required String name,
    required String age,
    required String gender,
    required String lastSeenLocation,
    required String lastSeenDate,
    required String clothingDescription,
    required String distinguishingFeatures,
  }) async {
    try {
      _errorMessage = null;
      notifyListeners();
      return await _missingPersonService.generateCaseDescription(
        name: name,
        age: age,
        gender: gender,
        lastSeenLocation: lastSeenLocation,
        lastSeenDate: lastSeenDate,
        clothingDescription: clothingDescription,
        distinguishingFeatures: distinguishingFeatures,
      );
    } catch (e) {
      _errorMessage = 'Failed to generate description: $e';
      notifyListeners();
      return null;
    }
  }

  @override
  void dispose() {
    _socketSubscription?.cancel();
    _webSocketClient.disconnect();
    super.dispose();
  }
}
