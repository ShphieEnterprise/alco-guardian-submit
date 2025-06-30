"""
Guardian Agent - ADKベースの実装
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

try:
    from google.adk.agents import Agent
    from google.adk.messages import Message
except ImportError:
    logging.warning("Google ADK not available, using conceptual implementation")
    
from firebase_admin import firestore
from vertexai.generative_models import GenerativeModel


class GuardianAgent:
    """ADKスタイルのGuardianエージェント"""
    
    # 推奨値（エージェントの判断基準）
    SAFE_PACE_DRINKS_PER_30MIN = 1
    DAILY_LIMIT_G = 20  # 純アルコール20g（適正飲酒の目安）
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.agent_id = "guardian"
        self.model = GenerativeModel(model_name)
        self.db = firestore.client()
        
        # エージェントの能力定義
        self.capabilities = {
            "pace_monitoring": True,
            "alcohol_calculation": True,
            "risk_assessment": True,
            "intervention": True
        }
        
        # A2Aメッセージの購読設定
        self.subscriptions = {
            "drink.added": self._handle_drink_added,
            "drink.suggested": self._handle_drink_suggested,
            "session.started": self._handle_session_started,
            "bartender.chat": self._handle_bartender_chat
        }
        
        # 内部状態
        self.monitoring_sessions = {}  # user_id -> session状態
        
    async def analyze_drinking_pattern(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """飲酒パターンをAIで分析"""
        
        # セッションデータを取得
        session_data = await self._get_session_data(user_id, session_id)
        recent_drinks = await self._get_recent_drinks(user_id, session_id, minutes=30)
        
        # Geminiによる高度な分析
        analysis_prompt = self._build_analysis_prompt(session_data, recent_drinks)
        response = self.model.generate_content(analysis_prompt)
        
        # AI分析結果をパース
        ai_analysis = self._parse_ai_response(response.text)
        
        # 判定レベルを決定
        level = self._determine_warning_level(
            session_data['total_alcohol_g'],
            len(recent_drinks),
            ai_analysis
        )
        
        # A2Aメッセージで警告を発行
        if level['severity'] in ['warning', 'stop']:
            await self._publish_message({
                "type": "guardian.alert",
                "to": "all",  # 全エージェントに通知
                "payload": {
                    "user_id": user_id,
                    "level": level,
                    "ai_analysis": ai_analysis,
                    "recommendations": self._generate_recommendations(level, ai_analysis)
                }
            })
        
        return {
            "level": level,
            "ai_analysis": ai_analysis,
            "session_stats": {
                "total_alcohol_g": session_data['total_alcohol_g'],
                "drinks_count": len(session_data.get('drinks', [])),
                "duration_minutes": self._calculate_duration(session_data)
            },
            "agent_id": self.agent_id,
            "capabilities_used": ["risk_assessment", "alcohol_calculation"]
        }
    
    def _build_analysis_prompt(self, session_data: Dict, recent_drinks: List) -> str:
        """AI分析用のプロンプトを構築"""
        
        prompt = f"""あなたはGuardian AIエージェントとして、ユーザーの飲酒パターンを分析し、健康的な飲酒をサポートします。

# 現在のセッション情報
- 総アルコール量: {session_data.get('total_alcohol_g', 0)}g
- セッション開始時刻: {session_data.get('start_time', 'Unknown')}
- 最近30分の飲酒数: {len(recent_drinks)}杯

# 推奨基準
- 1日の適正量: 20g以下
- 30分あたりの推奨: 1杯以下

# 分析タスク
1. 現在の飲酒ペースの評価
2. 健康リスクの評価
3. 今後の推奨行動

