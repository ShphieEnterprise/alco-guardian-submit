import 'package:flutter_sound/flutter_sound.dart';
import 'package:flutter/foundation.dart';
import '../services/recorder_service.dart';

// 条件付きインポート
import 'player_service_stub.dart' 
  if (dart.library.html) 'dart:html' as html;

class PlayerService {
  final FlutterSoundPlayer _player = FlutterSoundPlayer();
  html.AudioElement? _webAudio;
  final RecorderService? _recorderService;
  
  PlayerService({RecorderService? recorderService}) : _recorderService = recorderService;

  Future<void> init() async {
    if (kIsWeb) {
      _webAudio = html.AudioElement();
      await _player.openPlayer(); // Web環境でもflutter_soundプレイヤーを開く
    } else {
      await _player.openPlayer();
    }
  }

  Future<void> play(String path) async {
    try {
      if (kIsWeb) {
        // Web環境ではflutter_soundの内部プレイヤーを使用
        print('Playing last recorded audio using flutter_sound...');
        await _player.startPlayer();
        print('Web playback started successfully');
      } else {
        await _player.startPlayer(fromURI: path);
      }
    } catch (e) {
      print('PlayerService.play() error: $e');
      if (kIsWeb) {
        print('Trying alternative playback method...');
        try {
          // 代替手段: 録音データがある場合
          final recordingData = _recorderService?.getWebRecordingData();
          if (recordingData != null) {
            print('Using recording data for playback');
            final blob = html.Blob([recordingData], 'audio/webm');
            final url = html.Url.createObjectUrl(blob);
            _webAudio!.src = url;
            await _webAudio!.play();
            _webAudio!.onEnded.listen((_) {
              html.Url.revokeObjectUrl(url);
            });
          } else {
            throw Exception('No recording data available for playback');
          }
        } catch (e2) {
          print('Alternative playback also failed: $e2');
          rethrow;
        }
      } else {
        rethrow;
      }
    }
  }

  Future<void> playFromUrl(String audioUrl) async {
    try {
      if (kIsWeb) {
        // Web環境ではHTML AudioElementを使用してURLから直接再生
        print('Playing audio from URL: $audioUrl');
        _webAudio!.src = audioUrl;
        await _webAudio!.play();
        print('Web URL playback started successfully');
      } else {
        // モバイル環境ではflutter_soundを使用
        await _player.startPlayer(fromURI: audioUrl);
        print('Mobile URL playback started successfully');
      }
    } catch (e) {
      print('PlayerService.playFromUrl() error: $e');
      rethrow;
    }
  }

  Future<void> stop() async {
    if (kIsWeb) {
      _webAudio?.pause();
      _webAudio?.currentTime = 0;
      await _player.stopPlayer(); // flutter_soundプレイヤーも停止
    } else {
      await _player.stopPlayer();
    }
  }
  
  void dispose() {
    if (kIsWeb) {
      _webAudio = null;
      _player.closePlayer(); // Web環境でもプレイヤーを閉じる
    } else {
      _player.closePlayer();
    }
  }
}
