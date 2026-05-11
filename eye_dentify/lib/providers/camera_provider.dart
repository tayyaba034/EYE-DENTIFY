import 'package:flutter/foundation.dart';
import '../models/camera_model.dart';
import '../services/camera_service.dart';

class CameraProvider extends ChangeNotifier {
  final CameraService _cameraService;

  CameraProvider(this._cameraService);

  List<CameraModel> _cameras = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<CameraModel> get cameras => _cameras;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> fetchCameras() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _cameras = await _cameraService.getCameras();
    } catch (e) {
      _errorMessage = 'Failed to fetch cameras: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  int get totalCameras => _cameras.length;
  int get activeCameras => _cameras.where((c) => c.status == 'active').length;
}
