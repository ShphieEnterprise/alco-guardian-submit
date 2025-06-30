"""Drinking Coach Analyze endpoint"""
import json
import logging
import functions_framework
from datetime import datetime, timedelta
from firebase_admin import firestore, auth, initialize_app
import os

# Firebase Admin SDK初期化
try:
    initialize_app()
except ValueError:
    # すでに初期化されている場合はパス
    pass

# Firestore client
db = firestore.client()

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

def get_user_id(request):
    """Extract user ID from request (mock for hackathon)"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            token = auth_header.split('Bearer ')[1]
            decoded = auth.verify_id_token(token)
            return decoded['uid']
        except:
            pass
    return "demo_user_001"

def get_or_create_session(user_id):
    """Get active session or create new one"""
    sessions_ref = db.collection('users').document(user_id).collection('sessions')
    active_sessions = sessions_ref.where('status', '==', 'active').limit(1).get()
    
    if active_sessions:
        return active_sessions[0].id
    
    # Create new session
    session_data = {
        'start_time': firestore.SERVER_TIMESTAMP,
        'end_time': None,
        'total_alcohol_g': 0,
        'status': 'active',
        'guardian_warnings': []
    }
    
    doc_ref = sessions_ref.add(session_data)
    return doc_ref[1].id

@functions_framework.http
def drinking_coach_analyze(request):
    """Drinking coach analysis endpoint"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        session_id = get_or_create_session(user_id)
        
        # セッションデータを取得
        session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
        session_data = session_ref.get().to_dict()
        
        # 飲酒履歴を取得
        drinks_ref = session_ref.collection('drinks')
        drinks = []
        for drink in drinks_ref.order_by('timestamp').get():
            drink_data = drink.to_dict()
            drinks.append(drink_data)
        
        # 飲酒ペースを分析
        pace_analysis = "適度なペース"
        if len(drinks) >= 2:
            # 最初の飲み物から最後の飲み物までの時間を計算
            first_drink_time = drinks[0].get('timestamp')
            last_drink_time = drinks[-1].get('timestamp')
            
            if hasattr(first_drink_time, 'seconds') and hasattr(last_drink_time, 'seconds'):
                duration_minutes = (last_drink_time.seconds - first_drink_time.seconds) / 60
                drinks_per_hour = len(drinks) / (duration_minutes / 60) if duration_minutes > 0 else 0
                
                if drinks_per_hour > 3:
                    pace_analysis = "ペースが速すぎます"
                elif drinks_per_hour > 2:
                    pace_analysis = "少しペースが速いです"
                else:
                    pace_analysis = "良いペースです"
        
        # 分析結果を構築
        analysis = {
            "pace": pace_analysis,
            "total_drinks": len(drinks),
            "total_alcohol_g": session_data.get('total_alcohol_g', 0),
            "recommendations": [
                "水分補給を忘れずに",
                "おつまみも食べながら楽しみましょう",
                "適度なペースで楽しみましょう"
            ]
        }
        
        return add_cors_headers(
            json.dumps({
                "success": True,
                "user_id": user_id,
                "session_id": session_id,
                "analysis": analysis
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error in drinking coach analyze: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )