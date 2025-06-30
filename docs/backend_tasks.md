# バックエンド実装タスク（6/30ハッカソン提出用）

## 🎯 バックエンド側の実装優先順位

### Week 1（6/22-6/28）: コア機能実装

## Day 1-2: 飲酒トラッキング基盤

### 1. Firestoreスキーマ設計と実装
```javascript
// コレクション構造
drinks_master: {
  beer: {
    name: "ビール",
    alcohol_percentage: 5,
    standard_volume_ml: 350,
    category: "beer"
  },
  // ... 他のドリンク
}

users/{userId}/sessions/{sessionId}: {
  start_time: Timestamp,
  end_time: Timestamp | null,
  total_alcohol_g: number,
  status: "active" | "ended",
  guardian_warnings: []
}

users/{userId}/sessions/{sessionId}/drinks/{drinkId}: {
  drink_type: "beer",
  volume_ml: 350,
  alcohol_g: 14,
  timestamp: Timestamp
}
```

### 2. ドリンク管理API実装

#### `/drinks/master` - ドリンクマスターデータ取得
```python
@functions_framework.http
def get_drinks_master(request):
    """利用可能なドリンクリストを返す"""
    drinks = {
        "beer": {"name": "ビール", "alcohol": 5, "volume": 350},
        "wine": {"name": "ワイン", "alcohol": 12, "volume": 125},
        "sake": {"name": "日本酒", "alcohol": 15, "volume": 180},
        "highball": {"name": "ハイボール", "alcohol": 7, "volume": 350},
        "shochu": {"name": "焼酎水割り", "alcohol": 10, "volume": 200},
        "cocktail": {"name": "カクテル", "alcohol": 15, "volume": 100}
    }
    return add_cors_headers(json.dumps(drinks), 200)
```

#### `/drinks/add` - ドリンク追加
```python
@functions_framework.http
def add_drink(request):
    """飲酒記録を追加"""
    data = request.get_json()
    user_id = get_user_id(request)  # 認証から取得
    
    # 純アルコール量計算
    alcohol_g = calculate_pure_alcohol(
        data['drink_id'], 
        data.get('volume_ml')
    )
    
    # Firestoreに保存
    session_id = get_or_create_session(user_id)
    save_drink_record(user_id, session_id, data, alcohol_g)
    
    # Guardianチェック
    guardian_result = check_guardian_rules(user_id, session_id)
    
    return add_cors_headers(json.dumps({
        "success": True,
        "alcohol_g": alcohol_g,
        "total_alcohol_g": get_session_total(user_id, session_id),
        "guardian": guardian_result
    }), 200)
```

### 3. 純アルコール量計算ユーティリティ
```python
def calculate_pure_alcohol(drink_type, volume_ml):
    """
    純アルコール量（g）= 飲酒量(ml) × アルコール度数(%) ÷ 100 × 0.8
    """
    drink_data = DRINKS_MASTER.get(drink_type)
    if not drink_data:
        raise ValueError(f"Unknown drink type: {drink_type}")
    
    alcohol_percentage = drink_data['alcohol']
    volume = volume_ml or drink_data['volume']
    
    return volume * (alcohol_percentage / 100) * 0.8
```

## Day 3-4: Guardian実装

### 1. Guardianエージェント本体
```python
# functions/guardian.py

class GuardianAgent:
    # 推奨値
    SAFE_PACE_DRINKS_PER_HOUR = 1
    DAILY_LIMIT_G = 20  # 純アルコール20g
    WARNING_LEVELS = {
        "ok": {"color": "green", "message": "良いペースです"},
        "caution": {"color": "orange", "message": "ペースに注意してください"},
        "warning": {"color": "red", "message": "飲み過ぎです。水分補給を"},
        "stop": {"color": "red", "message": "これ以上は危険です"}
    }
    
    def analyze_drinking_pattern(self, user_id, session_id):
        """飲酒パターンを分析"""
        session_data = get_session_data(user_id, session_id)
        
        # 1. 総量チェック
        total_alcohol = session_data['total_alcohol_g']
        
        # 2. ペースチェック（30分あたりの飲酒数）
        recent_drinks = get_recent_drinks(user_id, session_id, minutes=30)
        pace_score = len(recent_drinks)
        
        # 3. 時間経過チェック
        duration_hours = get_session_duration(session_data) / 3600
        
        # 判定ロジック
        if total_alcohol > self.DAILY_LIMIT_G * 1.5:
            return self.WARNING_LEVELS["stop"]
        elif total_alcohol > self.DAILY_LIMIT_G:
            return self.WARNING_LEVELS["warning"]
        elif pace_score >= 2:
            return self.WARNING_LEVELS["caution"]
        else:
            return self.WARNING_LEVELS["ok"]
```

