# 🎯 音声転写エンドポイント テスト手順書（共同開発者向け）

## 📢 実装完了報告

音声転写エンドポイントの実装が完了しました！
以下の手順に従ってテストを実行してください。

---

## 🚀 クイックスタート

### 最初に確認すること
✅ **エンドポイントURL**: `https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/transcribe`  
✅ **認証**: Firebase ID Token必須  
✅ **入力**: multipart/form-data（音声ファイル）  
✅ **出力**: JSON形式の転写結果  

---

## 📱 Method 1: Flutterアプリでのテスト（推奨）

### 1. 環境準備
```bash
# プロジェクトルートに移動
cd mobile

# 依存関係確認
flutter pub get

# 利用可能なデバイス確認
flutter devices
```

### 2. アプリ起動
```bash
# macOSで起動（推奨）
flutter run -d macos

# または iOSデバイス
flutter run -d satory074_iPhone_SE3

# または Webブラウザ
flutter run -d chrome
```

### 3. テスト手順
1. **アプリ起動確認**
   - "音声文字起こしテスト" タイトルが表示される
   - "音声ファイルを選択" ボタンが表示される

2. **音声ファイル選択**
   - ボタンをタップ
   - ファイル選択ダイアログが開く
   - 音声ファイル（.wav, .mp3, .m4a等）を選択

3. **処理確認**
   - "処理中..." 表示に変わる
   - ローディングインジケーターが表示される
   - 数秒〜数十秒で完了

4. **結果確認**
   - カード内に転写結果が表示される
   - 日本語音声なら日本語テキスト
   - 英語音声なら英語テキスト

### 4. テスト用音声ファイル作成
```bash
# macOSの場合
say "これは音声転写のテストです。正常に動作していることを確認します。" -o test_japanese.wav

# 英語版
say "This is a test for voice transcription. Please confirm it works correctly." -o test_english.wav -v Alex
```

---

## 🧪 Method 2: cURLでの直接テスト

### 1. Firebase認証トークン取得
**Web Console を使用**:
```javascript
// ブラウザのコンソールで実行
firebase.auth().signInAnonymously().then(async () => {
  const token = await firebase.auth().currentUser.getIdToken();
  console.log('Token:', token);
});
```

### 2. cURLテスト実行
```bash
# 環境変数設定
export FUNCTION_URL="https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/transcribe"
export ID_TOKEN="YOUR_FIREBASE_ID_TOKEN"

# 音声ファイルアップロード
curl -X POST $FUNCTION_URL \
  -F "file=@test_japanese.wav" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: multipart/form-data"
```

### 3. 期待するレスポンス
```json
{
  "message": "Transcription successful (direct bytes).",
  "original_filename": "test_japanese.wav", 
  "transcript": "これは音声転写のテストです。正常に動作していることを確認します。"
}
```

---

## ⚠️ エラーケーステスト

### 1. 認証エラー
```bash
# トークンなし
curl -X POST $FUNCTION_URL -F "file=@test.wav"
# 期待結果: {"code": "UNAUTHORIZED", "message": "Authorization token required"}

# 無効なトークン
curl -X POST $FUNCTION_URL -F "file=@test.wav" -H "Authorization: Bearer invalid"
# 期待結果: {"code": "UNAUTHORIZED", "message": "Invalid token"}
```

### 2. ファイルエラー
```bash
# ファイルなし
curl -X POST $FUNCTION_URL -H "Authorization: Bearer $ID_TOKEN"
# 期待結果: {"code": "BAD_REQUEST", "message": "No file part in the request"}
```

### 3. CORS確認
```bash
curl -X OPTIONS $FUNCTION_URL \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type"
# 期待結果: 204 No Content + CORS headers
```

---

## 🔧 トラブルシューティング

### Flutter アプリの問題

#### ❌ "認証トークンが取得できません"
**原因**: Firebase初期化エラー
**解決法**: 
1. `flutter clean && flutter pub get` 実行
2. Firebase設定ファイル確認
3. アプリ再起動

#### ❌ "APIエラー: DioException"
**原因**: ネットワークまたはエンドポイントエラー
**解決法**:
1. インターネット接続確認
2. エンドポイントURLの確認
3. Firebase認証状態の確認

#### ❌ ファイル選択ダイアログが表示されない
**原因**: プラットフォーム権限不足
**解決法**:
- macOS: システム設定でアプリ権限確認
- iOS: Info.plist権限設定確認

### cURL テストの問題

#### ❌ "Invalid token"
**解決法**:
1. トークンの有効期限確認（1時間）
2. 新しいトークンを取得
3. Bearerプレフィックス確認

#### ❌ "Connection refused"
**解決法**:
1. エンドポイントURL確認
2. Cloud Functions状態確認: `gcloud functions describe transcribe --region=asia-northeast1`

---

## 📊 テストチェックリスト

### 基本機能
- [ ] Flutterアプリが起動する
- [ ] ファイル選択ダイアログが開く
- [ ] 音声ファイルをアップロードできる
- [ ] 転写結果が表示される
- [ ] エラーメッセージが適切に表示される

### セキュリティ
- [ ] 認証なしでアクセスが拒否される
- [ ] 無効なトークンでアクセスが拒否される
- [ ] CORS設定が正常に動作する

### パフォーマンス
- [ ] 短い音声（5秒）: 10秒以内で完了
- [ ] 中程度の音声（30秒）: 30秒以内で完了
- [ ] 大きなファイル（5MB+）: エラーまたは適切な処理

### 対応形式
- [ ] .wav ファイル
- [ ] .mp3 ファイル  
- [ ] .m4a ファイル
- [ ] 日本語音声
- [ ] 英語音声

---

## 🎯 テスト結果報告

テスト完了後、以下の情報を共有してください：

### 成功ケース
- 使用したプラットフォーム（macOS/iOS/Web）
- テストした音声ファイル形式
- 転写精度の感想
- 処理時間

### 問題・改善点
- エラーメッセージとその状況
- UI/UXの改善提案
- パフォーマンスの問題

### 報告フォーマット例
```
## テスト結果
- **プラットフォーム**: macOS
- **音声形式**: .wav (日本語, 10秒)
- **結果**: ✅ 成功
- **処理時間**: 約8秒
- **転写精度**: 良好
- **問題**: なし
```

---

## 📞 サポート

問題が発生した場合：
1. 上記トラブルシューティングを確認
2. ログ確認: `gcloud functions logs read transcribe --region=YOUR_REGION --limit=20`
3. 具体的なエラーメッセージを添えて報告

---

**Happy Testing! 🚀**