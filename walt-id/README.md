# walt.id v1.2.0の比較実験

Issuer2、Wallet2、Verifier2をそれぞれ公式コンテナで起動します。
同じネットワーク名前空間を使うため、サービス同士もホスト側のPythonもlocalhostの18101〜18103番ポートで接続できます。
ホストへの公開先は127.0.0.1に限定しています。

[共通の準備](../README.md)でPythonの仮想環境を作成した後、リポジトリのルートで実行します。

```sh
.venv/bin/python scripts/prepare.py walt
docker compose --profile walt up -d
.venv/bin/python scripts/wait-ready.py walt
.venv/bin/python walt-id/run.py
```

```text
happy-path COMPLETED ACCEPT SUCCESSFUL target=True
tampered-claim COMPLETED REJECT FAILED target=True
expired COMPLETED REJECT FAILED target=True
wrong-holder-key COMPLETED REJECT FAILED target=True
untrusted-issuer COMPLETED REJECT SUCCESSFUL target=True
missing-required-claim COMPLETED REJECT SUCCESSFUL target=True
wrong-course COMPLETED REJECT SUCCESSFUL target=True
wrong-nonce COMPLETED REJECT FAILED target=True
wrong-audience COMPLETED REJECT FAILED target=True
missing-key-binding COMPLETED REJECT FAILED target=False
```

## 処理の順序

`run.py`は、管理APIから発行オファーを作り、Wallet2の受領APIで証明を保存します。
Verifier2が作ったDCQLの要求に対してWallet2が提示データを作り、Pythonがそのデータを検証者の応答APIへ送ります。
失敗例では、送信直前に提示を変更するか、異なる内容で発行した証明を使います。

発行者は実行時に作ったdid:jwkとES256鍵を使い、保有者の鍵は各ケースで生成してWallet2へ登録します。
発行者の信頼は、提示されたDIDをそのまま信用するのではなく、準備時に別途保存したDIDとの一致で確認します。
did:jwkには公開鍵が含まれるため、この実験ではDIDの固定が公開鍵の固定も兼ねます。

署名、開示値のダイジェスト、期限、保有者鍵、nonce、audienceの確認はOSSが担当します。
発行者の信頼、必須属性、対象コース、申込者名の一致は`business_check`で追加しています。
この構成のVerifier2は、nameを隠した提示にも`SUCCESSFUL`を返したため、DCQLへ書くだけで必須項目の検査が完了すると考えるわけにはいきません。

改ざんケースでは、開示値だけを変更した後に正しい保有者鍵でKey Binding JWTを作り直します。
提示全体のハッシュや保有者署名が先に失敗することを避け、発行者が署名した開示値のダイジェストとの不一致を調べるためです。

Key Binding JWTを取り除くとHTTP 400で拒否されますが、返る理由はJWSの構文エラーです。
したがって、この1件は保有者鍵の検査に到達した結果として数えず、`target=False`としています。
改ざん時のHTTP 503についても[結果](../docs/results.md)を参照してください。

## 保存と停止

ウォレットはメモリへ保存するため、再起動すると証明と保有者鍵は失われます。
起動用の発行者鍵は`runtime/walt/`、結果は`runtime/walt-results.json`に保存します。

```sh
docker compose --profile walt stop wallet verifier issuer
# 他方の実験も含めた削除はREADMEのdownコマンドを使う。
```
