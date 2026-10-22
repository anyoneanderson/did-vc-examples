# 比較条件を決めるための参照資料

確認日: 2026-10-20。

- [RFC 9901: Selective Disclosure for JSON Web Tokens](https://www.rfc-editor.org/rfc/rfc9901.html)：選択的開示とKey Bindingの仕組み。教材では保有者の鍵を確認する構成を選びます。
- [SD-JWT VC draft 19](https://www.ietf.org/archive/id/draft-ietf-oauth-sd-jwt-vc-19.html)：SD-JWTを証明として扱う仕様の参照版。草案です。
- [SD-JWT VCの改訂状況](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)：確認時点ではdraft 19。実装採用時に改めて確認します。
- [第1回の記事](https://zench-aine.io/media/vc-formats-comparison)：共通の研修修了データ。
- [第2回の記事](https://zench-aine.io/media/did-vc-oss-landscape)：OSSの役割と比較の目的。

この参照版と、各OSSが実装している版が一致することはまだ確認していません。
実装回では参照仕様、READMEの説明、固定コードで確認した挙動を別々に記録します。

## 実装で参照した資料

- [walt.idの固定版](https://github.com/walt-id/waltid-identity/tree/ef516ecec4c79fd9fba6f1e8b226b52a4e8cf790)：Wallet2IssuerVerifier2IntegrationTest、CredentialOfferModels、Wallet2RouteHandler、VerificationSessionSetupDataを参照した。
- [Procivisの固定版](https://github.com/procivis/one-core/tree/8b701da849c8b9ad8a339c76c5191d69548bffff)：router.rs、credential schemaとidentifierのDTO、SD-JWT VC formatter、OpenID4VP final1_0の処理を参照した。
- [Procivisの一往復ガイド](https://docs.procivis.ch/getting-started/credentials)：固定版と異なったAPIパスとquery IDの扱いは、ソースと実行結果に合わせた。
- [cryptographyの楕円曲線API](https://cryptography.io/en/46.0.3/hazmat/primitives/asymmetric/ec/)：テスト用署名の生成。
- [JWCryptoのJWE](https://jwcrypto.readthedocs.io/en/v1.5.6/jwe.html)：暗号化されたOpenID4VP応答の生成。
