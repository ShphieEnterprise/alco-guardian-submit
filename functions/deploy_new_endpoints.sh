#!/bin/bash
# 新規エンドポイントのみデプロイ

PROJECT_ID="YOUR_PROJECT_ID"
REGION="asia-northeast1"
RUNTIME="python312"

echo "🚀 新規エンドポイントのデプロイ開始..."

# プロジェクト設定
gcloud config set project $PROJECT_ID

# 共通オプション（Gen2を使用）
COMMON_OPTS="--runtime $RUNTIME --region $REGION --memory 1GB --timeout 60s --trigger-http --allow-unauthenticated --gen2"
ENV_VARS="UPLOAD_BUCKET=${PROJECT_ID}.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001"

# 新規エンドポイントをデプロイ
ENDPOINTS=(
  "bartender"
  "guardian_monitor" 
  "drinking_coach_analyze"
  "tts"
)

for endpoint in "${ENDPOINTS[@]}"; do
  echo ""
  echo "📦 Deploying $endpoint..."
  gcloud functions deploy $endpoint \
    $COMMON_OPTS \
    --entry-point $endpoint \
    --set-env-vars $ENV_VARS \
    --source . \
    --project $PROJECT_ID
  
  if [ $? -eq 0 ]; then
    echo "✅ $endpoint deployed successfully"
  else
    echo "❌ Failed to deploy $endpoint"
  fi
done

echo ""
echo "✅ デプロイ完了!"
echo ""
echo "📌 新規エンドポイント:"
for endpoint in "${ENDPOINTS[@]}"; do
  echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/$endpoint"
done