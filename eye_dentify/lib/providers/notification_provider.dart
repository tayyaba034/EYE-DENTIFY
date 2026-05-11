import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../core/network/api_config.dart';
import '../core/network/websocket_client.dart';
import '../services/notification_service.dart';
import '../services/storage_service.dart';

class NotificationProvider extends ChangeNotifier {
  final NotificationService _notificationService;
  final StorageService _storageService;
  final WebSocketClient _webSocketClient;
  List<Map<String, dynamic>> _notifications = [];
  bool _isLoading = false;
  String? _errorMessage;
  StreamSubscription<dynamic>? _socketSubscription;
  bool _isRealtimeInitialized = false;
  String? _currentUserId;

  NotificationProvider(
    this._notificationService,
    this._storageService, {
    WebSocketClient? webSocketClient,
  }) : _webSocketClient =
           webSocketClient ?? WebSocketClient(ApiConfig.webSocketUrl);

  List<Map<String, dynamic>> get notifications => _notifications;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> initialize() async {
    final user = await _storageService.getUserData();
    _currentUserId = user?['id']?.toString();
    await fetchNotifications();
    _subscribeRealtime();
  }

  Future<void> fetchNotifications() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final data = await _notificationService.getNotifications();
      _notifications = data
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
    } catch (e) {
      _errorMessage = 'Failed to load notifications: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> markAsRead(String id) async {
    try {
      await _notificationService.markAsRead(id);
      final index = _notifications.indexWhere((n) => n['id'].toString() == id);
      if (index != -1) {
        _notifications[index]['read_at'] = DateTime.now().toIso8601String();
      }
      notifyListeners();
    } catch (e) {
      _errorMessage = 'Failed to mark notification read: $e';
      notifyListeners();
    }
  }

  void _subscribeRealtime() {
    if (_isRealtimeInitialized) return;
    _isRealtimeInitialized = true;
    _webSocketClient.connect();
    _socketSubscription = _webSocketClient.stream.listen(
      _handleSocketMessage,
      onError: (error) {
        _errorMessage = 'Notification realtime error: $error';
        notifyListeners();
      },
    );
  }

  Future<void> _handleSocketMessage(dynamic data) async {
    try {
      dynamic decoded = data;
      if (data is String) {
        decoded = jsonDecode(data);
      }
      if (decoded is! Map<String, dynamic>) return;

      if (decoded['type'] == 'notification_created') {
        final payload = decoded['payload'];
        final targetUserId =
            payload is Map<String, dynamic> ? payload['user_id'] : null;
        if (await _isCurrentUserEvent(targetUserId)) {
          unawaited(fetchNotifications());
        }
        return;
      }

      if (decoded['type'] == 'notification_updated') {
        final payload = decoded['payload'];
        final targetUserId =
            payload is Map<String, dynamic> ? payload['user_id'] : null;
        if (await _isCurrentUserEvent(targetUserId)) {
          unawaited(fetchNotifications());
        }
      }
    } catch (e) {
      _errorMessage = 'Notification realtime parse error: $e';
      notifyListeners();
    }
  }

  Future<bool> _isCurrentUserEvent(dynamic targetUserId) async {
    if (_currentUserId == null) {
      final user = await _storageService.getUserData();
      _currentUserId = user?['id']?.toString();
    }

    return _currentUserId != null &&
        targetUserId != null &&
        _currentUserId == targetUserId.toString();
  }

  @override
  void dispose() {
    _socketSubscription?.cancel();
    _webSocketClient.disconnect();
    super.dispose();
  }
}
