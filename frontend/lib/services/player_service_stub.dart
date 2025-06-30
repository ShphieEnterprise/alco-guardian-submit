// スタブファイル（モバイル用）
import 'dart:typed_data';

class AudioElement {
  Future<void> play() async {}
  void pause() {}
  set src(String value) {}
  set currentTime(num value) {}
  Stream<dynamic> get onEnded => Stream.empty();
}

class Blob {
  Blob(List<dynamic> parts, String type);
}

class Url {
  static String createObjectUrl(dynamic blob) => '';
  static void revokeObjectUrl(String url) {}
}