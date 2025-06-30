#!/bin/bash

# APIテストスクリプト
BASE_URL="https://asia-northeast1-alco-guardian.cloudfunctions.net"

echo "🧪 API テストを開始します..."
echo ""

# 1. Bartender Chat APIのテスト（認証なしバージョン）
echo "1️⃣ Bartender Chat API テスト"
echo "================================"
echo "リクエスト:"
echo 'curl -X POST "'$BASE_URL'/chat" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"message": "今日は疲れたから、リラックスできるお酒を教えて", "enableTTS": true}'"'"''
echo ""
echo "レスポンス:"
curl -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "今日は疲れたから、リラックスできるお酒を教えて", "enableTTS": true}' \
  2>/dev/null | python3 -m json.tool

echo ""
echo ""

# 2. TTS APIのテスト（認証なしバージョン）
echo "2️⃣ TTS API テスト"
echo "================="
echo "リクエスト:"
echo 'curl -X POST "'$BASE_URL'/tts" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"text": "こんにちは！今日はどんなお酒を楽しみましょうか？"}'"'"''
echo ""
echo "レスポンス:"
curl -X POST "$BASE_URL/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは！今日はどんなお酒を楽しみましょうか？"}' \
  2>/dev/null | python3 -m json.tool

echo ""
echo ""

# 3. 異なるメッセージでのBartenderテスト
echo "3️⃣ Bartender Chat API テスト（別メッセージ）"
echo "=========================================="
echo "リクエスト:"
echo 'curl -X POST "'$BASE_URL'/chat" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"message": "ビールが飲みたい気分だけど、何かおすすめある？", "enableTTS": false}'"'"''
echo ""
echo "レスポンス:"
curl -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "ビールが飲みたい気分だけど、何かおすすめある？", "enableTTS": false}' \
  2>/dev/null | python3 -m json.tool

echo ""
echo "✅ テスト完了！"