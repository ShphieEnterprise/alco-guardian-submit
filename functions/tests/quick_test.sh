#!/bin/bash

# 簡単なテストスクリプト

echo "================================"
echo "Cloud Functions 簡易テスト"
echo "================================"

# 1. 認証なしでテスト（401エラーが期待される）
echo -e "\n1. 認証なしでテスト:"
curl -X POST \
  -F "file=@test_audio.m4a" \
  -H "Content-Type: multipart/form-data" \
  https://asia-northeast1-alco-guardian.cloudfunctions.net/transcribe \
  -w "\nHTTP Status: %{http_code}\n"

echo -e "\n================================"
echo "テスト完了"
echo "期待される結果: HTTP Status 401 (Unauthorized)"
echo "これは認証が正しく動作していることを示しています"
echo "================================"