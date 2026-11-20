# DID/VC Examples

ZenChAIneのDID/VC連載と電子書籍に向けた公開教材です。
架空の研修修了証をwalt.idとProcivis One Coreで発行、受領、提示、検証し、正常系と9つの失敗例を比較します。

2026年10月20日に両実装を動かし、正常な証明の受け入れと9つの失敗入力の拒否を確認しました。
ただし、狙った検査で拒否されたことまで確認できたのはそれぞれ10件中9件であり、残る2件の挙動は[検証結果](docs/results.md)に記載しています。
主教材の選定と第3回の記事公開はこれからです。

## システムの構成

walt.idの3つのAPIサービスと、ProcivisのCore・データベースの構成を、[アーキテクチャ図](docs/architecture.md)で説明しています。
今回作ったPythonスクリプトの役割、接続先のポート、OSSが担当する処理も図と本文で確認できます。

## 必要な環境

- Git、Python 3.11以上、Docker EngineとCompose v2。
- 検証環境はmacOS 25.3、Apple Silicon、Python 3.14.8、Docker Engine 29.3.1。Dockerへ8GB以上のメモリを割り当てる構成を想定しています。
- 初回はコンテナ、Pythonパッケージ、ProcivisのソースとRust依存物を取得するため、インターネット接続が必要です。
- 18101〜18104番ポートを使います。アカウント、APIキー、有償サービス、スマホは不要です。

LinuxとWindowsでの実行は未検証です。
ProcivisのRustビルドはDocker内で行うため、ホストへRustをインストールする必要はありません。

## 実行する

```sh
git clone https://github.com/anyoneanderson/did-vc-examples.git
cd did-vc-examples
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/prepare.py all

# walt.idの発行者、ウォレット、検証者
docker compose --profile walt up -d
.venv/bin/python scripts/wait-ready.py walt
.venv/bin/python walt-id/run.py

# Procivis CoreとPostgreSQL。初回はソースからビルドする。
docker compose --profile procivis up -d --build
.venv/bin/python scripts/wait-ready.py procivis
.venv/bin/python procivis-one/run.py
```

各スクリプトは新しい鍵と架空データを作るため、繰り返し実行できます。
`prepare.py`は設定が既にある場合は鍵を更新せず、`runtime/`に置いた鍵や認証情報を再利用します。
発行時に含めたemailを提示から外し、name、courseId、completedOnだけを採用企業へ渡します。

出力には、発行・受領・提示の進行に続いて、各ケースで何を試すか、最終判定とその理由を表示します。
例えば、署名の検証を通っても、採用企業が信頼していない発行者の修了証は教材側で拒否します。

```text
[5/10] 信用しない発行者 (untrusted-issuer)
  試す内容: 採用企業が信頼対象に登録していない発行者の修了証を提示します。
  最終判定: 拒否（期待: 拒否 / 想定どおり）
  OSSの検証: 受理（APIの状態名: ACCEPTED）
  採用企業の条件を調べる教材側の処理で、受け入れを拒否しました。
  確認できたこと: 発行者が、採用企業の信頼対象に登録した発行者と一致しません。
```

これはProcivisの出力例です。
意図した拒否を確認できたケースと、通信障害などで検証を完了できない「実行失敗」を区別します。
拒否されたものの、狙った検査まで確認できなかったケースには、その理由を表示します。
最後に、想定どおりの判定件数と、狙った検査まで確認できた件数を別々に集計します。
詳しい手順と出力は[walt.id](walt-id/README.md)と[Procivis](procivis-one/README.md)を参照してください。

生成した結果は`runtime/walt-results.json`と`runtime/procivis-results.json`へ保存します。
次のコマンドで、トークンと生ログを除いた結果を`results/implementation-status.json`へ出力できます。

```sh
.venv/bin/python scripts/report.py
python3 scripts/check-fixtures.py
.venv/bin/python -m unittest discover -s tests -v
```

`check-fixtures.py`と単体テストだけではOSSとの一往復を検証できないため、再現時は上の2つの実装スクリプトも実行してください。

## 停止と後片付け

```sh
# この教材のコンテナとネットワークを削除する。
docker compose --profile walt --profile procivis down
```

walt.idのウォレットはメモリ、Procivisのデータベースは一時ファイルシステムを使います。
コンテナの停止で証明の保存データは失われ、次回起動時に作り直します。
鍵、認証情報、実行結果、取得したソースも削除する場合は、リポジトリのルートで次を実行します。

```sh
rm -rf runtime .venv
# ローカルでビルドした教材用イメージも不要なら削除する。
docker image rm did-vc-examples-procivis:v1.87.2
```

公式イメージとDockerのビルドキャッシュは残ります。
他のプロジェクトと共有するものがあるため、ここでは一括削除しません。

## 教材の内容と版

1. [修了証と受け入れ条件](docs/scenario.md)、[共通データ](fixtures/training-completion.json)、[10ケース](fixtures/cases.json)
2. [受け入れ条件](docs/acceptance.md)と[実行結果](docs/results.md)
3. [固定版](versions.json)、[利用条件](THIRD_PARTY.md)、[既知の制約](docs/limitations.md)

`preparation-v0.1.0`は準備資料のタグです。
この実装をレビューした後、記事公開時に`chapter-03-v1.0.0`などのタグを作成し、記事から固定版を参照します。
公開済みタグは付け替えません。

## 連載と問い合わせ

- [第1回：証明書形式の比較](https://zench-aine.io/media/vc-formats-comparison)
- [第2回：主要OSS](https://zench-aine.io/media/did-vc-oss-landscape)
- [電子書籍のEpic](https://github.com/anyoneanderson/ZenchainWeb/issues/197) / [実装Issue](https://github.com/anyoneanderson/did-vc-examples/issues/1)

サンプル固有のコード、文書、架空データは[MIT License](LICENSE)です。
依存物のライセンスは[THIRD_PARTY.md](THIRD_PARTY.md)に記載しています。
質問と不具合は[Issues](https://github.com/anyoneanderson/did-vc-examples/issues)へ、[報告手順](CONTRIBUTING.md)に沿ってお寄せください。
