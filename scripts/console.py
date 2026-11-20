"""Reader-facing output; verification results remain in the JSON reports."""
from lab import FIXTURE


SCENARIOS = {
    'happy-path': '正常な修了証を、発行時に登録した保有者の鍵で提示します。',
    'tampered-claim': '発行後に研修コードを書き換えて提示します。',
    'expired': '正しく発行された修了証を、有効期限が切れた状態で提示します。',
    'wrong-holder-key': '修了証に登録された保有者とは別の鍵で、提示データに署名します。',
    'untrusted-issuer': '採用企業が信頼対象に登録していない発行者の修了証を提示します。',
    'missing-required-claim': '採用企業が要求している氏名を隠して提示します。',
    'wrong-course': '採用企業が求める研修とは別の研修の修了証を提示します。',
    'wrong-nonce': '今回の提示要求を識別する値（nonce）を別の値にして送ります。',
    'wrong-audience': '提示先（audience）を別の検証者にして送ります。',
    'missing-key-binding': '保有者の鍵で署名した提示の証明（Key Binding JWT）を付けずに送ります。',
}
CHECKS = {
    'all': 'OSSの検証と、教材側の発行者・必須項目・研修コード・申込者名の確認を通過しました。',
    'integrity': '開示された値と、発行者が署名したハッシュ値の不一致を検出しました。',
    'validity': '証明の有効期限切れを検出しました。',
    'holder-binding': '保有者の鍵による提示の証明が欠けているか、署名が一致しません。',
    'issuer-trust': '発行者が、採用企業の信頼対象に登録した発行者と一致しません。',
    'required-claims': '要求した必須項目が検証時に揃いませんでした。',
    'business-policy': '研修コードまたは申込者名が、採用企業の受け入れ条件と一致しません。',
    'request-binding': '今回の提示要求または提示先と、送られた値が一致しません。',
    'presentation-parser': '提示データを読み取る段階で、形式エラーになりました。',
}


def say(message=''):
    print(message, flush=True)


def introduction(product):
    say(f'\n{product}で研修修了証を発行・提示・検証します。')
    say('研修会社、受講者、採用企業の処理をローカルのAPIで動かします。データはすべて架空です。')
    claims = FIXTURE['claims']
    say(f"修了証: {claims['name']} / 研修 {claims['courseId']} / 修了日 {claims['completedOn']}")
    say('修了証にはメールアドレスも含めますが、採用企業への提示では隠します。')
    say('まず通常の一往復を行い、その後、条件を変えた提示を試します。\n')


def step(number, message):
    say(f'  {number}. {message}')


def case_start(index, total, case):
    say(f"\n[{index}/{total}] {case['name']} ({case['id']})")
    say('  試す内容: ' + SCENARIOS[case['id']])


def case_result(case, result):
    if result['executionStatus'] != 'COMPLETED':
        say('  実行失敗: このケースの検証を完了できませんでした。拒否の確認として数えません。')
        say('  保存先のJSONにあるerrorと、ローカルのサービスログを確認してください。')
        return
    actual = '受け入れ' if result['actualDecision'] == 'ACCEPT' else '拒否'
    expected = '受け入れ' if case['expectedDecision'] == 'ACCEPT' else '拒否'
    matches = result['actualDecision'] == case['expectedDecision']
    say(f"  最終判定: {actual}（期待: {expected} / {'想定どおり' if matches else '想定と異なります'}）")
    status = result['ossStatus']
    oss_accepted = status in {'ACCEPTED', 'SUCCESSFUL'}
    say(f"  OSSの検証: {'受理' if oss_accepted else '拒否'}（APIの状態名: {status}）")
    if oss_accepted and result['actualDecision'] == 'REJECT':
        say('  採用企業の条件を調べる教材側の処理で、受け入れを拒否しました。')
    say('  確認できたこと: ' + CHECKS.get(result.get('observedCheck'), '検査の原因は未特定です。'))
    if result.get('targetCovered') is not True:
        say('  注意: 狙った検査で拒否されたことまでは確認できていません。')
        if case['id'] == 'tampered-claim' and result.get('observedCheck') == 'required-claims':
            say('  今回は必須項目の不足として拒否されました。改ざんの検出に成功した件数には含めません。')
        elif case['id'] == 'missing-key-binding' and result.get('observedCheck') == 'presentation-parser':
            say('  形式エラーで止まったため、保有者の鍵を確認する検査の成功件数には含めません。')
    if case['id'] == 'happy-path' and result.get('emailUndisclosed'):
        say('  提示データにメールアドレスが含まれないことも確認しました。')


def summary(cases, results, output):
    matched = sum(r['executionStatus'] == 'COMPLETED' and r['actualDecision'] == c['expectedDecision']
                  for c, r in zip(cases, results))
    covered = sum(r['executionStatus'] == 'COMPLETED' and r.get('targetCovered') is True for r in results)
    errors = sum(r['executionStatus'] != 'COMPLETED' for r in results)
    say(f'\n結果: 想定どおりの判定 {matched}/{len(cases)}件、狙った検査まで確認 {covered}/{len(cases)}件、実行失敗 {errors}件。')
    say(f'詳しい結果の保存先: {output}')
    say('OSSの状態名がERRORでも、原因を調べて意図した拒否と確認できた場合は、実行失敗には数えません。')
