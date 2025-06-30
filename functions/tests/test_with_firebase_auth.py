#!/usr/bin/env python3
"""
Firebase AuthでカスタムトークンとIDトークンを生成してテスト
"""
import os
import json
import requests
import firebase_admin
from firebase_admin import auth

# Firebase Admin SDKを初期化
firebase_admin.initialize_app()

def create_test_token():
    """テスト用のカスタムトークンを作成"""
    # テスト用のUIDを生成
    test_uid = "test-user-001"
    
    # カスタムトークンを作成
    custom_token = auth.create_custom_token(test_uid)
    
    # カスタムトークンを文字列に変換
    if isinstance(custom_token, bytes):
        custom_token = custom_token.decode('utf-8')
    
    return custom_token

def test_transcribe_with_auth():
    """認証付きでCloud Functionsをテスト"""
    FUNCTION_URL = "https://asia-northeast1-alco-guardian.cloudfunctions.net/transcribe"
    audio_file_path = "test_audio.m4a"
    
    if not os.path.exists(audio_file_path):
        print(f"Error: {audio_file_path} not found")
        return
    
    try:
        # カスタムトークンを作成
        custom_token = create_test_token()
        print(f"Created custom token for testing")
        
        # 注意: カスタムトークンをIDトークンに交換するにはクライアントSDKが必要
        # ここでは、カスタムトークンをそのまま使用（本来はクライアント側で交換が必要）
        print("\n⚠️  Note: Custom tokens need to be exchanged for ID tokens on the client side.")
        print("For full testing, you'll need to use the Firebase client SDK.")
        
        # デモ用：カスタムトークンをヘッダーに設定（本来はIDトークンを使用）
        headers = {
            "Authorization": f"Bearer {custom_token}"
        }
        
    except Exception as e:
        print(f"Error creating token: {e}")
        headers = {}
    
    # ファイルを準備
    with open(audio_file_path, 'rb') as f:
        files = {
            'file': (audio_file_path, f, 'audio/m4a')
        }
        
        print(f"\nSending request to: {FUNCTION_URL}")
        print(f"File: {audio_file_path}")
        
        # リクエストを送信
        response = requests.post(
            FUNCTION_URL,
            headers=headers,
            files=files
        )
    
    # レスポンスを表示
    print(f"\nStatus Code: {response.status_code}")
    
    try:
        response_json = response.json()
        print(f"\nResponse Body:")
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
    except:
        print(f"\nResponse Body (raw): {response.text}")

if __name__ == "__main__":
    test_transcribe_with_auth()