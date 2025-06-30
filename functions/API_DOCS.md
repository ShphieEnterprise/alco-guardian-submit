# Alco Guardian API ドキュメント

## 概要

Alco Guardian APIは、AI Bartenderチャット機能と音声合成機能を提供するREST APIです。

## ベースURL

```
https://asia-northeast1-alco-guardian.cloudfunctions.net
```

## エンドポイント

### 1. Bartender Chat API

AI Bartenderとチャットを行うエンドポイント。

#### エンドポイント
```
POST /chat
```

#### リクエスト

**Headers:**
```
Content-Type: application/json
Authorization: Bearer {ID_TOKEN} (オプション - 開発中はスキップ可)
```

**Body:**
```json
{
  "message": "ユーザーからのメッセージ",
  "enableTTS": true  // 音声生成を有効にするか（デフォルト: true）
}
```

#### レスポンス

**成功時 (200 OK):**
```json
{
  "success": true,
  "message": "Bartenderからの返答",
  "imageId": 5,  // 1-10のランダムな画像ID
  "timestamp": "2024-06-28T12:34:56.789Z",
  "agent": "bartender",
  "audioUrl": "https://storage.googleapis.com/alco-guardian-uploads/tts/ja-JP-Neural2-B/abc123.mp3"  // enableTTS=trueの場合
}
```

**エラー時 (400/401/500):**
```json
{
  "code": "ERROR_CODE",
  "message": "エラーメッセージ"
}
```

#### 使用例

```bash
curl -X POST "https://asia-northeast1-alco-guardian.cloudfunctions.net/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "今日は疲れたから、リラックスできるお酒を教えて",
    "enableTTS": true
  }'
```

### 2. Text-to-Speech API

テキストを音声に変換するエンドポイント。

#### エンドポイント
```
POST /tts
```

#### リクエスト

**Headers:**
```
Content-Type: application/json
Authorization: Bearer {ID_TOKEN} (オプション - 開発中はスキップ可)
```

**Body:**
```json
{
  "text": "音声に変換するテキスト",
  "voice": "ja-JP-Neural2-B"  // オプション（デフォルト: ja-JP-Neural2-B）
}
```

#### レスポンス

**成功時 (200 OK):**
```json
{
  "success": true,
  "audioUrl": "https://storage.googleapis.com/alco-guardian-uploads/tts/ja-JP-Neural2-B/xyz789.mp3",
  "cached": false,  // キャッシュから取得したか
  "filename": "tts/ja-JP-Neural2-B/xyz789.mp3",
  "duration": 3.5  // 音声の長さ（秒）- 概算値
}
```

**エラー時 (400/401/500):**
```json
{
  "code": "ERROR_CODE",
  "message": "エラーメッセージ"
}
```

#### 使用例

```bash
curl -X POST "https://asia-northeast1-alco-guardian.cloudfunctions.net/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは！今日はどんなお酒を楽しみましょうか？"
  }'
```

### 3. Drink Record API

飲酒記録を登録するエンドポイント。

#### エンドポイント
```
POST /drink
```

#### リクエスト

**Headers:**
```
Content-Type: application/json
Authorization: Bearer {ID_TOKEN} (オプション - 開発中はスキップ可)
```

**Body:**
```json
{
  "drinkType": "ビール",  // "ビール" | "ハイボール" | "その他"
  "alcoholPercentage": 5,  // アルコール度数 (%)
  "volume": 350  // 飲酒量 (ml)
}
```

#### レスポンス

**成功時 (200 OK):**
```json
{
  "success": true,
  "message": "飲酒記録を登録しました",
  "data": {
    "id": "drink_abc123",
    "drinkType": "ビール",
    "alcoholPercentage": 5,
    "volume": 350,
    "timestamp": "2024-06-29T12:34:56.789Z",
    "userId": "user123"
  }
}
```

**エラー時 (400/401/500):**
```json
{
  "code": "ERROR_CODE",
  "message": "エラーメッセージ"
}
```

#### 使用例

```bash
curl -X POST "https://asia-northeast1-alco-guardian.cloudfunctions.net/drink" \
  -H "Content-Type: application/json" \
  -d '{
    "drinkType": "ビール",
    "alcoholPercentage": 5,
    "volume": 350
  }'
```

### 4. Transcribe API（既存）

音声ファイルをテキストに変換するエンドポイント。

#### エンドポイント
```
POST /transcribe
```

（詳細は省略 - 既存のドキュメントを参照）

## 特徴

### AI応答生成
- Gemini 2.0 Flashモデルを使用
- コンテキストに応じた自然な会話
- 時刻・曜日を考慮した返答
- 健康的な飲み方を促すガイドライン

### 音声合成
- Google Cloud Text-to-Speech APIを使用
- 高品質な日本語Neural2音声
- 音声ファイルの自動キャッシュ（24時間）
- MP3形式で提供

### 画像ID
- 1-10のランダムな画像IDを返却
- フロントエンドでBartenderのアバター表示に使用

## エラーコード

| コード | 説明 |
|--------|------|
| BAD_REQUEST | リクエストパラメータが不正 |
| UNAUTHORIZED | 認証エラー（本番環境） |
| INTERNAL_ERROR | サーバー内部エラー |

## 制限事項

- TTSテキストは最大1000文字
- リクエストタイムアウト: 60秒
- 音声ファイルキャッシュ: 24時間

## 開発者向け情報

### テストモード
開発中は認証をスキップして`test-user`として処理されます。

### CORS
すべてのオリジンからのアクセスを許可（開発環境）。本番環境では特定のドメインに制限することを推奨。

### 音声URL
音声ファイルは公開URLとして提供されます。本番環境では署名付きURLの使用を検討してください。