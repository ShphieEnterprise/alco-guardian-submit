# ハッカソン提出用TODO（6/30締切）

## 🎯 デモシナリオ
「金曜の夜、飲み過ぎを防ぎながら楽しく飲む」3分間のストーリー

## Week 1（6/22-6/28）: コア機能実装

### Day 1-2: 飲酒トラッキング基盤
- [ ] ドリンクマスターデータ作成（ビール、ワイン、日本酒など10種類）
- [ ] `/drinks/add` エンドポイント実装（簡易版）
- [ ] Firestoreに飲酒記録を保存
- [ ] 純アルコール量計算ユーティリティ

### Day 3-4: Guardian実装
- [ ] 飲酒ペース監視ロジック（30分で1ドリンク推奨）
- [ ] 警告メッセージ生成（3段階：注意・警告・停止）
- [ ] BartenderへのVeto機能（飲み過ぎ時は提案を拒否）

### Day 5-6: Flutter UI改善
- [ ] ドリンク選択画面（ボタン式で簡単入力）
- [ ] 本日の飲酒状況ダッシュボード
  - 純アルコール量グラフ
  - ペース表示（適正/注意/危険）
  - Guardian警告表示エリア
- [ ] セッション管理（飲み始め/終了ボタン）

### Day 7: 統合テスト
- [ ] エンドツーエンドのフロー確認
- [ ] デモシナリオの練習

## Week 2（6/29-6/30）: デモ準備

### Day 1: ビジュアル改善
- [ ] アイコン・画像の追加
- [ ] アニメーション追加（警告時の点滅など）
- [ ] ダミーデータでリッチな表示

### Day 2: 発表準備
- [ ] 3分デモ動画の撮影
- [ ] スライド作成（コンセプト説明）
- [ ] GitHub README更新
- [ ] Zenn記事執筆

## 💡 デモ映えする機能

### 1. リアルタイム警告
```dart
// Guardianからの警告をポップアップ表示
showDialog(
  context: context,
  builder: (context) => AlertDialog(
    title: Text('⚠️ Guardianからの警告'),
    content: Text('飲むペースが速すぎます。水を飲みましょう！'),
  ),
);
```

### 2. 飲酒量ビジュアライゼーション
```dart
// 円形プログレスバーで適正量との比較
CircularProgressIndicator(
  value: currentAlcohol / recommendedLimit,
  backgroundColor: Colors.green,
  valueColor: AlwaysStoppedAnimation(
    currentAlcohol > recommendedLimit ? Colors.red : Colors.blue,
  ),
);
```

### 3. Bartender ↔ Guardian 協調デモ
```python
# Guardianがvetoした時のBartenderの応答
if guardian_veto:
    return "今日はもう十分飲んだみたいだね。お水でも飲んで、楽しい話でもしようか！🚰"
```

## 🚫 実装しないもの（時間節約）

- 実際の外部API連携（すべてモック）
- 複雑な認証フロー
- 課金システム
- メール通知
- 多言語対応
- オフライン対応

## 📝 モックデータ例

### drinks_master.json
```json
{
  "drinks": [
    {"id": "beer", "name": "ビール", "alcohol": 5, "volume": 350},
    {"id": "wine", "name": "ワイン", "alcohol": 12, "volume": 125},
    {"id": "sake", "name": "日本酒", "alcohol": 15, "volume": 180},
    {"id": "highball", "name": "ハイボール", "alcohol": 7, "volume": 350}
  ]
}
```

### demo_scenario.json
```json
{
  "timeline": [
    {"time": "19:00", "action": "セッション開始", "message": "今日も一日お疲れ様！"},
    {"time": "19:15", "action": "ビール注文", "guardian": "良いペースですね"},
    {"time": "19:45", "action": "ハイボール注文", "guardian": "少しペースに注意"},
    {"time": "20:00", "action": "日本酒注文", "guardian": "警告：ペースが速すぎます"},
    {"time": "20:15", "action": "追加注文試行", "bartender": "Guardianからストップがかかりました"}
  ]
}
```