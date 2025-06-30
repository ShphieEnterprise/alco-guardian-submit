#!/bin/bash

# 環境変数の設定
PROJECT_ID="alco-guardian"
REGION="asia-northeast1"
UPLOAD_BUCKET="alco-guardian-uploads"

echo "🚀 Cloud Functions のデプロイを開始します..."

# 1. transcribe関数（音声認識）
echo "📝 transcribe関数をデプロイ中..."
gcloud functions deploy transcribe \
  --gen2 \
  --runtime=python312 \
  --region=$REGION \
  --source=. \
  --entry-point=transcribe \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT=$PROJECT_ID,UPLOAD_BUCKET=$UPLOAD_BUCKET,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001" \
  --memory=512MB \
  --timeout=60s

# 2. chat関数（Bartenderエージェント）
echo "🍸 chat関数（Bartender）をデプロイ中..."
gcloud functions deploy chat \
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

# 3. tts関数（音声合成）
echo "🔊 tts関数をデプロイ中..."
gcloud functions deploy tts \
  --gen2 \
  --runtime=python312 \
  --region=$REGION \
  --source=. \
  --entry-point=tts \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT=$PROJECT_ID,UPLOAD_BUCKET=$UPLOAD_BUCKET" \
  --memory=512MB \
  --timeout=60s

echo "✅ デプロイが完了しました！"
echo ""
echo "📌 エンドポイント:"
echo "  - Transcribe: https://$REGION-$PROJECT_ID.cloudfunctions.net/transcribe"
echo "  - Chat (Bartender): https://$REGION-$PROJECT_ID.cloudfunctions.net/chat"
echo "  - TTS: https://$REGION-$PROJECT_ID.cloudfunctions.net/tts"