# Cloud Functions

## 概要

音声ファイルを文字起こしするCloud Functions（Python）です。Firebase Authenticationで認証し、Vertex AI（Gemini）を使用して音声を文字起こしします。

## ファイル構成

```
functions/
├── main.py                    # 音声文字起こしCloud Functions
├── bartender.py               # Bartenderエージェント
├── requirements.txt           # Python依存関係
├── README.md                 # このファイル
└── tests/                    # テスト関連
    ├── README.md             # テスト手順
    ├── test_audio.m4a        # テスト用音声ファイル
    ├── quick_test.sh         # 簡易テストスクリプト
    ├── test_bartender.sh     # Bartenderテストスクリプト
    ├── simple_test.py        # Python詳細テスト
    └── test_with_firebase_auth.py  # Firebase Auth付きテスト
```

## デプロイ

```bash
# プロジェクトを設定
gcloud config set project alco-guardian

# Cloud Functionsをデプロイ
gcloud functions deploy transcribe \
  --runtime python312 \
  --trigger-http \
  --require-authentication \
  --memory 512MB \
  --timeout 60s \
  --region asia-northeast1 \
  --set-env-vars UPLOAD_BUCKET=alco-guardian.appspot.com,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001
```

## テスト

詳細なテスト手順は `tests/README.md` を参照してください。

### 簡易テスト
```bash
cd tests
./quick_test.sh
```

### 詳細テスト
```bash
cd tests
uv run simple_test.py
```

## API仕様

### 1. 音声文字起こしエンドポイント

- **URL**: https://asia-northeast1-alco-guardian.cloudfunctions.net/transcribe
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Authentication**: Firebase ID Token (Bearer)

#### リクエスト
```bash
curl -X POST \
  -H "Authorization: Bearer $ID_TOKEN" \
  -F "file=@audio.m4a" \
  https://asia-northeast1-alco-guardian.cloudfunctions.net/transcribe
```

#### レスポンス
```json
{
  "success": true,
  "transcript": "文字起こし結果",
  "filename": "audio.m4a"
}
```

### 2. Bartenderチャットエンドポイント

- **URL**: https://asia-northeast1-alco-guardian.cloudfunctions.net/chat
- **Method**: POST
- **Content-Type**: application/json
- **Authentication**: Firebase ID Token (Bearer)

#### リクエスト
```bash
curl -X POST \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "こんばんは！"}' \
  https://asia-northeast1-alco-guardian.cloudfunctions.net/chat
```

#### レスポンス
```json
{
  "success": true,
  "message": "こんばんは！今日も一日お疲れ様でした。何か飲まれますか？",
  "imageId": 7,
  "timestamp": "2025-06-22T13:00:00Z",
  "agent": "bartender"
}
```

## 環境変数

- `UPLOAD_BUCKET`: Cloud Storageバケット名
- `GEMINI_LOCATION`: Vertex AIのリージョン
- `GEMINI_MODEL`: 使用するGeminiモデル
- `DISABLE_AUTH`: テスト用認証無効化フラグ（本番では使用しない）