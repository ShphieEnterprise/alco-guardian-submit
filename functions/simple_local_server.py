#!/usr/bin/env python3
"""
Simple local server for testing AlcoGuardian backend
"""
import os
import json
import random
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set environment variables
os.environ['GCP_PROJECT'] = 'alco-guardian-test-local'
os.environ['DISABLE_AUTH'] = 'true'

app = Flask(__name__)
CORS(app)

# Drink master data (from main.py)
DRINKS_MASTER = {
    "beer": {"name": "ビール", "alcohol": 5, "volume": 350, "category": "beer"},
    "wine": {"name": "ワイン", "alcohol": 12, "volume": 125, "category": "wine"},
    "sake": {"name": "日本酒", "alcohol": 15, "volume": 180, "category": "sake"},
    "highball": {"name": "ハイボール", "alcohol": 7, "volume": 350, "category": "beer"},
    "shochu": {"name": "焼酎水割り", "alcohol": 10, "volume": 200, "category": "shochu"},
    "cocktail": {"name": "カクテル", "alcohol": 15, "volume": 100, "category": "cocktail"}
}

# In-memory session storage
sessions = {}
current_session = None

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "server": "local-test"})

@app.route('/get_drinks_master', methods=['GET', 'OPTIONS'])
def get_drinks_master():
    if request.method == 'OPTIONS':
        return '', 204
    return jsonify(DRINKS_MASTER)

@app.route('/transcribe', methods=['POST', 'OPTIONS'])
def transcribe():
    if request.method == 'OPTIONS':
        return '', 204
    
    # Check if audio file is provided
    if 'audio' not in request.files:
        return jsonify({"error": "音声ファイルが提供されていません"}), 400
    
    audio_file = request.files['audio']
    
    # Mock transcription for testing
    mock_transcriptions = [
        "こんばんは。今日は仕事が終わって一杯飲みたい気分です。",
        "おすすめのお酒を教えてください。さっぱりしたものがいいです。",
        "今日は本当に疲れました。ストレス発散したいです。",
        "ビールとワインはどちらがアルコール度数が高いですか。"
    ]
    
    import random
    transcription = random.choice(mock_transcriptions)
    
    return jsonify({
        "success": True,
        "transcription": transcription,
        "filename": audio_file.filename,
        "message": "音声を正常に文字起こししました"
    })

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 204
    
    data = request.get_json() or {}
    message = data.get('message', '')
    
    # Simple response logic
    responses = [
        "こんばんは！今日もお疲れ様でした。何か飲まれますか？",
        "いい選択ですね！美味しいお酒を楽しみましょう。",
        "適度に楽しむのが一番ですよ。水分補給も忘れずに！"
    ]
    
    import random
    response = random.choice(responses)
    
    return jsonify({
        "success": True,
        "message": response,
        "imageId": random.randint(1, 10),
        "agent": "bartender"
    })

@app.route('/start_session', methods=['POST', 'OPTIONS'])
def start_session():
    if request.method == 'OPTIONS':
        return '', 204
    
    global current_session
    
    session_id = str(uuid.uuid4())
    current_session = {
        "id": session_id,
        "start_time": datetime.now().isoformat(),
        "drinks": [],
        "total_alcohol_g": 0
    }
    sessions[session_id] = current_session
    
    return jsonify({
        "sessionId": session_id,
        "startTime": current_session["start_time"],
        "message": "飲酒セッションを開始しました。適度に楽しみましょう！"
    })

@app.route('/drink', methods=['POST', 'OPTIONS'])
def drink():
    if request.method == 'OPTIONS':
        return '', 204
    
    global current_session
    if not current_session:
        # Auto-create session
        session_id = str(uuid.uuid4())
        current_session = {
            "id": session_id,
            "start_time": datetime.now().isoformat(),
            "drinks": [],
            "total_alcohol_g": 0
        }
        sessions[session_id] = current_session
    
    data = request.get_json() or {}
    drink_name = data.get('drinkName', 'ビール')
    volume = data.get('volume', 350)
    alcohol_percentage = data.get('alcoholPercentage', 5)
    
    # Calculate pure alcohol
    pure_alcohol_g = volume * alcohol_percentage / 100 * 0.8
    current_session['total_alcohol_g'] += pure_alcohol_g
    
    # Determine warning level
    total = current_session['total_alcohol_g']
    if total < 20:
        warning_level = 'green'
    elif total < 40:
        warning_level = 'yellow'
    elif total < 60:
        warning_level = 'orange'
    else:
        warning_level = 'red'
    
    drink_record = {
        "name": drink_name,
        "volume": volume,
        "alcohol_percentage": alcohol_percentage,
        "pure_alcohol_g": pure_alcohol_g,
        "timestamp": datetime.now().isoformat()
    }
    current_session['drinks'].append(drink_record)
    
    response_message = f"🍻 {drink_name}を記録しました！純アルコール量: {pure_alcohol_g:.1f}g"
    if warning_level == 'yellow':
        response_message += "\n⚠️ そろそろペースを落としましょう。"
    elif warning_level == 'orange':
        response_message += "\n⚠️ かなり飲んでいます。水分補給を忘れずに！"
    elif warning_level == 'red':
        response_message += "\n🚨 飲みすぎです！今日はここまでにしましょう。"
    
    return jsonify({
        "success": True,
        "message": response_message,
        "pureAlcoholG": pure_alcohol_g,
        "totalAlcoholG": current_session['total_alcohol_g'],
        "imageId": random.randint(1, 10),
        "guardianResponse": {
            "warningLevel": warning_level,
            "message": response_message,
            "recommendation": "適度な飲酒を心がけましょう"
        },
        "coachResponse": {
            "pace": "moderate" if warning_level in ['green', 'yellow'] else "fast",
            "totalConsumption": current_session['total_alcohol_g'],
            "recommendation": "水分補給を忘れずに"
        }
    })

