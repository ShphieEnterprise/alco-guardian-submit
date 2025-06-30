"""
Guardian Agent - 飲酒ペース監視と警告生成
"""
import logging
from datetime import datetime, timedelta
from firebase_admin import firestore

# Firestore client
db = firestore.client()


class GuardianAgent:
    # 推奨値
    SAFE_PACE_DRINKS_PER_HOUR = 1
    DAILY_LIMIT_G = 20  # 純アルコール20g
    WARNING_LEVELS = {
        "ok": {"color": "green", "message": "良いペースです"},
        "caution": {"color": "orange", "message": "ペースに注意してください"},
        "warning": {"color": "red", "message": "飲み過ぎです。水分補給を"},
        "stop": {"color": "red", "message": "これ以上は危険です"}
    }
    
    def analyze_drinking_pattern(self, user_id, session_id):
        """飲酒パターンを分析"""
        try:
            session_data = self._get_session_data(user_id, session_id)
            
            # 1. 総量チェック
            total_alcohol = session_data.get('total_alcohol_g', 0)
            
            # 2. ペースチェック（30分あたりの飲酒数）
            recent_drinks = self._get_recent_drinks(user_id, session_id, minutes=30)
            pace_score = len(recent_drinks)
            
            # 3. 時間経過チェック
            duration_hours = self._get_session_duration(session_data) / 3600
            
            # 判定ロジック
            if total_alcohol > self.DAILY_LIMIT_G * 1.5:
                return self.WARNING_LEVELS["stop"]
            elif total_alcohol > self.DAILY_LIMIT_G:
                return self.WARNING_LEVELS["warning"]
            elif pace_score >= 2:
                return self.WARNING_LEVELS["caution"]
            else:
                return self.WARNING_LEVELS["ok"]
                
        except Exception as e:
            logging.error(f"Error in Guardian analysis: {e}")
            return self.WARNING_LEVELS["ok"]  # エラー時は安全側に
    
    def _get_session_data(self, user_id, session_id):
        """セッションデータを取得"""
        session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
        session_doc = session_ref.get()
        
        if session_doc.exists:
            return session_doc.to_dict()
        return {}
    
    def _get_recent_drinks(self, user_id, session_id, minutes=30):
        """最近の飲酒記録を取得"""
        drinks_ref = db.collection('users').document(user_id).collection('sessions').document(session_id).collection('drinks')
        
        # 時間でフィルタリング
        time_threshold = datetime.now() - timedelta(minutes=minutes)
        recent_drinks = drinks_ref.where('timestamp', '>=', time_threshold).get()
        
        return recent_drinks
    
    def _get_session_duration(self, session_data):
        """セッション継続時間を秒で返す"""
        start_time = session_data.get('start_time')
        if not start_time:
            return 0
            
        # Firestoreのタイムスタンプをdatetimeに変換
        if hasattr(start_time, 'seconds'):
            start_datetime = datetime.fromtimestamp(start_time.seconds)
        else:
            start_datetime = start_time
            
        duration = datetime.now() - start_datetime
        return duration.total_seconds()
    
    def check_veto(self, user_id, session_id):
        """Bartenderへの拒否権チェック"""
        result = self.analyze_drinking_pattern(user_id, session_id)
        
        if result['color'] == 'red':
            return {
                'veto': True,
                'reason': result['message']
            }
        
        return {
            'veto': False,
            'reason': None
        }


def save_guardian_warning(user_id, session_id, warning):
    """警告履歴を保存"""
    session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
    
    warning_data = {
        'timestamp': firestore.SERVER_TIMESTAMP,
        'level': warning['color'],
        'message': warning['message']
    }
    
    session_ref.update({
        'guardian_warnings': firestore.ArrayUnion([warning_data])
    })


def check_guardian_rules(user_id, session_id):
    """Guardian判定を実行して結果を返す"""
    guardian = GuardianAgent()
    return guardian.analyze_drinking_pattern(user_id, session_id)