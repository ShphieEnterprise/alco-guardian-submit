"""Guardian Monitor endpoint"""
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
def guardian_monitor(request):
    """Guardian monitoring endpoint"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        session_id = get_or_create_session(user_id)
        
        # セッションデータを取得
        session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
        session_data = session_ref.get().to_dict()
        
        # 飲酒量を取得
        total_alcohol_g = session_data.get('total_alcohol_g', 0)
        
        # Guardian分析を実行（簡易版）
        if total_alcohol_g >= 20:
            level = {"color": "red", "message": "飲み過ぎです。水分補給をしましょう。"}
        elif total_alcohol_g >= 15:
            level = {"color": "orange", "message": "そろそろペースを落としましょう。"}
        elif total_alcohol_g >= 10:
            level = {"color": "yellow", "message": "良いペースです。水も飲みましょう。"}
        else:
            level = {"color": "green", "message": "適度に楽しんでいます。"}
        
        result = {
            "level": level,
            "total_alcohol_g": total_alcohol_g,
            "recommendations": ["水分補給を忘れずに", "適度なペースで楽しみましょう"]
        }
        
        return add_cors_headers(
            json.dumps({
                "success": True,
                "user_id": user_id,
                "session_id": session_id,
                "guardian_status": result
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error in guardian monitor: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )