#!/bin/bash
# 新しい関数のみをデプロイ（Gen2で統一）

PROJECT_ID="YOUR_PROJECT_ID"
REGION="asia-northeast1"
RUNTIME="python312"

echo "🚀 新規関数のみデプロイ開始..."

# 共通オプション（Gen2を使用）
COMMON_OPTS="--runtime $RUNTIME --region $REGION --memory 1GB --timeout 60s --trigger-http --allow-unauthenticated --gen2"
ENV_VARS="UPLOAD_BUCKET=${PROJECT_ID}.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001"

# 新規関数のみデプロイ
FUNCTIONS=(
  "get_drinks_master"
  "add_drink"
  "start_session"
  "get_current_session"
  "guardian_check"
)

for func in "${FUNCTIONS[@]}"; do
  echo ""
  echo "📦 Deploying $func..."
  gcloud functions deploy $func \
    $COMMON_OPTS \
    --entry-point $func \
    --set-env-vars $ENV_VARS \
    --source . \
    --project $PROJECT_ID
done

echo ""
echo "✅ デプロイ完了!"
echo ""
echo "🧪 動作確認:"
echo "curl https://$REGION-$PROJECT_ID.cloudfunctions.net/get_drinks_master"