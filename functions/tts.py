import hashlib
import json
import logging
import os
from datetime import datetime, timedelta

import functions_framework
from firebase_admin import auth
from google.cloud import storage, texttospeech
from google.cloud.exceptions import NotFound

# ---------- 初期化 ----------
PROJECT = os.getenv("GCP_PROJECT")
UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)

# Text-to-Speech クライアントの初期化
tts_client = texttospeech.TextToSpeechClient()
storage_client = storage.Client()

# TTS設定
VOICE_NAME = "ja-JP-Neural2-B"  # 日本語男性の声
AUDIO_ENCODING = texttospeech.AudioEncoding.MP3
SPEAKING_RATE = 1.0
PITCH = 0.0


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


def generate_audio_filename(text, voice_name):
    """テキストと声の設定からユニークなファイル名を生成"""
    # テキストと声の設定をハッシュ化して重複を防ぐ
    content = f"{text}:{voice_name}:{SPEAKING_RATE}:{PITCH}"
    hash_digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"tts/{voice_name}/{hash_digest}.mp3"


def synthesize_speech(text, voice_name=VOICE_NAME):
    """テキストを音声に変換"""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name=voice_name
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=AUDIO_ENCODING,
        speaking_rate=SPEAKING_RATE,
        pitch=PITCH
    )
    
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    return response.audio_content


def upload_audio_to_storage(audio_content, filename):
    """音声ファイルをCloud Storageにアップロード"""
    bucket = storage_client.bucket(UPLOAD_BUCKET)
    blob = bucket.blob(filename)
    
    # キャッシュ制御の設定（24時間）
    blob.cache_control = "public, max-age=86400"
    blob.content_type = "audio/mpeg"
    
    blob.upload_from_string(audio_content)
    
    # 公開URLの生成（署名付きURLまたは公開URL）
    # 注: 本番環境では署名付きURLの使用を推奨
    blob.make_public()
    return blob.public_url


def get_cached_audio_url(filename):
    """キャッシュされた音声ファイルのURLを取得"""
    bucket = storage_client.bucket(UPLOAD_BUCKET)
    blob = bucket.blob(filename)
    
    try:
        # ファイルが存在するかチェック
        blob.reload()
        if blob.exists():
            return blob.public_url
    except NotFound:
        pass
    
    return None


@functions_framework.http
def tts(request):
    """Text-to-Speech エンドポイント"""
    
    # CORS対応
    if request.method == "OPTIONS":
        return add_cors_headers("", 204)
    
    try:
        # 認証チェック（開発中は一時的にスキップ可能）
        id_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        uid = "test-user"  # デフォルトのテストユーザー
        
        if id_token:
            try:
                uid = auth.verify_id_token(id_token)["uid"]
            except auth.InvalidIdTokenError:
                logging.warning("Invalid ID token provided. Using test mode.")
                uid = "test-user"
        else:
            logging.warning("No authorization token provided. Using test mode.")
            uid = "test-user"
        
        logging.info(f"Processing TTS request from user: {uid}")
        
        # リクエストボディの取得
        try:
            request_json = request.get_json()
        except Exception:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "Invalid JSON"}),
                400
            )
        
        # テキストの取得
        text = request_json.get("text", "")
        if not text:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "Text is required"}),
                400
            )
        
        # 文字数制限（1000文字）
        if len(text) > 1000:
            return add_cors_headers(
                json.dumps({"code": "BAD_REQUEST", "message": "Text is too long (max 1000 characters)"}),
                400
            )
        
        # 声の選択（オプション）
        voice_name = request_json.get("voice", VOICE_NAME)
        
        # ファイル名の生成
        filename = generate_audio_filename(text, voice_name)
        
        # キャッシュチェック
        cached_url = get_cached_audio_url(filename)
        if cached_url:
            logging.info(f"Using cached audio: {filename}")
            return add_cors_headers(
                json.dumps({
                    "success": True,
                    "audioUrl": cached_url,
                    "cached": True,
                    "filename": filename
                }),
                200
            )
        
        # 音声合成
        logging.info(f"Synthesizing speech for text length: {len(text)}")
        audio_content = synthesize_speech(text, voice_name)
        
        # Cloud Storageにアップロード
        audio_url = upload_audio_to_storage(audio_content, filename)
        logging.info(f"Audio uploaded to: {filename}")
        
        # レスポンス
        return add_cors_headers(
            json.dumps({
                "success": True,
                "audioUrl": audio_url,
                "cached": False,
                "filename": filename,
                "duration": len(audio_content) / 1000 / 32  # 概算（MP3 128kbps想定）
            }),
            200
        )
        
    except Exception as e:
        logging.error(f"Unexpected error in TTS endpoint: {e}", exc_info=True)
        
        return add_cors_headers(
            json.dumps({
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "error": str(e)
            }),
            500
        )