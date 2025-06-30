import 'dart:typed_data';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

class StorageService {
  final FirebaseStorage _storage = FirebaseStorage.instance;
  
  Future<String?> uploadAudioFile({
    required Uint8List audioData,
    required String fileName,
  }) async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('ユーザーがログインしていません');
      }

      // Firebase Storageバケットの参照を作成
      final storageRef = _storage.refFromURL('gs://alco-guardian.firebasestorage.app');
      
      // ユーザー別のパスを作成: users/{userId}/recordings/{fileName}
      final filePath = 'users/${user.uid}/recordings/$fileName';
      final fileRef = storageRef.child(filePath);

      print('Uploading to: $filePath');
      print('Data size: ${audioData.length} bytes');

      // メタデータを設定
      final metadata = SettableMetadata(
        contentType: 'audio/webm', // Web録音のデフォルト形式
        customMetadata: {
          'uploadedAt': DateTime.now().toIso8601String(),
          'userId': user.uid,
          'userEmail': user.email ?? '',
        },
      );

      // ファイルをアップロード
      final uploadTask = fileRef.putData(audioData, metadata);
      
      // アップロード進行状況を監視（Web環境では制限あり）
      if (!kIsWeb) {
        uploadTask.snapshotEvents.listen((TaskSnapshot snapshot) {
          final progress = snapshot.bytesTransferred / snapshot.totalBytes;
          print('Upload progress: ${(progress * 100).toStringAsFixed(2)}%');
        });
      }

      // アップロード完了を待機
      final snapshot = await uploadTask;
      
      // ダウンロードURLを取得
      final downloadUrl = await snapshot.ref.getDownloadURL();
      
      print('Upload successful. Download URL: $downloadUrl');
      return downloadUrl;
      
    } catch (e) {
      print('StorageService.uploadAudioFile() error: $e');
      rethrow;
    }
  }

  Future<List<Reference>> getUserAudioFiles() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('ユーザーがログインしていません');
      }

      // ユーザーの録音ファイル一覧を取得
      final storageRef = _storage.refFromURL('gs://alco-guardian-audio');
      final userRef = storageRef.child('users/${user.uid}/recordings');
      
      final result = await userRef.listAll();
      return result.items;
      
    } catch (e) {
      print('StorageService.getUserAudioFiles() error: $e');
      rethrow;
    }
  }

  Future<void> deleteAudioFile(String filePath) async {
    try {
      final storageRef = _storage.refFromURL('gs://alco-guardian-audio');
      final fileRef = storageRef.child(filePath);
      
      await fileRef.delete();
      print('File deleted: $filePath');
      
    } catch (e) {
      print('StorageService.deleteAudioFile() error: $e');
      rethrow;
    }
  }
}