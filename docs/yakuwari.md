# 「Yoppi」アプリ開発マネジメントプラン

_開発人数：2 名（A さん＝フロント担当 / B さん＝バックエンド担当）_

---

## 0. 前提

-   以前共有した **`inshu_ai_agent_design_v2.md`** を機能仕様のソースオブトゥルースとする
-   期間：**8 週間スプリント（1 週 = 1 スプリント）**
-   手法：軽量 Scrum
-   リポジトリ：GitHub（`main` / `dev/*` ブランチ運用）

---

## 1. 役割分担

| メンバー                | フォーカス         | 主担当タスク                                                                                                                                        | 兼務タスク           |
| ----------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| **A さん**<br>_Flutter_ | UI / UX / アバター | - Flutter 画面実装<br>- Unity(or Rive) アバター組込<br>- ローカルキャッシュ & オフライン同期<br>- STT/TTS クライアント呼び出し                      | QA テスト / デザイン |
| **B さん**<br>_GCP_     | サーバ / インフラ  | - Firestore スキーマ & SecurityRules<br>- Cloud Functions (飲酒計算・Gemini 呼び出し)<br>- Cloud Scheduler & PDF レポート<br>- CI/CD & モニタリング | DevOps サポート / QA |

---

## 2. ワークフロー

1. **バックログ管理**：GitHub Projects (Kanban)
2. **デイリースタンドアップ**：10 分（Slack huddle or Discord）
3. **スプリントプランニング**：毎週月曜 30 分
4. **レビュー & レトロ**：毎週金曜 30 分
5. **定義済みの完了 (DoD)**
    - 単体テスト 80% カバレッジ
    - CI ✅ パス
    - PR レビュー 1 名以上
    - QA 手動チェックリスト通過

---

## 3. ハイレベルタイムライン

| 週    | フロント (A)                               | バックエンド (B)                                     | 共有マイルストン                         |
| ----- | ------------------------------------------ | ---------------------------------------------------- | ---------------------------------------- |
| **1** | - Flutter 雛形<br>- Yoppi UI ラフ実装      | - Firestore ER 図 & スキーマ PR<br>- dev 環境構築    | ✅ プロジェクトセットアップ完了          |
| **2** | - アバター SDK PoC<br>- STT プラグイン調査 | - Functions boilerplate<br>- 飲酒計算ユーティリティ  | ✅ 「純アルコール計算」ユースケース DEMO |
| **3** | - アバター口パク完了<br>- Chat UI 実装     | - Gemini Function Calling 試作<br>- SecurityRules v1 | ✅ テキスト対話 MVP                      |
| **4** | - 音声出力 (TTS) 組込                      | - Calendar OAuth & fetch<br>- Firestore hooks        | ✅ 音声付き対話                          |
| **5** | - ログ画面 / グラフ表示                    | - 飲酒警告ロジック<br>- Push 通知                    | ✅ 飲酒量モニタリング                    |
| **6** | - オフライン同期テスト<br>- UI polish      | - 週次 PDF レポート生成                              | ✅ Beta Feature Freeze                   |
| **7** | - 多言語切替                               | - Cost ロギング / BigQuery Export                    | ✅ Internal Beta リリース                |
| **8** | - UX 微調整                                | - インフラ hardening                                 | ✅ 公開準備 & ストア申請                 |

---

## 4. チケット雛形（例）

```
[SP-05] Functions: 純アルコール計算ユーティリティ
---
概要: Firestore ドリンク doc 追加時に totalAlcoholGram 更新
完了条件:
- ユーティリティ関数 unit‑tested (>=90%)
- エッジケース: 異常値・null をハンドリング
```

---

## 5. ブランチ戦略

```
main        -- production 固定
└─ dev/a-ui-foo   (A作業)
└─ dev/b-func-bar (B作業)
   ↑ PR → main (Squash merge, Conventional Commits)
```

---

## 6. CI/CD

-   **GitHub Actions**
    -   `flutter test` / `dart analyze`
    -   `npm test` for Functions
    -   Deploy preview to **Firebase Hosting (preview channel)**
-   **Cloud Build Trigger** on `main` → Functions & Hosting prod deploy

---

## 7. リスク & コミュニケーション

| リスク     | トリガー              | オーナー  | 対策                     |
| ---------- | --------------------- | --------- | ------------------------ |
| MVP 遅延   | 週次バーンダウン悪化  | PO (共有) | スコープ調整 or ペア開発 |
| コスト爆増 | BigQuery レポート超過 | B         | Token 制限・キャッシュ   |
| UI 破綻    | マルチ解像度対応      | A         | Figma Variants で先設計  |

---

## 8. KPI / メトリクス（β 版）

| カテゴリ | 指標                 | 目標   |
| -------- | -------------------- | ------ |
| 利用     | 週次アクティブユーザ | 50 MAU |
| 行動     | 1 セッション平均杯数 | ≤ 3 杯 |
| 健康     | 警告発火率           | < 20%  |
| 技術     | LLM Token / 月       | ≤ 5M   |

---

### 連絡ツール

-   Slack `#yoppi-dev`
-   緊急: LINE グループ
-   週次議事録: Notion

---

> **開発を楽しみながらヘルシーな飲酒文化も作ろう！**  
> 疑問・ブロッカーはすぐ共有して小さく解決していきましょう。
