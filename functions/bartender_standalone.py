import json
import logging
import os
import random
from datetime import datetime, timezone

import functions_framework
import vertexai
from firebase_admin import auth, initialize_app
from vertexai.preview.generative_models import GenerativeModel

# Firebase Admin SDK初期化
try:
    initialize_app()
except ValueError:
    # すでに初期化されている場合はパス
    pass

# ---------- 初期化 ----------
PROJECT = os.getenv("GCP_PROJECT")
GEMINI_LOCATION = os.getenv("GEMINI_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

vertexai.init(project=PROJECT, location=GEMINI_LOCATION)
model = GenerativeModel(GEMINI_MODEL)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)


def add_cors_headers(response_data, status_code, content_type="application/json"):
    """レスポンスにCORSヘッダーを追加する共通関数"""
    headers = {
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "Authorization,Content-Type",
        "Access-Control-Allow-Credentials": "true",
    }
    return (response_data, status_code, headers)


# Bartenderエージェントのシステムプロンプト
BARTENDER_PROMPT = """あなたは「AI Bartender」として、ユーザーと楽しく温かい会話をするエージェントです。

# 役割
- ユーザーの話を共感的に聞き、楽しい会話を提供する
- お酒の話題を適度に織り交ぜながら、健康的な飲み方をさりげなく促す
- ユーザーが飲み過ぎそうな場合は、雑談で時間を稼ぐ
- 明るく親しみやすいトーンで対応する

# ガイドライン
- 説教くさくならないよう注意
- ユーザーの感情に寄り添う
- 短めの返答（1-3文程度）を心がける
- 絵文字は控えめに使用（1つまで）

# 現在の状況
- 時刻: {current_time}
- 曜日: {day_of_week}
"""


def get_current_context():
    """現在のコンテキスト情報を取得"""
    now = datetime.now()
    days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    
    return {
        "current_time": now.strftime("%H:%M"),
        "day_of_week": days[now.weekday()]
    }


@functions_framework.http
def bartender(request):
    """Bartenderエージェントのチャットエンドポイント（スタンドアロン版）"""
    
    # CORS対応
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        # 認証チェック（開発中は一時的にスキップ可能）
        id_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        uid = "test-user"  # デフォルトのテストユーザー
        
        if id_token:
            try:
                uid = auth.verify_id_token(id_token)["uid"]
            except Exception:
                logging.warning("Invalid ID token provided. Using test mode.")
                uid = "test-user"
        else:
            logging.warning("No authorization token provided. Using test mode.")
            uid = "test-user"
        
        logging.info(f"Processing chat request from user: {uid}")
        
        # リクエストボディの取得
        try:
            request_json = request.get_json()
        except Exception:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "Invalid JSON"}),
                400
            )
        
        # メッセージの取得
        user_message = request_json.get("message", "")
        if not user_message:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "Message is required"}),
                400
            )
        
        # コンテキスト情報の取得
        context = get_current_context()
        
        # プロンプトの構築
        system_prompt = BARTENDER_PROMPT.format(**context)
        
        # Geminiでレスポンス生成
        try:
            prompt = f"{system_prompt}\n\nユーザー: {user_message}\n\nBartender:"
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini")
            
            bartender_response = response.text.strip()
            
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            # フォールバック応答
            bartender_response = "すみません、ちょっと聞き取れませんでした。もう一度お願いできますか？"
        
        # ランダムな画像IDを生成（1-10）
        image_id = random.randint(1, 10)
        
        # レスポンスの構築（音声なし版）
        response_data = {
            "success": True,
            "message": bartender_response,
            "imageId": image_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "bartender"
        }
        
        return add_cors_headers(
            json.dumps(response_data, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "error": str(e)
            }),
            500
        )