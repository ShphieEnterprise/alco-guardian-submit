# クイックスタートガイド

最終更新: 2025-06-30

## はじめに

このガイドでは、Alco Guardian の開発環境をセットアップし、最初のテストを実行するまでの手順を説明します。

## 必要な環境

- Python 3.12 以上
- Flutter 3.32 以上
- Google Cloud SDK
- Firebase CLI
- Git

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/ShphieEnterprise/alco-guardian.git
cd alco-guardian
```

### 2. Google Cloud の設定

```bash
# Google Cloud にログイン
gcloud auth login

# プロジェクトの設定
gcloud config set project YOUR_PROJECT_ID

# 必要な API を有効化
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable texttospeech.googleapis.com
```

### 3. バックエンドのセットアップ

```bash
cd functions

# Python 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 4. フロントエンドのセットアップ

```bash
cd ../frontend

# Flutter の依存関係をインストール
flutter pub get

# Firebase の設定
flutterfire configure
```

## 動作確認

### 1. バックエンドのローカルテスト

```bash
cd functions

# 純アルコール計算のテスト
python test_simple.py

# API エンドポイントのテスト
cd tests
./quick_test.sh
```

### 2. フロントエンドのローカル実行

```bash
cd frontend

# Web版で起動
flutter run -d chrome

# または特定のデバイスで起動
flutter devices  # 利用可能なデバイスを確認
flutter run -d [device-id]
```

### 3. API の動作確認

別のターミナルで以下を実行：

```bash
# Bartender とチャット
curl -X POST https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは！"}'

# ドリンクマスターデータの取得
curl https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/get_drinks_master
```

## 開発の始め方

### 1. 新しい機能の追加

#### バックエンド（Cloud Functions）
```python
# functions/my_new_function.py
import functions_framework
from flask import jsonify

@functions_framework.http
def my_new_function(request):
    """新しいエンドポイントの実装"""
    return jsonify({
        "success": True,
        "message": "Hello from new function!"
    })
```

#### フロントエンド（Flutter）
```dart
// frontend/lib/services/api_service.dart に追加
Future<Map<String, dynamic>> callMyNewFunction() async {
  final response = await http.post(
    Uri.parse('$baseUrl/my_new_function'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({}),
  );
  return jsonDecode(response.body);
}
```

### 2. テストの作成

#### バックエンドテスト
```python
# functions/tests/test_my_function.py
import unittest
from my_new_function import my_new_function

class TestMyFunction(unittest.TestCase):
    def test_success_response(self):
        # テストの実装
        pass
```

#### フロントエンドテスト
```dart
// frontend/test/my_widget_test.dart
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('My widget test', (WidgetTester tester) async {
    // テストの実装
  });
}
```

## よくある問題と解決方法

### 1. CORS エラーが発生する

Cloud Functions で CORS ヘッダーを設定：
```python
from flask import jsonify

def my_function(request):
    # CORS の処理
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    # 通常のレスポンスにも CORS ヘッダーを追加
    response = jsonify({"message": "Hello"})
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response
```

### 2. 認証エラーが発生する

開発環境では認証をスキップ：
```python
# デモユーザーとして処理
user_id = "demo_user_001"
```

### 3. パッケージの依存関係エラー

```bash
# バックエンド
pip install --upgrade -r requirements.txt

# フロントエンド
flutter clean
flutter pub get
```

## 便利なコマンド

### ログの確認
```bash
# Cloud Functions のログ
gcloud functions logs read [FUNCTION_NAME] --limit 50

# リアルタイムログ
gcloud functions logs tail [FUNCTION_NAME]
```

### デプロイ
```bash
# 単一関数のデプロイ
cd functions
gcloud functions deploy [FUNCTION_NAME] \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated

# 全関数のデプロイ
./deploy_all_gen2.sh
```

### デバッグ
```bash
# Python デバッガー
python -m pdb my_script.py

# Flutter デバッグモード
flutter run --debug
```

## 次のステップ

1. [API リファレンス](./API_REFERENCE.md) を読んで API の詳細を理解
2. [アーキテクチャ概要](./ARCHITECTURE_OVERVIEW.md) でシステム設計を学習
3. [デプロイメントガイド](./DEPLOYMENT_GUIDE.md) で本番環境へのデプロイ方法を確認
4. GitHub Issues で課題を確認し、貢献を開始

## サポート

質問や問題がある場合：
- GitHub Issues で報告
- Slack チャンネル #alco-guardian で質問
- ドキュメントの改善提案も歓迎します！