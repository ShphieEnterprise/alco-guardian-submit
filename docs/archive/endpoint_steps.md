## Python Cloud Functions で **音声ファイルを受け取って Gemini に渡す専用エンドポイント** を作る手順

（例: `POST /v1/transcribe` で音声 → 文字起こし／要約）

---

### 0. ざっくり構成図

```
Flutter ──(multipart/form-data + IDToken)──▶ CF /transcribe
        (≤20 MB: そのまま)            (＞20 MB: Cloud Storage に一時アップ後 URI)
CF /transcribe
 ├─ Firebase Admin で IDToken 検証
 ├─ (必要なら) Cloud Storage にファイル保存
 └─ Vertex AI Gemini へ
         ・file_uri=gs://...      ← 推奨
         ・mime_type=audio/wav 等
```

Gemini への呼び出しは **GCS URI** を渡すのが推奨ルート（Files API は Vertex AI キー利用時のみサポート）。Google の公式サンプルも同方式です。([Google Cloud][1])

---

## 1. GCP 側の準備

| 手順                          | コマンド / 設定                                                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| ① プロジェクト選択            | `gcloud config set project <PROJECT_ID>`                                                                                                |
| ② 必要 API 有効化             | `gcloud services enable cloudfunctions.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com storage.googleapis.com` |
| ③ 音声用バケット              | `gsutil mb -l asia-northeast1 gs://<PROJECT_ID>-audio`                                                                                  |
| ④ バケット IAM                | Cloud Functions の SA に **Storage Object Admin**（最小権限なら _create & get_ のみで OK）                                              |
| ⑤ Functions SA に Vertex 権限 | `roles/aiplatform.user`（既に Node 版で付与済みなら不要）                                                                               |

---

## 2. ソース構成

```
functions/
├─ main.py
├─ requirements.txt
└─ .gcloudignore
```

### `requirements.txt`

```text
firebase-admin==6.4.0
google-cloud-aiplatform==1.38.0
google-cloud-storage==2.16.0
functions-framework==3.5.0
python-multipart==0.0.9      # multipart 解析用
nanoid==2.0.0
```

### `main.py`（抜粋：最小 MVP）

```python
import os, json, logging, base64
from datetime import datetime, timezone
from nanoid import generate

import functions_framework
import firebase_admin
from firebase_admin import auth
from google.cloud import storage
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part

# ---------- 初期化 ----------
firebase_admin.initialize_app()
PROJECT   = os.getenv("GCP_PROJECT")
LOCATION  = os.getenv("VERTEX_LOCATION", "asia-northeast1")
MODEL_ID  = os.getenv("VERTEX_MODEL",  "gemini-1.5-pro")

vertexai.init(project=PROJECT, location=LOCATION)
model = GenerativeModel(MODEL_ID)
bucket_name = os.getenv("UPLOAD_BUCKET")          # gs:// なし

storage_client = storage.Client()

# ---------- ユーティリティ ----------
def _save_to_gcs(file_obj, mime_type) -> str:
    blob_name = f"tmp/{datetime.now().timestamp()}_{file_obj.filename}"
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file_obj, content_type=mime_type)
    return f"gs://{bucket_name}/{blob_name}"

# ---------- HTTP Function ----------
@functions_framework.http
def transcribe(request):
    try:
        # ----- CORS -----
        if request.method == "OPTIONS":
            return ("", 204, _cors())
        headers = _cors()

        # ----- 認証 -----
        id_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        uid = auth.verify_id_token(id_token)["uid"]

        # ----- multipart 解析（python-multipart）-----
        parser = request.get_json(silent=True)
        if parser:                                             # JSON(BASE64) で来た場合
            b64_audio = parser["audioBase64"]
            mime      = parser.get("mimeType", "audio/wav")
            gcs_uri   = _save_to_gcs(io.BytesIO(base64.b64decode(b64_audio)), mime)
            prompt_text = parser.get("prompt", "")
        else:                                                  # multipart/form-data の場合
            form = request.files
            file_obj = form["audio"]
            mime     = file_obj.content_type or "audio/wav"
            gcs_uri  = _save_to_gcs(file_obj, mime)
            prompt_text = request.form.get("prompt", "")

        # ----- Gemini 呼び出し -----
        response = model.generate_content(
            contents=[{
                "role": "user",
                "parts": [
                    Part.from_uri(gcs_uri, mime_type=mime),
                    prompt_text or "音声を文字起こししてください。"
                ]
            }]
        )

        return (json.dumps({
            "messageId": f"msg_{generate(size=6)}",
            "aiText": response.candidates[0].text,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }), 200, headers)

    except auth.InvalidIdTokenError:
        return (json.dumps({"code":"UNAUTHORIZED","message":"Invalid token"}), 401, {})
    except Exception as e:
        logging.exception(e)
        return (json.dumps({"code":"INTERNAL","message":"Unexpected"}), 500, {})

def _cors():
    return {"Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization,Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS"}
```

