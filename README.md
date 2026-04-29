# tanren（鍛錬）

毎日の取り組みを記録し、過去の文脈を踏まえてアドバイスをくれるエンジニア特化のAIコーチCLIです。

## 特徴

- **文脈のあるコーチング** — 過去のチェックイン・目標・スキルを踏まえてClaudeが回答
- **毎日の記録** — 作業・学び・詰まったこと・エネルギーを蓄積
- **成長の可視化** — スキルマップ・目標管理・振り返りレポート
- **コスト管理** — 月次予算の上限設定・警告・自動ブロック
- **DB肥大化対策** — 古い記録を週次→月次→年次で自動サマリー化

---

## インストール

```bash
git clone https://github.com/shouzou-nozaki/tanren.git
cd tanren
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

PATHを通す（一度だけ実行）:

```bash
echo 'export PATH="$HOME/tanren/.venv/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

---

## セットアップ

[console.anthropic.com](https://console.anthropic.com) でAPIキーを取得してから：

```bash
tanren setup
```

APIキーと月の予算上限（デフォルト300円）を設定します。

---

## コマンド一覧

### 毎日の記録

```bash
tanren checkin
```

今日やったこと・学んだこと・詰まったこと・エネルギーレベルを記録します。

---

### AIコーチに質問

```bash
tanren ask "質問内容"
```

過去のチェックイン・目標・スキルを文脈として、Claudeがコーチングします。

---

### 過去のやり取りを確認

```bash
tanren history             # 直近10件の一覧
tanren history -n 20       # 件数を指定
tanren history --id 3      # ID=3の全文表示
```

---

### 振り返り

```bash
tanren review                  # 週次振り返り（デフォルト）
tanren review --period month   # 月次振り返り
```

期間内のチェックイン記録をAIが分析し、学びや詰まりのパターン・次のアクションを提示します。

---

### 成長レポート

```bash
tanren report
```

チェックイン統計・スキルマップ・目標サマリー・累計コスト + AIの総評を表示します。

---

### 目標管理

```bash
tanren goal add          # 目標を追加
tanren goal list         # 一覧表示（--status active/completed/paused/all）
tanren goal update <ID>  # 内容・ステータスを更新
tanren goal delete <ID>  # 削除
```

カテゴリ: `technical` / `career` / `mindset`

---

### スキル管理

```bash
tanren skills            # 一覧表示
tanren skills add        # スキルを追加
tanren skills update     # レベル・カテゴリを更新
tanren skills delete     # 削除
```

カテゴリ: `language` / `framework` / `infrastructure` / `database` / `soft` / `other`
レベル: 1=入門 〜 5=エキスパート

---

### 予算管理

```bash
tanren budget status     # 今月の使用量と残予算を表示
tanren budget set 500    # 月の予算上限を変更（円）
```

使用率80%で警告、100%でAPIコールをブロックします。

---

### データ圧縮

```bash
tanren compact
```

古いチェックインをサマリー化してDBを軽量に保ちます。

| 対象 | 処理 |
|------|------|
| 30日以上前のチェックイン | 週次サマリーへ圧縮 |
| 180日以上前の週次サマリー | 月次サマリーへ圧縮 |
| 1年以上前の月次サマリー | 年次サマリーへ圧縮 |

---

## データの保存場所

```
~/.tanren/
├── config.json   # APIキー・予算設定
└── tanren.db     # 全記録（SQLite）
```

APIキーはプロジェクトフォルダに含まれないため、GitHubに誤って公開される心配はありません。

---

## コスト目安

claude-sonnet-4-6 使用。プロンプトキャッシュ適用済み。

| 使い方 | 月額目安 |
|--------|---------|
| `tanren ask` × 1回/日 + `tanren review` × 週1回 | 約100〜200円 |
| フル活用（ask複数回 + review + report） | 約300〜500円 |
