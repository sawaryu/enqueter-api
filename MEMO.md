# メモ

## lazy

`lazy="dynamic"`
モデルが生成された際に関連づけられた子モデルなどをデータベースから取得しない。

メリット
query user.questions.first()のようにクエリを連続できる

`user.questions`の時点ではsqlを定義しているだけ

不必要な読み込みを行わない。 > 必要な時のみにDBloadingを行う

## tasks

◇ Email confirmation.
*　送信メールにリッチなhtmlを送信する(bootstrapがベターか？)。 ← jinjaを使用する
* urlをaタグでマスクする。

◇基本

* open close の切り分け処理
* 所持者、未回答、回答済みによっての各エンドポイントへのアクセス可否
* next のclose排除: ok

◇留意点

* リソースを削除する際は関連する通知を全て削除する
  (例：ユーザーの削除、質問の削除、Relationshipの削除)

## バッチ処理

◇処理

```text
from app import app

@app.app_context()
def step_1():
    # 以下に処理内容を記述
    pass
```

◇モデル構造

|user_id|week|moth|total|a|a|
|---|---|---|---|---|---|
|td|td|a|a|a|a|
|td|td|a|a|a|a|
|td|td|a|a|a|a|


