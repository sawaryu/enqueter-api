# Enqueter API

## tasks

◇基本

* open close の切り分け処理
* 所持者、未回答、回答済みによっての各エンドポイントへのアクセス可否
* next のclose排除: ok

◇留意点

* リソースを削除する際は関連する通知を全て削除する
  (例：ユーザーの削除、質問の削除、Relationshipの削除)



## 概要
EnqueterプロジェクトのAPI。python(flask)を使用



## 注意事項
*　import補完が効かない事象が発生

`.venv`を除外フォルダーとして指定することで解決

![image](images/import-problem.png)