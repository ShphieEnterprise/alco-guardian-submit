#!/bin/bash

# Bartenderエージェントのテストスクリプト

echo "================================"
echo "Bartender Agent テスト"
echo "================================"

# エンドポイントURL
CHAT_URL="https://asia-northeast1-alco-guardian.cloudfunctions.net/chat"

# 1. 認証なしでテスト（401エラーが期待される）
echo -e "\n1. 認証なしでテスト:"
curl -X POST $CHAT_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "こんばんは！"}' \
  -w "\nHTTP Status: %{http_code}\n"

echo -e "\n================================"
echo "テスト完了"
echo "期待される結果: HTTP Status 401 (Unauthorized)"
echo "================================"