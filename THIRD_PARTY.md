# 依存物と参照資料

サンプル固有のコードはMIT Licenseです。
以下の依存物にはそれぞれのライセンスが適用されます。
OSSのソースは`runtime/`へ取得し、このリポジトリへコピーして再配布していません。

| 部品 | 固定版 | 利用条件と取得元 | 使用方法 |
|---|---|---|---|
| walt.id Issuer2 / Wallet2 / Verifier2 | v1.2.0 / ef516ecec4c79fd9fba6f1e8b226b52a4e8cf790 | [Apache-2.0](https://github.com/walt-id/waltid-identity/blob/ef516ecec4c79fd9fba6f1e8b226b52a4e8cf790/LICENSE) | 公式のコンテナを取得。ソース改変なし |
| Procivis One Core | v1.87.2 / 8b701da849c8b9ad8a339c76c5191d69548bffff | [Apache-2.0](https://github.com/procivis/one-core/blob/8b701da849c8b9ad8a339c76c5191d69548bffff/LICENSE) | 独自Dockerfileでローカルビルド。OSSのソース改変なし。ビルドしたイメージの配布なし |
| cryptography | 46.0.3 | [Apache-2.0 OR BSD-3-Clause](https://pypi.org/project/cryptography/46.0.3/) | 失敗入力を作るための鍵生成と署名 |
| jwcrypto | 1.5.6 | [LGPLv3+](https://pypi.org/project/jwcrypto/1.5.6/) | Procivisの応答へJWEを生成 |
| cffi | 2.1.1 | [MIT-0](https://pypi.org/project/cffi/2.1.1/) | Python間接依存 |
| pycparser | 3.11 | [BSD-3-Clause](https://pypi.org/project/pycparser/3.11/) | Python間接依存 |
| typing_extensions | 4.16.0 | [PSF-2.0](https://pypi.org/project/typing-extensions/4.16.0/) | Python間接依存 |
| PostgreSQL | 18.3 | [PostgreSQL License](https://www.postgresql.org/about/licence/) | 公式コンテナ。データは一時保存 |

コンテナのdigestは[versions.json](versions.json)、Pythonの固定版は[requirements.txt](requirements.txt)にあります。
Rust依存は取得したProcivisのCargo.lockに従い、`cargo build --locked`でビルドします。
RustとDebianのコンテナにはOSパッケージも含まれるため、配布物を再配布する場合はそれぞれのライセンス情報も確認してください。
