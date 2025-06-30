#!/bin/bash
# 全エンドポイントをデプロイするスクリプト

PROJECT_ID="YOUR_PROJECT_ID"
REGION="asia-northeast1"
RUNTIME="python312"

echo "🚀 Cloud Functions デプロイ開始..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# プロジェクト設定
gcloud config set project $PROJECT_ID

# 共通オプション
COMMON_OPTS="--runtime $RUNTIME --region $REGION --memory 1GB --timeout 60s --trigger-http --allow-unauthenticated --no-gen2"
ENV_VARS="UPLOAD_BUCKET=${PROJECT_ID}.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001"

echo ""
echo "1️⃣ Deploying transcribe..."
gcloud functions deploy transcribe \
  $COMMON_OPTS \
  --entry-point transcribe \
  --set-env-vars $ENV_VARS

echo ""
echo "2️⃣ Deploying chat..."
gcloud functions deploy chat \
  $COMMON_OPTS \
  --entry-point chat \
  --set-env-vars $ENV_VARS

echo ""
echo "3️⃣ Deploying get_drinks_master..."
gcloud functions deploy get_drinks_master \
  $COMMON_OPTS \
  --entry-point get_drinks_master \
  --set-env-vars $ENV_VARS

echo ""
echo "4️⃣ Deploying add_drink..."
gcloud functions deploy add_drink \
  $COMMON_OPTS \
  --entry-point add_drink \
  --set-env-vars $ENV_VARS

echo ""
echo "5️⃣ Deploying start_session..."
gcloud functions deploy start_session \
  $COMMON_OPTS \
  --entry-point start_session \
  --set-env-vars $ENV_VARS

echo ""
echo "6️⃣ Deploying get_current_session..."
gcloud functions deploy get_current_session \
  $COMMON_OPTS \
  --entry-point get_current_session \
  --set-env-vars $ENV_VARS

echo ""
echo "7️⃣ Deploying guardian_check..."
gcloud functions deploy guardian_check \
  $COMMON_OPTS \
  --entry-point guardian_check \
  --set-env-vars $ENV_VARS

echo ""
echo "✅ デプロイ完了!"
echo ""
echo "📌 エンドポイント一覧:"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/transcribe"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/chat"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/get_drinks_master"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/add_drink"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/start_session"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/get_current_session"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/guardian_check"