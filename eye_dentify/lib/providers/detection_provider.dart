import 'package:flutter/foundation.dart';
import '../models/alert_model.dart';
import '../services/detection_service.dart';

class DetectionProvider extends ChangeNotifier {
  final DetectionService _detectionService;

  DetectionProvider(this._detectionService);

  DetectionData? _selectedDetection;
  bool _isLoading = false;
  String? _errorMessage;

  DetectionData? get selectedDetection => _selectedDetection;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> fetchDetectionById(int id) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _selectedDetection = await _detectionService.getDetectionById(id);
    } catch (e) {
      _errorMessage = 'Failed to load detection details: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> verifyDetection(int detectionId, bool verified) async {
    try {
      await _detectionService.verifyDetection(detectionId, verified);
      // Optimistically update if the selected detection matches
      if (_selectedDetection?.detectionId == detectionId) {
        // We'd ideally need a copyWith method on DetectionData or fetch again.
        // For now, let's re-fetch to ensure data consistency.
        await fetchDetectionById(detectionId);
      }
    } catch (e) {
      _errorMessage = 'Failed to verify detection: $e';
      notifyListeners();
    }
  }

  Future<void> confirmMatch(int alertId,
      {Map<String, dynamic>? decisionPayload}) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _detectionService.confirmMatch(alertId,
          decisionPayload: decisionPayload);
    } catch (e) {
      _errorMessage = 'Failed to confirm match: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> rejectMatch(int alertId,
      {Map<String, dynamic>? decisionPayload}) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _detectionService.rejectMatch(alertId,
          decisionPayload: decisionPayload);
    } catch (e) {
      _errorMessage = 'Failed to reject match: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearSelectedDetection() {
    _selectedDetection = null;
    notifyListeners();
  }
}
