import 'dart:typed_data';
import 'dart:html' as html;
import 'dart:async';
import 'package:flutter/foundation.dart';

class WebRecorder {
  html.MediaStream? _stream;
  List<html.Blob> _recordedChunks = [];
  bool _isRecording = false;
  Completer<Uint8List?>? _recordingCompleter;
  html.MediaRecorder? _mediaRecorder;

  Future<void> initialize() async {
    if (!kIsWeb) return;
    
    try {
      // マイクアクセス権限を取得
      final mediaDevices = html.window.navigator.mediaDevices;
      if (mediaDevices == null) {
        throw Exception('このブラウザはマイク機能をサポートしていません');
      }

      _stream = await mediaDevices.getUserMedia({
        'audio': {
          'echoCancellation': true,
          'noiseSuppression': true,
          'autoGainControl': true,
        }
      });
      
      if (_stream == null) {
        throw Exception('マイクアクセスが拒否されました');
      }
      
      print('WebRecorder initialized with stream: ${_stream!.id}');
    } catch (e) {
      print('WebRecorder initialization error: $e');
      if (e.toString().contains('Permission denied') || e.toString().contains('NotAllowedError')) {
        throw Exception('マイクアクセスが拒否されました。ブラウザの設定でマイクを許可してください。');
      } else {
        throw Exception('マイクの初期化に失敗しました: $e');
      }
    }
  }

  Future<void> startRecording() async {
    if (!kIsWeb || _stream == null) {
      throw Exception('WebRecorder not initialized');
    }

    try {
      _recordedChunks.clear();
      _recordingCompleter = Completer<Uint8List?>();
      
      // dart:htmlのMediaRecorderを直接使用
      _mediaRecorder = html.MediaRecorder(_stream!);
      
      // データ受信イベント
      _mediaRecorder!.addEventListener('dataavailable', (event) {
        final blobEvent = event as html.BlobEvent;
        if (blobEvent.data != null && blobEvent.data!.size > 0) {
          _recordedChunks.add(blobEvent.data!);
          print('Recorded chunk: ${blobEvent.data!.size} bytes');
        }
      });

      // 停止イベント
      _mediaRecorder!.addEventListener('stop', (event) async {
        print('Recording stopped. Total chunks: ${_recordedChunks.length}');
        
        if (_recordedChunks.isNotEmpty) {
          try {
            // Blobを結合
            final blob = html.Blob(_recordedChunks, 'audio/webm');
            print('Created blob with size: ${blob.size} bytes');
            
            // BlobをUint8Listに変換
            final arrayBuffer = await _blobToArrayBuffer(blob);
            final uint8List = Uint8List.view(arrayBuffer);
            
            _recordingCompleter?.complete(uint8List);
          } catch (e) {
            print('Error processing recording: $e');
            _recordingCompleter?.complete(null);
          }
        } else {
          _recordingCompleter?.complete(null);
        }
      });

      // 録音開始
      _mediaRecorder!.start(1000); // 1秒ごとにdataavailableイベント
      _isRecording = true;
      print('WebRecorder: Recording started');
      
    } catch (e) {
      print('WebRecorder start error: $e');
      _recordingCompleter?.completeError(e);
      rethrow;
    }
  }

  Future<Uint8List?> stopRecording() async {
    if (!kIsWeb || _mediaRecorder == null || !_isRecording) {
      return null;
    }

    try {
      // 録音停止
      _mediaRecorder!.stop();
      _isRecording = false;
      
      // stopイベントの処理を待機
      return await _recordingCompleter?.future;
      
    } catch (e) {
      print('WebRecorder stop error: $e');
      return null;
    }
  }

  Future<ByteBuffer> _blobToArrayBuffer(html.Blob blob) async {
    final completer = Completer<ByteBuffer>();
    final reader = html.FileReader();
    
    reader.onLoadEnd.listen((html.ProgressEvent e) {
      final result = reader.result;
      if (result is Uint8List) {
        completer.complete(result.buffer);
      } else if (result is ByteBuffer) {
        completer.complete(result);
      } else {
        completer.completeError('Unexpected result type: ${result.runtimeType}');
      }
    });
    
    reader.onError.listen((html.Event e) {
      completer.completeError('Failed to read blob');
    });
    
    reader.readAsArrayBuffer(blob);
    return completer.future;
  }

  void dispose() {
    if (_mediaRecorder != null) {
      try {
        _mediaRecorder!.stop();
      } catch (e) {
        // すでに停止している場合は無視
      }
      _mediaRecorder = null;
    }
    
    if (_stream != null) {
      _stream!.getTracks().forEach((track) => track.stop());
      _stream = null;
    }
    
    _recordedChunks.clear();
    _isRecording = false;
    _recordingCompleter = null;
  }

  bool get isRecording => _isRecording;
}