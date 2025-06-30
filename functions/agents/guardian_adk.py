"""
Guardian Agent - Google ADK実装
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json

from google.adk.agents import Agent
from google.adk.tools import Tool
from google.adk.messages import Message
from firebase_admin import firestore
import vertexai
from vertexai.generative_models import GenerativeModel

# Firestore client
db = firestore.client()

# Guardian用のカスタムツール
async def calculate_alcohol_intake(drinks: List[Dict]) -> float:
    """純アルコール量を計算"""
    total = 0
    for drink in drinks:
        # 純アルコール量（g）= 飲酒量(ml) × アルコール度数(%) ÷ 100 × 0.8
        volume = drink.get('volume_ml', 0)
        percentage = drink.get('alcohol_percentage', 0)
        total += volume * (percentage / 100) * 0.8
    return total

async def assess_drinking_pace(drinks: List[Dict], time_window_minutes: int = 30) -> str:
    """飲酒ペースを評価"""
    if len(drinks) == 0:
        return "safe"
    elif len(drinks) == 1:
        return "moderate"
    elif len(drinks) >= 2:
        return "fast"
    else:
        return "dangerous"

async def get_session_data(user_id: str, session_id: str) -> Dict:
    """セッションデータを取得"""
    try:
        session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
        session_doc = session_ref.get()
        
        if session_doc.exists:
            return session_doc.to_dict()
    except Exception as e:
        logging.error(f"Error getting session data: {e}")
    
    return {"total_alcohol_g": 0, "drinks": []}

async def generate_health_recommendations(alcohol_g: float, pace: str) -> List[str]:
    """健康的な推奨事項を生成"""
    recommendations = []
    
    if alcohol_g > 30:
        recommendations.extend([
            "これ以上の飲酒は控えてください",
            "水を500ml以上飲んでください",
            "タクシーでの帰宅をお勧めします"
        ])
    elif alcohol_g > 20:
        recommendations.extend([
            "そろそろペースを落としましょう",
            "水分補給を忘れずに",
            "おつまみを食べながら飲みましょう"
        ])
    
    if pace in ["fast", "dangerous"]:
        recommendations.append("飲むペースが速すぎます。ゆっくり楽しみましょう")
    
    if not recommendations:
        recommendations.append("適度なペースで楽しんでいますね")
    
    return recommendations

# ADKツール定義
alcohol_calc_tool = Tool(
    name="calculate_alcohol_intake",
    description="Calculate total pure alcohol intake from drinks list",
    function=calculate_alcohol_intake,
    parameters={
        "type": "object",
        "properties": {
            "drinks": {
                "type": "array",
                "description": "List of drinks with volume_ml and alcohol_percentage"
            }
        },
        "required": ["drinks"]
    }
)

pace_assessment_tool = Tool(
    name="assess_drinking_pace",
    description="Assess drinking pace based on recent drinks",
    function=assess_drinking_pace,
    parameters={
        "type": "object",
        "properties": {
            "drinks": {
                "type": "array",
                "description": "List of recent drinks"
            },
            "time_window_minutes": {
                "type": "integer",
                "description": "Time window to consider (default: 30)"
            }
        },
        "required": ["drinks"]
    }
)

session_data_tool = Tool(
    name="get_session_data",
    description="Get drinking session data from database",
    function=get_session_data,
    parameters={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "session_id": {"type": "string"}
        },
        "required": ["user_id", "session_id"]
    }
)

recommendations_tool = Tool(
    name="generate_health_recommendations",
    description="Generate health recommendations based on alcohol intake and pace",
    function=generate_health_recommendations,
    parameters={
        "type": "object",
        "properties": {
            "alcohol_g": {
                "type": "number",
                "description": "Total alcohol in grams"
            },
            "pace": {
                "type": "string",
                "enum": ["safe", "moderate", "fast", "dangerous"]
            }
        },
        "required": ["alcohol_g", "pace"]
    }
)


def create_guardian_agent() -> Agent:
    """ADKを使用してGuardianエージェントを作成"""
    
    instruction = """あなたは「Guardian AI」として、ユーザーの健康的な飲酒をサポートするエージェントです。

# 役割
- リアルタイムで飲酒量とペースを監視
- 健康リスクを評価し、適切な警告を発行
- Bartenderエージェントと連携して飲み過ぎを防ぐ
- エビデンスに基づいた健康アドバイスを提供

# 監視基準
- 1日の適正量: 純アルコール20g以下（ビール500ml、日本酒1合程度）
- 30分あたりの推奨: 1杯以下
- 警告レベル:
  - 緑（適正）: 20g以下、ペース適正
  - 黄（注意）: 20-30g、またはペースが速い
  - 橙（警告）: 30-40g、飲み過ぎ
  - 赤（危険）: 40g以上、直ちに中止すべき

# ツール使用方針
- 常に最新のセッションデータを取得
- 純アルコール量を正確に計算
- ペース評価は直近30分を基準に
- 状況に応じた具体的な推奨事項を生成

