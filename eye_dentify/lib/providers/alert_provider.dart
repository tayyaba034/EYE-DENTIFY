import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import '../core/network/api_config.dart';
import '../core/network/websocket_client.dart';
import '../models/alert_model.dart';
import '../models/enums.dart';
import '../services/alert_service.dart';

class AlertProvider extends ChangeNotifier with WidgetsBindingObserver {
  final AlertService _alertService;
  final WebSocketClient _webSocketClient;
  StreamSubscription<dynamic>? _socketSubscription;
  StreamController<List<AlertModel>>? _alertsStreamController;
  bool _isRealtimeConnected = false;
  String? _realtimeError;
  bool _realtimeInitialized = false;
  Timer? _snapshotTimer;
  Timer? _snapshotRetryTimer;
  Duration _snapshotRetryDelay = const Duration(seconds: 5);
  bool _isSnapshotSyncing = false;
  DateTime? _lastSnapshotSync;
  final Map<String, List<_DetectionObservation>> _trackObservations = {};
  final Map<int, _PendingDecision> _pendingDecisions = {};
  Timer? _lowPriorityEmitTimer;

  AlertProvider(this._alertService, {WebSocketClient? webSocketClient})
      : _webSocketClient =
            webSocketClient ?? WebSocketClient(ApiConfig.webSocketUrl);

  List<AlertModel> _alerts = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<AlertModel> get alerts => _alerts;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isRealtimeConnected => _isRealtimeConnected;
  String? get realtimeError => _realtimeError;
  bool get isSnapshotSyncing => _isSnapshotSyncing;
  DateTime? get lastSnapshotSync => _lastSnapshotSync;
  Stream<List<AlertModel>> get alertStream =>
      _alertsStreamController?.stream ?? const Stream.empty();

