#!/bin/bash
# 飲酒記録エンドポイントをデプロイ

PROJECT_ID="alco-guardian"
REGION="asia-northeast1"
RUNTIME="python312"

echo "🍺 Deploying drink function..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# プロジェクト設定
gcloud config set project $PROJECT_ID

# Cloud Storage バケット名を設定
STORAGE_BUCKET="${PROJECT_ID}.appspot.com"

# デプロイ
gcloud functions deploy drink \
  --runtime $RUNTIME \
  --region $REGION \
  --memory 1GB \
  --timeout 60s \
  --trigger-http \
  --allow-unauthenticated \
  --gen2 \
  --entry-point drink \
  --set-env-vars "STORAGE_BUCKET=$STORAGE_BUCKET,LOG_LEVEL=INFO" \
  --source . \
  --project $PROJECT_ID

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📌 Endpoint:"
echo "https://$REGION-$PROJECT_ID.cloudfunctions.net/drink"
echo ""
echo "🧪 Test command:"
echo 'curl -X POST "https://asia-northeast1-alco-guardian.cloudfunctions.net/drink" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d "{"drinkType": "ビール", "alcoholPercentage": 5, "volume": 350}"'