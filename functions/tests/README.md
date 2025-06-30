# Cloud Functions テスト

## 概要

このディレクトリには、音声文字起こしCloud Functionsのテスト用ファイルとスクリプトが含まれています。

## テストファイル

- `test_audio.m4a`: 音声文字起こし用テストファイル
- `test_file.txt`: 基本的なファイルアップロードテスト用

## テストスクリプト

### 1. 簡易テスト（推奨）
```bash
./quick_test.sh
```
認証なしでエンドポイントをテストし、正しく401エラーが返されることを確認

### 2. Python詳細テスト
```bash
uv run simple_test.py
```
Pythonでエンドポイントをテストし、詳細なレスポンス情報を表示

### 3. Firebase Auth付きテスト（開発用）
```bash
uv run test_with_firebase_auth.py
```
Firebase Admin SDKでカスタムトークンを生成してテスト

## 本格的なテスト方法

### Flutterアプリからテスト（推奨）
```bash
cd ../mobile
flutter run
```
1. アプリでログイン（Firebase Auth）
2. 音声ファイルを選択して送信
3. 文字起こし結果を確認

### 認証を一時的に無効化してテスト
```bash
gcloud functions deploy transcribe \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --memory 512MB \
  --timeout 60s \
  --region asia-northeast1 \
  --set-env-vars UPLOAD_BUCKET=alco-guardian.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001,DISABLE_AUTH=true
```

## エンドポイント

- **URL**: https://asia-northeast1-alco-guardian.cloudfunctions.net/transcribe
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Authentication**: Firebase ID Token required

## 期待される結果

- **認証なし**: HTTP 401 Unauthorized
- **正常**: HTTP 200 OK + transcriptフィールド
- **エラー**: HTTP 400/500 + errorフィールド