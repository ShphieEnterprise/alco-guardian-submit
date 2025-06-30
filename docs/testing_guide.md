# 音声転写エンドポイント テスト手順書

## 概要

このドキュメントでは、音声転写エンドポイント (`/transcribe`) の包括的なテスト手順を説明します。

### エンドポイント仕様
- **URL**: `https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/transcribe`
- **メソッド**: POST
- **認証**: Firebase ID Token (Bearer Token)
- **入力**: multipart/form-data で音声ファイル
- **出力**: JSON形式の転写結果

---

## 1. 事前準備

### 必要なツール
- curl
- Node.js (ローカルテスト用)
- Firebase CLI
- gcloud CLI
- テスト用音声ファイル

### 環境変数設定
```bash
export GCP_PROJECT=alco-guardian-test-satory074
export UPLOAD_BUCKET=${GCP_PROJECT}-audio
export GEMINI_LOCATION=asia-northeast1
export GEMINI_MODEL=gemini-2.0-flash-001
```

### テスト用音声ファイル準備
以下の形式のサンプルファイルを用意：
- `test_short.wav` (5秒以内、日本語音声)
- `test_medium.mp3` (30秒程度、英語音声)
- `test_large.wav` (5MB以上、長時間音声)
- `test_invalid.txt` (音声以外のファイル)

---

## 2. ローカル環境テスト

### 2.1 Functions Framework起動
```bash
cd functions
pip install -r requirements.txt
functions-framework --target=transcribe --debug --port=8080
```

### 2.2 基本動作確認

#### CORS確認
```bash
curl -X OPTIONS http://localhost:8080 \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type" \
  -v
```

**期待結果**: 204 No Content + CORS ヘッダー

#### 音声ファイルアップロード（認証なし）
```bash
curl -X POST http://localhost:8080 \
  -F "file=@test_short.wav" \
  -H "Content-Type: multipart/form-data" \
  -v
```

**期待結果**: 200 OK + 転写結果JSON

---

## 3. 認証テスト

### 3.1 Firebase IDトークン取得

#### Flutter アプリから取得
```dart
final user = FirebaseAuth.instance.currentUser;
final idToken = await user!.getIdToken();
print('ID Token: $idToken');
```

#### Web コンソールから取得
```javascript
// Firebase Web SDK
firebase.auth().onAuthStateChanged(async (user) => {
  if (user) {
    const token = await user.getIdToken();
    console.log('ID Token:', token);
  }
});
```

### 3.2 認証付きリクエスト
```bash
ID_TOKEN="YOUR_FIREBASE_ID_TOKEN"

curl -X POST http://localhost:8080 \
  -F "file=@test_short.wav" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: multipart/form-data"
```

**期待結果**: 200 OK + 転写結果JSON + ログにユーザーUID表示

---

## 4. デプロイ後テスト

### 4.1 デプロイ
```bash
cd functions
gcloud functions deploy transcribe \
  --gen2 \
  --region asia-northeast1 \
  --runtime python311 \
  --source . \
  --entry-point transcribe \
  --trigger-http \
  --memory 1Gi \
  --timeout 120s \
  --no-allow-unauthenticated \
  --set-env-vars VERTEX_LOCATION=us-central1,VERTEX_MODEL=gemini-2.0-flash-001,UPLOAD_BUCKET=${GCP_PROJECT}-audio
```

### 4.2 デプロイ確認
```bash
gcloud functions describe transcribe --region=asia-northeast1
```

### 4.3 本番環境テスト
```bash
FUNCTION_URL="https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/transcribe"
ID_TOKEN="YOUR_FIREBASE_ID_TOKEN"

curl -X POST $FUNCTION_URL \
  -F "file=@test_short.wav" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: multipart/form-data"
```

---

## 5. エラーケーステスト

### 5.1 必須エラーパターン

#### ファイル未指定エラー
```bash
curl -X POST $FUNCTION_URL \
  -H "Authorization: Bearer $ID_TOKEN"
```
**期待結果**: 400 Bad Request + "No file part in the request"

#### 空ファイル名エラー
```bash
curl -X POST $FUNCTION_URL \
  -F "file=" \
  -H "Authorization: Bearer $ID_TOKEN"
```
**期待結果**: 400 Bad Request + "No selected file"

#### 無効なトークンエラー
```bash
curl -X POST $FUNCTION_URL \
  -F "file=@test_short.wav" \
  -H "Authorization: Bearer invalid_token"
```
**期待結果**: 401 Unauthorized + "Invalid token"

#### 大きすぎるファイルエラー
```bash
# 10MB以上のファイルを作成
dd if=/dev/zero of=large_file.wav bs=1M count=15

curl -X POST $FUNCTION_URL \
  -F "file=@large_file.wav" \
  -H "Authorization: Bearer $ID_TOKEN"
```
**期待結果**: 413 Payload Too Large または 500 Internal Server Error

#### 無効なファイル形式
```bash
echo "テストテキスト" > test_invalid.txt

curl -X POST $FUNCTION_URL \
  -F "file=@test_invalid.txt" \
  -H "Authorization: Bearer $ID_TOKEN"
```
**期待結果**: 処理されるが、転写結果が空またはエラー

---

## 6. Flutter統合テスト

