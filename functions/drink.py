import json
import logging
import os
from datetime import datetime, timezone
import hashlib
import random
from datetime import timedelta

import functions_framework
import firebase_admin
from firebase_admin import auth, firestore
from google.cloud import texttospeech, storage

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_admin.initialize_app()

# ログレベル設定
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)

# Firestore client
db = firestore.client()

# Cloud Storage設定
BUCKET_NAME = os.getenv("STORAGE_BUCKET", "alco-guardian.appspot.com")
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

# TTS設定
tts_client = texttospeech.TextToSpeechClient()
VOICE_NAME = "ja-JP-Neural2-B"  # 日本語男性音声


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


def synthesize_speech(text, voice_name=VOICE_NAME):
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


def upload_audio_to_storage(audio_content, filename):
    """音声データをCloud Storageにアップロード"""
    blob = bucket.blob(filename)
    
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


def get_image_id_from_context(drink_type, alcohol_g, guardian_level):
    """コンテキストに基づいて画像IDを決定"""
    # 画像IDマッピング
    # 1-3: 通常・楽しそうなバーテンダー
    # 4-6: 少し心配そうなバーテンダー  
    # 7-9: 真剣・警告モードのバーテンダー
    # 10: 水を勧めるバーテンダー
    
    if guardian_level.get("color") == "red":
        return 10  # 水を勧める
    elif guardian_level.get("color") == "orange":
        return random.choice([7, 8, 9])  # 真剣モード
    elif guardian_level.get("color") == "yellow":
        return random.choice([4, 5, 6])  # 心配モード
    else:
        # 通常時は飲み物の種類で変える
        if "ビール" in drink_type or "beer" in drink_type.lower():
            return 1
        elif "ワイン" in drink_type or "wine" in drink_type.lower():
            return 2
        elif "日本酒" in drink_type or "sake" in drink_type.lower():
            return 3
        else:
            return random.choice([1, 2, 3])


def generate_party_style_message(drink_type, volume, guardian_result, session_stats, conversation_context=None):
    """飲み会風の応答メッセージを生成"""
    
    # 会話コンテキストを考慮
    if conversation_context and conversation_context.get("message"):
        user_msg = conversation_context["message"].lower()
        
        # ユーザーの発言に応じたカスタマイズ
        if "つかれ" in user_msg or "疲れ" in user_msg:
            return f"お疲れ様！{drink_type}でリフレッシュだね！{volume}ml記録したよ〜"
        elif "楽し" in user_msg or "最高" in user_msg:
            return f"イェーイ！その調子！{drink_type}{volume}mlでさらに盛り上がろう！"
        elif "おかわり" in user_msg or "もう一杯" in user_msg:
            return f"おかわりきた〜！{drink_type}{volume}mlいっちゃう？いいね〜！"
    base_messages = [
        f"おっ！{drink_type}いいね〜！{volume}mlね、記録したよ！",
        f"{drink_type}キター！{volume}ml追加っと！",
        f"いえーい！{drink_type}{volume}ml入りました〜！",
        f"よっしゃ！{drink_type}で乾杯〜！{volume}ml記録！"
    ]
    
    level_color = guardian_result.get("level", {}).get("color", "green")
    
    if level_color == "red":
        return random.choice([
            f"{drink_type}{volume}ml...って、ちょっと待って！今日はもう結構飲んでるよ？水飲も水！",
            f"おーい、{drink_type}はちょっとストップ！今は水タイムにしよ？体大事だよ〜",
            f"ま、まてまて！{drink_type}より水がいいって！明日のこと考えよ？"
        ])
    elif level_color == "orange":
        return random.choice([
            f"{drink_type}{volume}mlね...そろそろペース落とさない？楽しく飲もうぜ〜",
            f"お、{drink_type}か〜。でもちょっとペース早くない？ゆっくり楽しもう！",
            f"{volume}mlっと...今日は長く楽しみたいよね？ちょっと休憩入れよ！"
        ])
    elif level_color == "yellow":
        return random.choice([
            f"{drink_type}いいね！でも{volume}mlの後は、ちょっと水も飲んどこ？",
            f"おっけー{drink_type}{volume}ml！いいペースだけど、無理しないでね〜",
            f"{drink_type}記録！でもそろそろつまみも食べよ？胃に優しくね！"
        ])
    else:
        # 飲み始めかペースが良い時
        total_drinks = session_stats.get("total_drinks", 0)
        if total_drinks == 0:
            return random.choice([
                f"今日の一杯目！{drink_type}で乾杯〜！楽しい夜にしようぜ！",
                f"よーし飲み会スタート！{drink_type}{volume}mlからいくぞ〜！",
                f"待ってました！{drink_type}で始まり始まり〜！"
            ])
        else:
            return random.choice(base_messages)


