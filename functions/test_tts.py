#!/usr/bin/env python3
"""
TTS機能のテストスクリプト
"""
import json
import os
import requests
from firebase_admin import auth, credentials, initialize_app

# Firebase Admin SDK初期化
if not len([app for app in firebase_admin._apps.values()]):
    cred = credentials.ApplicationDefault()
    initialize_app(cred)

def get_id_token():
    """テスト用のIDトークンを取得（実際の実装では適切な認証を使用）"""
    # 注: これは簡易的な例です。実際のテストでは適切な認証方法を使用してください
    # Firebase AuthのREST APIを使用してテストユーザーでログイン
    return "YOUR_TEST_ID_TOKEN"

def test_tts_endpoint():
    """TTSエンドポイントのテスト"""
    base_url = "https://asia-northeast1-alco-guardian.cloudfunctions.net"
    
    # テストデータ
    test_text = "こんにちは！今日はどんなお酒を楽しみましょうか？"
    
    headers = {
        "Authorization": f"Bearer {get_id_token()}",
        "Content-Type": "application/json"
    }
    
    data = {
        "text": test_text,
        "voice": "ja-JP-Neural2-B"
    }
    
    try:
        response = requests.post(
            f"{base_url}/tts",
            headers=headers,
            json=data
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 音声URL: {result.get('audioUrl')}")
            print(f"キャッシュ済み: {result.get('cached')}")
            print(f"ファイル名: {result.get('filename')}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

def test_bartender_chat_with_tts():
    """Bartenderチャットエンドポイント（TTS付き）のテスト"""
    base_url = "https://asia-northeast1-alco-guardian.cloudfunctions.net"
    
    headers = {
        "Authorization": f"Bearer {get_id_token()}",
        "Content-Type": "application/json"
    }
    
    data = {
        "message": "今日は疲れたから、リラックスできるお酒を教えて",
        "enableTTS": True
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat",
            headers=headers,
            json=data
        )
        
        print(f"\nBartenderチャットテスト:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ メッセージ: {result.get('message')}")
            print(f"音声URL: {result.get('audioUrl')}")
            print(f"画像ID: {result.get('imageId')}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    print("=== TTS機能テスト ===\n")
    
    # 注: 実際のテストではFirebase Authの適切な認証トークンが必要です
    print("⚠️  注意: このスクリプトを実行するには有効なFirebase IDトークンが必要です")
    print("Firebase Authでユーザーを作成し、IDトークンを取得してください\n")
    
    # TTSエンドポイントのテスト
    print("1. TTSエンドポイントのテスト:")
    # test_tts_endpoint()
    
    # Bartenderチャットのテスト（TTS付き）
    print("\n2. Bartenderチャット（TTS付き）のテスト:")
    # test_bartender_chat_with_tts()