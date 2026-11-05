# Codex 向け Switch Power

[English](README.md) · [Español](README.es.md) · [Русский](README.ru.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

Switch Power は、Codex がリクエストごとに実行方法を選ぶためのプラグインです。メインのチャットが作業を評価し、必要に応じて Codex のネイティブなサブエージェントに委任します。結果の確認と返信は元のチャットで行います。同じチャットでも、新しいリクエストはその都度評価します。

ファイル数の集計には Luna の `low`、画面のレビューには Terra、複雑な監査には Sol が候補になります。利用可能なモデル、ツール、難易度、誤りの影響を考慮します。Sol、Terra、Luna の `low`、`medium`、`high` は事前承認済みです。Astra または `high` を超える推論レベルには、現在の作業と範囲に対する明示的な同意が必要です。

## インストール

バージョン 0.1.2 には Python 3.11 以上と、`plugin marketplace`、`plugin add`、および `model/list`、`skills/list`、`hooks/list` に対応する Codex CLI が必要です。リポジトリのルート、または ZIP を展開したディレクトリから実行してください。

**macOS と Linux**

```bash
python3 scripts/setup.py
```

**Windows（PowerShell、ネイティブ Codex）**

```powershell
py -3 scripts/setup.py
```

Python を `python` コマンドで実行できる場合は、`py -3` の代わりに使用できます。Codex が見つからない場合は、`--codex` に `codex.exe` のフルパスを指定します。`--coordinator` を付けると、コーディネーターの既定値を GPT‑6.1 Sol と `high` に設定できます。

インストール後は Codex CLI の `/hooks` で Switch Power の四つのフックを確認し、有効にしたいものを承認してください。その後、新しい Codex セッションを開始します。インストーラーはユーザープロファイルにプラグインを登録し、グローバルの `AGENTS.md` または `AGENTS.override.md` に管理用の設定を追加します。

## 使い方

「`scripts/` にある `.py` ファイルを数えて」のように、普段どおり依頼します。コーディネーターが実行者を選び、結果を確認して元のチャットで返信します。検証済みの V2 インターフェースでは、モデルと推論レベルを明示する際に `fork_turns: "none"` を使用し、必要な文脈を作業の指示に含めます。メインチャットのモデルは Codex が管理します。

## 無効化とアンインストール

プロジェクトのディレクトリで `python3 scripts/install.py disable` を実行すると無効にできます。`enable` に替えると再有効化、`remove` に替えるとアンインストールできます。Windows では `python3` の代わりに `py -3` を使用します。コーディネーターのモデルと推論レベルは `scripts/configure.py restore` で個別に復元できます。

バージョン 0.1.2 は 31 件のテストと macOS での新規インストール検証を通過しました。Windows ネイティブ Codex でのエンドツーエンドの検証は未実施です。詳細はロシア語の[検証レポート](docs/verification.md)と[アーキテクチャ文書](docs/architecture.md)を参照してください。
