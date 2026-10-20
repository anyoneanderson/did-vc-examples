# 比較結果を記録する

[implementation-status.json](../results/implementation-status.json)は未実施であることを示す一覧です。
[run-template.json](../results/run-template.json)をコピーし、実験ごとに版、環境、実行手順、実際の結果を追記します。
準備版の整合性確認は、ここでいうOSS実験に含めません。

`executionStatus`にはNOT_RUN、COMPLETED、ERROR、UNSUPPORTEDを使います。
`actualDecision`は実際に判定されたときだけACCEPTまたはREJECTとし、未実行や通信エラーではnullのままにします。
期待結果と異なった場合も実測値を記録し、期待値に書き換えません。

各記録には、OSSの固定コミット、コンテナdigest、使った仕様の版、OSとCPU、鍵の保管場所、信頼設定を含めます。
追加コード、依存サービス、有償機能の要否、起動に必要な作業も比較します。
認証情報を含む生ログや秘密鍵は`artifacts/`などのGit管理外に保存し、公開する証跡は架空データと秘密情報を除いたログにします。

ケースごとの証跡では、暗号検証、発行者への信頼、業務条件の判定がどこで実行されたかを示してください。
エラーや未対応を、想定した拒否に成功した結果として扱わないことが必要です。
