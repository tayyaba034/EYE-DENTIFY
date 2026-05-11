import 'dart:async';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class WebSocketClient {
  WebSocketChannel? _channel;
  StreamController<dynamic>? _streamController;
  bool _isConnected = false;
  final Uri _url;

  WebSocketClient(String url) : _url = Uri.parse(url);

  Stream<dynamic> get stream =>
      _streamController?.stream ?? const Stream.empty();

  bool get isConnected => _isConnected;

  void connect() {
    if (_isConnected) return;

    _streamController = StreamController<dynamic>.broadcast();
    try {
      _channel = WebSocketChannel.connect(_url);
      _isConnected = true;
      _channel!.stream.listen(
        (data) {
          _streamController!.add(data);
        },
        onDone: () {
          _isConnected = false;
          debugPrint('WebSocket disconnected.');
          // Implement reconnection logic here
        },
        onError: (error) {
          _isConnected = false;
          debugPrint('WebSocket error: $error');
          // Implement reconnection logic here
        },
      );
    } catch (e) {
      debugPrint('Error connecting to WebSocket: $e');
      _isConnected = false;
    }
  }

  void sendMessage(String message) {
    if (_isConnected && _channel != null) {
      _channel!.sink.add(message);
    }
  }

  void disconnect() {
    if (!_isConnected) return;
    _channel?.sink.close();
    _streamController?.close();
    _isConnected = false;
  }
}
