# DID/VC Examples

ZenChAIneのDID/VC連載と電子書籍に向けた公開教材です。
架空の研修修了証を使い、walt.idとProcivis One Coreで発行、受領、提示、検証を比較する予定です。

**現在は比較条件と共通データを準備した段階です。OSSの起動手順や署名付き証明を発行する実装はまだありません。**
次のコマンドは教材ファイルの整合性だけを確認します。証明の署名、期限、保有者の鍵を検証するものではありません。

## まず共通データを確認する

GitとPython 3.9以上が必要です。Pythonの追加パッケージ、Docker、アカウント、APIキーは不要です。

```sh
git clone https://github.com/anyoneanderson/did-vc-examples.git
cd did-vc-examples
git checkout preparation-v0.1.0
python3 scripts/check-fixtures.py
```

成功時の出力:

```text
PASS: fixture consistency (4 claims, 10 planned cases, 2 implementations)
NOTE: no credential issuance, signature verification, or OSS integration was run.
```

この確認はサーバーやコンテナを起動せず、ファイルも生成しません。停止操作は不要です。
後片付けは作業ディレクトリを削除するだけですが、自分で編集したファイルがないことを先に確認してください。

## 読む順序

1. [修了証の項目と受け入れ条件](docs/scenario.md)
2. [共通の業務データ](fixtures/training-completion.json)と[実験ケース](fixtures/cases.json)
3. [成功条件と失敗例](docs/acceptance.md)
4. [walt.idの実装予定](walt-id/README.md) / [Procivis One Coreの実装予定](procivis-one/README.md)
5. [実験結果の記録方法](docs/results.md)

## 現在地

| 対象 | 状態 |
|---|---|
| 修了証の項目、比較条件、失敗条件 | 定義済み |
| 共通データの整合性確認 | 実行可能 |
| OSSの版と実行環境の固定 | 未決定 |
| OSSの起動、発行、受領、提示、検証 | 未実装・未検証 |
| 主教材の選定 | 未決定 |

`preparation-v0.1.0`は準備資料のタグです。第3回の記事に対応する実装完了タグではありません。
記事公開時の版の残し方は[読者向け完了条件](docs/reader-checklist.md)を参照してください。

## 連載と作業管理

- [第1回：W3C VC、SD-JWT VC、mdocの比較](https://zench-aine.io/media/vc-formats-comparison)
- [第2回：主要OSSの開発元、導入事例、選び方](https://zench-aine.io/media/did-vc-oss-landscape)
- [電子書籍のEpic](https://github.com/anyoneanderson/ZenchainWeb/issues/197)
- [今回の準備作業](https://github.com/anyoneanderson/ZenchainWeb/issues/209)

## 利用条件と報告先

このリポジトリで作成したコード、文書、架空データは[MIT License](LICENSE)で利用できます。
依存OSSにはそれぞれのライセンスが適用されます。現在は依存OSSのコードを同梱していません。
固定版を導入する際は[依存物の記録](THIRD_PARTY.md)へ追記します。

質問と不具合は[このリポジトリのIssues](https://github.com/anyoneanderson/did-vc-examples/issues)へお願いします。
報告方法は[CONTRIBUTING.md](CONTRIBUTING.md)、既知の制約は[docs/limitations.md](docs/limitations.md)に記載しています。
