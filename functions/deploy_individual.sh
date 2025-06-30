#!/bin/bash

# 個別デプロイスクリプト
PROJECT_ID="alco-guardian"
REGION="asia-northeast1"
UPLOAD_BUCKET="alco-guardian-uploads"

echo "🚀 個別デプロイを開始します..."

# 1. bartender-chat関数をデプロイ
echo "🍸 bartender-chat関数をデプロイ中..."
gcloud functions deploy bartender-chat \
  --gen2 \
  --runtime=python312 \
  --region=$REGION \
  --source=. \
  --entry-point=chat \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT=$PROJECT_ID,UPLOAD_BUCKET=$UPLOAD_BUCKET,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001" \
  --memory=512MB \
  --timeout=60s

echo "✅ bartender-chat関数のデプロイ完了"
echo "エンドポイント: https://$REGION-$PROJECT_ID.cloudfunctions.net/bartender-chat"