@app.route('/add_drink', methods=['POST', 'OPTIONS'])
def add_drink():
    if request.method == 'OPTIONS':
        return '', 204
    
    global current_session
    if not current_session:
        # Auto-create session
        start_session()
    
    data = request.get_json() or {}
    drink_id = data.get('drink_id')
    
    if not drink_id or drink_id not in DRINKS_MASTER:
        return jsonify({"code": "BAD_REQUEST", "message": "Invalid drink_id"}), 400
    
    drink = DRINKS_MASTER[drink_id]
    alcohol_g = drink['volume'] * (drink['alcohol'] / 100) * 0.8
    
    current_session['drinks'].append({
        "drink_id": drink_id,
        "alcohol_g": alcohol_g,
        "timestamp": datetime.now().isoformat()
    })
    current_session['total_alcohol_g'] += alcohol_g
    
    # Simple guardian logic
    total = current_session['total_alcohol_g']
    if total > 40:
        guardian_color = "red"
        guardian_message = "飲み過ぎです！水を飲んで休憩しましょう。"
    elif total > 20:
        guardian_color = "orange"
        guardian_message = "そろそろペースを落としましょう。"
    elif total > 10:
        guardian_color = "yellow"
        guardian_message = "適度なペースを心がけましょう。"
    else:
        guardian_color = "green"
        guardian_message = "良いペースです。"
    
    return jsonify({
        "success": True,
        "alcohol_g": alcohol_g,
        "total_alcohol_g": current_session['total_alcohol_g'],
        "guardian": {
            "level": {
                "color": guardian_color,
                "message": guardian_message
            }
        }
    })

@app.route('/guardian_check', methods=['POST', 'OPTIONS'])
def guardian_check():
    if request.method == 'OPTIONS':
        return '', 204
    
    global current_session
    if not current_session:
        return jsonify({
            "warningLevel": "green",
            "message": "セッションが開始されていません",
            "recommendation": "飲酒を始める際は適度に楽しみましょう"
        })
    
    total = current_session['total_alcohol_g']
    if total < 20:
        warning_level = 'green'
        message = "健康的な飲酒量です。このペースを保ちましょう。"
    elif total < 40:
        warning_level = 'yellow'
        message = "適度な飲酒量ですが、ペースに注意してください。"
    elif total < 60:
        warning_level = 'orange'
        message = "かなり飲んでいます。休憩を取ることをお勧めします。"
    else:
        warning_level = 'red'
        message = "飲みすぎです！今日はここまでにしましょう。"
    
    return jsonify({
        "warningLevel": warning_level,
        "message": message,
        "recommendation": "水分補給を忘れずに、おつまみも食べましょう",
        "estimatedBAC": total * 0.015,  # Simple estimation
        "totalAlcoholG": total
    })

@app.route('/get_current_session', methods=['GET', 'OPTIONS'])
def get_current_session():
    if request.method == 'OPTIONS':
        return '', 204
    
    if not current_session:
        return jsonify({"active": False})
    
    from datetime import datetime
    start_time = datetime.fromisoformat(current_session['start_time'])
    duration_minutes = int((datetime.now() - start_time).total_seconds() / 60)
    
    return jsonify({
        "active": True,
        "session_id": current_session['id'],
        "start_time": current_session['start_time'],
        "duration_minutes": duration_minutes,
        "total_alcohol_g": current_session['total_alcohol_g'],
        "drinks": current_session['drinks']
    })

if __name__ == '__main__':
    print("🚀 AlcoGuardian Simple Local Server")
    print("📍 Running on http://localhost:8080")
    print("\nAvailable endpoints:")
    print("  GET  /health")
    print("  GET  /get_drinks_master")
    print("  POST /chat")
    print("  POST /start_session")
    print("  POST /add_drink")
    print("  GET  /get_current_session")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=8080, debug=True)