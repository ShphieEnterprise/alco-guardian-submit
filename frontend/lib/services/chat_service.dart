import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth/firebase_auth_service.dart';

class ChatService {
  final FirebaseAuthService _authService = FirebaseAuthService();
  static const String _baseUrl = 'https://asia-northeast1-alco-guardian.cloudfunctions.net';

  Future<ChatResponse> sendMessage(String message, {bool enableTTS = true}) async {
    try {
      // Get the ID token for authentication
      final idToken = await _authService.getIdToken();
      
      final response = await http.post(
        Uri.parse('$_baseUrl/chat'),
        headers: {
          'Content-Type': 'application/json',
          if (idToken != null) 'Authorization': 'Bearer $idToken',
        },
        body: jsonEncode({
          'message': message,
          'enableTTS': enableTTS,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return ChatResponse.fromJson(data);
      } else {
        final errorData = jsonDecode(response.body);
        throw ChatException(
          code: errorData['code'] ?? 'UNKNOWN_ERROR',
          message: errorData['message'] ?? 'Unknown error occurred',
        );
      }
    } catch (e) {
      if (e is ChatException) {
        rethrow;
      }
      throw ChatException(
        code: 'NETWORK_ERROR',
        message: 'Failed to send message: $e',
      );
    }
  }
}

class ChatResponse {
  final bool success;
  final String message;
  final int imageId;
  final String timestamp;
  final String agent;
  final String? audioUrl;

  ChatResponse({
    required this.success,
    required this.message,
    required this.imageId,
    required this.timestamp,
    required this.agent,
    this.audioUrl,
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      success: json['success'] ?? false,
      message: json['message'] ?? '',
      imageId: json['imageId'] ?? 1,
      timestamp: json['timestamp'] ?? '',
      agent: json['agent'] ?? 'unknown',
      audioUrl: json['audioUrl'],
    );
  }
}

class ChatException implements Exception {
  final String code;
  final String message;

  ChatException({required this.code, required this.message});

  @override
  String toString() => 'ChatException: $code - $message';
}