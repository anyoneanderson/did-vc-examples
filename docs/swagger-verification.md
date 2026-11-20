# ProcivisのSwagger UI修正確認

2026年11月20日、Procivis One Core v1.87.2（`8b701da849c8b9ad8a339c76c5191d69548bffff`）で確認しました。
教材用Dockerfileをデバッグビルドからリリースビルドに変更しています。
Procivisのソースコードは変更していません。

| 確認対象 | 修正前 | 修正後 |
|---|---|---|
| `GET /health` | 204 | 204 |
| `/api-docs/openapi.json` | 200 | 200 |
| `/swagger-ui/index.html` | 404 | 200 |
| `/swagger-ui/swagger-ui.css` | 404 | 200 |
| Swaggerのbundle、standalone preset、initializer | 未取得 | 3ファイルとも200 |
| `scripts/wait-ready.py procivis`（修正版） | Swaggerの404で失敗 | `READY: procivis` |

ブラウザでもSwaggerの表示を確認し、`GET /health`の「Try it out」→「Execute」を操作して、Server responseに204が表示されることを確認しました。
画面は[API一覧](images/procivis-swagger.png)と[実行結果](images/procivis-swagger-health.png)に保存しています。

再ビルド後に`procivis-one/run.py`を実行し、Core自身のウォレットによる受領・提示と、Pythonクライアントによる10ケースを確認しました。
10ケースの最終判定はすべて想定どおりで、実行失敗はありませんでした。
ただし、改ざんケースは必須項目の不足として拒否される既存の制約が残っており、狙った検査を確認できたのは9件です。
今回の修正によって改ざん検出まで確認できたわけではありません。

起動確認の回帰テスト4件と既存テスト5件、共通fixtureのチェックも通過しました。
APIが動いていてもSwaggerが404になる場合と、JavaScriptの代わりにステータス200のエラーページが返る場合は、起動確認が失敗することをテストしています。