JSON形式で以下の項目を含めて回答してください:
{{
    "pace_evaluation": "適正/注意/危険",
    "health_risk": "低/中/高",
    "risk_factors": ["リスク要因のリスト"],
    "recommendations": ["推奨行動のリスト"],
    "intervention_needed": true/false
}}"""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """AI応答をパース"""
        try:
            # JSON部分を抽出
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            logging.error(f"Failed to parse AI response: {response_text}")
        
        # パース失敗時のデフォルト
        return {
            "pace_evaluation": "不明",
            "health_risk": "中",
            "risk_factors": [],
            "recommendations": ["適度な飲酒を心がけましょう"],
            "intervention_needed": False
        }
    
    def _determine_warning_level(self, total_alcohol: float, recent_drinks: int, ai_analysis: Dict) -> Dict:
        """警告レベルを決定"""
        
        # AI分析と数値基準を組み合わせて判定
        if ai_analysis.get("intervention_needed") or total_alcohol > self.DAILY_LIMIT_G * 1.5:
            return {
                "severity": "stop",
                "color": "red",
                "message": "これ以上の飲酒は危険です。直ちに水分補給をしてください。"
            }
        elif ai_analysis.get("health_risk") == "高" or total_alcohol > self.DAILY_LIMIT_G:
            return {
                "severity": "warning",
                "color": "orange",
                "message": "飲み過ぎています。ペースを落として水分を取りましょう。"
            }
        elif ai_analysis.get("pace_evaluation") == "注意" or recent_drinks >= 2:
            return {
                "severity": "caution",
                "color": "yellow",
                "message": "ペースが速くなっています。ゆっくり楽しみましょう。"
            }
        else:
            return {
                "severity": "ok",
                "color": "green",
                "message": "良いペースです。このまま適度に楽しみましょう。"
            }
    
    async def check_veto(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Bartenderへの拒否権チェック"""
        
        analysis = await self.analyze_drinking_pattern(user_id, session_id)
        
        if analysis['level']['severity'] in ['warning', 'stop']:
            # A2Aメッセージ: Bartenderに拒否権を発動
            await self._publish_message({
                "type": "guardian.veto",
                "to": "bartender",
                "payload": {
                    "veto": True,
                    "reason": analysis['level']['message'],
                    "severity": analysis['level']['severity'],
                    "ai_reasoning": analysis['ai_analysis']
                }
            })
            
            return {
                "veto": True,
                "reason": analysis['level']['message']
            }
        
        return {
            "veto": False,
            "reason": None
        }
    
    async def _handle_drink_added(self, message: Dict):
        """飲酒追加メッセージを処理"""
        user_id = message['payload']['user_id']
        session_id = message['payload']['session_id']
        
        # 即座に分析を実行
        analysis = await self.analyze_drinking_pattern(user_id, session_id)
        
        # 統計情報をA2Aメッセージで共有
        await self._publish_message({
            "type": "session.stats",
            "to": "all",
            "payload": {
                "user_id": user_id,
                "session_id": session_id,
                "stats": analysis['session_stats'],
                "current_level": analysis['level']
            }
        })
    
    async def _handle_drink_suggested(self, message: Dict):
        """Bartenderからの飲み物提案を処理"""
        # プロアクティブにチェック
        context = message['payload']['context']
        
        # AIで提案の適切性を評価
        evaluation_prompt = f"""
Bartenderが以下の提案をしています:
「{message['payload']['suggestion']}」

ユーザーのコンテキスト: {context}

この提案が健康的な飲酒の観点から適切かどうか評価してください。
不適切な場合は理由を説明してください。
"""
        
        response = self.model.generate_content(evaluation_prompt)
        logging.info(f"Drink suggestion evaluation: {response.text}")
    
    async def _handle_session_started(self, message: Dict):
        """セッション開始メッセージを処理"""
        user_id = message['payload']['user_id']
        session_id = message['payload']['session_id']
        
        # モニタリング開始
        self.monitoring_sessions[user_id] = {
            "session_id": session_id,
            "start_time": datetime.now(),
            "warnings_sent": 0
        }
        
        logging.info(f"Guardian monitoring started for user {user_id}")
    
    async def _handle_bartender_chat(self, message: Dict):
        """Bartenderの会話内容を監視"""
        # 会話内容から飲酒意図を検出
        pass
    
    def _generate_recommendations(self, level: Dict, ai_analysis: Dict) -> List[str]:
        """レベルとAI分析に基づいて推奨事項を生成"""
        recommendations = ai_analysis.get('recommendations', [])
        
        if level['severity'] == 'stop':
            recommendations.extend([
                "これ以上の飲酒は控えてください",
                "水を500ml以上飲んでください",
                "タクシーの手配をお勧めします"
            ])
        elif level['severity'] == 'warning':
            recommendations.extend([
                "次の1時間は飲酒を控えめに",
                "おつまみを食べながら飲みましょう"
            ])
        
        return list(set(recommendations))  # 重複を除去
    
    async def _get_session_data(self, user_id: str, session_id: str) -> Dict:
        """Firestoreからセッションデータを取得"""
        session_ref = self.db.collection('users').document(user_id).collection('sessions').document(session_id)
        session_doc = session_ref.get()
        
        if session_doc.exists:
            return session_doc.to_dict()
        return {}
    
    async def _get_recent_drinks(self, user_id: str, session_id: str, minutes: int = 30) -> List[Dict]:
        """最近の飲酒記録を取得"""
        drinks_ref = self.db.collection('users').document(user_id).collection('sessions').document(session_id).collection('drinks')
        
        # 時間でフィルタリング
        time_threshold = datetime.now() - timedelta(minutes=minutes)
        recent_drinks = drinks_ref.where('timestamp', '>=', time_threshold).get()
        
        return [drink.to_dict() for drink in recent_drinks]
    
    def _calculate_duration(self, session_data: Dict) -> int:
        """セッション継続時間を分で計算"""
        start_time = session_data.get('start_time')
        if not start_time:
            return 0
            
        if hasattr(start_time, 'seconds'):
            start_datetime = datetime.fromtimestamp(start_time.seconds)
        else:
            start_datetime = start_time
            
        duration = datetime.now() - start_datetime
        return int(duration.total_seconds() / 60)
    
    async def _publish_message(self, message: Dict):
        """A2Aメッセージを発行"""
        message["from"] = self.agent_id
        message["timestamp"] = datetime.now().isoformat()
        message["messageId"] = f"msg_{datetime.now().timestamp()}"
        
        logging.info(f"Guardian A2A Message: {json.dumps(message, ensure_ascii=False)}")
        
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
def create_guardian_agent() -> GuardianAgent:
    """Guardianエージェントのインスタンスを作成"""
    return GuardianAgent(model_name="gemini-2.0-flash")