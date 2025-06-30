#!/bin/bash
# 最終デプロイスクリプト

PROJECT_ID="YOUR_PROJECT_ID"
REGION="asia-northeast1"
RUNTIME="python312"

echo "🚀 Cloud Functions デプロイ開始..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# プロジェクト設定
gcloud config set project $PROJECT_ID

# 共通オプション（Gen2を使用）
COMMON_OPTS="--runtime $RUNTIME --region $REGION --memory 1GB --timeout 60s --trigger-http --allow-unauthenticated --gen2"
ENV_VARS="UPLOAD_BUCKET=${PROJECT_ID}.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001"

echo ""
echo "========== 新規エンドポイントのデプロイ =========="

# bartenderエンドポイント
echo ""
echo "1️⃣ Deploying bartender..."
gcloud functions deploy bartender \
  $COMMON_OPTS \
  --entry-point bartender \
  --set-env-vars $ENV_VARS \
  --source .

# guardian_monitorエンドポイント  
echo ""
echo "2️⃣ Deploying guardian_monitor..."
gcloud functions deploy guardian_monitor \
  $COMMON_OPTS \
  --entry-point guardian_monitor \
  --set-env-vars $ENV_VARS \
  --source .

# drinking_coach_analyzeエンドポイント
echo ""
echo "3️⃣ Deploying drinking_coach_analyze..."
gcloud functions deploy drinking_coach_analyze \
  $COMMON_OPTS \
  --entry-point drinking_coach_analyze \
  --set-env-vars $ENV_VARS \
  --source .

# ttsエンドポイント
echo ""
echo "4️⃣ Deploying tts..."
gcloud functions deploy tts \
  $COMMON_OPTS \
  --entry-point tts \
  --set-env-vars $ENV_VARS \
  --source .

echo ""
echo "========== Gen1関数の更新 =========="

# Gen1関数用のオプション
GEN1_OPTS="--runtime $RUNTIME --region $REGION --memory 1GB --timeout 60s --trigger-http --allow-unauthenticated --no-gen2"

# start_session
echo ""
echo "5️⃣ Deploying start_session (Gen1)..."
gcloud functions deploy start_session \
  $GEN1_OPTS \
  --entry-point start_session \
  --set-env-vars $ENV_VARS

# get_current_session
echo ""
echo "6️⃣ Deploying get_current_session (Gen1)..."  
gcloud functions deploy get_current_session \
  $GEN1_OPTS \
  --entry-point get_current_session \
  --set-env-vars $ENV_VARS

# get_drinks_master
echo ""
echo "7️⃣ Deploying get_drinks_master (Gen1)..."
gcloud functions deploy get_drinks_master \
  $GEN1_OPTS \
  --entry-point get_drinks_master \
  --set-env-vars $ENV_VARS

echo ""
echo "✅ デプロイ完了!"
echo ""
echo "📌 エンドポイント一覧:"
echo ""
echo "Gen2エンドポイント:"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/chat"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/add_drink"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/guardian_check"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/bartender"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/guardian_monitor"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/drinking_coach_analyze"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/tts"
echo ""
echo "Gen1エンドポイント:"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/transcribe"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/start_session"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/get_current_session"
echo "- https://$REGION-$PROJECT_ID.cloudfunctions.net/get_drinks_master"