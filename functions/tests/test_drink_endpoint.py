#!/usr/bin/env python3
"""
新しい /drink エンドポイントのテストスクリプト
バックエンドの新機能をテスト
"""

import requests
import json
import time
from datetime import datetime

# エンドポイントURL
BASE_URL = "https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net"
DRINK_URL = f"{BASE_URL}/drink"

# テストデータ
test_drinks = [
    {
        "drinkType": "ビール",
        "alcoholPercentage": 5.0,
        "volume": 350,
        "context": {
            "message": "今日も一日お疲れ様！",
            "history": []
        }
    },
    {
        "drinkType": "ワイン",
        "alcoholPercentage": 12.0,
        "volume": 125,
        "context": {
            "message": "いい感じになってきた！楽しい！",
            "history": ["今日も一日お疲れ様！"]
        }
    },
    {
        "drinkType": "日本酒",
        "alcoholPercentage": 15.0,
        "volume": 180,
        "context": {
            "message": "もう一杯いっちゃう？",
            "history": ["今日も一日お疲れ様！", "いい感じになってきた！楽しい！"]
        }
    },
    {
        "drinkType": "ハイボール",
        "alcoholPercentage": 7.0,
        "volume": 350,
        "context": {
            "message": "ちょっと疲れてきたかも...",
            "history": ["今日も一日お疲れ様！", "いい感じになってきた！楽しい！", "もう一杯いっちゃう？"]
        }
    }
]

def print_response(response_data, drink_num):
    """レスポンスを見やすく表示"""
    print(f"\n{'='*60}")
    print(f"🍺 {drink_num}杯目の結果:")
    print(f"{'='*60}")
    
    if response_data.get("success"):
        print(f"✅ 成功")
        print(f"📝 メッセージ: {response_data.get('message')}")
        
        # 画像ID（コンテキストベース）
        print(f"🖼️  画像ID: {response_data.get('imageId')}")
        
        # Guardian状態
        guardian = response_data.get('guardian', {})
        if guardian:
            level = guardian.get('level', {})
            print(f"🚦 Guardian: {level.get('color')} - {level.get('message')}")
        
        # Drinking Coach分析
        coach = response_data.get('drinkingCoach')
        if coach:
            print(f"\n🏃 Drinking Coach分析:")
            pace = coach.get('pace_analysis', {})
            total = coach.get('total_analysis', {})
            print(f"   ペース: {pace.get('status')} ({pace.get('current_pace')}g/h)")
            print(f"   総量: {total.get('status')} ({total.get('total_alcohol_g')}g)")
            
            # 推奨事項
            recommendations = coach.get('recommendations', [])
            if recommendations:
                print(f"   💡 アドバイス:")
                for rec in recommendations:
                    print(f"      - {rec.get('message')}")
        
        # セッション統計
        stats = response_data.get('sessionStats', {})
        if stats:
            print(f"\n📊 セッション統計:")
            print(f"   総アルコール: {stats.get('totalAlcoholG')}g")
            print(f"   総杯数: {stats.get('totalDrinks')}杯")
            print(f"   経過時間: {stats.get('sessionDuration')}分")
        
        # 音声URL
        audio_url = response_data.get('audioUrl')
        if audio_url:
            print(f"\n🔊 音声URL: {audio_url[:50]}...")
        
        # 会話コンテキスト
        conv_context = response_data.get('conversationContext', {})
        if conv_context:
            print(f"\n💬 会話履歴: {conv_context.get('historyLength')}件")
            if conv_context.get('lastMessage'):
                print(f"   最後の発言: '{conv_context.get('lastMessage')}'")
    else:
        print(f"❌ エラー: {response_data.get('message')}")

def main():
    print("🧪 新しい /drink エンドポイントのテスト開始")
    print(f"⏰ 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for i, drink_data in enumerate(test_drinks, 1):
        print(f"\n🍻 {i}杯目を注文中...")
        
        try:
            response = requests.post(
                DRINK_URL,
                json=drink_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            response_data = response.json()
            print_response(response_data, i)
            
            # 次の飲酒まで少し待つ（リアルな飲酒ペースをシミュレート）
            if i < len(test_drinks):
                wait_time = 5  # 5秒待機
                print(f"\n⏳ {wait_time}秒待機中...")
                time.sleep(wait_time)
                
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
    
    print("\n" + "="*60)
    print("✅ テスト完了！")
    print("="*60)
    
    print("\n📋 新機能の確認ポイント:")
    print("1. 画像IDがGuardianレベルに応じて変化している")
    print("2. メッセージが飲み会風でカジュアル")
    print("3. Drinking Coachの詳細な分析が表示されている")
    print("4. 会話コンテキストが考慮されている")
    print("5. セッション統計が正しく更新されている")

if __name__ == "__main__":
    main()