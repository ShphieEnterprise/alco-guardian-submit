# デプロイメントガイド

最終更新: 2025-06-30

## 概要

このガイドでは、Alco Guardian の各コンポーネントのデプロイ方法について説明します。

## 前提条件

- Google Cloud SDK がインストールされていること
- Firebase CLI がインストールされていること
- Google Cloud プロジェクトが設定されていること
- 必要な権限を持つサービスアカウントが設定されていること

## プロジェクト設定

```bash
PROJECT_ID="YOUR_PROJECT_ID"
REGION="asia-northeast1"

# Google Cloud プロジェクトの設定
gcloud config set project $PROJECT_ID
```

## バックエンド（Cloud Functions）のデプロイ

### 1. 全エンドポイントの一括デプロイ

```bash
cd functions
./deploy_all_gen2.sh
```

### 2. 新規エンドポイントのみデプロイ

```bash
cd functions
./deploy_new_endpoints.sh
```

### 3. 個別エンドポイントのデプロイ

特定のエンドポイントのみをデプロイする場合：

```bash
cd functions

# 例: chat エンドポイントのデプロイ
gcloud functions deploy chat \
  --runtime python312 \
  --region asia-northeast1 \
  --memory 1GB \
  --timeout 60s \
  --trigger-http \
  --allow-unauthenticated \
  --gen2 \
  --entry-point chat \
  --set-env-vars "UPLOAD_BUCKET=${PROJECT_ID}.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001"
```

### デプロイ済みエンドポイント一覧

- `/transcribe` - 音声文字起こし
- `/chat` - Bartenderチャット（音声応答付き）
- `/tts` - テキスト音声変換
- `/get_drinks_master` - ドリンクマスターデータ
- `/add_drink` - 飲酒記録追加
- `/start_session` - セッション開始
- `/get_current_session` - 現在のセッション情報
- `/bartender` - Bartenderエージェント
- `/guardian_check` - Guardian状態確認
- `/guardian_monitor` - Guardian監視
- `/drinking_coach_analyze` - 飲酒コーチ分析

## フロントエンド（Flutter Web）のデプロイ

### 1. Firebase Hosting へのデプロイ

```bash
cd frontend

# ビルド
flutter build web

# Firebase Hosting にデプロイ
firebase deploy --only hosting
```

### 2. ローカルでのテスト

```bash
cd frontend
flutter run -d chrome
```

## モバイルアプリのデプロイ

### iOS

```bash
cd mobile

# iOS用ビルド
flutter build ios --release

# App Store Connect にアップロード（要Xcode）
```

### Android

```bash
cd mobile

# Android用ビルド
flutter build appbundle --release

# Google Play Console にアップロード
```

## 環境変数の設定

### Cloud Functions の環境変数

```bash
# 必須の環境変数
UPLOAD_BUCKET="${PROJECT_ID}.appspot.com"
GEMINI_LOCATION="us-central1"
GEMINI_MODEL="gemini-2.0-flash-001"

# 環境変数の設定
gcloud functions deploy [FUNCTION_NAME] \
  --set-env-vars "UPLOAD_BUCKET=$UPLOAD_BUCKET,GEMINI_LOCATION=$GEMINI_LOCATION,GEMINI_MODEL=$GEMINI_MODEL"
```

### Firebase の設定

1. Firebase Console で必要なサービスを有効化：
   - Authentication
   - Firestore Database
   - Cloud Storage

2. Firebase Admin SDK の認証情報を設定

## テストとデバッグ

### エンドポイントのテスト

```bash
# 基本的なヘルスチェック
curl https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/chat \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは"}'

# 詳細なテストスクリプト
cd functions/tests
./demo_scenario.sh
```

### ログの確認

```bash
# Cloud Functions のログを確認
gcloud functions logs read [FUNCTION_NAME] --limit 50

# リアルタイムでログを監視
gcloud functions logs tail [FUNCTION_NAME]
```

## トラブルシューティング

### よくある問題と解決方法

1. **CORS エラー**
   - Cloud Functions のレスポンスヘッダーに CORS 設定が含まれているか確認
   - `Access-Control-Allow-Origin: *` が設定されているか確認

2. **認証エラー**
   - サービスアカウントの権限を確認
   - Firebase Admin SDK の初期化が正しく行われているか確認

3. **タイムアウトエラー**
   - Cloud Functions のタイムアウト設定を延長（最大540秒）
   - 処理の最適化を検討

4. **メモリ不足エラー**
   - Cloud Functions のメモリ割り当てを増やす（最大32GB）

## セキュリティ考慮事項

1. **API キーの管理**
   - API キーは環境変数で管理
   - クライアントサイドにAPIキーを含めない

2. **認証の実装**
   - 本番環境では Firebase Authentication を必須に
   - ID トークンの検証を実装

3. **レート制限**
   - Cloud Functions の呼び出し回数制限を設定
   - 必要に応じて Cloud Armor を導入

## パフォーマンス最適化

1. **Cold Start の軽減**
   - Cloud Functions Gen2 を使用
   - 最小インスタンス数を設定

2. **キャッシュの活用**
   - TTS の音声ファイルをキャッシュ
   - Firestore のキャッシュ機能を活用

3. **非同期処理**
   - 重い処理は非同期で実行
   - Cloud Tasks や Pub/Sub の活用を検討

## 監視とアラート

1. **Cloud Monitoring の設定**
   ```bash
   # アラートポリシーの作成
   gcloud alpha monitoring policies create \
     --notification-channels=[CHANNEL_ID] \
     --display-name="Function Error Rate" \
     --condition-display-name="Error rate > 5%" \
     --condition-threshold-value=0.05
   ```

2. **ダッシュボードの作成**
   - Cloud Console でカスタムダッシュボードを作成
   - 主要メトリクスを可視化

## バックアップとリカバリ

1. **Firestore のバックアップ**
   ```bash
   # 定期バックアップの設定
   gcloud firestore backups schedules create \
     --database='(default)' \
     --recurrence=daily \
     --retention=7d
   ```

2. **Cloud Functions のバージョン管理**
   - Git でソースコードを管理
   - デプロイ前にタグを作成

## 次のステップ

1. CI/CD パイプラインの構築
2. 本番環境向けの設定
3. スケーリング戦略の策定
4. 災害復旧計画の作成