### 2. Guardian API エンドポイント
```python
@functions_framework.http
def guardian_check(request):
    """現在の飲酒状況をGuardianが判定"""
    user_id = get_user_id(request)
    session_id = get_current_session(user_id)
    
    guardian = GuardianAgent()
    result = guardian.analyze_drinking_pattern(user_id, session_id)
    
    # 警告履歴を保存
    if result['color'] in ['orange', 'red']:
        save_guardian_warning(user_id, session_id, result)
    
    return add_cors_headers(json.dumps({
        "level": result,
        "stats": {
            "total_alcohol_g": get_session_total(user_id, session_id),
            "drinks_count": get_drinks_count(user_id, session_id),
            "duration_minutes": get_session_duration_minutes(user_id, session_id)
        }
    }), 200)
```

### 3. Bartender ↔ Guardian連携
```python
# bartender.pyの修正
def chat(request):
    # 既存のチャット処理...
    
    # Guardian連携チェック
    if "飲み" in user_message or "おかわり" in user_message:
        guardian_result = check_guardian_veto(user_id)
        
        if guardian_result['veto']:
            # Guardianが拒否
            bartender_response = generate_refusal_message(guardian_result['reason'])
        else:
            # 通常の提案
            bartender_response = generate_drink_suggestion(user_message)
```

## Day 5-6: セッション管理とAPI統合

### 1. セッション管理API

#### `/sessions/start` - 飲酒セッション開始
```python
@functions_framework.http
def start_session(request):
    user_id = get_user_id(request)
    
    # 既存のアクティブセッションをチェック
    active_session = get_active_session(user_id)
    if active_session:
        return add_cors_headers(json.dumps({
            "error": "既にセッションが開始されています"
        }), 400)
    
    # 新規セッション作成
    session_id = create_new_session(user_id)
    
    return add_cors_headers(json.dumps({
        "session_id": session_id,
        "start_time": datetime.now().isoformat(),
        "message": "飲酒セッションを開始しました。適度に楽しみましょう！"
    }), 200)
```

#### `/sessions/current` - 現在のセッション情報取得
```python
@functions_framework.http
def get_current_session_info(request):
    user_id = get_user_id(request)
    session = get_active_session(user_id)
    
    if not session:
        return add_cors_headers(json.dumps({
            "active": False
        }), 200)
    
    drinks = get_session_drinks(user_id, session['id'])
    guardian_status = GuardianAgent().analyze_drinking_pattern(user_id, session['id'])
    
    return add_cors_headers(json.dumps({
        "active": True,
        "session_id": session['id'],
        "start_time": session['start_time'].isoformat(),
        "duration_minutes": calculate_duration(session['start_time']),
        "total_alcohol_g": session['total_alcohol_g'],
        "drinks": drinks,
        "guardian_status": guardian_status,
        "recommendations": generate_recommendations(session)
    }), 200)
```

## 実装順序とテスト

### 実装順序
1. Firestoreスキーマとユーティリティ関数
2. ドリンク管理API（`/drinks/master`, `/drinks/add`）
3. セッション管理API（`/sessions/start`, `/sessions/current`）
4. Guardian分析ロジック
5. Bartender-Guardian連携

### テスト項目
```python
# tests/test_guardian.py
def test_guardian_pace_check():
    """30分で2杯以上で警告が出るか"""
    # モックデータでテスト
    
def test_alcohol_calculation():
    """純アルコール計算が正しいか"""
    assert calculate_pure_alcohol("beer", 350) == 14.0
    
def test_session_management():
    """セッション開始・終了が正しく動作するか"""
    # Firestoreエミュレータでテスト
```

## デプロイメント

### 環境変数の追加
```bash
gcloud functions deploy drinks-add \
  --set-env-vars "FIRESTORE_PROJECT_ID=alco-guardian"
  
gcloud functions deploy guardian-check \
  --set-env-vars "DAILY_ALCOHOL_LIMIT=20,PACE_LIMIT=1"
```

### Cloud Schedulerでの定期実行（オプション）
```bash
# 毎日0時にセッションを自動終了
gcloud scheduler jobs create http daily-session-cleanup \
  --schedule="0 0 * * *" \
  --uri="https://asia-northeast1-alco-guardian.cloudfunctions.net/sessions/cleanup"
```

## モック対応（時間節約）

以下はハードコードでOK：
- ドリンクマスターデータ（6種類固定）
- 推奨値（20g/日、1杯/時間）
- デモシナリオ用の固定レスポンス

## 未実装でOK（ハッカソン後）

- ユーザー設定（体重、性別による調整）
- 詳細な統計API
- 管理画面
- データエクスポート
- 外部API連携（カレンダー、タクシー等）