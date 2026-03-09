# Daily Body Log

朝・昼・晩に食べたもの、体重、内臓脂肪、運動を日単位で記録するアプリです。

このリポジトリは Django 版を中心に構成されています。

- Django 版: `manage.py` + `daily_body_log/` + `bodylog/`

## Django 版の概要

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
