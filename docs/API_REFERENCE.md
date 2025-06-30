# API リファレンス

最終更新: 2025-06-30

## 概要

Alco Guardian APIは、AI Bartenderチャット機能、音声処理、飲酒管理機能を提供するREST APIです。すべてのエンドポイントは Google Cloud Functions 上にデプロイされています。

## ベースURL

```
https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net
```

## 認証

- すべてのエンドポイントで認証は**オプション**です（ハッカソン用）
- 認証する場合: `Authorization: Bearer {idToken}`
- 認証しない場合: デモユーザー（`demo_user_001`）として処理されます

## エンドポイント一覧

### 基本機能

#### 1. 音声文字起こし - `/transcribe`
音声ファイルをテキストに変換します。

**Method:** POST  
**Content-Type:** multipart/form-data  
**Request:**
```
- file: 音声ファイル（audio/mpeg, audio/wav等）
```
**Response:**
```json
{
  "message": "Transcription successful (direct bytes).",
  "original_filename": "audio.mp3",
  "transcript": "今日はビールを飲みました"
}
```

#### 2. チャット（Bartender） - `/chat`
AI Bartenderとチャットを行い、音声応答も生成します。

**Method:** POST  
**Content-Type:** application/json  
**Request:**
```json
{
  "message": "今日は疲れたなあ",
  "enableTTS": true  // 音声生成オプション（デフォルト: true）
}
```
**Response:**
```json
{
  "success": true,
  "message": "お疲れ様！今日も一日頑張ったね。ビールでも飲んでリフレッシュしよう！",
  "imageId": 3,  // 1-10のランダムな画像ID
  "timestamp": "2025-06-30T00:00:00Z",
  "agent": "bartender",
  "audioUrl": "https://storage.googleapis.com/..."  // TTS音声URL（enableTTS=trueの場合）
}
```

#### 3. テキスト音声変換 - `/tts`
テキストを音声に変換します。

**Method:** POST  
**Content-Type:** application/json  
**Request:**
```json
{
  "text": "こんにちは！今日も楽しく飲みましょう！",
  "voiceName": "ja-JP-Neural2-B"  // オプション（デフォルト: ja-JP-Neural2-B）
}
```
**Response:**
```json
{
  "success": true,
  "audioUrl": "https://storage.googleapis.com/...",
  "cached": false,  // true=キャッシュから、false=新規生成
  "text": "こんにちは！今日も楽しく飲みましょう！"
}
```

### 飲酒管理

#### 4. 飲み物マスターデータ取得 - `/get_drinks_master`
利用可能な飲み物の一覧を取得します。

**Method:** GET  
**Response:**
```json
{
  "beer": {"name": "ビール", "alcohol": 5, "volume": 350, "category": "beer"},
  "wine": {"name": "ワイン", "alcohol": 12, "volume": 125, "category": "wine"},
  "sake": {"name": "日本酒", "alcohol": 15, "volume": 180, "category": "sake"},
  "highball": {"name": "ハイボール", "alcohol": 7, "volume": 350, "category": "beer"},
  "shochu": {"name": "焼酎水割り", "alcohol": 10, "volume": 200, "category": "shochu"},
  "cocktail": {"name": "カクテル", "alcohol": 15, "volume": 100, "category": "cocktail"}
}
```

#### 5. 飲酒記録追加 - `/add_drink`
飲酒記録を追加し、Guardian分析を取得します。

**Method:** POST  
**Content-Type:** application/json  
**Request:**
```json
{
  "drink_id": "beer",  // drink masterのキー
  "volume_ml": 350     // オプション（省略時はマスターのデフォルト値）
}
```
**Response:**
```json
{
  "success": true,
  "alcohol_g": 14.0,  // 純アルコール量（g）
  "total_alcohol_g": 28.0,  // セッション合計
  "guardian": {
    "level": {
      "color": "yellow",  // green/yellow/orange/red
      "message": "そろそろペースを落としましょう"
    },
    "analysis": "現在のペースは少し速めです"
  }
}
```

#### 6. セッション開始 - `/start_session`
新しい飲酒セッションを開始します。

**Method:** POST  
**Response:**
```json
{
  "session_id": "abc123...",
  "start_time": "2025-06-30T00:00:00Z",
  "message": "飲酒セッションを開始しました。適度に楽しみましょう！"
}
```

#### 7. 現在のセッション取得 - `/get_current_session`
アクティブな飲酒セッションの情報を取得します。

