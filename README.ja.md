# agent-voice-notifier

[![CI](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/ci.yml)
[![CodeQL](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/codeql.yml/badge.svg)](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/codeql.yml)
[![gitleaks](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/gitleaks.yml)

[English](README.md)

別途インストールした VOICEVOX エンジンと「ずんだもん／ノーマル」で、
コーディングエージェントの完了・承認待ち・エラーを日本語で通知します。
Python 3.11 以上、実行時の依存は標準ライブラリのみです。
対応フックアダプターは Codex と Claude Code です。

**VOICEVOX:ずんだもん** — 非公式プロジェクトです。エンジン、コア、音声モデル、
キャラクター画像、生成音声は同梱しません。
[第三者の権利について](THIRD_PARTY_NOTICES.md)と
[音源利用規約](https://zunko.jp/con_ongen_kiyaku.html)を確認してください。
生成音声を使用するアプリや動画などには、見つけられる場所に上記クレジットが必要です。
本パッケージのコードは [MIT](LICENSE) ですが、音声などの権利は別です。

## インストールと実行

[VOICEVOX](https://voicevox.hiroshiba.jp/) を別途導入し、ずんだもんを利用できる
エンジンを起動してください。Python 環境のコンソールスクリプトを PATH に通します。

```sh
python -m pip install .
agent-voice-notifier --version
agent-voice-notifier --event complete
agent-voice-notifier --event approval --no-play
agent-voice-notifier --demo --output-dir out
```

`--event` は `complete`、`approval`、`error` に対応します。
完了通知はテスト成功を保証せず、承認通知は画面確認を促します。
引数なしでもデモを生成します。デモは３種類の WAV と `manifest.json` を作り、
再生しません。`--no-play` も合成は実行するため、エンジンが必要です。

接続先の初期値は `http://127.0.0.1:50021` で、`--base-url` で変更できます。
信頼できるエンジンにのみ接続してください。出力先は実行時の作業ディレクトリを
基準とした `out/` で、`--output-dir` で変更できます。

再生は Windows および Windows PowerShell を利用できる WSL に対応します。
WSL では `wslpath -w` で変換し、PowerShell の `System.Media.SoundPlayer` で
同期再生します。他の OS では `--no-play` または `--demo` で音声を生成できます。

## 任意のフック設定

[Codex の例](examples/codex/README.md)と
[Claude Code の例](examples/claude-code/README.md)は
`agent-voice-notifier --hook` を実行し、標準入力から JSON オブジェクトを受け取ります。
利用者自身が内容を確認し、信頼したうえで導入してください。
パッケージのインストールでフックは有効になりません。このリポジトリでも有効化しません。

| 入力 | 通知 |
| --- | --- |
| バックグラウンドタスク・セッション cron のない `Stop` | 完了 |
| `PermissionRequest`、または `permission_prompt` の `Notification` | 承認待ち |
| `StopFailure`、または失敗した `PostModelRequest` | エラー |
| Bash / PowerShell で pytest を実行した `PostToolUseFailure` | エラー |
| Bash の pytest 実行後、失敗出力を検出した `PostToolUse` | エラー |

イベントの提供状況はアダプターとバージョンに依存します。アイドル通知や無関係な
ツールの失敗は無視します。無視した場合は通信もファイル作成もせず、無出力で正常終了します。
処理したフックも標準出力には何も書きません。実行時エラーは機密を含まない診断を
標準エラーに出し、エージェントを妨げないよう正常終了します。
手動実行の失敗は終了コード 1、不正な CLI 引数は 2 です。

**Codex の制限:** テスト対象の `PostToolUse` ペイロードには信頼できる終了コードが
ありません。pytest のエラー検出は出力の `FAILED`、`ERROR`、`N failed` による推測です。
無出力の非ゼロ終了は見逃します。特殊な出力では誤検知・見逃しもあり得ます。
テスト結果の監視を保証するものではありません。

## キャッシュとプライバシー

読み上げは固定メッセージと、フックの `cwd` から取得した短いプロジェクト名のみです。
Windows / POSIX の区切りに対応し、英数字・`_`・`-` 以外をハイフンに変換して
32 文字に制限します。空の場合や手動実行は `coding-agent` を使います。
プロジェクト名自体が機密の場合もあるため、読み上げられ、接続先エンジンへ送信される
点に注意してください。トランスクリプトは読みません。

`GET /speakers` で話者 ID を解決し、クエリパラメーター付きの
`POST /audio_query` と `POST /synthesis` で合成します。
接続先・話者 ID・文章の SHA-256 を WAV 名として使います。
PCM WAV を検証し、正常なキャッシュは再利用、破損したものは再生成します。
同じ接続先・ID のエンジンや音声を交換した場合は手動でキャッシュを削除してください。

`events.jsonl` は UTC の受信・再生時刻、イベント、許可済みフック名、WAV ファイル名、
長さ、キャッシュと再生の状態のみを記録します。再生省略時の時刻は null、再生失敗時は
開始のみを記録します。合成失敗は記録しません。生ペイロード、文章、プロジェクト名、
セッション ID、モデル・プロバイダー情報、コマンド、cwd、トランスクリプトのパスは
ログに保存しません。生成物はローカルに保存し、Git の対象から除外します。
出力ディレクトリを削除すればキャッシュとログを消去できます。

## 開発

[CONTRIBUTING.md](CONTRIBUTING.md)を参照してください。
`.[test]` 導入後に `python -m pytest -q` を実行します。
テストは架空データを使い、実際の通信・再生を禁止しています。
CI は Python 3.11–3.14 と基本的な gitleaks 検査を実行します。
リリースパイプラインはありません。
