"""
Bartender Agent - ADKベースの実装
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Note: ADKはまだ実際にはリリースされていないため、
# 概念的な実装となります。実際のADKがリリースされたら更新必要
try:
    from google.adk.agents import Agent, Tool
    from google.adk.messages import Message, MessageType
except ImportError:
    # ADKがまだ利用できない場合のフォールバック
    logging.warning("Google ADK not available, using conceptual implementation")
    
from vertexai.generative_models import GenerativeModel


class BartenderAgent:
    """ADKスタイルのBartenderエージェント"""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.agent_id = "bartender"
        self.model = GenerativeModel(model_name)
        
        # エージェントの能力定義
        self.capabilities = {
            "conversation": True,
            "drink_recommendation": True,
            "context_awareness": True,
            "voice_response": True
        }
        
        # A2Aメッセージの購読設定
        self.subscriptions = {
            "guardian.veto": self._handle_guardian_veto,
            "health.warning": self._handle_health_warning,
            "mood.update": self._handle_mood_update
        }
        
        # 内部状態
        self.context = {
            "guardian_warnings": [],
            "current_mood": "neutral",
            "conversation_history": []
        }
        
    async def process_chat(self, user_message: str, session_context: Dict) -> Dict[str, Any]:
        """ユーザーとのチャットを処理"""
        
        # コンテキストを更新
        self._update_context(session_context)
        
        # A2Aメッセージ: 会話開始を通知
        await self._publish_message({
            "type": "conversation.started",
            "payload": {
                "user_message": user_message,
                "timestamp": datetime.now().isoformat()
            }
        })
        
        # プロンプトを構築
        prompt = self._build_prompt(user_message)
        
        # Geminiで応答生成
        response = self.model.generate_content(prompt)
        bartender_response = response.text.strip()
        
        # 飲み物の提案を検出
        if self._detect_drink_suggestion(user_message, bartender_response):
            # A2Aメッセージ: 飲み物提案を通知
            await self._publish_message({
                "type": "drink.suggested",
                "to": "guardian",
                "payload": {
                    "suggestion": bartender_response,
                    "context": user_message
                }
            })
        
        # ムード検出
        detected_mood = self._detect_mood(user_message)
        if detected_mood != self.context["current_mood"]:
            # A2Aメッセージ: ムード変化を通知
            await self._publish_message({
                "type": "mood.detected",
                "to": "mood_monitor",
                "payload": {
                    "previous_mood": self.context["current_mood"],
                    "current_mood": detected_mood
                }
            })
            self.context["current_mood"] = detected_mood
        
        # 会話履歴に追加
        self.context["conversation_history"].append({
            "user": user_message,
            "agent": bartender_response,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "message": bartender_response,
            "agent_id": self.agent_id,
            "capabilities_used": ["conversation", "context_awareness"],
            "a2a_messages_sent": 2 if self._detect_drink_suggestion(user_message, bartender_response) else 1
        }
    
    def _build_prompt(self, user_message: str) -> str:
        """コンテキストを含むプロンプトを構築"""
        
        # 基本的な役割設定
        prompt = """あなたは「AI Bartender」として、ユーザーと楽しく温かい会話をするエージェントです。

# 役割
- ユーザーの話を共感的に聞き、楽しい会話を提供する
- お酒の話題を適度に織り交ぜながら、健康的な飲み方をさりげなく促す
- 明るく親しみやすいトーンで対応する

# ガイドライン
- 短めの返答（1-3文程度）を心がける
- 絵文字は控えめに使用（1つまで）
"""
        
        # Guardian警告がある場合
        if self.context["guardian_warnings"]:
            latest_warning = self.context["guardian_warnings"][-1]
            prompt += f"\n# 重要な注意事項\nGuardian AIから警告: {latest_warning['message']}\n優しく飲酒を控えるよう促してください。\n"
        
        # 現在の状況を追加
        now = datetime.now()
        days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
        prompt += f"\n# 現在の状況\n- 時刻: {now.strftime('%H:%M')}\n- 曜日: {days[now.weekday()]}\n"
        
        # 会話履歴（直近3つ）
        if self.context["conversation_history"]:
            prompt += "\n# 直近の会話\n"
            for conv in self.context["conversation_history"][-3:]:
                prompt += f"ユーザー: {conv['user']}\nBartender: {conv['agent']}\n"
        
        prompt += f"\nユーザー: {user_message}\nBartender:"
        
        return prompt
    
    def _detect_drink_suggestion(self, user_message: str, response: str) -> bool:
        """飲み物の提案を検出"""
        drink_keywords = ["飲み", "おかわり", "もう一杯", "ビール", "ワイン", "日本酒", "カクテル"]
        return any(keyword in user_message or keyword in response for keyword in drink_keywords)
    
    def _detect_mood(self, user_message: str) -> str:
        """ユーザーのムードを検出"""
        # 簡易的なムード検出（実際はより高度な分析が必要）
        if any(word in user_message for word in ["楽しい", "嬉しい", "最高"]):
            return "positive"
        elif any(word in user_message for word in ["疲れた", "辛い", "悲しい"]):
            return "negative"
        else:
            return "neutral"
    
    def _update_context(self, session_context: Dict):
        """セッションコンテキストで内部状態を更新"""
        if "total_alcohol_g" in session_context:
            self.context["current_alcohol"] = session_context["total_alcohol_g"]
        if "duration_minutes" in session_context:
            self.context["session_duration"] = session_context["duration_minutes"]
    
    async def _handle_guardian_veto(self, message: Dict):
        """Guardianからの拒否権メッセージを処理"""
        self.context["guardian_warnings"].append({
            "timestamp": message["timestamp"],
            "message": message["payload"]["reason"],
            "severity": message["payload"]["severity"]
        })
        logging.info(f"Guardian veto received: {message['payload']['reason']}")
    
    async def _handle_health_warning(self, message: Dict):
        """健康警告メッセージを処理"""
        logging.info(f"Health warning received: {message}")
    
    async def _handle_mood_update(self, message: Dict):
        """ムード更新メッセージを処理"""
        self.context["current_mood"] = message["payload"]["mood"]
    
    async def _publish_message(self, message: Dict):
        """A2Aメッセージを発行"""
        # 実際のADK実装では、メッセージブローカーに発行
        message["from"] = self.agent_id
        message["timestamp"] = datetime.now().isoformat()
        message["messageId"] = f"msg_{datetime.now().timestamp()}"
        
        logging.info(f"A2A Message published: {json.dumps(message, ensure_ascii=False)}")
        
        # TODO: 実際のメッセージブローカー（Pub/Sub, Firestore等）に発行
    
    async def handle_a2a_message(self, message: Dict):
        """受信したA2Aメッセージを処理"""
        message_type = message.get("type")
        if message_type in self.subscriptions:
            handler = self.subscriptions[message_type]
            await handler(message)
        else:
            logging.warning(f"Unknown message type: {message_type}")


# エージェントのファクトリー関数
def create_bartender_agent() -> BartenderAgent:
    """Bartenderエージェントのインスタンスを作成"""
    return BartenderAgent(model_name="gemini-2.0-flash")