  Future<void> fetchMyAlerts() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _alerts = await _alertService.getMyAlerts();
      _emitAlertsUpdate();
    } catch (e) {
      _errorMessage = 'Failed to fetch alerts: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> markAsRead(int alertId) async {
    try {
      final updatedAlert = await _alertService.markAsRead(alertId);
      _upsertAlert(updatedAlert);
    } catch (e) {
      debugPrint('Error marking alert as read: $e');
    }
  }

  Future<void> acknowledgeAlert(int alertId) async {
    try {
      final updatedAlert = await _alertService.acknowledgeAlert(alertId);
      _upsertAlert(updatedAlert);
    } catch (e) {
      debugPrint('Error acknowledging alert: $e');
      _errorMessage = 'Failed to acknowledge alert';
      notifyListeners();
    }
  }

  Future<void> acknowledge(int alertId) => acknowledgeAlert(alertId);

  Future<void> dismissAlert(int alertId) async {
    try {
      final updatedAlert = await _alertService.dismissAlert(alertId);
      _upsertAlert(updatedAlert);
    } catch (e) {
      debugPrint('Error dismissing alert: $e');
      _errorMessage = 'Failed to dismiss alert';
      notifyListeners();
    }
  }

  Future<void> dismiss(int alertId) => dismissAlert(alertId);

  void initializeRealtime() {
    if (_realtimeInitialized) return;
    _realtimeInitialized = true;

    _alertsStreamController ??= StreamController<List<AlertModel>>.broadcast();
    WidgetsBinding.instance.addObserver(this);
    _webSocketClient.connect();
    _isRealtimeConnected = _webSocketClient.isConnected;
    _socketSubscription = _webSocketClient.stream.listen(
      _handleSocketMessage,
      onError: (error) {
        _realtimeError = error.toString();
        _isRealtimeConnected = false;
        notifyListeners();
      },
      onDone: () {
        _isRealtimeConnected = false;
        notifyListeners();
      },
    );

    _startSnapshotSyncTimer();
    syncSnapshot(force: true);
    notifyListeners();
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

        if (type == 'alert_created' || type == 'alert_updated') {
          final alertJson = payload is Map<String, dynamic>
              ? payload['alert'] ?? payload
              : null;
          if (alertJson is Map<String, dynamic>) {
            _upsertAlert(AlertModel.fromJson(alertJson));
            return;
          }
        }

        if (type == 'alerts_snapshot' && payload is List) {
          _replaceAlertsFromPayload(payload);
          return;
        }

        if (decoded.containsKey('alert_id')) {
          _upsertAlert(AlertModel.fromJson(decoded));
          return;
        }
      } else if (decoded is List) {
        _replaceAlertsFromPayload(decoded);
        return;
      }
    } catch (e) {
      _realtimeError = 'Realtime parse error: $e';
      notifyListeners();
    }
  }

  void _replaceAlertsFromPayload(List<dynamic> payload) {
    final nextAlerts = <AlertModel>[];
    for (final item in payload) {
      if (item is Map<String, dynamic>) {
        nextAlerts.add(AlertModel.fromJson(item));
      }
    }
    _alerts = nextAlerts;
    _emitAlertsUpdate();
  }

  void _upsertAlert(AlertModel alert) {
    final index = _alerts.indexWhere((a) => a.alertId == alert.alertId);
    if (index == -1) {
      _alerts.insert(0, alert);
    } else {
      _alerts[index] = alert;
    }
    _recordDetectionObservation(alert);
    _emitAlertsUpdate();
  }

  void updateAlertStatus(int alertId, AlertStatus status) {
    final index = _alerts.indexWhere((a) => a.alertId == alertId);
    if (index == -1) return;
    final updated = _alerts[index].copyWith(status: status);
    _alerts[index] = updated;
    _emitAlertsUpdate();
  }

  void _emitAlertsUpdate() {
    _applyExpiryAndSort();
    final hasCritical = _alerts.any(
        (a) => _priorityRank(a.alertLevel) >= _priorityRank(AlertLevel.critical));

    if (hasCritical) {
      _alertsStreamController?.add(List.unmodifiable(_alerts));
      notifyListeners();
      return;
    }

    _lowPriorityEmitTimer?.cancel();
    _lowPriorityEmitTimer = Timer(const Duration(milliseconds: 400), () {
      _alertsStreamController?.add(List.unmodifiable(_alerts));
      notifyListeners();
    });
  }

  int get alertsTodayCount {
    final now = DateTime.now();
    return _alerts
        .where((a) =>
            a.alertTimestamp.year == now.year &&
            a.alertTimestamp.month == now.month &&
            a.alertTimestamp.day == now.day)
        .length;
  }

  int get pendingVerificationCount {
    return _alerts
        .where((a) => verificationState(a) == VerificationState.pendingVerification)
        .length;
  }

  int get confirmedAlertsCount {
    return _alerts
        .where((a) => verificationState(a) == VerificationState.confirmedMatch)
        .length;
  }

  bool isDecisionPending(int alertId) {
    return _pendingDecisions.containsKey(alertId);
  }

  Future<void> queueDecision({
    required AlertModel alert,
    required AlertStatus targetStatus,
    required Future<void> Function() finalize,
  }) async {
    _pendingDecisions[alert.alertId]?.cancel();
    _pendingDecisions[alert.alertId] = _PendingDecision(
      alertId: alert.alertId,
      targetStatus: targetStatus,
      timer: Timer(const Duration(seconds: 10), () async {
        await finalize();
        _pendingDecisions.remove(alert.alertId);
        notifyListeners();
      }),
    );
    notifyListeners();
  }

  void undoDecision(int alertId) {
    final pending = _pendingDecisions.remove(alertId);
    pending?.cancel();
    notifyListeners();
  }

  void _applyExpiryAndSort() {
    final now = DateTime.now();
    _alerts.removeWhere((alert) {
      final level = alert.alertLevel;
      if (level == AlertLevel.critical) return false;

      final lastSeen = alert.lastSeenTime ?? alert.alertTimestamp;
      final ageMinutes = now.difference(lastSeen).inMinutes;
      if (level == AlertLevel.preliminary) return ageMinutes > 2;
      if (level == AlertLevel.tracking) return ageMinutes > 5;
      if (level == AlertLevel.strongMatch) return ageMinutes > 10;
      return false;
    });

    _alerts.sort((a, b) {
      final rankDiff = _priorityRank(b.alertLevel) - _priorityRank(a.alertLevel);
      if (rankDiff != 0) return rankDiff;
      return b.alertTimestamp.compareTo(a.alertTimestamp);
    });
  }

  int _priorityRank(AlertLevel level) {
    switch (level) {
      case AlertLevel.critical:
        return 4;
      case AlertLevel.strongMatch:
        return 3;
      case AlertLevel.tracking:
        return 2;
      case AlertLevel.preliminary:
        return 1;
    }
  }

  VerificationState verificationState(AlertModel alert) {
    final detection = alert.detection;
    final isMultiFrame = _isMultiFrameConfirmed(detection);
    final passesConfidence = _meetsConfidenceThresholds(detection, alert);

    if (!isMultiFrame) {
      return VerificationState.preliminary;
    }

    if (alert.status == AlertStatus.acknowledged) {
      return passesConfidence
          ? VerificationState.confirmedMatch
          : VerificationState.needsReview;
    }
    if (alert.status == AlertStatus.dismissed) {
      return VerificationState.rejectedFalseAlarm;
    }

    final age = DateTime.now().difference(alert.alertTimestamp);
    if (age.inSeconds >= 30) {
      return VerificationState.cloudTimeout;
    }
    return VerificationState.pendingVerification;
  }

  SystemStatus get systemStatus {
    if (!_webSocketClient.isConnected) {
      return SystemStatus.offline;
    }
    final hasPending = _alerts.any((alert) =>
        verificationState(alert) == VerificationState.pendingVerification ||
        verificationState(alert) == VerificationState.cloudTimeout);
    if (hasPending) {
      return SystemStatus.cloudDelay;
    }
    return SystemStatus.operational;
  }

  Future<void> syncSnapshot({bool force = false}) async {
    if (_isSnapshotSyncing && !force) return;
    _isSnapshotSyncing = true;
    _realtimeError = null;
    notifyListeners();
    try {
      final snapshot = await _alertService.getAlertsSnapshot();
      _reconcileSnapshot(snapshot);
      _lastSnapshotSync = DateTime.now();
      _snapshotRetryDelay = const Duration(seconds: 5);
    } catch (e) {
      _realtimeError = 'Snapshot sync failed: $e';
      _scheduleSnapshotRetry();
    } finally {
      _isSnapshotSyncing = false;
      notifyListeners();
    }
  }

  void _reconcileSnapshot(List<AlertModel> snapshot) {
    final snapshotMap = {
      for (final alert in snapshot) alert.alertId: alert
    };
    final localMap = {for (final alert in _alerts) alert.alertId: alert};

    // Add or update alerts from snapshot
    for (final entry in snapshotMap.entries) {
      final local = localMap[entry.key];
      if (local == null) {
        _alerts.add(entry.value);
      } else if (local.status != entry.value.status ||
          local.alertTimestamp != entry.value.alertTimestamp ||
          local.detection?.combinedScore !=
              entry.value.detection?.combinedScore) {
        _alerts[_alerts.indexWhere((a) => a.alertId == entry.key)] =
            entry.value;
      }
    }

    // Remove alerts not present in snapshot
    _alerts.removeWhere((a) => !snapshotMap.containsKey(a.alertId));

    for (final alert in _alerts) {
      _recordDetectionObservation(alert);
    }
    _emitAlertsUpdate();
  }

  void _startSnapshotSyncTimer() {
    _snapshotTimer?.cancel();
    _snapshotTimer =
        Timer.periodic(const Duration(minutes: 1), (_) => syncSnapshot());
  }

  void _scheduleSnapshotRetry() {
    _snapshotRetryTimer?.cancel();
    _snapshotRetryTimer = Timer(_snapshotRetryDelay, () {
      _snapshotRetryDelay = Duration(
          seconds: (_snapshotRetryDelay.inSeconds * 2).clamp(5, 120));
      syncSnapshot(force: true);
    });
  }

  void _recordDetectionObservation(AlertModel alert) {
    final detection = alert.detection;
    if (detection == null || detection.trackId == null) return;
    final trackId = detection.trackId!;
    final observation = _DetectionObservation(
      timestamp: detection.detectionTimestamp,
      cameraId: detection.cameraId ?? detection.cameraLocation,
    );

    final list = _trackObservations.putIfAbsent(trackId, () => []);
    list.add(observation);
    final cutoff =
        detection.detectionTimestamp.subtract(const Duration(seconds: 5));
    list.removeWhere((item) => item.timestamp.isBefore(cutoff));
  }

  bool _isMultiFrameConfirmed(DetectionData? detection) {
    if (detection == null || detection.trackId == null) return false;
    final observations = _trackObservations[detection.trackId!];
    if (observations == null || observations.isEmpty) return false;

    if (observations.length < 3) {
      final distinctCameras = observations
          .map((o) => o.cameraId)
          .whereType<String>()
          .toSet();
      return distinctCameras.length >= 2;
    }

    final distinctCameras = observations
        .map((o) => o.cameraId)
        .whereType<String>()
        .toSet();

    if (distinctCameras.length >= 2) return true;
    if (observations.length >= 3) {
      final windowStart = observations.first.timestamp;
      final windowEnd = observations.last.timestamp;
      return windowEnd.difference(windowStart).inSeconds <= 5;
    }
    return false;
  }

  bool _meetsConfidenceThresholds(
      DetectionData? detection, AlertModel alert) {
    if (detection == null) return false;
    const faceThreshold = 0.8;
    const clothingThreshold = 0.7;

    final cameraWeight = alert.cameraReliabilityScore ?? 1.0;
    final effectiveFace = detection.faceMatchScore * cameraWeight;
    final effectiveClothing =
        (detection.colorMatchScore ?? 0) * cameraWeight;

    final faceOk = effectiveFace >= faceThreshold;
    final clothingOk =
        detection.colorMatchScore == null ? true : effectiveClothing >= clothingThreshold;
    return faceOk && clothingOk;
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _socketSubscription?.cancel();
    _webSocketClient.disconnect();
    _alertsStreamController?.close();
    _snapshotTimer?.cancel();
    _snapshotRetryTimer?.cancel();
    _lowPriorityEmitTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      syncSnapshot(force: true);
    }
  }
}

class _DetectionObservation {
  final DateTime timestamp;
  final String? cameraId;

  _DetectionObservation({required this.timestamp, required this.cameraId});
}

class _PendingDecision {
  final int alertId;
  final AlertStatus targetStatus;
  final Timer timer;

  _PendingDecision({
    required this.alertId,
    required this.targetStatus,
    required this.timer,
  });

  void cancel() {
    timer.cancel();
  }
}
