# 🧪 バックエンド動作確認ガイド

## 1. 🚀 クイックテスト（1分で確認）

### ブラウザで確認
以下のURLをブラウザで開いて、JSONが表示されればOK：

```
https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/get_drinks_master
```

期待される表示：
```json
{
  "beer": {"name": "ビール", "alcohol": 5, "volume": 350, "category": "beer"},
  "wine": {"name": "ワイン", "alcohol": 12, "volume": 125, "category": "wine"},
  ...
}
```

## 2. 📱 実機テスト（5分で全機能確認）

### 方法A: Pythonスクリプト実行
```bash
cd functions/tests
python3 backend_integration_test.py
```

### 方法B: シェルスクリプトでデモ実行
```bash
cd functions/tests
./demo_scenario.sh
```

## 3. 🎯 手動テスト（個別機能確認）

### 1️⃣ Bartenderとチャット
```bash
curl -X POST https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "こんばんは！"}'
```

### 2️⃣ セッション開始
```bash
curl -X POST https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/start_session
```

### 3️⃣ ドリンク追加（Guardian連携確認）
```bash
# ビールを追加
curl -X POST https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/add_drink \
  -H "Content-Type: application/json" \
  -d '{"drink_id": "beer"}'

# 返答に guardian フィールドがあることを確認
```

### 4️⃣ Guardian状態確認
```bash
curl https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/guardian_check
```

### 5️⃣ 現在のセッション情報
```bash
curl https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/get_current_session
```

## 4. ✅ チェックリスト

- [ ] `/get_drinks_master` - 6種類のドリンクデータが返る
- [ ] `/chat` - Bartenderから日本語の返答がある
- [ ] `/start_session` - セッションIDが返る（または既存エラー）
- [ ] `/add_drink` - 純アルコール量とguardian判定が返る
- [ ] `/guardian_check` - level（色）とstatsが返る
- [ ] `/get_current_session` - アクティブセッション情報が返る
- [ ] Guardian警告 - 3杯目あたりで黄色/オレンジ警告
- [ ] Bartender拒否 - 飲み過ぎ時に「水を飲もう」的な返答

## 5. 🔥 トラブルシューティング

### CORSエラーが出る場合
→ バックエンドは正常。Flutterアプリからのアクセス時のみ発生

### 401 Unauthorized
→ 認証不要のデモモードで動作中。正常です

### guardian フィールドが空
→ ADKのインポートエラーの可能性。フォールバックで動作中

## 6. 📊 期待される動作フロー

1. **初回**: Guardian = 緑（適正）
2. **2杯目（30分以内）**: Guardian = 黄（注意）
3. **3杯目（純アルコール30g超）**: Guardian = オレンジ/赤（警告）
4. **追加注文時**: Bartenderが拒否メッセージ

これで動作確認は完璧です！ 🎉