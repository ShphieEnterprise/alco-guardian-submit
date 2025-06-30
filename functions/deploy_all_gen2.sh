#!/bin/bash
# 全エンドポイントをGen2でデプロイ（新機能含む）

PROJECT_ID="YOUR_PROJECT_ID"
REGION="asia-northeast1"
RUNTIME="python312"

echo "🚀 Cloud Functions デプロイ開始 (Gen2)..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# プロジェクト設定
gcloud config set project $PROJECT_ID

# 共通オプション（Gen2を使用）
COMMON_OPTS="--runtime $RUNTIME --region $REGION --memory 1GB --timeout 60s --trigger-http --allow-unauthenticated --gen2"
ENV_VARS="UPLOAD_BUCKET=${PROJECT_ID}.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001"

# 全関数リスト
FUNCTIONS=(
  "transcribe"
  "chat"
  "get_drinks_master"
  "add_drink"
  "start_session"
  "get_current_session"
  "guardian_check"
  "bartender"
  "guardian_monitor"
  "drinking_coach_analyze"
  "tts"
)

# デプロイ実行
for i in "${!FUNCTIONS[@]}"; do
  func="${FUNCTIONS[$i]}"
  echo ""
  echo "$((i+1))️⃣ Deploying $func..."
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
echo "📌 エンドポイント一覧:"
for func in "${FUNCTIONS[@]}"; do
  echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/$func"
done