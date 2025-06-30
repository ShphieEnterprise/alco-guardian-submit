import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import random

import firebase_admin
import functions_framework
import vertexai
from firebase_admin import auth, firestore
from google.cloud import storage, texttospeech
from nanoid import generate
from vertexai.preview.generative_models import GenerativeModel, Part

# ---------- 初期化 ----------
firebase_admin.initialize_app()
PROJECT = os.getenv("GCP_PROJECT")
# Vertex AI API を呼び出す際の推奨ロケーション (Geminiモデル用)
GEMINI_LOCATION = os.getenv("GEMINI_LOCATION", "us-central1")
# 使用するGeminiモデル
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")  # デフォルトを1.5 Proから2.0 Flashに変更

# Cloud Functionsのデプロイリージョンとは別にVertex AIの処理リージョンを指定
# (互換性の高い us-central1 を推奨)
vertexai.init(project=PROJECT, location=GEMINI_LOCATION)
model = GenerativeModel(GEMINI_MODEL)

# 他の環境変数 (ログレベル、アップロードバケットなど)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)
bucket_name = os.getenv("UPLOAD_BUCKET")
storage_client = storage.Client()

# Firestore client
db = firestore.client()

# Text-to-Speech クライアントの初期化
tts_client = texttospeech.TextToSpeechClient()

# TTS用のバケット設定
TTS_BUCKET_NAME = os.getenv("STORAGE_BUCKET", "alco-guardian.appspot.com")
tts_bucket = storage_client.bucket(TTS_BUCKET_NAME)

# 日本語男性音声
VOICE_NAME = "ja-JP-Neural2-B"


def add_cors_headers(response_data, status_code, content_type="application/json"):
    """レスポンスにCORSヘッダーを追加する共通関数"""
    headers = {
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": "*",  # 本番環境では特定のオリジンに制限することを推奨
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "Authorization,Content-Type",
        "Access-Control-Allow-Credentials": "true",
    }
    return (response_data, status_code, headers)


@functions_framework.http
def transcribe(request):
    # CORS対応
    if request.method == "OPTIONS":
        return (
            "",
            204,
            {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
                "Access-Control-Allow-Headers": "Authorization,Content-Type",
            },
        )

    try:
        # 認証チェック
        id_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        uid = None
        if id_token:
            try:
                uid = auth.verify_id_token(id_token)["uid"]
            except auth.InvalidIdTokenError:
                logging.warning("Invalid ID token provided.")
                return add_cors_headers(
                    json.dumps({"code": "UNAUTHORIZED", "message": "Invalid token"}),
                    401
                )
        else:
            logging.warning("No authorization token provided.")
            return add_cors_headers(
                json.dumps({"code": "UNAUTHORIZED", "message": "Authorization token required"}),
                401
            )

        logging.info(f"Processing request from user: {uid}")

        if "file" not in request.files:
            logging.error("No file part in the request.")
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "No file part in the request"}),
                400
            )

        request_file = request.files["file"]

        if request_file.filename == "":
            logging.error("No selected file.")
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "No selected file"}),
                400
            )

        if not bucket_name:
            logging.error("UPLOAD_BUCKET environment variable is not set.")
            return add_cors_headers(
                json.dumps({"code": "INTERNAL_CONFIG_ERROR", "message": "Server configuration error (bucket)"}),
                500
            )

        # ===== DEBUG MODE: load bytes instead of GCS =====
        tmp_file_path = None  # finallyブロックで参照するため先に定義
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(request_file.filename).suffix) as tmp:
                request_file.save(tmp.name)  # saveメソッドはファイルオブジェクトのパスを期待
                # tmp.flush() # saveが完了すればflushは不要な場合もある
                audio_bytes = Path(tmp.name).read_bytes()
                tmp_file_path = tmp.name

            effective_mime_type = request_file.content_type
            if not effective_mime_type or not effective_mime_type.startswith("audio/"):
                logging.warning(
                    f"Uploaded file MIME type '{request_file.content_type}' is not specific. Falling back to 'audio/mpeg'."
                )
                effective_mime_type = "audio/mpeg"  # MP3を想定したフォールバック

            logging.info(
                f"File '{request_file.filename}' saved to temporary path: {tmp_file_path}. Effective MIME type: {effective_mime_type}. Size: {len(audio_bytes)} bytes."
            )

            audio_part = Part.from_data(data=audio_bytes, mime_type=effective_mime_type)
            prompt = "以下の音声を書き起こしてください。"

            logging.info(f"Calling Gemini API with in-memory bytes for file: {request_file.filename}")
            response = model.generate_content([audio_part, prompt])
            transcript = response.text
            logging.info(f"Transcription successful using in-memory bytes. Transcript length: {len(transcript)}")

            return add_cors_headers(
                json.dumps(
                    {
                        "message": "Transcription successful (direct bytes).",
                        "original_filename": request_file.filename,
                        "transcript": transcript,
                    }
                ),
                200
            )
        finally:
            if tmp_file_path and Path(tmp_file_path).exists():
                Path(tmp_file_path).unlink()
                logging.info(f"Temporary file {tmp_file_path} deleted.")
        # ===== END DEBUG MODE =====

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        logging.error(
            f"Error processing request (direct bytes mode). Type: {error_type}, Message: {error_message}", exc_info=True
        )

        response_payload = {
            "code": "TRANSCRIPTION_ERROR",
            "message": "Error during transcription process (direct bytes mode).",
            "error_type": error_type,
        }
        if len(error_message) > 200:  # 長すぎるエラーメッセージは一部のみ含める
            response_payload["error_preview"] = error_message[:200] + "..."
        else:
            response_payload["error_preview"] = error_message

        return add_cors_headers(
            json.dumps(response_payload),
            500
        )


