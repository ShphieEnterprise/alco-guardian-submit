import json
import functions_framework
from datetime import datetime

@functions_framework.http
def simple_chat(request):
    """シンプルなテスト用チャットエンドポイント"""
    
    # CORS対応
    if request.method == "OPTIONS":
        return ("", 204, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Authorization,Content-Type",
        })
    
    try:
        # リクエストボディの取得
        request_json = request.get_json() if request.is_json else {}
        
        # メッセージの取得
        user_message = request_json.get("message", "こんにちは")
        
        # シンプルな返答
        responses = {
            "こんにちは": "こんにちは！今日はどんなお酒を楽しみましょうか？",
            "ビール": "ビールいいですね！キンキンに冷えたビールは最高です！",
            "ワイン": "ワインですか。赤と白、どちらがお好みですか？",
            "日本酒": "日本酒もいいですね。熱燗と冷酒、どちらにしましょう？",
        }
        
        # デフォルトの返答
        bartender_response = responses.get(user_message, 
            f"「{user_message}」ですね。今日はゆっくりお酒を楽しみましょう！")
        
        # レスポンスの構築
        response_data = {
            "success": True,
            "message": bartender_response,
            "imageId": 1,
            "timestamp": datetime.now().isoformat(),
            "agent": "bartender"
        }
        
        return (
            json.dumps(response_data, ensure_ascii=False),
            200,
            {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        return (
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": "An error occurred",
                "error": str(e)
            }),
            500,
            {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            }
        )