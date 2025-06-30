"""
Bartender Agent - Google ADK実装
"""
import logging
from typing import Dict, Any, List
from datetime import datetime
import json

# Google ADKを使用
from google.adk.agents import Agent
from google.adk.tools import Tool
from google.adk.messages import Message
import vertexai
from vertexai.generative_models import GenerativeModel

# カスタムツールの定義
async def check_guardian_status(user_id: str) -> Dict[str, Any]:
    """Guardianエージェントの状態を確認"""
    # TODO: 実際のGuardian APIを呼び出し
    return {
        "status": "ok",
        "warnings": [],
        "total_alcohol_g": 0
    }

async def suggest_drink(drink_type: str, context: str) -> Dict[str, Any]:
    """飲み物を提案"""
    return {
        "drink": drink_type,
        "suggested_at": datetime.now().isoformat(),
        "context": context
    }

async def detect_mood(message: str) -> str:
    """メッセージからムードを検出"""
    positive_words = ["楽しい", "嬉しい", "最高", "happy", "great"]
    negative_words = ["疲れた", "辛い", "悲しい", "tired", "sad"]
    
    if any(word in message.lower() for word in positive_words):
        return "positive"
    elif any(word in message.lower() for word in negative_words):
        return "negative"
    return "neutral"

# ツールをADK形式で定義
guardian_check_tool = Tool(
    name="check_guardian_status",
    description="Check Guardian agent's assessment of current drinking status",
    function=check_guardian_status,
    parameters={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "User ID to check"
            }
        },
        "required": ["user_id"]
    }
)

drink_suggestion_tool = Tool(
    name="suggest_drink",
    description="Suggest a drink based on context",
    function=suggest_drink,
    parameters={
        "type": "object",
        "properties": {
            "drink_type": {
                "type": "string",
                "description": "Type of drink to suggest"
            },
            "context": {
                "type": "string",
                "description": "Context for the suggestion"
            }
        },
        "required": ["drink_type", "context"]
    }
)

mood_detection_tool = Tool(
    name="detect_mood",
    description="Detect user's mood from their message",
    function=detect_mood,
    parameters={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to analyze"
            }
        },
        "required": ["message"]
    }
)


def create_bartender_agent() -> Agent:
    """ADKを使用してBartenderエージェントを作成"""
    
    # 現在時刻とコンテキスト
    now = datetime.now()
    days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    current_context = f"現在は{now.strftime('%H:%M')}、{days[now.weekday()]}です。"
    
    # エージェントのインストラクション
    instruction = f"""あなたは「AI Bartender」として、ユーザーと楽しく温かい会話をするエージェントです。

# 役割
- ユーザーの話を共感的に聞き、楽しい会話を提供する
- お酒の話題を適度に織り交ぜながら、健康的な飲み方をさりげなく促す
- 明るく親しみやすいトーンで対応する
- Guardianエージェントと連携して、飲み過ぎを防ぐ

# ガイドライン
- 短めの返答（1-3文程度）を心がける
- 絵文字は控えめに使用（1つまで）
- 飲み物の話題が出たら、必ずGuardianの状態を確認する
- Guardianから警告が出ている場合は、優しく飲酒を控えるよう促す

# 現在の状況
{current_context}

# 利用可能なツール
- check_guardian_status: Guardianエージェントの評価を確認
- suggest_drink: コンテキストに基づいて飲み物を提案
- detect_mood: ユーザーのムードを検出
"""
    
    # ADKエージェントを作成
    bartender_agent = Agent(
        name="bartender",
        model="gemini-2.0-flash",
        instruction=instruction,
        description="楽しく健康的な飲酒をサポートするAI Bartender",
        tools=[guardian_check_tool, drink_suggestion_tool, mood_detection_tool],
        # A2A設定
        a2a_config={
            "publishes": ["drink.suggested", "mood.detected", "conversation.started"],
            "subscribes": ["guardian.veto", "health.warning", "mood.update"]
        }
    )
    
    return bartender_agent


class BartenderService:
    """Bartenderエージェントのサービスラッパー"""
    
    def __init__(self):
        self.agent = create_bartender_agent()
        self.conversation_history = []
        
    async def chat(self, user_message: str, user_id: str = "demo_user") -> Dict[str, Any]:
        """ユーザーとチャット"""
        
        # A2Aメッセージ: 会話開始を通知
        start_message = Message(
            type="conversation.started",
            from_agent="bartender",
            to_agent="all",
            payload={
                "user_id": user_id,
                "message": user_message,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # エージェントに問い合わせ
        response = await self.agent.chat(
            message=user_message,
            context={
                "user_id": user_id,
                "history": self.conversation_history[-5:] if self.conversation_history else []
            }
        )
        
        # 会話履歴に追加
        self.conversation_history.append({
            "user": user_message,
            "agent": response.text,
            "timestamp": datetime.now().isoformat()
        })
        
        # 飲み物の提案を検出
        if any(word in user_message or word in response.text for word in ["飲み", "ビール", "ワイン", "お酒"]):
            # A2Aメッセージ: 飲み物提案を通知
            drink_message = Message(
                type="drink.suggested",
                from_agent="bartender",
                to_agent="guardian",
                payload={
                    "user_id": user_id,
                    "context": user_message,
                    "suggestion": response.text
                }
            )
            # TODO: メッセージブローカーに発行
        
        return {
            "message": response.text,
            "agent_id": "bartender",
            "tools_used": response.tools_used if hasattr(response, 'tools_used') else [],
            "timestamp": datetime.now().isoformat()
        }
    
    async def handle_a2a_message(self, message: Message):
        """A2Aメッセージを処理"""
        if message.type == "guardian.veto":
            # Guardianからの拒否権を内部状態に反映
            logging.info(f"Guardian veto received: {message.payload}")
            # 次の応答に影響を与えるよう状態を更新
            self.agent.update_context({
                "guardian_warning": message.payload.get("reason")
            })
        elif message.type == "health.warning":
            logging.info(f"Health warning received: {message.payload}")
        elif message.type == "mood.update":
            logging.info(f"Mood update received: {message.payload}")


# エクスポート用のファクトリー関数
def create_bartender_service() -> BartenderService:
    """Bartenderサービスのインスタンスを作成"""
    return BartenderService()