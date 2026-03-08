# Daily Body Log

朝・昼・晩に食べたものと、その日の体重・内臓脂肪値を記録するPythonアプリです。

- CLI版: `app.py`
- GUI版: `gui_app.py`（Tkinter / ダッシュボード風レイアウト）

## GUI版の仕様

- 勤怠ダッシュボード風の画面構成（左サイドバー + 右メイン）
- 月単位表示（1日〜月末まで全行を表示、未入力日も空欄で表示）
- `<< 前月` / `翌月 >>` / `当月` で月送り
- 列: 日付 / 朝食 / 昼食 / 夕食 / 体重 / 内臓脂肪 / 運動 / 履行
- 各セルは直接入力可能（マスごとの区切り線あり）
- 入力確定（Enter またはフォーカス移動）時に、その日の行を自動保存

## GUI版の起動（バッチ実行）

`run_daily_body_log.bat` を実行するとGUIが起動します。

## CLI版の使い方

```bash
python app.py add --date 2026-03-08 --breakfast "ヨーグルト" --lunch "そば" --dinner "鍋" --weight 63.1 --visceral-fat 7.4 --exercise "散歩30分" --execution "計画どおり"
python app.py list
python app.py today
```

## データ保存先

- 実データ: `data/records.csv`
- `data/`配下は`.gitignore`で除外済みです（`data/.gitkeep`のみ追跡）。
