#!/usr/bin/env python3
"""
シンプルなテスト - 認証を一時的に無効化してテスト
"""
import os
import json
import requests

def test_without_auth():
    """認証なしでテスト（デバッグ用）"""
    FUNCTION_URL = "https://asia-northeast1-alco-guardian.cloudfunctions.net/transcribe"
    audio_file_path = "test_audio.m4a"
    
    if not os.path.exists(audio_file_path):
        print(f"Error: {audio_file_path} not found")
        return
    
    print("=" * 60)
    print("Cloud Functions テスト結果")
    print("=" * 60)
    
    # ファイルを準備
    with open(audio_file_path, 'rb') as f:
        files = {
            'file': (audio_file_path, f, 'audio/m4a')
        }
        
        print(f"エンドポイント: {FUNCTION_URL}")
        print(f"音声ファイル: {audio_file_path}")
        print(f"ファイルサイズ: {os.path.getsize(audio_file_path)} bytes")
        
        # リクエストを送信（認証なし）
        response = requests.post(
            FUNCTION_URL,
            files=files
        )
    
    # レスポンスを表示
    print(f"\nステータスコード: {response.status_code}")
    
    try:
        response_json = response.json()
        print(f"\nレスポンス:")
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
        
        if response.status_code == 401:
            print("\n✅ 認証が正しく動作しています")
            print("   （認証トークンが必要です）")
        elif response.status_code == 200:
            print("\n✅ 文字起こしが成功しました")
            if 'transcript' in response_json:
                print(f"\n文字起こし結果:")
                print(f"「{response_json['transcript']}」")
        else:
            print("\n❌ エラーが発生しました")
            
    except:
        print(f"\nレスポンス (raw): {response.text}")
    
    print("\n" + "=" * 60)
    print("テスト結果サマリー:")
    print(f"- プロジェクト: alco-guardian")
    print(f"- Function URL: {FUNCTION_URL}")
    print(f"- 認証状態: {'必要（正常）' if response.status_code == 401 else 'その他'}")
    print("=" * 60)

if __name__ == "__main__":
    test_without_auth()