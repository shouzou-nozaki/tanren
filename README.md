# tanren（鍛錬）

**T**echnical **A**gent for **N**urturing & **R**einforcing **E**ngineering **N**avigation

エンジニア特化のAIコーチCLIです。毎日の作業・学びを記録し、過去の文脈を踏まえてコーチングします。

```
tanren checkin   # 今日の記録
tanren ask "設計力を上げるには？"
tanren skills    # AIによるスキルマップ
tanren review    # 週次振り返り
```

---

## 特徴

- **文脈のあるコーチング** — 過去のチェックイン・目標・スキルを踏まえてAIが回答
- **AIスキル査定** — GitHubリポジトリ＋チェックイン記録から6分野のスキルマップを自動生成
- **毎日の記録** — 作業・学び・詰まったこと・エネルギーを蓄積
- **マルチプロバイダー** — Gemini（無料枠あり）または Claude を選択可能
- **DB自動圧縮** — 古い記録を週次→月次→年次で自動サマリー化

---

## インストール

```bash
pip install tanren
```

---

## セットアップ

```bash
tanren setup
```

- AIプロバイダー選択（Gemini推奨 — [aistudio.google.com](https://aistudio.google.com) で無料取得）
- APIキー入力
- GitHubユーザー名（任意・スキル査定の精度向上）

---

## コマンド一覧

### 毎日の記録

```bash
tanren checkin
```

今日やったこと・学んだこと・詰まったこと・エネルギーレベル（1〜5）を記録します。
チェックイン後、7日以上経過していればスキル査定を自動実行します。

---

### AIコーチに質問

```bash
tanren ask "設計力を上げるには？"
tanren ask   # 引数なしで対話モード
```

過去のチェックイン・目標・スキルを文脈として活用してコーチングします。

---

### スキルマップ

```bash
tanren skills          # 最新の査定結果を表示
tanren skills --assess # 今すぐ再査定
```

チェックイン記録とGitHubリポジトリの言語統計をもとに6分野でスキルを評価します。

| 大分類 | 評価対象の例 |
|--------|------------|
| 実装力 | Python, Java, TypeScript など言語・フレームワーク |
| 設計力 | システム設計, API設計, DB設計 |
| インフラ・運用 | Docker, AWS, Linux, GitHub Actions |
| データベース | PostgreSQL, MySQL, Redis |
| セキュリティ | 認証・認可, 暗号化, 脆弱性対策 |
| ソフトスキル | コードレビュー, 技術共有, ドキュメント作成 |

**レベル基準:**

| Lv | 基準 |
|----|------|
| 1 | 指示があればできる |
| 2 | 一人でできる |
| 3 | 他人に教えられる |
| 4 | 改善・最適化できる |
| 5 | 仕組み化・標準化できる |

---

### 振り返り

```bash
tanren review                  # 週次振り返り
tanren review --period month   # 月次振り返り
```

チェックイン記録をAIが分析し、学びのパターン・課題・次のアクションを提示します。

---

### 成長レポート

```bash
tanren report
```

チェックイン統計・スキルマップ・目標サマリー + AIの総評を表示します。

---

### 目標管理

```bash
tanren goal add          # 目標を追加
tanren goal list         # 一覧表示
tanren goal update <ID>  # 更新
tanren goal delete <ID>  # 削除
```

---

### 過去のやり取りを確認

```bash
tanren history          # 直近10件
tanren history -n 20    # 件数を指定
tanren history --id 3   # ID指定で全文表示
```

---

### 設定変更

```bash
tanren config show              # 現在の設定を表示
tanren config provider          # AIプロバイダーを変更
tanren config model             # モデルを変更
tanren config language          # 応答言語を変更
tanren config github            # GitHubユーザー名を設定
tanren config api-key           # APIキーを更新
```

---

### 予算管理

```bash
tanren budget status     # 今月の使用量を表示
tanren budget set 500    # 月の予算上限を変更（円）
```

---

## データの保存場所

```
~/.tanren/
├── config.json   # APIキー・設定（GitHubにはコミットされません）
└── tanren.db     # 全記録（SQLite）
```

---

## 対応AIプロバイダー

| プロバイダー | 無料枠 | 取得先 |
|---|---|---|
| Google Gemini（推奨） | あり（1日1500リクエスト） | [aistudio.google.com](https://aistudio.google.com) |
| Anthropic Claude | なし（有料） | [console.anthropic.com](https://console.anthropic.com) |
