# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code)向けのガイダンスを提供します。

## コマンド

### 開発
```bash
# Web開発サーバーの起動 (localhost:8080)
flutter run -d chrome --web-hostname localhost --web-port 8080

# 他のプラットフォームでの実行
flutter run -d ios     # iOS
flutter run -d android # Android

# クリーンとリビルド
flutter clean
flutter pub get

# コード解析
flutter analyze

# テスト実行
flutter test
```

### デプロイ
```bash
# Webビルド
flutter build web

# Google Cloud Runへのデプロイ
gcloud run deploy alco-guardian-frontend \
  --source . \
  --region [REGION] \
  --allow-unauthenticated

# Dockerイメージのローカルビルド
docker build -t alco-guardian-frontend .
```

## アーキテクチャ概要

### サービスレイヤーアーキテクチャ
このアプリはサービス指向アーキテクチャを採用し、以下のコアサービスで構成されています：

1. **認証 (`lib/services/auth/`)**
   - `firebase_auth_service.dart`: メール/パスワード認証用のFirebase Authラッパー
   - `cloud_functions_service.dart`: IDトークン注入による認証済みCloud Functions呼び出し

2. **メディアサービス (`lib/services/`)**
   - `recorder_service.dart`: クロスプラットフォーム音声録音オーケストレーター
   - `web_recorder.dart`: dart:htmlを使用したWeb専用MediaRecorder実装
   - `player_service.dart`: 音声再生（モバイルのみ）
   - `storage_service.dart`: ユーザースコープパスを持つFirebase Cloud Storage統合

### プラットフォーム別実装
- **Web録音**: `web_recorder.dart`経由でHTML5 MediaRecorder APIを使用
- **モバイル録音**: AACフォーマットでflutter_soundパッケージを使用
- **音声フォーマット**: Web用WebM/opus、モバイル用AAC

### Firebase設定
- **Storage バケット**: `gs://alco-guardian-audio`（専用音声バケット）
- **Storage 構造**: `users/{userId}/recordings/{filename}`
- **認証**: Firebase Authでメール/パスワード
- **Cloud Functions**: Bearerトークンによる認証エンドポイント

### UIアーキテクチャ
- **エントリーポイント**: `AuthWrapper`ウィジェットが認証状態を管理
- **状態管理**: サービス注入によるローカルウィジェット状態
- **テーマ**: ライト/ダークモード対応のMaterial3

### Webデプロイメント
- Google Cloud Run用に最適化（ポート8080）
- SPAルーティング用Nginx設定
- 最小イメージサイズのためのDockerマルチステージビルド

### よくある問題と解決策

1. **Web上のMediaRecorderエラー**
   - マイクアクセスにはHTTPSまたはlocalhostが必要
   - MediaRecorder APIのブラウザ互換性を確認
   - JS相互運用ではなく、dart:html MediaRecorderを直接使用

2. **Firebase Storageアップロード**
   - アップロード前にユーザーが認証されていることを確認
   - Firebase Storageルールがユーザーアップロードを許可しているか確認
   - 正しいcontent-typeメタデータが設定されているか確認

3. **クロスプラットフォーム録音**
   - WebはWebRecorder、モバイルはflutter_soundを使用
   - 異なる音声フォーマット：WebM（Web）対AAC（モバイル）
   - マイクアクセスには権限処理が必要

### 理解すべき主要ファイル
- `lib/ui/auth_wrapper.dart`: 認証フローのエントリーポイント
- `lib/services/recorder_service.dart`: メイン録音ロジックのオーケストレーション
- `lib/services/web_recorder.dart`: Web専用録音実装
- `lib/ui/home_screen.dart`: 録音コントロールを持つメインUI