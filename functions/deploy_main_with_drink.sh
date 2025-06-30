#!/bin/bash
# main.pyのchatとdrink関数をデプロイ

PROJECT_ID="alco-guardian"
REGION="asia-northeast1"
RUNTIME="python312"

echo "🚀 Deploying main.py functions (chat and drink)..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# プロジェクト設定
gcloud config set project $PROJECT_ID

# 環境変数
ENV_VARS="GCP_PROJECT=$PROJECT_ID,UPLOAD_BUCKET=$PROJECT_ID-uploads,STORAGE_BUCKET=$PROJECT_ID-tts,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001,LOG_LEVEL=INFO"

# chat関数のデプロイ
echo ""
echo "📦 Deploying chat function..."
gcloud functions deploy chat \
  --runtime $RUNTIME \
  --region $REGION \
  --memory 512MB \
  --timeout 60s \
  --trigger-http \
  --allow-unauthenticated \
  --gen2 \
  --entry-point chat \
  --set-env-vars $ENV_VARS \
  --source . \
  --project $PROJECT_ID

# drink関数のデプロイ
echo ""
echo "🍺 Deploying drink function..."
gcloud functions deploy drink \
  --runtime $RUNTIME \
  --region $REGION \
  --memory 512MB \
  --timeout 60s \
  --trigger-http \
  --allow-unauthenticated \
  --gen2 \
  --entry-point drink \
  --set-env-vars $ENV_VARS \
  --source . \
  --project $PROJECT_ID

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📌 Endpoints:"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/chat"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/drink"