#!/usr/bin/env python3
"""
飲酒記録エンドポイントのテストスクリプト
ローカルおよびデプロイ環境でテストできます
"""

import json
import requests
import sys
from datetime import datetime

# テスト設定
TEST_LOCAL = False  # Falseにするとデプロイ済みのエンドポイントをテスト
LOCAL_URL = "http://localhost:8080"
DEPLOYED_URL = "https://asia-northeast1-alco-guardian.cloudfunctions.net/drink"

# テストデータ
TEST_CASES = [
    {
        "name": "ビール350ml",
        "data": {
            "drinkType": "ビール",
            "alcoholPercentage": 5.0,
            "volume": 350
        }
    },
    {
        "name": "ハイボール500ml",
        "data": {
            "drinkType": "ハイボール",
            "alcoholPercentage": 7.0,
            "volume": 500
        }
    },
    {
        "name": "その他（ワイン）120ml",
        "data": {
            "drinkType": "その他",
            "alcoholPercentage": 12.0,
            "volume": 120
        }
    }
]

# エラーケース
ERROR_CASES = [
    {
        "name": "drinkType欠落",
        "data": {
            "alcoholPercentage": 5.0,
            "volume": 350
        }
    },
    {
        "name": "alcoholPercentage欠落",
        "data": {
            "drinkType": "ビール",
            "volume": 350
        }
    },
    {
        "name": "不正なalcoholPercentage",
        "data": {
            "drinkType": "ビール",
            "alcoholPercentage": 150,  # 100を超える
            "volume": 350
        }
    },
    {
        "name": "不正なvolume",
        "data": {
            "drinkType": "ビール",
            "alcoholPercentage": 5.0,
            "volume": -100  # 負の値
        }
    }
]


def test_endpoint(url, test_case):
    """エンドポイントをテスト"""
    print(f"\n📍 テスト: {test_case['name']}")
    print(f"   リクエスト: {json.dumps(test_case['data'], ensure_ascii=False)}")
    
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=test_case["data"],
            timeout=30
        )
        
        print(f"   ステータス: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 成功")
            print(f"   メッセージ: {data.get('message', 'なし')}")
            
            # 音声URLの確認
            if 'audioUrl' in data:
                print(f"   🔊 音声URL: {data['audioUrl']}")
            else:
                print(f"   ⚠️  音声URLなし")
            
            # Guardian分析結果
            if 'guardian' in data and data['guardian']:
                guardian = data['guardian']
                if 'level' in guardian:
                    color = guardian['level'].get('color', '不明')
                    print(f"   🚦 Guardian状態: {color}")
            
            # 純アルコール量
            if 'data' in data and 'alcoholG' in data['data']:
                print(f"   🍺 純アルコール量: {data['data']['alcoholG']:.1f}g")
                
        else:
            print(f"   ❌ エラー")
            try:
                error_data = response.json()
                print(f"   エラー内容: {error_data}")
            except:
                print(f"   レスポンス: {response.text}")
                
    except requests.exceptions.Timeout:
        print(f"   ❌ タイムアウト")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 接続エラー（サーバーが起動していない可能性があります）")
    except Exception as e:
        print(f"   ❌ エラー: {type(e).__name__}: {e}")


def main():
    """メイン処理"""
    url = LOCAL_URL if TEST_LOCAL else DEPLOYED_URL
    
    print(f"🧪 飲酒記録エンドポイントテスト")
    print(f"📌 URL: {url}")
    print(f"🕐 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 正常系テスト
    print("\n\n=== 正常系テスト ===")
    for test_case in TEST_CASES:
        test_endpoint(url, test_case)
    
    # エラー系テスト
    print("\n\n=== エラー系テスト ===")
    for test_case in ERROR_CASES:
        test_endpoint(url, test_case)
    
    print("\n\n✅ テスト完了")
    
    # 使用方法の説明
    print("\n📝 使用方法:")
    print("1. ローカルテスト: functions-framework --target=drink でサーバー起動後、このスクリプトを実行")
    print("2. デプロイ済みテスト: TEST_LOCAL = False に変更して実行")
    print("3. 音声URLが返された場合、ブラウザで開いて音声を確認できます")


if __name__ == "__main__":
    main()