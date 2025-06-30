#!/bin/bash
# 安全なデプロイスクリプト（エラーハンドリング付き）

PROJECT_ID="YOUR_PROJECT_ID"
REGION="asia-northeast1"
RUNTIME="python312"

echo "🚀 Cloud Functions 安全デプロイ開始..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# プロジェクト設定
gcloud config set project $PROJECT_ID

# 共通オプション（Gen2を使用）
COMMON_OPTS="--runtime $RUNTIME --region $REGION --memory 1GB --timeout 60s --trigger-http --allow-unauthenticated --gen2"
ENV_VARS="UPLOAD_BUCKET=${PROJECT_ID}.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001"

# 関数リスト
FUNCTIONS=(
  # 既存のGen2関数
  "chat"
  "add_drink"
  "start_session"
  "get_current_session"
  "get_drinks_master"
  "guardian_check"
  # 新規関数
  "bartender"
  "guardian_monitor"
  "drinking_coach_analyze"
  "tts"
)

# 各関数のソースファイルを指定
declare -A FUNCTION_SOURCES
FUNCTION_SOURCES["bartender"]="bartender_standalone.py"
FUNCTION_SOURCES["guardian_monitor"]="guardian_monitor.py"
FUNCTION_SOURCES["drinking_coach_analyze"]="drinking_coach_analyze.py"
FUNCTION_SOURCES["tts"]="tts.py"

# デプロイ実行
FAILED_FUNCTIONS=()
SUCCEEDED_FUNCTIONS=()

for func in "${FUNCTIONS[@]}"; do
  echo ""
  echo "📦 Deploying $func..."
  
  # ソースファイルの指定
  if [[ -n "${FUNCTION_SOURCES[$func]}" ]]; then
    SOURCE_FILE="${FUNCTION_SOURCES[$func]}"
    echo "  Using source file: $SOURCE_FILE"
  else
    SOURCE_FILE="main.py"
  fi
  
  # デプロイ実行
  if gcloud functions deploy $func \
    $COMMON_OPTS \
    --entry-point $func \
    --set-env-vars $ENV_VARS \
    --source . \
    --project $PROJECT_ID; then
    echo "✅ $func deployed successfully"
    SUCCEEDED_FUNCTIONS+=("$func")
  else
    echo "❌ Failed to deploy $func"
    FAILED_FUNCTIONS+=("$func")
  fi
done

echo ""
echo "========== デプロイ結果 =========="
echo ""

if [ ${#SUCCEEDED_FUNCTIONS[@]} -gt 0 ]; then
  echo "✅ 成功した関数 (${#SUCCEEDED_FUNCTIONS[@]}個):"
  for func in "${SUCCEEDED_FUNCTIONS[@]}"; do
    echo "  - https://$REGION-$PROJECT_ID.cloudfunctions.net/$func"
  done
fi

if [ ${#FAILED_FUNCTIONS[@]} -gt 0 ]; then
  echo ""
  echo "❌ 失敗した関数 (${#FAILED_FUNCTIONS[@]}個):"
  for func in "${FAILED_FUNCTIONS[@]}"; do
    echo "  - $func"
  done
  echo ""
  echo "失敗した関数のログを確認してください:"
  echo "gcloud functions logs read [関数名] --region $REGION"
fi

echo ""
echo "========================================="

# 失敗があった場合は非ゼロのexit codeを返す
if [ ${#FAILED_FUNCTIONS[@]} -gt 0 ]; then
  exit 1
fi