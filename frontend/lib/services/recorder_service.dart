import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_sound/flutter_sound.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:flutter/foundation.dart';
import 'storage_service.dart';
import 'transcription_service.dart';
import 'auth/firebase_auth_service.dart';

// 条件付きインポート: Webではweb_recorder.dart、それ以外ではスタブを使用
import 'web_recorder_stub.dart'
  if (dart.library.html) 'web_recorder.dart';

class RecorderService {
  final FlutterSoundRecorder _recorder = FlutterSoundRecorder();
  final StorageService _storageService = StorageService();
  final FirebaseAuthService _authService = FirebaseAuthService();
  late final TranscriptionService _transcriptionService;
  WebRecorder? _webRecorder; // Web専用レコーダー
  late final Directory? _dir;
  Uint8List? _webRecordingData; // Web録音データを保持
  String? _lastRecordingPath; // 最後の録音パスを保持
  String? _webRecordingUrl; // Web録音のBlobURL
  
  RecorderService() {
    _transcriptionService = TranscriptionService(_authService);
  }

  Future<void> init() async {
    if (!kIsWeb) {
      _dir = await getApplicationDocumentsDirectory();
      await Permission.microphone.request();
      await _recorder.openRecorder();
    } else {
      _dir = null;
      // Web環境では専用レコーダーを初期化
      _webRecorder = WebRecorder();
      await _webRecorder!.initialize();
    }
  }

  Future<String> start() async {
    try {
      if (kIsWeb) {
        // Web環境では専用レコーダーを使用
        print('Starting web recording with WebRecorder...');
        await _webRecorder!.startRecording();
        _lastRecordingPath = 'web_recording_${DateTime.now().millisecondsSinceEpoch}';
        return _lastRecordingPath!;
      } else {
        final path = '${_dir!.path}/${DateTime.now().millisecondsSinceEpoch}.aac';
        await _recorder.startRecorder(toFile: path, codec: Codec.aacADTS);
        _lastRecordingPath = path; // モバイルでもパスを保持
        return path;
      }
    } catch (e) {
      print('RecorderService.start() error: $e');
      if (kIsWeb) {
        print('Web recording failed. This may be due to:');
        print('1. Microphone permission denied');
        print('2. Browser security restrictions');
        print('3. No HTTPS connection (required for microphone access)');
      }
      rethrow;
    }
  }

  Future<void> stop() async {
    try {
      if (kIsWeb) {
        // Web環境では専用レコーダーを停止
        print('Stopping web recording...');
        _webRecordingData = await _webRecorder!.stopRecording();
        if (_webRecordingData != null) {
          print('Web recording completed. Data size: ${_webRecordingData!.length} bytes');
        } else {
          print('No recording data received from WebRecorder');
        }
      } else {
        await _recorder.stopRecorder();
      }
    } catch (e) {
      print('RecorderService.stop() error: $e');
      rethrow;
    }
  }

  
  // Web環境で録音データを取得
  Uint8List? getWebRecordingData() => _webRecordingData;
  
  // Web環境で録音URLを取得
  String? getWebRecordingUrl() => _webRecordingUrl;
  
  // 最後の録音パスを取得
  String? getLastRecordingPath() => _lastRecordingPath;

  // 録音データをCloud Storageにアップロード
  Future<String?> uploadRecording() async {
    try {
      Uint8List? dataToUpload;
      String fileName;

      if (kIsWeb) {
        // Web環境: 録音データを取得
        dataToUpload = _webRecordingData;
        if (dataToUpload == null) {
          throw Exception('アップロードする録音データがありません');
        }
        fileName = 'web_recording_${DateTime.now().millisecondsSinceEpoch}.webm';
      } else {
        // モバイル環境: ファイルから読み込み
        if (_lastRecordingPath == null) {
          throw Exception('アップロードする録音ファイルがありません');
        }
        final file = File(_lastRecordingPath!);
        if (!await file.exists()) {
          throw Exception('録音ファイルが見つかりません');
        }
        dataToUpload = await file.readAsBytes();
        fileName = 'mobile_recording_${DateTime.now().millisecondsSinceEpoch}.aac';
      }

      print('Uploading recording: $fileName (${dataToUpload.length} bytes)');
      
      final downloadUrl = await _storageService.uploadAudioFile(
        audioData: dataToUpload,
        fileName: fileName,
      );

      print('Recording uploaded successfully: $downloadUrl');
      return downloadUrl;

    } catch (e) {
      print('RecorderService.uploadRecording() error: $e');
      rethrow;
    }
  }

  // 録音データをCloud Runに送信して転写
  Future<Map<String, dynamic>> transcribeRecording() async {
    try {
      Uint8List? dataToTranscribe;
      String fileName;

      if (kIsWeb) {
        // Web環境: 録音データを取得
        dataToTranscribe = _webRecordingData;
        if (dataToTranscribe == null) {
          throw Exception('転写する録音データがありません');
        }
        fileName = 'web_recording_${DateTime.now().millisecondsSinceEpoch}.webm';
      } else {
        // モバイル環境: ファイルから読み込み
        if (_lastRecordingPath == null) {
          throw Exception('転写する録音ファイルがありません');
        }
        final file = File(_lastRecordingPath!);
        if (!await file.exists()) {
          throw Exception('録音ファイルが見つかりません');
        }
        dataToTranscribe = await file.readAsBytes();
        fileName = 'mobile_recording_${DateTime.now().millisecondsSinceEpoch}.aac';
      }

      print('Transcribing recording: $fileName (${dataToTranscribe.length} bytes)');
      
      // TranscriptionServiceを使用してCloud Runに送信
      final result = await _transcriptionService.transcribeAudio(
        audioData: dataToTranscribe,
        fileName: fileName,
      );

      if (result['success'] == true) {
        print('Recording transcribed successfully');
      } else {
        print('Transcription failed: ${result['error']}');
      }
      
      return result;

    } catch (e) {
      print('RecorderService.transcribeRecording() error: $e');
      return {
        'success': false,
        'error': e.toString(),
        'timestamp': DateTime.now().toIso8601String(),
      };
    }
  }

  void dispose() {
    if (kIsWeb) {
      _webRecorder?.dispose();
    } else {
      _recorder.closeRecorder();
    }
  }
}
