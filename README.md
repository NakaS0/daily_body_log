# Daily Body Log

朝・昼・晩に食べたもの、体重、内臓脂肪、運動を日単位で記録するアプリです。

## Screen Demo

![Dashboard demo](docs/assets/dashboard-demo-20260311.gif)

## 開発背景
減量合宿での経験を、一時的なイベントで終わらせず、日常生活で継続・定着させるための自己管理ツールが必要だと考え、開発に至りました。

## 課題
- 日常生活におけるレコーディング（記録）の習慣化の難しさ。
- 体重等の数値変化が直感的に把握できず、改善アクションに繋がりにくい点。

## 主な機能
- 食事・運動・身体データの記録: 毎日の食事内容、運動時間、体重の入力。
- データの可視化: 体重および内臓脂肪の推移をグラフ表示し、現状を把握。

## 今後の展望（ロードマップ）
- 判定ロジックのカスタマイズ: 個人の目標に合わせ、評価（はなまる等）の基準を柔軟に変更できる機能。
- マルチLLM対応Chatbot: Local LLMを含む複数のモデルを切り替え、パーソナルなアドバイスを受けられる対話機能の実装。

## 概要

- SQLite を使った永続化
- 月単位ダッシュボード表示
- `<< 前月` / `翌月 >>` / `当月` の月送り
- 各日の行をブラウザ上で直接編集
- 入力変更またはフォーカスアウト時に自動保存
- すべて空欄にするとその日の記録を削除

## Django 版の起動手順

まず Django をインストールします。

```bash
pip install -r requirements.txt
```

初回のみマイグレーションを適用します。

```bash
python manage.py migrate
```

必要なら CSV を取り込みます。

```bash
python manage.py import_csv_records --path path\\to\\your.csv
```

開発サーバーを起動します。

```bash
python manage.py runserver
```

ブラウザで `http://127.0.0.1:8000/` を開くと、月次ダッシュボードが表示されます。

## OMRON CSV の自動取り込み

監視フォルダに CSV を置くと自動で取り込めます。

```bash
python manage.py watch_omron_csv
```

または `run_omron_csv_watcher.bat` を実行してください。

使用フォルダ:

- 監視先: `data/omron_inbox`
- 取り込み成功後: `data/omron_processed`
- 取り込み失敗後: `data/omron_failed`

スマートフォンから送った CSV を `data/omron_inbox` に置くと、自動で DB に反映されます。

## データ保存先

- Django 版: `db.sqlite3`
- `data/` 配下は `.gitignore` で除外済みです（`data/.gitkeep` のみ追跡）
