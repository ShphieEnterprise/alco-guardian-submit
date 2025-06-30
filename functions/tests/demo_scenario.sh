#!/bin/bash
# デモシナリオ実行スクリプト - ハッカソンデモの流れを再現

BASE_URL="https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net"

# 色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🍺 AI Bartender Suite デモシナリオ  ${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. ドリンクマスターデータ確認
echo -e "\n${YELLOW}1. 利用可能なドリンクを確認${NC}"
echo "curl ${BASE_URL}/get_drinks_master"
curl -s "${BASE_URL}/get_drinks_master" | jq '.' || curl -s "${BASE_URL}/get_drinks_master"
echo ""

# 2. Bartenderと挨拶
echo -e "\n${YELLOW}2. Bartenderに挨拶${NC}"
echo 'curl -X POST ${BASE_URL}/chat -d {"message": "こんばんは！金曜日だし一杯どう？"}'
curl -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "こんばんは！金曜日だし一杯どう？"}' \
  -s | jq '.message' || echo "Error"

# 3. セッション開始
echo -e "\n${YELLOW}3. 飲酒セッション開始${NC}"
echo "curl -X POST ${BASE_URL}/start_session"
curl -X POST "${BASE_URL}/start_session" -s | jq '.' || echo "Session already exists"

# 4. 1杯目：ビール
echo -e "\n${YELLOW}4. 1杯目：ビール（19:00）${NC}"
echo 'curl -X POST ${BASE_URL}/add_drink -d {"drink_id": "beer"}'
RESULT=$(curl -X POST "${BASE_URL}/add_drink" \
  -H "Content-Type: application/json" \
  -d '{"drink_id": "beer"}' -s)
echo "$RESULT" | jq '.' || echo "$RESULT"

# 5. 2杯目：ハイボール（30分後）
echo -e "\n${YELLOW}5. 2杯目：ハイボール（19:30）${NC}"
echo "30秒待機中...（本来は30分後）"
sleep 30

echo 'curl -X POST ${BASE_URL}/add_drink -d {"drink_id": "highball"}'
RESULT=$(curl -X POST "${BASE_URL}/add_drink" \
  -H "Content-Type: application/json" \
  -d '{"drink_id": "highball"}' -s)
echo "$RESULT" | jq '.' || echo "$RESULT"

# Guardian状態確認
echo -e "\n${GREEN}>>> Guardian状態チェック${NC}"
curl -s "${BASE_URL}/guardian_check" | jq '.' || curl -s "${BASE_URL}/guardian_check"

# 6. 3杯目：日本酒（警告が出るはず）
echo -e "\n${YELLOW}6. 3杯目：日本酒を注文（20:00）${NC}"
echo 'curl -X POST ${BASE_URL}/add_drink -d {"drink_id": "sake"}'
RESULT=$(curl -X POST "${BASE_URL}/add_drink" \
  -H "Content-Type: application/json" \
  -d '{"drink_id": "sake"}' -s)
echo "$RESULT" | jq '.' || echo "$RESULT"

# 7. Bartenderにもう一杯頼む（Guardian介入デモ）
echo -e "\n${YELLOW}7. Bartenderにもう一杯頼む${NC}"
echo 'curl -X POST ${BASE_URL}/chat -d {"message": "もう一杯日本酒ください！"}'
RESPONSE=$(curl -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "もう一杯日本酒ください！"}' -s)
echo -e "${RED}Bartender:${NC}"
echo "$RESPONSE" | jq -r '.message' || echo "$RESPONSE"

# 8. 現在のセッション情報
echo -e "\n${YELLOW}8. 現在のセッション情報${NC}"
echo "curl ${BASE_URL}/get_current_session"
SESSION=$(curl -s "${BASE_URL}/get_current_session")
echo "$SESSION" | jq '.' || echo "$SESSION"

# 結果サマリー
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}         デモシナリオ完了！            ${NC}"
echo -e "${BLUE}========================================${NC}"

# セッション情報から重要な値を抽出
TOTAL_ALCOHOL=$(echo "$SESSION" | jq -r '.total_alcohol_g' 2>/dev/null || echo "N/A")
GUARDIAN_COLOR=$(echo "$SESSION" | jq -r '.guardian_status.color' 2>/dev/null || echo "N/A")

echo -e "\n${GREEN}📊 飲酒状況サマリー：${NC}"
echo -e "  総純アルコール量: ${TOTAL_ALCOHOL}g"
echo -e "  Guardian判定: ${GUARDIAN_COLOR}"
echo -e "\n${GREEN}✅ デモポイント：${NC}"
echo -e "  1. 音声でBartenderと自然な会話"
echo -e "  2. 正確な純アルコール計算"
echo -e "  3. リアルタイムGuardian監視"
echo -e "  4. 飲み過ぎ時の介入（Veto機能）"