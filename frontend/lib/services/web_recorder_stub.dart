// スタブファイル（モバイル用）
import 'dart:typed_data';
import 'dart:async';

class WebRecorder {
  Future<void> initialize() async {
    throw UnsupportedError('WebRecorder is not supported on this platform');
  }
  
  Future<void> startRecording() async {
    throw UnsupportedError('WebRecorder is not supported on this platform');
  }
  
  Future<Uint8List?> stopRecording() async {
    throw UnsupportedError('WebRecorder is not supported on this platform');
  }
  
  void dispose() {}
  
  bool get isRecording => false;
}