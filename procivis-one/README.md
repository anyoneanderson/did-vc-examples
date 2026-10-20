# Procivis One Core v1.87.2の比較実験

固定コミットからCore APIをDocker内でビルドし、PostgreSQLと一緒に起動します。
発行者、保有者、検証者の処理は同じCoreプロセスに置き、管理APIで組織と鍵を分けます。
本番サービスの組織間分離を検証する構成ではありません。

[共通の準備](../README.md)でPythonの仮想環境を作成した後、リポジトリのルートで実行します。

```sh
.venv/bin/python scripts/prepare.py procivis
docker compose --profile procivis up -d --build
.venv/bin/python scripts/wait-ready.py procivis
.venv/bin/python procivis-one/run.py
```

```text
native-wallet ACCEPTED
happy-path COMPLETED ACCEPT ACCEPTED target=True
tampered-claim COMPLETED REJECT ERROR target=False
expired COMPLETED REJECT ERROR target=True
wrong-holder-key COMPLETED REJECT ERROR target=True
untrusted-issuer COMPLETED REJECT ACCEPTED target=True
missing-required-claim COMPLETED REJECT ERROR target=True
wrong-course COMPLETED REJECT ACCEPTED target=True
wrong-nonce COMPLETED REJECT ERROR target=True
wrong-audience COMPLETED REJECT ERROR target=True
missing-key-binding COMPLETED REJECT ERROR target=True
```

`ERROR`はProcivisのproof requestの状態です。
この状態だけで期待通りの拒否と判断せず、同じリクエストIDのログから期限切れや鍵の不一致などの原因を確認します。
原因が一致しなければ実験自体の`executionStatus`を`ERROR`にし、終了コード1を返します。

## 2つの実行経路

最初の`native-wallet`では、Core自身の受領APIと提示APIを使って一往復します。
受領後の証明IDを提示に使い、検証結果にname、courseId、completedOnの3項目が返ることを確認します。

続く10ケースでは、保有者役のPythonクライアントがOpenID4VCIでCoreの発行者から証明を受け取り、OpenID4VPの要求へ応答します。
発行者と検証者はCoreのまま、保有者の鍵やnonceを一つずつ変更するための構成です。
正常なケースも同じクライアントで実行し、失敗した原因がクライアントの接続不備でないことを確認します。

このクライアントは検証用であり、一般利用者向けウォレットには使えません。
自分で生成したlocalhostの要求だけを読む前提で、要求JWTの発行者を認証する機能や利用者の同意画面を省いています。
提示データは、検証者が広告した公開鍵へJWEで暗号化して送ります。
emailが提示に含まれないことは、暗号化直前のJWT本文と開示値で確認します。
Core自身のウォレットが送る暗号化済み通信はこのクライアントで復号していないため、そちらの確認範囲は検証APIに返った3項目です。

発行者はdid:key、署名はES256です。
信頼するDIDは発行前に別途取得して固定し、業務判定で照合します。
対象コースと申込者名の一致も教材側で確認します。

## 固定版で調整した点

公式ガイドの受領パスには`v1`が抜けていましたが、この版の実際のパスは`/api/interaction/v1/issuance-accept`です。
提示時はcredential schemaのIDをそのままキーにせず、presentation-definitionの`credentialQueries`から取得したIDを使います。

有効期限はcredential schemaの`expiration`へ秒数を指定します。
通常は3600秒、期限切れの実験では1秒で発行し、許容時刻差の2秒も過ぎてから提示します。
共通データの「過去のiatとexpを指定する」手順とは異なりますが、署名済みのexpを書き換えず、正当に発行された証明が期限切れになった状態を作れます。

SQLiteで同一プロセスの発行と受領を試すと受領が完了しなかったため、教材はPostgreSQLを使います。
初回のRustビルドは数分かかり、依存物の取得状況やCPUで変わります。

## 保存と停止

秘密鍵はCoreの内部ストレージに置き、実行時に生成した暗号化キーを設定します。
PostgreSQLは一時ファイルシステムを使うため、停止でデータは失われます。
結果は`runtime/procivis-results.json`へ保存します。

```sh
docker compose --profile procivis stop core database
```

起動設定、コンテナ、ソースまで削除する手順は[共通README](../README.md#停止と後片付け)に記載しています。
