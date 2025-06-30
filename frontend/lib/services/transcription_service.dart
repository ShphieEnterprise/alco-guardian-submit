import 'dart:typed_data';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth/firebase_auth_service.dart';

class TranscriptionService {
  final FirebaseAuthService _authService;
  final String _transcribeEndpoint = 'https://asia-northeast1-alco-guardian.cloudfunctions.net/transcribe';

  TranscriptionService(this._authService);

  Future<Map<String, dynamic>> transcribeAudio({
    required Uint8List audioData,
    required String fileName,
  }) async {
    try {
      // IDトークンを取得
      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('認証されていません');
      }

      // print('デバッグ情報は本番環境ではコメントアウト')

      // マルチパートリクエストを作成
      final request = http.MultipartRequest('POST', Uri.parse(_transcribeEndpoint));
      
      // 認証ヘッダーを追加
      request.headers['Authorization'] = 'Bearer $idToken';
      
      // CORSはバックエンド側で対応済み
      
      // 音声ファイルを追加
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          audioData,
          filename: fileName,
          // contentType: MediaType('audio', 'webm'), // 必要に応じてcontent-typeを設定
        ),
      );

      // リクエストを送信
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        // レスポンスをJSONとしてパース
        final responseData = jsonDecode(response.body);
        return {
          'success': true,
          'transcription': responseData['transcript'] ?? '',
          'original_filename': responseData['original_filename'] ?? fileName,
          'message': responseData['message'] ?? '',
          'timestamp': DateTime.now().toIso8601String(),
        };
      } else {
        // エラーレスポンスをパース
        Map<String, dynamic> errorData;
        try {
          errorData = jsonDecode(response.body);
        } catch (e) {
          errorData = {'message': response.body};
        }
        
        final errorMessage = errorData['message'] ?? 'Unknown error';
        final errorCode = errorData['code'] ?? 'UNKNOWN';
        
        throw Exception('[$errorCode] $errorMessage');
      }
    } catch (e) {
      // エラーログは本番環境では最小限に
      return {
        'success': false,
        'error': e.toString(),
        'timestamp': DateTime.now().toIso8601String(),
      };
    }
  }

  // Cloud Storageに保存された音声ファイルのURLから転写する場合
  Future<Map<String, dynamic>> transcribeFromUrl({
    required String audioUrl,
  }) async {
    try {
      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('認証されていません');
      }

      // URLから音声データをダウンロード
      final audioResponse = await http.get(Uri.parse(audioUrl));
      if (audioResponse.statusCode != 200) {
        throw Exception('音声ファイルのダウンロードに失敗しました');
      }

      // ダウンロードしたデータを使って転写
      return transcribeAudio(
        audioData: audioResponse.bodyBytes,
        fileName: 'audio_from_url.webm',
      );
    } catch (e) {
      // print('TranscriptionService.transcribeFromUrl() error: $e');
      return {
        'success': false,
        'error': e.toString(),
        'timestamp': DateTime.now().toIso8601String(),
      };
    }
  }
}