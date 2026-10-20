# 比較条件を決めるための参照資料

確認日: 2026-10-20。

- [RFC 9901: Selective Disclosure for JSON Web Tokens](https://www.rfc-editor.org/rfc/rfc9901.html)：選択的開示とKey Bindingの仕組み。教材では保有者の鍵を確認する構成を選びます。
- [SD-JWT VC draft 19](https://www.ietf.org/archive/id/draft-ietf-oauth-sd-jwt-vc-19.html)：SD-JWTを証明として扱う仕様の参照版。草案です。
- [SD-JWT VCの改訂状況](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)：確認時点ではdraft 19。実装採用時に改めて確認します。
- [第1回の記事](https://zench-aine.io/media/vc-formats-comparison)：共通の研修修了データ。
- [第2回の記事](https://zench-aine.io/media/did-vc-oss-landscape)：OSSの役割と比較の目的。

この参照版と、各OSSが実装している版が一致することはまだ確認していません。
実装回では参照仕様、READMEの説明、固定コードで確認した挙動を別々に記録します。