**Method:** GET  
**Response（アクティブなセッションがある場合）:**
```json
{
  "active": true,
  "session_id": "abc123...",
  "start_time": "2025-06-30T00:00:00Z",
  "duration_minutes": 45,
  "total_alcohol_g": 28.0,
  "drinks": [
    {
      "id": "xyz789...",
      "drink_type": "beer",
      "volume_ml": 350,
      "alcohol_g": 14.0,
      "timestamp": {...}
    }
  ],
  "guardian_status": {...},
  "recommendations": [
    "水分補給を忘れずに",
    "おつまみも忘れずに"
  ]
}
```

### エージェント機能

#### 8. Bartenderエージェント - `/bartender`
コンテキストに応じた会話を生成します。

**Method:** POST  
**Content-Type:** application/json  
**Request:**
```json
{
  "message": "最近どう？",
  "context": {  // オプション
    "mood": "happy",
    "recent_drinks": ["beer"]
  }
}
```
**Response:**
```json
{
  "message": "いい感じだね！今日も楽しく飲もう！",
  "imageId": 2,
  "timestamp": "2025-06-30T00:00:00Z"
}
```

#### 9. Guardian状態チェック - `/guardian_check`
現在の飲酒状態をチェックします。

**Method:** GET  
**Response:**
```json
{
  "level": {
    "color": "green",  // green/yellow/orange/red
    "message": "適度に楽しんでいます"
  },
  "stats": {
    "total_alcohol_g": 14.0,
    "drinks_count": 2,
    "duration_minutes": 30
  }
}
```

#### 10. Guardian監視 - `/guardian_monitor`
飲酒状態の継続的な監視を行います。

**Method:** POST  
**Response:**
```json
{
  "success": true,
  "user_id": "demo_user_001",
  "session_id": "abc123...",
  "guardian_status": {
    "level": {
      "color": "green",
      "message": "適度に楽しんでいます。"
    },
    "total_alcohol_g": 14.0,
    "recommendations": [
      "水分補給を忘れずに",
      "適度なペースで楽しみましょう"
    ]
  }
}
```

#### 11. 飲酒コーチ分析 - `/drinking_coach_analyze`
詳細な飲酒パターン分析を提供します。

**Method:** POST  
**Response:**
```json
{
  "success": true,
  "user_id": "demo_user_001",
  "session_id": "abc123...",
  "analysis": {
    "pace": "良いペースです",
    "total_drinks": 2,
    "total_alcohol_g": 28.0,
    "recommendations": [
      "水分補給を忘れずに",
      "おつまみも食べながら楽しみましょう",
      "適度なペースで楽しみましょう"
    ]
  }
}
```

## 画像IDとBartenderの状態

画像IDは1-10で、Guardian警告レベルに応じて自動選択されます：
- **1-3**: 通常/楽しい状態（緑）
- **4-6**: 少し心配（黄）
- **7-9**: 警告モード（橙）
- **10**: 水を勧める（赤）

## エラーレスポンス

すべてのエンドポイントで共通のエラー形式：
```json
{
  "code": "ERROR_CODE",
  "message": "エラーの説明"
}
```

主なエラーコード：
- `BAD_REQUEST`: リクエストパラメータエラー
- `UNAUTHORIZED`: 認証エラー（認証を使用する場合）
- `INTERNAL_ERROR`: サーバー内部エラー

## 制限事項

- TTSテキストは最大1000文字
- リクエストタイムアウト: 60秒
- 音声ファイルキャッシュ: 24時間
- 音声ファイルは10MB以下を推奨

## CORS設定

すべてのエンドポイントでCORS対応済み：
- Access-Control-Allow-Origin: *
- Access-Control-Allow-Methods: POST,OPTIONS,GET
- Access-Control-Allow-Headers: Authorization,Content-Type

## 推奨実装フロー

1. **初回起動時**: `/start_session`でセッション開始
2. **音声入力時**: `/transcribe` → `/chat`で会話
3. **飲酒記録時**: `/add_drink` → Guardian警告を表示
4. **定期的に**: `/guardian_check`で状態確認
5. **セッション情報**: `/get_current_session`で取得

## 純アルコール計算の仕様

純アルコール量（g）= 飲酒量(ml) × アルコール度数(%) ÷ 100 × 0.8

例:
- ビール350ml (5%) = 14.0g
- ワイン125ml (12%) = 12.0g
- 日本酒180ml (15%) = 21.6g

適正飲酒の目安: 1日20g以下（厚生労働省ガイドライン準拠）