---

## 3. デプロイ

```bash
gcloud functions deploy transcribe \
  --gen2 \
  --region asia-northeast1 \
  --runtime python311 \
  --source ./functions \
  --entry-point transcribe \
  --trigger-http \
  --memory 1Gi \
  --timeout 120s \
  --no-allow-unauthenticated \
  --set-env-vars \
      VERTEX_LOCATION=asia-northeast1,VERTEX_MODEL=gemini-1.5-pro,\
      UPLOAD_BUCKET=<PROJECT_ID>-audio
```

---

## 4. Flutter から呼び出す例

```dart
final dio = Dio();
final idToken = await FirebaseAuth.instance.currentUser!.getIdToken();

final form = FormData.fromMap({
  'audio': await MultipartFile.fromFile(
      file.path, filename: 'voice.wav', contentType: MediaType('audio', 'wav')),
  'prompt': 'この音声を文字起こしして'
});

final resp = await dio.post(
  'https://asia-northeast1-<PROJECT_ID>.cloudfunctions.net/transcribe',
  data: form,
  options: Options(headers: {
    'Authorization': 'Bearer $idToken',
    'Content-Type': 'multipart/form-data'
  }),
);

print(resp.data['aiText']);
```

> **サイズが 20 MB を超えるファイルは直接送らず Cloud Storage URI 経由で渡す**のが公式推奨です。SDK 直叩き時も同じ制約があります。([Firebase][2])

---

## 5. 失敗しやすいポイント

| 症状                     | 主な原因                                                        |
| ------------------------ | --------------------------------------------------------------- |
| 413 Payload Too Large    | Cloud Functions の 10 MB 制限 →Cloud Storage 経由に切替         |
| PERMISSION_DENIED on GCS | Functions SA にバケット権限が無い                               |
| 403 on Gemini            | SA に `roles/aiplatform.user` が無い or モデル名/リージョン誤り |
| Multipart 解析エラー     | Flutter 側ヘッダ `multipart/form-data` が設定されていない       |

---

## 6. `Vertex AI in Firebase` を直接使う場合（参考）

バックエンド無しで音声ファイルを直接 Gemini に渡すなら **Vertex AI in Firebase Dart SDK** を導入し、App Check で保護する。リクエストサイズは **20 MB 上限**、大きい場合は Cloud Storage for Firebase の URI を渡す流れになります（コードパターンは上記とほぼ同じ）。サーバーを挟むか否かは **キー秘匿・課金制御・追加ロジックの必要性**で選択してください。

---

これで **音声ファイル →Gemini** のエンドポイントが完成します。
デプロイ後に `curl` などで動作を確認し、問題があればエラーメッセージごとお知らせください！

[1]: https://cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-gemini-audio-transcription "Transcript an audio file with Gemini 1.5 Pro  |  Generative AI on Vertex AI  |  Google Cloud"
[2]: https://firebase.google.com/docs/vertex-ai/solutions/cloud-storage?utm_source=chatgpt.com "Include large files in multimodal requests and manage ... - Firebase"