# ========== Session Management APIs ==========

@functions_framework.http
def start_session(request):
    """Start drinking session"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        
        # Check for existing active session
        sessions_ref = db.collection('users').document(user_id).collection('sessions')
        active_sessions = sessions_ref.where('status', '==', 'active').limit(1).get()
        
        if active_sessions:
            return add_cors_headers(
                json.dumps({
                    "code": "SESSION_EXISTS",
                    "message": "既にセッションが開始されています"
                }, ensure_ascii=False),
                400
            )
        
        # Create new session
        session_data = {
            'start_time': firestore.SERVER_TIMESTAMP,
            'end_time': None,
            'total_alcohol_g': 0,
            'status': 'active',
            'guardian_warnings': []
        }
        
        doc_ref = sessions_ref.add(session_data)
        session_id = doc_ref[1].id
        
        return add_cors_headers(
            json.dumps({
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "message": "飲酒セッションを開始しました。適度に楽しみましょう！"
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error starting session: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )


@functions_framework.http
def get_current_session(request):
    """Get current session info"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        
        # Get active session
        sessions_ref = db.collection('users').document(user_id).collection('sessions')
        active_sessions = sessions_ref.where('status', '==', 'active').limit(1).get()
        
        if not active_sessions:
            return add_cors_headers(
                json.dumps({
                    "active": False
                }),
                200
            )
        
        session = active_sessions[0]
        session_id = session.id
        session_data = session.to_dict()
        
        # Get drinks
        drinks_ref = sessions_ref.document(session_id).collection('drinks')
        drinks = []
        for drink in drinks_ref.get():
            drink_data = drink.to_dict()
            drink_data['id'] = drink.id
            drinks.append(drink_data)
        
        # Get Guardian status
        from guardian import GuardianAgent
        guardian = GuardianAgent()
        guardian_status = guardian.analyze_drinking_pattern(user_id, session_id)
        
        # Calculate duration
        start_time = session_data.get('start_time')
        if hasattr(start_time, 'seconds'):
            start_datetime = datetime.fromtimestamp(start_time.seconds)
        else:
            start_datetime = start_time or datetime.now()
        
        duration_minutes = int((datetime.now() - start_datetime).total_seconds() / 60)
        
        return add_cors_headers(
            json.dumps({
                "active": True,
                "session_id": session_id,
                "start_time": start_datetime.isoformat(),
                "duration_minutes": duration_minutes,
                "total_alcohol_g": session_data.get('total_alcohol_g', 0),
                "drinks": drinks,
                "guardian_status": guardian_status,
                "recommendations": generate_recommendations(session_data)
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error getting session: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )


def generate_recommendations(session_data):
    """Generate recommendations based on session data"""
    total_alcohol = session_data.get('total_alcohol_g', 0)
    
    if total_alcohol > 20:
        return ["水分補給をしましょう", "そろそろ切り上げ時かも", "タクシーの手配をお勧めします"]
    elif total_alcohol > 10:
        return ["水を飲みながら楽しみましょう", "おつまみも忘れずに"]
    else:
        return ["適度なペースで楽しみましょう"]


@functions_framework.http 
def guardian_check(request):
    """Guardian status check endpoint"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        session_id = get_or_create_session(user_id)
        
        from guardian import GuardianAgent, save_guardian_warning
        guardian = GuardianAgent()
        result = guardian.analyze_drinking_pattern(user_id, session_id)
        
        # Save warning if needed
        if result['color'] in ['orange', 'red']:
            save_guardian_warning(user_id, session_id, result)
        
        # Get session stats
        session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
        session_data = session_ref.get().to_dict()
        
        # Count drinks
        drinks_ref = session_ref.collection('drinks')
        drinks_count = len(drinks_ref.get())
        
        # Calculate duration
        start_time = session_data.get('start_time')
        if hasattr(start_time, 'seconds'):
            start_datetime = datetime.fromtimestamp(start_time.seconds)
        else:
            start_datetime = start_time or datetime.now()
        
        duration_minutes = int((datetime.now() - start_datetime).total_seconds() / 60)
        
        return add_cors_headers(
            json.dumps({
                "level": result,
                "stats": {
                    "total_alcohol_g": session_data.get('total_alcohol_g', 0),
                    "drinks_count": drinks_count,
                    "duration_minutes": duration_minutes
                }
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error in guardian check: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR", 
                "message": str(e)
            }),
            500
        )


import hashlib
import random
from firebase_admin import firestore

# Firestore client
db = firestore.client()

def generate_audio_filename(text, voice_name):
    """テキストと声の設定からユニークなファイル名を生成"""
    content = f"{text}:{voice_name}"
    hash_digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"tts/{voice_name}/{hash_digest}.mp3"


def synthesize_speech(text, voice_name="ja-JP-Neural2-B"):
    """テキストを音声に変換"""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name=voice_name
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
        pitch=0.0
    )
    
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    return response.audio_content


@functions_framework.http
def chat(request):
    """Bartenderチャットエンドポイント（音声返答対応版）"""
    
    # CORS対応
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        # リクエストボディの取得
        request_json = request.get_json() if request.is_json else {}
        
        # メッセージの取得
        user_message = request_json.get("message", "")
        if not user_message:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "Message is required"}),
                400
            )
        
        # 音声生成オプション
        enable_tts = request_json.get("enableTTS", True)
        
        # Bartenderプロンプト
        now = datetime.now()
        days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
        context = {
            "current_time": now.strftime("%H:%M"),
            "day_of_week": days[now.weekday()]
        }
        
        bartender_prompt = f"""あなたは「AI Bartender」として、ユーザーと楽しく温かい会話をするエージェントです。

# 役割
- ユーザーの話を共感的に聞き、楽しい会話を提供する
- お酒の話題を適度に織り交ぜながら、健康的な飲み方をさりげなく促す
- 明るく親しみやすいトーンで対応する

# ガイドライン
- 短めの返答（1-3文程度）を心がける
- 絵文字は控えめに使用（1つまで）

# 現在の状況
- 時刻: {context['current_time']}
- 曜日: {context['day_of_week']}

ユーザー: {user_message}
Bartender:"""
        
        # ADK Bartenderエージェントを使用
        try:
            user_id = get_user_id(request)
            
            # ADK Bartenderサービスを使用
            from agents.bartender_adk import create_bartender_service
            bartender_service = create_bartender_service()
            
            # エージェントとチャット（同期的に実行）
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_data = loop.run_until_complete(
                bartender_service.chat(
                    user_message=user_message,
                    user_id=user_id
                )
            )
            
            bartender_response = response_data["message"]
            
        except Exception as e:
            logging.error(f"Error in ADK Bartender: {e}")
            # フォールバック: 従来のGemini直接呼び出し
            try:
                response = model.generate_content(bartender_prompt)
                bartender_response = response.text.strip() if response and response.text else "すみません、ちょっと聞き取れませんでした。"
            except:
                bartender_response = "すみません、ちょっと聞き取れませんでした。もう一度お願いできますか？"
        
        # ランダムな画像ID
        image_id = random.randint(1, 10)
        
        # 音声生成
        audio_url = None
        if enable_tts and bucket_name:
            try:
                voice_name = "ja-JP-Neural2-B"
                filename = generate_audio_filename(bartender_response, voice_name)
                
                # Cloud Storageに既存ファイルがあるかチェック
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(filename)
                
                if blob.exists():
                    audio_url = blob.public_url
                    logging.info(f"Using cached audio: {filename}")
                else:
                    # 音声合成
                    audio_content = synthesize_speech(bartender_response, voice_name)
                    
                    # Cloud Storageにアップロード
                    blob.cache_control = "public, max-age=86400"
                    blob.upload_from_string(audio_content, content_type="audio/mpeg")
                    blob.make_public()
                    audio_url = blob.public_url
                    logging.info(f"Generated new audio: {filename}")
                    
            except Exception as e:
                logging.error(f"Error generating TTS audio: {e}")
                # TTSエラーでもチャット機能は継続
        
        # レスポンスの構築
        response_data = {
            "success": True,
            "message": bartender_response,
            "imageId": image_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "bartender"
        }
        
        if audio_url:
            response_data["audioUrl"] = audio_url
        
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


# ========== Session Management APIs ==========

@functions_framework.http
def start_session(request):
    """Start drinking session"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        
        # Check for existing active session
        sessions_ref = db.collection('users').document(user_id).collection('sessions')
        active_sessions = sessions_ref.where('status', '==', 'active').limit(1).get()
        
        if active_sessions:
            return add_cors_headers(
                json.dumps({
                    "code": "SESSION_EXISTS",
                    "message": "既にセッションが開始されています"
                }, ensure_ascii=False),
                400
            )
        
        # Create new session
        session_data = {
            'start_time': firestore.SERVER_TIMESTAMP,
            'end_time': None,
            'total_alcohol_g': 0,
            'status': 'active',
            'guardian_warnings': []
        }
        
        doc_ref = sessions_ref.add(session_data)
        session_id = doc_ref[1].id
        
        return add_cors_headers(
            json.dumps({
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "message": "飲酒セッションを開始しました。適度に楽しみましょう！"
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error starting session: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )


@functions_framework.http
def get_current_session(request):
    """Get current session info"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        
        # Get active session
        sessions_ref = db.collection('users').document(user_id).collection('sessions')
        active_sessions = sessions_ref.where('status', '==', 'active').limit(1).get()
        
        if not active_sessions:
            return add_cors_headers(
                json.dumps({
                    "active": False
                }),
                200
            )
        
        session = active_sessions[0]
        session_id = session.id
        session_data = session.to_dict()
        
        # Get drinks
        drinks_ref = sessions_ref.document(session_id).collection('drinks')
        drinks = []
        for drink in drinks_ref.get():
            drink_data = drink.to_dict()
            drink_data['id'] = drink.id
            drinks.append(drink_data)
        
        # Get Guardian status
        from guardian import GuardianAgent
        guardian = GuardianAgent()
        guardian_status = guardian.analyze_drinking_pattern(user_id, session_id)
        
        # Calculate duration
        start_time = session_data.get('start_time')
        if hasattr(start_time, 'seconds'):
            start_datetime = datetime.fromtimestamp(start_time.seconds)
        else:
            start_datetime = start_time or datetime.now()
        
        duration_minutes = int((datetime.now() - start_datetime).total_seconds() / 60)
        
        return add_cors_headers(
            json.dumps({
                "active": True,
                "session_id": session_id,
                "start_time": start_datetime.isoformat(),
                "duration_minutes": duration_minutes,
                "total_alcohol_g": session_data.get('total_alcohol_g', 0),
                "drinks": drinks,
                "guardian_status": guardian_status,
                "recommendations": generate_recommendations(session_data)
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error getting session: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )


def generate_recommendations(session_data):
    """Generate recommendations based on session data"""
    total_alcohol = session_data.get('total_alcohol_g', 0)
    
    if total_alcohol > 20:
        return ["水分補給をしましょう", "そろそろ切り上げ時かも", "タクシーの手配をお勧めします"]
    elif total_alcohol > 10:
        return ["水を飲みながら楽しみましょう", "おつまみも忘れずに"]
    else:
        return ["適度なペースで楽しみましょう"]


@functions_framework.http 
def guardian_check(request):
    """Guardian status check endpoint"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        session_id = get_or_create_session(user_id)
        
        from guardian import GuardianAgent, save_guardian_warning
        guardian = GuardianAgent()
        result = guardian.analyze_drinking_pattern(user_id, session_id)
        
        # Save warning if needed
        if result['color'] in ['orange', 'red']:
            save_guardian_warning(user_id, session_id, result)
        
        # Get session stats
        session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
        session_data = session_ref.get().to_dict()
        
        # Count drinks
        drinks_ref = session_ref.collection('drinks')
        drinks_count = len(drinks_ref.get())
        
        # Calculate duration
        start_time = session_data.get('start_time')
        if hasattr(start_time, 'seconds'):
            start_datetime = datetime.fromtimestamp(start_time.seconds)
        else:
            start_datetime = start_time or datetime.now()
        
        duration_minutes = int((datetime.now() - start_datetime).total_seconds() / 60)
        
        return add_cors_headers(
            json.dumps({
                "level": result,
                "stats": {
                    "total_alcohol_g": session_data.get('total_alcohol_g', 0),
                    "drinks_count": drinks_count,
                    "duration_minutes": duration_minutes
                }
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error in guardian check: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR", 
                "message": str(e)
            }),
            500
        )


# ========== Drink Management APIs ==========

# Drink master data (hardcoded for hackathon)
DRINKS_MASTER = {
    "beer": {"name": "ビール", "alcohol": 5, "volume": 350, "category": "beer"},
    "wine": {"name": "ワイン", "alcohol": 12, "volume": 125, "category": "wine"},
    "sake": {"name": "日本酒", "alcohol": 15, "volume": 180, "category": "sake"},
    "highball": {"name": "ハイボール", "alcohol": 7, "volume": 350, "category": "beer"},
    "shochu": {"name": "焼酎水割り", "alcohol": 10, "volume": 200, "category": "shochu"},
    "cocktail": {"name": "カクテル", "alcohol": 15, "volume": 100, "category": "cocktail"}
}


def calculate_pure_alcohol(drink_type, volume_ml=None):
    """
    純アルコール量（g）= 飲酒量(ml) × アルコール度数(%) ÷ 100 × 0.8
    """
    drink_data = DRINKS_MASTER.get(drink_type)
    if not drink_data:
        raise ValueError(f"Unknown drink type: {drink_type}")
    
    alcohol_percentage = drink_data['alcohol']
    volume = volume_ml or drink_data['volume']
    
    return volume * (alcohol_percentage / 100) * 0.8


def get_or_create_session(user_id):
    """Get active session or create new one"""
    sessions_ref = db.collection('users').document(user_id).collection('sessions')
    
    # Check for active session
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


def save_drink_record(user_id, session_id, drink_data, alcohol_g):
    """Save drink record to Firestore"""
    drink_ref = db.collection('users').document(user_id).collection('sessions').document(session_id).collection('drinks')
    
    drink_record = {
        'drink_type': drink_data['drink_id'],
        'volume_ml': drink_data.get('volume_ml', DRINKS_MASTER[drink_data['drink_id']]['volume']),
        'alcohol_g': alcohol_g,
        'timestamp': firestore.SERVER_TIMESTAMP
    }
    
    drink_ref.add(drink_record)
    
    # Update session total
    session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
    session_ref.update({
        'total_alcohol_g': firestore.Increment(alcohol_g)
    })


def get_session_total(user_id, session_id):
    """Get total alcohol for session"""
    session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
    session_data = session_ref.get()
    
    if session_data.exists:
        return session_data.to_dict().get('total_alcohol_g', 0)
    return 0


def get_user_id(request):
    """Extract user ID from request (mock for hackathon)"""
    # For hackathon, use anonymous ID if no auth
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            token = auth_header.split('Bearer ')[1]
            decoded = auth.verify_id_token(token)
            return decoded['uid']
        except:
            pass
    
    # Return demo user for hackathon
    return "demo_user_001"


@functions_framework.http
def get_drinks_master(request):
    """Get available drinks list"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    return add_cors_headers(
        json.dumps(DRINKS_MASTER, ensure_ascii=False),
        200
    )


@functions_framework.http
def add_drink(request):
    """Add drink record"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        data = request.get_json()
        if not data or 'drink_id' not in data:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "drink_id is required"}),
                400
            )
        
        user_id = get_user_id(request)
        
        # Calculate pure alcohol
        alcohol_g = calculate_pure_alcohol(
            data['drink_id'], 
            data.get('volume_ml')
        )
        
        # Save to Firestore
        session_id = get_or_create_session(user_id)
        save_drink_record(user_id, session_id, data, alcohol_g)
        
        # Get Guardian check (ADK version)
        try:
            from agents.a2a_broker import get_broker, Message
            from agents.guardian_adk import create_guardian_service
            
            broker = get_broker()
            
            # A2Aメッセージで飲酒追加を通知
            drink_added_msg = Message(
                type="drink.added",
                from_agent="system",
                to_agent="guardian",
                payload={
                    "user_id": user_id,
                    "session_id": session_id,
                    "drink_id": data['drink_id'],
                    "alcohol_g": alcohol_g
                }
            )
            
            # 同期的に実行
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(broker.publish(drink_added_msg))
            
            # Guardian分析を実行
            guardian = create_guardian_service()
            guardian_result = loop.run_until_complete(
                guardian.analyze_drinking_pattern(user_id, session_id)
            )
        except Exception as e:
            logging.error(f"ADK Guardian error: {e}")
            # フォールバック
            guardian_result = {
                "level": {"color": "green", "message": "監視中"},
                "analysis": "エラーが発生しました"
            }
        
        return add_cors_headers(
            json.dumps({
                "success": True,
                "alcohol_g": alcohol_g,
                "total_alcohol_g": get_session_total(user_id, session_id),
                "guardian": guardian_result
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error adding drink: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )


# ========== Session Management APIs ==========

@functions_framework.http
def start_session(request):
    """Start drinking session"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        
        # Check for existing active session
        sessions_ref = db.collection('users').document(user_id).collection('sessions')
        active_sessions = sessions_ref.where('status', '==', 'active').limit(1).get()
        
        if active_sessions:
            return add_cors_headers(
                json.dumps({
                    "code": "SESSION_EXISTS",
                    "message": "既にセッションが開始されています"
                }, ensure_ascii=False),
                400
            )
        
        # Create new session
        session_data = {
            'start_time': firestore.SERVER_TIMESTAMP,
            'end_time': None,
            'total_alcohol_g': 0,
            'status': 'active',
            'guardian_warnings': []
        }
        
        doc_ref = sessions_ref.add(session_data)
        session_id = doc_ref[1].id
        
        return add_cors_headers(
            json.dumps({
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "message": "飲酒セッションを開始しました。適度に楽しみましょう！"
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error starting session: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )


@functions_framework.http
def get_current_session(request):
    """Get current session info"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        
        # Get active session
        sessions_ref = db.collection('users').document(user_id).collection('sessions')
        active_sessions = sessions_ref.where('status', '==', 'active').limit(1).get()
        
        if not active_sessions:
            return add_cors_headers(
                json.dumps({
                    "active": False
                }),
                200
            )
        
        session = active_sessions[0]
        session_id = session.id
        session_data = session.to_dict()
        
        # Get drinks
        drinks_ref = sessions_ref.document(session_id).collection('drinks')
        drinks = []
        for drink in drinks_ref.get():
            drink_data = drink.to_dict()
            drink_data['id'] = drink.id
            drinks.append(drink_data)
        
        # Get Guardian status
        from guardian import GuardianAgent
        guardian = GuardianAgent()
        guardian_status = guardian.analyze_drinking_pattern(user_id, session_id)
        
        # Calculate duration
        start_time = session_data.get('start_time')
        if hasattr(start_time, 'seconds'):
            start_datetime = datetime.fromtimestamp(start_time.seconds)
        else:
            start_datetime = start_time or datetime.now()
        
        duration_minutes = int((datetime.now() - start_datetime).total_seconds() / 60)
        
        return add_cors_headers(
            json.dumps({
                "active": True,
                "session_id": session_id,
                "start_time": start_datetime.isoformat(),
                "duration_minutes": duration_minutes,
                "total_alcohol_g": session_data.get('total_alcohol_g', 0),
                "drinks": drinks,
                "guardian_status": guardian_status,
                "recommendations": generate_recommendations(session_data)
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error getting session: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }),
            500
        )


def generate_recommendations(session_data):
    """Generate recommendations based on session data"""
    total_alcohol = session_data.get('total_alcohol_g', 0)
    
    if total_alcohol > 20:
        return ["水分補給をしましょう", "そろそろ切り上げ時かも", "タクシーの手配をお勧めします"]
    elif total_alcohol > 10:
        return ["水を飲みながら楽しみましょう", "おつまみも忘れずに"]
    else:
        return ["適度なペースで楽しみましょう"]


@functions_framework.http 
def guardian_check(request):
    """Guardian status check endpoint"""
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        user_id = get_user_id(request)
        session_id = get_or_create_session(user_id)
        
        from guardian import GuardianAgent, save_guardian_warning
        guardian = GuardianAgent()
        result = guardian.analyze_drinking_pattern(user_id, session_id)
        
        # Save warning if needed
        if result['color'] in ['orange', 'red']:
            save_guardian_warning(user_id, session_id, result)
        
        # Get session stats
        session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
        session_data = session_ref.get().to_dict()
        
        # Count drinks
        drinks_ref = session_ref.collection('drinks')
        drinks_count = len(drinks_ref.get())
        
        # Calculate duration
        start_time = session_data.get('start_time')
        if hasattr(start_time, 'seconds'):
            start_datetime = datetime.fromtimestamp(start_time.seconds)
        else:
            start_datetime = start_time or datetime.now()
        
        duration_minutes = int((datetime.now() - start_datetime).total_seconds() / 60)
        
        return add_cors_headers(
            json.dumps({
                "level": result,
                "stats": {
                    "total_alcohol_g": session_data.get('total_alcohol_g', 0),
                    "drinks_count": drinks_count,
                    "duration_minutes": duration_minutes
                }
            }, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error in guardian check: {e}")
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR", 
                "message": str(e)
            }),
            500
        )

# ========== TTS Helper Functions ==========

def synthesize_speech_for_drink(text, voice_name=VOICE_NAME):
    """テキストを音声に変換"""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name=voice_name
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
        pitch=0.0
    )
    
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    return response.audio_content


def upload_audio_to_storage_for_drink(audio_content, filename):
    """音声データをCloud Storageにアップロード"""
    blob = tts_bucket.blob(filename)
    
    # 既存チェック
    if blob.exists():
        logging.info(f"Audio file already exists: {filename}")
        blob.make_public()
        return blob.public_url
    
    # アップロード
    blob.upload_from_string(
        audio_content,
        content_type="audio/mpeg"
    )
    
    # キャッシュ設定
    blob.cache_control = "public, max-age=86400"
    blob.patch()
    
    # 公開設定
    blob.make_public()
    
    return blob.public_url


def generate_audio_response_for_drink(text, voice_name=VOICE_NAME):
    """テキストから音声URLを生成（キャッシュ対応）"""
    # ファイル名をハッシュで生成
    content_hash = hashlib.md5(f"{text}_{voice_name}".encode()).hexdigest()
    filename = f"tts/{voice_name}/{content_hash}.mp3"
    
    # Cloud Storageに既存チェック
    blob = tts_bucket.blob(filename)
    if blob.exists():
        logging.info(f"Using cached audio: {filename}")
        blob.make_public()
        return blob.public_url
    
    # 新規生成
    try:
        audio_content = synthesize_speech_for_drink(text, voice_name)
        audio_url = upload_audio_to_storage_for_drink(audio_content, filename)
        return audio_url
    except Exception as e:
        logging.error(f"TTS generation error: {e}")
        return None


# ========== Drink API with Audio Response ==========

@functions_framework.http
def drink(request):
    """飲酒記録エンドポイント（フロントエンド仕様対応）"""
    
    # CORS対応
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        # リクエストボディの取得
        try:
            request_json = request.get_json()
        except Exception:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "Invalid JSON"}),
                400
            )
        
        # 必須パラメータのチェック
        drink_type = request_json.get("drinkType")
        alcohol_percentage = request_json.get("alcoholPercentage")
        volume = request_json.get("volume")
        
        if not drink_type:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "drinkType is required"}),
                400
            )
        
        if alcohol_percentage is None:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "alcoholPercentage is required"}),
                400
            )
        
        if volume is None:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "volume is required"}),
                400
            )
        
        # 数値型チェック
        try:
            alcohol_percentage = float(alcohol_percentage)
            volume = float(volume)
        except (ValueError, TypeError):
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "alcoholPercentage and volume must be numbers"}),
                400
            )
        
        # 値の範囲チェック
        if alcohol_percentage < 0 or alcohol_percentage > 100:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "alcoholPercentage must be between 0 and 100"}),
                400
            )
        
        if volume <= 0:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "volume must be greater than 0"}),
                400
            )
        
        # ユーザーID取得
        user_id = get_user_id(request)
        
        # 純アルコール量計算
        # 純アルコール量（g）= 飲酒量(ml) × アルコール度数(%) ÷ 100 × 0.8
        alcohol_g = volume * (alcohol_percentage / 100) * 0.8
        
        # セッション取得または作成
        session_id = get_or_create_session(user_id)
        
        # 飲酒記録をFirestoreに保存
        drink_record = {
            'drink_type': drink_type,
            'alcohol_percentage': alcohol_percentage,
            'volume_ml': volume,
            'alcohol_g': alcohol_g,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        # Firestore に記録
        session_ref = db.collection('users').document(user_id).collection('sessions').document(session_id)
        drinks_ref = session_ref.collection('drinks')
        doc_ref = drinks_ref.add(drink_record)
        drink_id = doc_ref[1].id
        
        # セッションの総アルコール量を更新
        session_ref.update({
            'total_alcohol_g': firestore.Increment(alcohol_g)
        })
        
        # Guardian分析を実行
        guardian_result = None
        try:
            from agents.a2a_broker import get_broker, Message
            from agents.guardian_adk import create_guardian_service
            
            broker = get_broker()
            
            # A2Aメッセージで飲酒追加を通知
            drink_added_msg = Message(
                type="drink.added",
                from_agent="system",
                to_agent="guardian",
                payload={
                    "user_id": user_id,
                    "session_id": session_id,
                    "drink_type": drink_type,
                    "alcohol_g": alcohol_g
                }
            )
            
            # 同期的に実行
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(broker.publish(drink_added_msg))
            
            # Guardian分析を実行
            guardian = create_guardian_service()
            guardian_result = loop.run_until_complete(
                guardian.analyze_drinking_pattern(user_id, session_id)
            )
        except Exception as e:
            logging.error(f"ADK Guardian error: {e}")
            # Guardian分析エラーでも飲酒記録は成功とする
            guardian_result = {
                "level": {"color": "green", "message": "監視中"},
                "analysis": "Guardian分析でエラーが発生しました"
            }
        
        # Bartenderエージェントからのレスポンスメッセージを生成
        response_message = f"{drink_type}を{volume}ml記録しました。"
        
        # Guardian分析結果に基づいてメッセージを追加
        if guardian_result and guardian_result.get("level"):
            level_color = guardian_result["level"]["color"]
            if level_color == "yellow":
                response_message += " そろそろペースを落としましょうか。"
            elif level_color == "red":
                response_message += " 今日はもう十分飲みましたね。水分補給をお忘れなく。"
            else:
                response_message += " 良いペースですね。"
        
        # 音声レスポンスを生成
        audio_url = None
        try:
            audio_url = generate_audio_response_for_drink(response_message)
        except Exception as e:
            logging.error(f"Audio generation error: {e}")
            # 音声生成エラーでも処理は継続
        
        # Bartenderの画像IDをランダムに選択
        image_id = random.randint(1, 10)
        
        # 成功レスポンス
        response_data = {
            "success": True,
            "message": response_message,
            "data": {
                "id": drink_id,
                "drinkType": drink_type,
                "alcoholPercentage": alcohol_percentage,
                "volume": volume,
                "alcoholG": alcohol_g,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "userId": user_id
            },
            "guardian": guardian_result,
            "agent": "bartender",
            "imageId": image_id
        }
        
        # 音声URLがある場合は追加
        if audio_url:
            response_data["audioUrl"] = audio_url
        
        return add_cors_headers(
            json.dumps(response_data, ensure_ascii=False),
            200
        )
        
    except Exception as e:
        logging.error(f"Error in drink endpoint: {e}", exc_info=True)
        
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "error": str(e)
            }),
            500
        )


# ========== Import New Endpoints ==========
# These imports make the functions available to Functions Framework
from bartender_standalone import bartender
from guardian_monitor import guardian_monitor  
from drinking_coach_analyze import drinking_coach_analyze
from tts import tts