def generate_audio_response(text, voice_name=VOICE_NAME):
    """テキストから音声URLを生成（キャッシュ対応）"""
    # ファイル名をハッシュで生成
    content_hash = hashlib.md5(f"{text}_{voice_name}".encode()).hexdigest()
    filename = f"tts/{voice_name}/{content_hash}.mp3"
    
    # Cloud Storageに既存チェック
    blob = bucket.blob(filename)
    if blob.exists():
        logging.info(f"Using cached audio: {filename}")
        blob.make_public()
        return blob.public_url
    
    # 新規生成
    try:
        audio_content = synthesize_speech(text, voice_name)
        audio_url = upload_audio_to_storage(audio_content, filename)
        return audio_url
    except Exception as e:
        logging.error(f"TTS generation error: {e}")
        return None


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
        
        # 会話コンテキスト取得（オプション）
        conversation_context = request_json.get("context", {})
        user_message = conversation_context.get("message", "")
        conversation_history = conversation_context.get("history", [])
        
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
        
        # セッション統計を取得（応答生成用）
        session_data = session_ref.get().to_dict()
        drinks_count = len(list(drinks_ref.stream()))
        session_stats = {
            "total_alcohol_g": session_data.get("total_alcohol_g", alcohol_g),
            "total_drinks": drinks_count,
            "start_time": session_data.get("start_time")
        }
        
        # 会話履歴をFirestoreに保存
        if user_message:
            conversation_record = {
                "timestamp": firestore.SERVER_TIMESTAMP,
                "user_message": user_message,
                "drink_context": {
                    "drink_type": drink_type,
                    "volume": volume,
                    "alcohol_g": alcohol_g
                }
            }
            
            # 会話履歴コレクションに追加
            conversation_ref = session_ref.collection('conversations')
            conversation_ref.add(conversation_record)
        
        # Guardian分析を実行
        guardian_result = None
        coach_analysis = None
        try:
            from agents.a2a_broker import get_broker, Message
            from agents.guardian_adk import create_guardian_service
            from agents.drinking_coach_agent import create_drinking_coach
            
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
            
            # Drinking Coach分析も実行
            coach = create_drinking_coach()
            coach_analysis = loop.run_until_complete(
                coach.analyze_drinking_session(user_id, session_id)
            )
        except Exception as e:
            logging.error(f"ADK Guardian error: {e}")
            # Guardian分析エラーでも飲酒記録は成功とする
            guardian_result = {
                "level": {"color": "green", "message": "監視中"},
                "analysis": "Guardian分析でエラーが発生しました"
            }
            coach_analysis = {"success": False, "error": str(e)}
        
        # 飲み会風のレスポンスメッセージを生成
        response_message = generate_party_style_message(
            drink_type, volume, guardian_result, session_stats, conversation_context
        )
        
        # 音声レスポンスを生成
        audio_url = None
        try:
            audio_url = generate_audio_response(response_message)
        except Exception as e:
            logging.error(f"Audio generation error: {e}")
            # 音声生成エラーでも処理は継続
        
        # コンテキストに基づいて画像IDを決定
        import random
        image_id = get_image_id_from_context(
            drink_type, 
            session_stats.get("total_alcohol_g", alcohol_g),
            guardian_result.get("level", {"color": "green"})
        )
        
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
            "drinkingCoach": coach_analysis.get("analysis") if coach_analysis and coach_analysis.get("success") else None,
            "agent": "bartender",
            "imageId": image_id,
            "sessionStats": {
                "totalAlcoholG": session_stats.get("total_alcohol_g", alcohol_g),
                "totalDrinks": session_stats.get("total_drinks", 1),
                "sessionDuration": _calculate_session_duration(session_stats.get("start_time"))
            },
            "conversationContext": {
                "historyLength": len(conversation_history),
                "lastMessage": user_message if user_message else None
            }
        }
        
        # 音声URLがある場合は追加
        if audio_url:
            response_data["audioUrl"] = audio_url
        
        # 会話履歴にレスポンスを記録
        if user_message and response_message:
            # レスポンスも保存
            try:
                response_record = {
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "agent_message": response_message,
                    "agent_type": "bartender",
                    "image_id": image_id,
                    "guardian_level": guardian_result.get("level", {}).get("color", "green")
                }
                conversation_ref = session_ref.collection('conversations')
                conversation_ref.add(response_record)
            except Exception as e:
                logging.warning(f"Failed to save response to conversation history: {e}")
        
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


def _calculate_session_duration(start_time):
    """セッション継続時間を計算（分）"""
    if not start_time:
        return 0
    try:
        # Firestore Timestampの処理
        if hasattr(start_time, 'seconds'):
            start_dt = datetime.fromtimestamp(start_time.seconds, tz=timezone.utc)
        else:
            start_dt = start_time
        
        duration = datetime.now(timezone.utc) - start_dt
        return int(duration.total_seconds() / 60)
    except:
        return 0

