# Cloud Run CORS設定ガイド

## 現在の状況
- Cloud Runサービスは正常に動作し、リクエストを処理できています
- 転写も成功しています（ログで確認）
- しかし、CORSヘッダーが設定されていないため、ブラウザがレスポンスをブロックしています

## Cloud Run側で必要な設定

### 1. Flaskアプリケーションの場合

```python
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS

app = Flask(__name__)

# CORSを有効化（本番環境では特定のオリジンのみ許可）
CORS(app, origins=[
    "http://localhost:8080",  # 開発環境
    "https://your-production-domain.com"  # 本番環境
])

# または手動でCORSヘッダーを追加
@app.after_request
def after_request(response):
    # 開発環境では全てのオリジンを許可（本番では制限すること）
    origin = request.headers.get('Origin')
    if origin:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# プリフライトリクエスト（OPTIONS）への対応
@app.route('/transcribe', methods=['OPTIONS'])
def handle_preflight():
    response = make_response()
    origin = request.headers.get('Origin')
    if origin:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response
```

### 2. FastAPIの場合

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://your-production-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Flutter側の一時的な回避策

現在、`TranscriptionServiceProxy`を実装しました。これは：

1. **開発環境（Web + デバッグモード）**: 
   - Cloud Functions SDK経由で呼び出し（CORSを回避）
   - Base64エンコードした音声データをJSONで送信

2. **本番環境またはモバイル**:
   - 直接Cloud Runエンドポイントを呼び出し
   - マルチパートフォームデータで送信

## 推奨される対応

1. **即座に対応**: Cloud Run側でCORSヘッダーを追加
2. **長期的な対応**: 
   - 同一オリジンでホスティング
   - またはCloud Run側でより細かいCORS制御を実装

## テスト方法

1. Cloud Run側でCORS設定を追加後、以下を確認：
   ```bash
   curl -X OPTIONS https://us-central1-alco-guardian.cloudfunctions.net/transcribe \
     -H "Origin: http://localhost:8080" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type,Authorization" \
     -v
   ```

2. レスポンスヘッダーに以下が含まれていることを確認：
   - `Access-Control-Allow-Origin: http://localhost:8080`
   - `Access-Control-Allow-Methods: POST`
   - `Access-Control-Allow-Headers: Content-Type,Authorization`