# 🎉 新しいバックエンド機能

## 実装した機能

### 1. 画像IDのコンテキストベース決定 🖼️
- Guardian警告レベルに基づいて画像IDを動的に変更
  - 緑（安全）: ID 1-3（楽しそうなバーテンダー）
  - 黄（注意）: ID 4-6（心配そうなバーテンダー）
  - オレンジ/赤（警告）: ID 7-9（真剣なバーテンダー）
  - 赤（危険）: ID 10（水を勧めるバーテンダー）
- 飲み物の種類によっても変化

### 2. 強化された飲酒管理エージェント 🏃
**新しいDrinking Coach Agent**を実装:
- 飲酒ペース分析（g/h）
- 総飲酒量分析（標準ドリンク換算）
- 飲酒パターン検出（間隔、種類の多様性）
- パーソナライズされた推奨事項
- 特別なイベント検出（初回、長時間飲酒など）

### 3. 飲み会風の音声レスポンス 🎤
- カジュアルで親しみやすいメッセージに変更
- ユーザーの状態に応じたレスポンス
  - 疲れている時：「お疲れ様！リフレッシュだね！」
  - 楽しい時：「イェーイ！その調子！」
  - おかわり時：「おかわりきた〜！」
- Guardian警告レベルに応じた口調変化

### 4. 会話履歴の追跡と活用 💬
- Firestoreに会話履歴を保存
- ユーザーのメッセージコンテキストを考慮
- レスポンスの履歴も記録
- 履歴件数をレスポンスに含める

## 使用方法

### エンドポイント
```
POST /drink
```

### リクエスト例
```json
{
  "drinkType": "ビール",
  "alcoholPercentage": 5.0,
  "volume": 350,
  "context": {
    "message": "今日も一日お疲れ様！",
    "history": ["前のメッセージ1", "前のメッセージ2"]
  }
}
```

### レスポンス例
```json
{
  "success": true,
  "message": "お疲れ様！ビールでリフレッシュだね！350ml記録したよ〜",
  "imageId": 1,
  "guardian": {
    "level": {"color": "green", "message": "適正な飲酒"}
  },
  "drinkingCoach": {
    "pace_analysis": {"status": "safe", "current_pace": 8.5},
    "total_analysis": {"status": "light", "total_alcohol_g": 14.0},
    "recommendations": [
      {"type": "info", "message": "良いペースで飲んでいます"}
    ]
  },
  "sessionStats": {
    "totalAlcoholG": 14.0,
    "totalDrinks": 1,
    "sessionDuration": 0
  },
  "conversationContext": {
    "historyLength": 0,
    "lastMessage": "今日も一日お疲れ様！"
  },
  "audioUrl": "https://storage.googleapis.com/..."
}
```

## テスト方法

### 1. 個別テスト
```bash
cd functions/tests
./test_drink_endpoint.py
```

### 2. デプロイ
```bash
cd functions
./deploy_drink.sh
```

### 3. 手動テスト
```bash
curl -X POST https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/drink \
  -H "Content-Type: application/json" \
  -d '{
    "drinkType": "ビール",
    "alcoholPercentage": 5,
    "volume": 350,
    "context": {
      "message": "楽しい飲み会だ！"
    }
  }'
```

## データベース構造の更新

```
users/
  {userId}/
    sessions/
      {sessionId}/
        conversations/  # 新規追加
          {conversationId}/
            - timestamp
            - user_message
            - agent_message
            - agent_type
            - drink_context
            - image_id
            - guardian_level
```

## 注意事項

- 会話履歴は各セッション内で管理
- 画像IDは1-10の範囲で返却
- Drinking Coachの分析は非同期実行も考慮
- エラー時もユーザー体験を損なわないようフォールバック実装済み