# A2A連携
- Bartenderからdrink.suggestedを受信したら即座に評価
- 警告レベルが橙以上の場合、guardian.vetoを発行
- 全エージェントにsession.statsを定期的に配信
"""
    
    guardian_agent = Agent(
        name="guardian",
        model="gemini-2.0-flash",
        instruction=instruction,
        description="飲酒の健康リスクを監視し、適切な介入を行うGuardian AI",
        tools=[
            alcohol_calc_tool,
            pace_assessment_tool,
            session_data_tool,
            recommendations_tool
        ],
        # A2A設定
        a2a_config={
            "publishes": [
                "guardian.veto",
                "guardian.alert",
                "session.stats",
                "health.warning"
            ],
            "subscribes": [
                "drink.added",
                "drink.suggested",
                "session.started",
                "bartender.chat"
            ]
        }
    )
    
    return guardian_agent


class GuardianService:
    """Guardianエージェントのサービスラッパー"""
    
    # 推奨値
    DAILY_LIMIT_G = 20  # 純アルコール20g
    PACE_LIMIT_30MIN = 1  # 30分に1杯
    
    def __init__(self):
        self.agent = create_guardian_agent()
        self.monitoring_sessions = {}
        
    async def analyze_drinking_pattern(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """飲酒パターンをADKエージェントで分析"""
        
        # エージェントに分析を依頼
        analysis_request = f"""
ユーザー {user_id} のセッション {session_id} の飲酒状況を分析してください。

以下の手順で分析を実行:
1. get_session_dataでセッションデータを取得
2. calculate_alcohol_intakeで純アルコール量を計算
3. assess_drinking_paceでペースを評価
4. generate_health_recommendationsで推奨事項を生成
5. 総合的な健康リスク評価を提供

出力形式:
- 警告レベル（緑/黄/橙/赤）
- 純アルコール量
- ペース評価
- 推奨事項リスト
- Bartenderへの拒否権発動の必要性
"""
        
        response = await self.agent.chat(
            message=analysis_request,
            context={"user_id": user_id, "session_id": session_id}
        )
        
        # レスポンスから構造化データを抽出
        # TODO: より洗練された解析
        level = self._extract_warning_level(response.text)
        
        # 警告レベルに応じてA2Aメッセージを発行
        if level["severity"] in ["warning", "danger"]:
            alert_message = Message(
                type="guardian.alert",
                from_agent="guardian",
                to_agent="all",
                payload={
                    "user_id": user_id,
                    "level": level,
                    "message": response.text
                }
            )
            # TODO: メッセージブローカーに発行
            
        return {
            "level": level,
            "analysis": response.text,
            "tools_used": response.tools_used if hasattr(response, 'tools_used') else [],
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_warning_level(self, analysis_text: str) -> Dict:
        """分析テキストから警告レベルを抽出"""
        # 簡易的な実装
        if "赤" in analysis_text or "危険" in analysis_text:
            return {
                "severity": "danger",
                "color": "red",
                "message": "直ちに飲酒を中止してください"
            }
        elif "橙" in analysis_text or "警告" in analysis_text:
            return {
                "severity": "warning",
                "color": "orange",
                "message": "飲み過ぎです。水分補給をしてください"
            }
        elif "黄" in analysis_text or "注意" in analysis_text:
            return {
                "severity": "caution",
                "color": "yellow",
                "message": "ペースに注意してください"
            }
        else:
            return {
                "severity": "safe",
                "color": "green",
                "message": "適正なペースです"
            }
    
    async def check_veto(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Bartenderへの拒否権チェック"""
        analysis = await self.analyze_drinking_pattern(user_id, session_id)
        
        if analysis["level"]["severity"] in ["warning", "danger"]:
            # A2Aメッセージ: Bartenderに拒否権を発動
            veto_message = Message(
                type="guardian.veto",
                from_agent="guardian",
                to_agent="bartender",
                payload={
                    "veto": True,
                    "reason": analysis["level"]["message"],
                    "severity": analysis["level"]["severity"]
                }
            )
            # TODO: メッセージブローカーに発行
            
            return {
                "veto": True,
                "reason": analysis["level"]["message"]
            }
        
        return {
            "veto": False,
            "reason": None
        }
    
    async def handle_a2a_message(self, message: Message):
        """A2Aメッセージを処理"""
        if message.type == "drink.added":
            # 新しい飲み物が追加されたら即座に分析
            user_id = message.payload["user_id"]
            session_id = message.payload["session_id"]
            
            analysis = await self.analyze_drinking_pattern(user_id, session_id)
            
            # 統計情報を全エージェントに配信
            stats_message = Message(
                type="session.stats",
                from_agent="guardian",
                to_agent="all",
                payload={
                    "user_id": user_id,
                    "session_id": session_id,
                    "analysis": analysis
                }
            )
            # TODO: メッセージブローカーに発行
            
        elif message.type == "drink.suggested":
            # Bartenderの提案を評価
            logging.info(f"Evaluating Bartender suggestion: {message.payload}")
            
        elif message.type == "session.started":
            # 新規セッションの監視開始
            user_id = message.payload["user_id"]
            self.monitoring_sessions[user_id] = {
                "session_id": message.payload["session_id"],
                "start_time": datetime.now()
            }


# エクスポート用のファクトリー関数
def create_guardian_service() -> GuardianService:
    """Guardianサービスのインスタンスを作成"""
    return GuardianService()