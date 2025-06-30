"""
Drinking Coach Agent - 飲酒ペース管理とアドバイスを提供するエージェント
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import json
from firebase_admin import firestore

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DrinkingCoachAgent:
    """飲酒管理コーチエージェント"""
    
    def __init__(self):
        self.agent_id = "drinking_coach"
        self.db = firestore.client()
        
        # 飲酒ペース基準（1時間あたりの純アルコール量）
        self.PACE_THRESHOLDS = {
            "safe": 10,        # 10g/h以下：安全
            "moderate": 15,    # 15g/h以下：適度
            "fast": 20,        # 20g/h以下：速い
            "dangerous": 20    # 20g/h超過：危険
        }
        
        # 総アルコール量の閾値
        self.TOTAL_THRESHOLDS = {
            "light": 20,       # 20g以下：軽い
            "moderate": 40,    # 40g以下：適度
            "heavy": 60,       # 60g以下：多い
            "excessive": 60    # 60g超過：過度
        }
    
    async def analyze_drinking_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """飲酒セッションを総合的に分析"""
        try:
            # セッションデータ取得
            session_ref = self.db.collection('users').document(user_id)\
                .collection('sessions').document(session_id)
            session_data = session_ref.get().to_dict()
            
            if not session_data:
                return self._create_error_response("Session not found")
            
            # 飲酒履歴取得
            drinks_ref = session_ref.collection('drinks')
            drinks = [doc.to_dict() for doc in drinks_ref.stream()]
            
            # 分析実行
            analysis = {
                "pace_analysis": self._analyze_drinking_pace(session_data, drinks),
                "total_analysis": self._analyze_total_consumption(session_data),
                "pattern_analysis": self._analyze_drinking_pattern(drinks),
                "recommendations": [],
                "intervention_level": "none"
            }
            
            # 推奨事項とインターベンションレベルの決定
            analysis["recommendations"] = self._generate_recommendations(analysis)
            analysis["intervention_level"] = self._determine_intervention_level(analysis)
            
            # 特別なイベント検出
            analysis["special_events"] = self._detect_special_events(drinks, session_data)
            
            return {
                "success": True,
                "analysis": analysis,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing drinking session: {e}")
            return self._create_error_response(str(e))
    
    def _analyze_drinking_pace(self, session_data: Dict, drinks: List[Dict]) -> Dict[str, Any]:
        """飲酒ペースを分析"""
        if not drinks:
            return {"status": "no_drinks", "current_pace": 0}
        
        # セッション開始時刻
        start_time = session_data.get('start_time')
        if hasattr(start_time, 'seconds'):
            start_dt = datetime.fromtimestamp(start_time.seconds, tz=timezone.utc)
        else:
            start_dt = start_time or datetime.now(timezone.utc)
        
        # 経過時間（時間）
        duration_hours = (datetime.now(timezone.utc) - start_dt).total_seconds() / 3600
        duration_hours = max(duration_hours, 0.1)  # 最小0.1時間
        
        # 現在のペース（g/h）
        total_alcohol = session_data.get('total_alcohol_g', 0)
        current_pace = total_alcohol / duration_hours
        
        # 最近1時間のペース
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_drinks = [d for d in drinks if self._get_drink_time(d) > one_hour_ago]
        recent_alcohol = sum(d.get('alcohol_g', 0) for d in recent_drinks)
        
        # ペース評価
        if current_pace <= self.PACE_THRESHOLDS["safe"]:
            pace_status = "safe"
            message = "良いペースで飲んでいます"
        elif current_pace <= self.PACE_THRESHOLDS["moderate"]:
            pace_status = "moderate"
            message = "適度なペースです"
        elif current_pace <= self.PACE_THRESHOLDS["fast"]:
            pace_status = "fast"
            message = "少しペースが速いです"
        else:
            pace_status = "dangerous"
            message = "ペースが速すぎます！"
        
        return {
            "status": pace_status,
            "current_pace": round(current_pace, 1),
            "recent_pace": round(recent_alcohol, 1),
            "duration_hours": round(duration_hours, 1),
            "message": message
        }
    
    def _analyze_total_consumption(self, session_data: Dict) -> Dict[str, Any]:
        """総飲酒量を分析"""
        total_alcohol = session_data.get('total_alcohol_g', 0)
        
        if total_alcohol <= self.TOTAL_THRESHOLDS["light"]:
            status = "light"
            message = "まだ軽い飲酒量です"
        elif total_alcohol <= self.TOTAL_THRESHOLDS["moderate"]:
            status = "moderate"
            message = "適度な飲酒量です"
        elif total_alcohol <= self.TOTAL_THRESHOLDS["heavy"]:
            status = "heavy"
            message = "かなり飲んでいます"
        else:
            status = "excessive"
            message = "飲みすぎです！"
        
        # 標準ドリンク換算（1標準ドリンク = 10g純アルコール）
        standard_drinks = total_alcohol / 10
        
        return {
            "status": status,
            "total_alcohol_g": round(total_alcohol, 1),
            "standard_drinks": round(standard_drinks, 1),
            "message": message
        }
    
    def _analyze_drinking_pattern(self, drinks: List[Dict]) -> Dict[str, Any]:
        """飲酒パターンを分析"""
        if not drinks:
            return {"pattern": "none", "drink_intervals": []}
        
        # 飲み物の種類をカウント
        drink_types = {}
        for drink in drinks:
            drink_type = drink.get('drink_type', 'unknown')
            drink_types[drink_type] = drink_types.get(drink_type, 0) + 1
        
        # 飲酒間隔を計算
        intervals = []
        sorted_drinks = sorted(drinks, key=lambda d: self._get_drink_time(d))
        
        for i in range(1, len(sorted_drinks)):
            prev_time = self._get_drink_time(sorted_drinks[i-1])
            curr_time = self._get_drink_time(sorted_drinks[i])
            interval = (curr_time - prev_time).total_seconds() / 60  # 分単位
            intervals.append(interval)
        
        # パターン判定
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        
        if avg_interval < 10:
            pattern = "rapid"
            message = "非常に短い間隔で飲んでいます"
        elif avg_interval < 20:
            pattern = "fast"
            message = "やや速いペースです"
        elif avg_interval < 40:
            pattern = "moderate"
            message = "適度な間隔です"
        else:
            pattern = "slow"
            message = "ゆっくりペースです"
        
        return {
            "pattern": pattern,
            "message": message,
            "avg_interval_minutes": round(avg_interval, 1),
            "most_consumed": max(drink_types.items(), key=lambda x: x[1])[0] if drink_types else None,
            "variety_count": len(drink_types)
        }
    
    def _generate_recommendations(self, analysis: Dict) -> List[Dict[str, str]]:
        """分析結果に基づいて推奨事項を生成"""
        recommendations = []
        
        pace = analysis["pace_analysis"]["status"]
        total = analysis["total_analysis"]["status"]
        pattern = analysis["pattern_analysis"]["pattern"]
        
        # ペースに基づく推奨
        if pace == "dangerous":
            recommendations.append({
                "type": "urgent",
                "message": "すぐに水を飲んで、飲酒を一時中断してください"
            })
        elif pace == "fast":
            recommendations.append({
                "type": "warning",
                "message": "少しペースを落として、つまみを食べましょう"
            })
        
        # 総量に基づく推奨
        if total == "excessive":
            recommendations.append({
                "type": "urgent",
                "message": "今日はもう十分です。水分補給をしっかりしてください"
            })
        elif total == "heavy":
            recommendations.append({
                "type": "warning",
                "message": "そろそろ最後の一杯にしませんか？"
            })
        
        # パターンに基づく推奨
        if pattern == "rapid":
            recommendations.append({
                "type": "info",
                "message": "もう少しゆっくり楽しみましょう"
            })
        
        # 水分補給の推奨（1時間ごと）
        if analysis["pace_analysis"]["duration_hours"] > 1:
            recommendations.append({
                "type": "info",
                "message": "定期的な水分補給を忘れずに"
            })
        
        return recommendations
    
    def _determine_intervention_level(self, analysis: Dict) -> str:
        """インターベンションレベルを決定"""
        pace = analysis["pace_analysis"]["status"]
        total = analysis["total_analysis"]["status"]
        
        if pace == "dangerous" or total == "excessive":
            return "high"
        elif pace == "fast" or total == "heavy":
            return "medium"
        elif pace == "moderate" or total == "moderate":
            return "low"
        else:
            return "none"
    
    def _detect_special_events(self, drinks: List[Dict], session_data: Dict) -> List[Dict]:
        """特別なイベントを検出"""
        events = []
        
        # 初めての飲酒
        if len(drinks) == 1:
            events.append({
                "type": "first_drink",
                "message": "今日の飲み会スタート！楽しんでくださいね"
            })
        
        # 3杯目の節目
        if len(drinks) == 3:
            events.append({
                "type": "milestone",
                "message": "3杯目ですね。水も飲みましょう"
            })
        
        # 長時間飲酒（3時間以上）
        start_time = session_data.get('start_time')
        if start_time:
            if hasattr(start_time, 'seconds'):
                start_dt = datetime.fromtimestamp(start_time.seconds, tz=timezone.utc)
            else:
                start_dt = start_time
            
            duration = (datetime.now(timezone.utc) - start_dt).total_seconds() / 3600
            if duration > 3:
                events.append({
                    "type": "long_session",
                    "message": "長時間お疲れ様です。そろそろ締めの時間かも？"
                })
        
        return events
    
    def _get_drink_time(self, drink: Dict) -> datetime:
        """飲酒記録から時刻を取得"""
        timestamp = drink.get('timestamp')
        if hasattr(timestamp, 'seconds'):
            return datetime.fromtimestamp(timestamp.seconds, tz=timezone.utc)
        elif isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            return datetime.now(timezone.utc)
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """エラーレスポンスを作成"""
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ファクトリー関数
def create_drinking_coach() -> DrinkingCoachAgent:
    """Drinking Coachエージェントのインスタンスを作成"""
    return DrinkingCoachAgent()