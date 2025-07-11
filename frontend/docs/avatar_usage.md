# VRM/3Dアバターの利用方法

このドキュメントでは、アプリケーション内でVRMや3Dアバターを表示するための設定方法について説明します。

## 1. アバターファイルの準備と配置

### 対応フォーマット
現在は主に `.vrm` および `.glb` (glTF Binary) フォーマットをサポートしています。

### ファイルの配置場所
表示したい3Dアバターのファイルは、プロジェクトの `assets` フォルダ内に配置することを推奨します。
もし `assets` フォルダが存在しない場合は、プロジェクトのルートディレクトリに作成してください。

例:
```
your_flutter_project/
├── assets/
│   └── your_avatar_model.vrm  # または your_avatar_model.glb
├── lib/
├── ... (その他のプロジェクトファイル)
```

## 2. `pubspec.yaml` の設定
`assets` フォルダに配置したアバターファイルをアプリケーションが認識できるように、`pubspec.yaml` ファイルに設定を追加する必要があります。

`flutter` セクション以下に `assets` を追加し、アバターファイルへのパスを記述します。

```yaml
flutter:
  uses-material-design: true
  assets:
    - assets/your_avatar_model.vrm  # あなたのアバターファイル名に合わせて変更
    # 他のアセットファイルがあればここに追加
    # - assets/another_model.glb
```
特定のフォルダ内のすべてのアセットを含める場合は、フォルダ名を指定することも可能です。
```yaml
flutter:
  uses-material-design: true
  assets:
    - assets/   # assetsフォルダ内のすべてのファイルを含める
```

## 3. アプリケーション内での表示
アバターは `HomeScreen` の中央に表示されるように設定されています。
表示するアバターモデルは、`lib/ui/home_screen.dart` ファイル内で指定されています。

```dart
// lib/ui/home_screen.dart の一部 (イメージ)
// ...
BabylonJSViewer(
  src: 'assets/your_avatar_model.vrm', // ここのパスを実際に配置したファイル名に変更
)
// ...
```
新しいアバターファイルを使用する場合は、この `src` の値を変更してください。

## 4. デプロイ時の注意事項

### Web版をデプロイする場合
- **WebGLのサポート:** アバター表示にはWebGLが利用されます。デプロイ先のブラウザがWebGLをサポートしていることを確認してください。
- **CORSポリシー:** モデルファイルが別ドメインから配信される場合、CORS (Cross-Origin Resource Sharing) ポリシーの設定が必要になることがあります。通常は `assets` に含めることでこの問題は回避されます。
- **ファイルサイズ:** 3Dモデルファイルはサイズが大きくなることがあります。表示パフォーマンスやロード時間に影響するため、可能な限り最適化されたモデルを使用してください。

### モバイルアプリ版をデプロイする場合
- **パフォーマンス:**複雑な3Dモデルや多数のモデルを同時に表示すると、特にローエンドのデバイスではパフォーマンスに影響が出る可能性があります。
- **ファイルサイズ:** Web版と同様に、アプリのサイズが大きくなりすぎないように、モデルファイルのサイズに注意してください。

## 5. トラブルシューティング
- **アバターが表示されない:**
    - `pubspec.yaml` の `assets` のパス指定が正しいか確認してください。
    - `lib/ui/home_screen.dart` の `BabylonJSViewer` の `src` のパスが正しいか確認してください。
    - Flutterのコンソールにエラーメッセージが出ていないか確認してください。
    - Web版の場合、ブラウザの開発者ツールでエラーを確認してください。
- **VRMの見た目が崩れる:**
    - `babylonjs_viewer` が使用しているBabylon.jsのバージョンとVRMの互換性に問題がある可能性があります。
    - VRMモデル自体に問題がないか、他のVRMビューアで確認してみてください。
```
