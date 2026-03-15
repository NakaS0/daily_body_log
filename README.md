# Daily Body Log

朝・昼・晩に食べたもの、体重、体脂肪率、運動を日単位で記録するアプリです。

## Screen Demo
Updated: 2026-03-11
![Dashboard demo](docs/assets/dashboard-demo-20260311.gif)

## 開発背景
減量合宿での経験を、一時的なイベントで終わらせず、日常生活で継続・定着させるための自己管理ツールが必要だと考え、開発に至りました。

## 課題
- 日常生活におけるレコーディングの習慣化が難しいこと
- 体重などの数値変化が直感的に把握しづらく、改善アクションにつながりにくいこと

## 主な機能
- 食事・運動・身体データの記録: 毎日の食事内容、運動時間、体重、体脂肪率を入力
- データの可視化: 体重および体脂肪率の推移をグラフ表示
- OMRON CSV の取込: `Omron.csv` などの CSV ファイルを読み込み、記録データへ反映

## 今後の展望
- タンパク質摂取のための鶏むね肉に飽きてしまった人向けの食品提案(マグロなど刺身類で成分表一覧を出して提案)
- 判定ロジックのカスタマイズ: 個人の目標に合わせて評価基準を変更できる機能
- マルチ LLM 対応チャットボット: 複数モデルを切り替えながら相談できる対話機能

## 概要
- SQLite を使った永続化
- 月単位ダッシュボード表示
- `<< 前月` / `翌月 >>` / `当月` の月送り
- 各日の行をブラウザ上で直接編集
- 入力変更時に自動保存
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

画面から `Omron.csv` をアップロードして、そのまま記録へ反映することもできます。

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

スマートフォンから送った `Omron.csv` を `data/omron_inbox` に置くと、自動で DB に反映されます。

## データ保存先

- Django 版: `db.sqlite3`
- テストデータ: `data/test_daily_records.json`
- 本運用データ: `data/personal_daily_records.json`
- `data/personal_daily_records.json` は `.gitignore` で除外しているため、GitHub には上がりません

## TypeScript

- フロントエンドの処理は `frontend/analysis.ts` と `frontend/dashboard.ts` で管理
- ビルド済みファイルは `static/bodylog/analysis.js` と `static/bodylog/dashboard.js`
- TypeScript の依存導入は `npm.cmd install`
- ビルドは `npm.cmd run build:ts`
- 型チェックは `npm.cmd run check:ts`
