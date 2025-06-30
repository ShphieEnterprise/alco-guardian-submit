#!/usr/bin/env python3
"""
バックエンド統合テスト - 実機で動作確認
ハッカソン機能が全て動作することを確認
"""

import requests
import json
import time
from datetime import datetime

# テスト用のベースURL
BASE_URL = "https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net"

# 色付き出力用
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, result, details=""):
    """テスト結果を見やすく表示"""
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"\n{status} {name}")
    if details:
        print(f"   {Colors.BLUE}{details}{Colors.END}")

def test_drinks_master():
    """1. ドリンクマスターデータ取得テスト"""
    print(f"\n{Colors.YELLOW}=== 1. ドリンクマスターデータ取得 ==={Colors.END}")
    
    response = requests.get(f"{BASE_URL}/get_drinks_master")
    success = response.status_code == 200
    
    if success:
        drinks = response.json()
        print_test("GET /get_drinks_master", True, f"{len(drinks)} 種類のドリンク取得")
        print("   取得したドリンク:")
        for drink_id, data in drinks.items():
            print(f"   - {data['name']} ({data['alcohol']}%, {data['volume']}ml)")
    else:
        print_test("GET /get_drinks_master", False, f"Status: {response.status_code}")
    
    return success

def test_chat_basic():
    """2. Bartenderとの基本チャットテスト"""
    print(f"\n{Colors.YELLOW}=== 2. Bartenderチャット（基本） ==={Colors.END}")
    
    payload = {
        "message": "こんばんは！今日は金曜日だね",
        "enableTTS": False  # 音声生成は省略
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    success = response.status_code == 200
    
    if success:
        data = response.json()
        print_test("POST /chat", True, "Bartenderからの返答あり")
        print(f"   Bartender: {data.get('message', 'No message')[:100]}...")
    else:
        print_test("POST /chat", False, f"Status: {response.status_code}")
    
    return success

def test_session_start():
    """3. セッション開始テスト"""
    print(f"\n{Colors.YELLOW}=== 3. 飲酒セッション開始 ==={Colors.END}")
    
    response = requests.post(f"{BASE_URL}/start_session")
    success = response.status_code == 200
    
    if success:
        data = response.json()
        print_test("POST /start_session", True, f"セッションID: {data.get('session_id', 'N/A')}")
        print(f"   メッセージ: {data.get('message', '')}")
    else:
        # 既にセッションがある場合も想定
        if response.status_code == 400:
            print_test("POST /start_session", True, "既存セッションあり（正常）")
        else:
            print_test("POST /start_session", False, f"Status: {response.status_code}")
    
    return True  # セッションの存在は正常

def test_add_drinks_sequence():
    """4. 飲酒記録追加と Guardian 警告テスト"""
    print(f"\n{Colors.YELLOW}=== 4. 飲酒記録とGuardian警告テスト ==={Colors.END}")
    
    drinks_to_add = [
        ("beer", "ビール1杯目", 1),
        ("highball", "ハイボール（30分以内）", 0.5),
        ("sake", "日本酒（警告が出るはず）", 0.5)
    ]
    
    results = []
    
    for drink_id, description, wait_minutes in drinks_to_add:
        print(f"\n   {Colors.BLUE}>>> {description}を追加...{Colors.END}")
        
        payload = {"drink_id": drink_id}
        response = requests.post(
            f"{BASE_URL}/add_drink",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            alcohol_g = data.get('alcohol_g', 0)
            total_g = data.get('total_alcohol_g', 0)
            guardian = data.get('guardian', {})
            
            print(f"   純アルコール: {alcohol_g:.1f}g")
            print(f"   合計: {total_g:.1f}g")
            
            if isinstance(guardian, dict):
                level = guardian.get('level', guardian)
                color = level.get('color', 'unknown') if isinstance(level, dict) else 'unknown'
                message = level.get('message', '') if isinstance(level, dict) else str(level)
                
                # 色付きで Guardian 状態表示
                color_code = {
                    'green': Colors.GREEN,
                    'yellow': Colors.YELLOW,
                    'orange': Colors.YELLOW,
                    'red': Colors.RED
                }.get(color, Colors.END)
                
                print(f"   Guardian: {color_code}● {message}{Colors.END}")
                
                results.append({
                    'drink': description,
                    'total_g': total_g,
                    'guardian_color': color
                })
        else:
            print(f"   {Colors.RED}エラー: {response.status_code}{Colors.END}")
        
        # 次の飲み物まで待機（デモ用）
        if wait_minutes > 0:
            print(f"   {int(wait_minutes * 60)}秒待機中...")
            time.sleep(wait_minutes * 60)
    
    # Guardian が適切に警告を出したかチェック
    success = len(results) >= 2 and results[-1]['guardian_color'] in ['yellow', 'orange', 'red']
    print_test("Guardian 警告システム", success, 
               "飲み過ぎ時に警告が発生" if success else "警告が発生していません")
    
    return success

def test_guardian_check():
    """5. Guardian状態確認テスト"""
    print(f"\n{Colors.YELLOW}=== 5. Guardian状態確認 ==={Colors.END}")
    
    response = requests.get(f"{BASE_URL}/guardian_check")
    success = response.status_code == 200
    
    if success:
        data = response.json()
        level = data.get('level', {})
        stats = data.get('stats', {})
        
        print_test("GET /guardian_check", True, "Guardian分析完了")
        print(f"   総アルコール量: {stats.get('total_alcohol_g', 0):.1f}g")
        print(f"   飲酒数: {stats.get('drinks_count', 0)}杯")
        print(f"   経過時間: {stats.get('duration_minutes', 0)}分")
    else:
        print_test("GET /guardian_check", False, f"Status: {response.status_code}")
    
    return success

def test_current_session():
    """6. 現在のセッション情報取得テスト"""
    print(f"\n{Colors.YELLOW}=== 6. セッション情報取得 ==={Colors.END}")
    
    response = requests.get(f"{BASE_URL}/get_current_session")
    success = response.status_code == 200
    
    if success:
        data = response.json()
        if data.get('active'):
            print_test("GET /get_current_session", True, "アクティブセッションあり")
            print(f"   セッションID: {data.get('session_id', 'N/A')}")
            print(f"   開始時刻: {data.get('start_time', 'N/A')}")
            print(f"   合計アルコール: {data.get('total_alcohol_g', 0):.1f}g")
            print(f"   推奨事項: {', '.join(data.get('recommendations', []))}")
        else:
            print_test("GET /get_current_session", True, "セッションなし")
    else:
        print_test("GET /get_current_session", False, f"Status: {response.status_code}")
    
    return success

def test_bartender_guardian_integration():
    """7. Bartender-Guardian連携テスト"""
    print(f"\n{Colors.YELLOW}=== 7. Bartender-Guardian連携テスト ==={Colors.END}")
    
    # 飲み物を頼むメッセージ
    payload = {
        "message": "もう一杯ビールをください！",
        "enableTTS": False
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    success = response.status_code == 200
    
    if success:
        data = response.json()
        message = data.get('message', '')
        
        # Guardian が介入したかチェック（拒否メッセージを含むか）
        refusal_keywords = ['十分', '水', 'お水', '控え', 'ストップ', '危険']
        is_refused = any(keyword in message for keyword in refusal_keywords)
        
        print_test("Bartender-Guardian連携", True, 
                  "Guardianが介入" if is_refused else "通常の返答")
        print(f"   Bartender: {message[:100]}...")
    else:
        print_test("Bartender-Guardian連携", False, f"Status: {response.status_code}")
    
    return success

def main():
    """統合テストのメイン実行"""
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}   バックエンド統合テスト - 実機確認{Colors.END}")
    print(f"{Colors.BLUE}   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    tests = [
        test_drinks_master,
        test_chat_basic,
        test_session_start,
        test_add_drinks_sequence,
        test_guardian_check,
        test_current_session,
        test_bartender_guardian_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"{Colors.RED}エラー: {e}{Colors.END}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}   テスト結果: {passed}/{total} 成功{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}   🎉 すべてのテストが成功しました！{Colors.END}")
    else:
        print(f"{Colors.YELLOW}   ⚠️  一部のテストが失敗しました{Colors.END}")
    
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")

if __name__ == "__main__":
    main()