### 6.1 テストファイル作成
`mobile/test/integration_test/transcribe_api_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:mobile/firebase_options.dart';

void main() {
  group('Transcribe API Integration Tests', () {
    setUpAll(() async {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
    });

    test('音声アップロード正常系テスト', () async {
      // Firebase認証（テスト用ユーザーでログイン）
      final credential = await FirebaseAuth.instance.signInAnonymously();
      final idToken = await credential.user!.getIdToken();
      
      // APIコール
      final dio = Dio();
      final response = await dio.post(
        'https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/transcribe',
        data: FormData.fromMap({
          'file': await MultipartFile.fromFile(
            'test/assets/test_audio.wav',
            filename: 'test_audio.wav',
            contentType: DioMediaType('audio', 'wav'),
          ),
        }),
        options: Options(
          headers: {
            'Authorization': 'Bearer $idToken',
          },
        ),
      );
      
      expect(response.statusCode, 200);
      expect(response.data, isA<Map<String, dynamic>>());
      expect(response.data['transcript'], isNotEmpty);
      expect(response.data['message'], contains('successful'));
    });

    test('認証エラーテスト', () async {
      final dio = Dio();
      
      expect(
        () async => await dio.post(
          'https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/transcribe',
          data: FormData.fromMap({
            'file': await MultipartFile.fromFile('test/assets/test_audio.wav'),
          }),
          options: Options(
            headers: {
              'Authorization': 'Bearer invalid_token',
            },
          ),
        ),
        throwsA(isA<DioException>()),
      );
    });
  });
}
```

### 6.2 テスト実行
```bash
cd mobile
flutter test test/integration_test/transcribe_api_test.dart
```

---

## 7. パフォーマンステスト

### 7.1 レスポンス時間測定
```bash
# 単発リクエストの時間測定
time curl -X POST $FUNCTION_URL \
  -F "file=@test_short.wav" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -w "Time: %{time_total}s\n"
```

### 7.2 同時リクエストテスト
```bash
# 5つの同時リクエスト
for i in {1..5}; do
  echo "Starting request $i"
  curl -X POST $FUNCTION_URL \
    -F "file=@test_short.wav" \
    -H "Authorization: Bearer $ID_TOKEN" \
    -w "Request $i: %{time_total}s\n" &
done
wait
echo "All requests completed"
```

### 7.3 負荷テスト（オプション）
```bash
# Apache Bench を使用
ab -n 10 -c 2 -H "Authorization: Bearer $ID_TOKEN" \
   -p test_short.wav -T multipart/form-data \
   $FUNCTION_URL
```

---

## 8. モニタリングとデバッグ

### 8.1 ログ確認
```bash
# 最新のログを確認
gcloud functions logs read transcribe \
  --region=asia-northeast1 \
  --limit=50

# リアルタイムログ監視
gcloud functions logs tail transcribe \
  --region=asia-northeast1
```

### 8.2 メトリクス確認
```bash
# 関数の実行統計
gcloud functions describe transcribe \
  --region=asia-northeast1 \
  --format="table(
    status,
    availableMemoryMb,
    timeout,
    maxInstances,
    minInstances
  )"
```

### 8.3 Cloud Console でのモニタリング
1. [Cloud Console](https://console.cloud.google.com) にアクセス
2. Cloud Functions → transcribe を選択
3. 「メトリクス」タブで以下を確認：
   - 呼び出し回数
   - 実行時間
   - エラー率
   - アクティブインスタンス数

---

## 9. テストチェックリスト

### 基本機能テスト
- [ ] CORS レスポンス正常
- [ ] 音声ファイルアップロード成功
- [ ] 転写結果JSON形式正常
- [ ] Firebase認証動作
- [ ] ログ出力正常

### エラーハンドリングテスト
- [ ] ファイル未指定エラー
- [ ] 空ファイル名エラー
- [ ] 無効認証トークンエラー
- [ ] 大きすぎるファイルエラー
- [ ] 無効ファイル形式処理

### パフォーマンステスト
- [ ] レスポンス時間 < 30秒（短い音声）
- [ ] 同時リクエスト処理可能
- [ ] メモリ使用量適正
- [ ] タイムアウト未発生

### セキュリティテスト
- [ ] 認証なしアクセス拒否
- [ ] 不正トークン拒否
- [ ] CORS設定適正
- [ ] 機密情報ログ出力なし

---

## 10. トラブルシューティング

### よくあるエラーと対処法

#### "PERMISSION_DENIED on GCS"
- Cloud Functions SAにStorage権限付与確認
- バケット名環境変数確認

#### "403 on Gemini"  
- SAに`roles/aiplatform.user`権限確認
- リージョン・モデル名設定確認

#### "Multipart解析エラー"
- Content-Typeヘッダー確認
- ファイル形式・サイズ確認

#### "Invalid ID token"
- トークン期限切れ確認（1時間）
- Firebase プロジェクト設定確認

---

## 付録

### A. サンプル音声ファイル生成
```bash
# macOS/Linux で短いテスト音声生成
say "これはテスト音声です" -o test_japanese.wav
espeak "This is a test audio" -w test_english.wav
```

### B. 環境別設定
```bash
# 開発環境
export FUNCTION_URL="http://localhost:8080"

# ステージング環境  
export FUNCTION_URL="https://asia-northeast1-alco-guardian-staging.cloudfunctions.net/transcribe"

# 本番環境
export FUNCTION_URL="https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/transcribe"
```

---

このテスト手順書に従って、エンドポイントの動作を包括的に検証してください。問題が発見された場合は、ログとエラーメッセージを確認して適切に対処してください。