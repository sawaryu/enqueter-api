# Python API　プロジェクト
FlaskAPIを使用したサンプルプロジェクト
TODOリストを作成して基本的なAPI開発を学ぶ。

### API設計方針
**1. 基準となるリソースを意識してエンドポイントを設計する。**

```
(GET)/users/1/posts
user(最初のユーザー) > posts(複数の投稿) 
(POST)/notifications
通知を一件作成する。
```

**2. レスポンス**

エラーレスポンス
* フロントエンドからの予期できるリクエストの場合
```
フラッシュメッセージでの使用を意識した正しいメッセージをレスポンスする。
# 例
return dict(status=404, messaeg="投稿が既に削除されている可能性があります。"), http.HTTPStatus.NOT_FOUND
```

* curlコマンド等を通した予期しないリクエストの場合
```
メッセージを英語で返す。
# 例
return dict(status=400, message="bad request."), http.HTTPStatus.BAD_REQUEST
```

サクセスレスポンス
* 原則、成功メッセージはフロント側で使用しないため。最低限内容が分かるものでOK
```
# 例
return dict(status=200, message="successfully changed status to 'watched'")
```


3. モデルのボリュームを重視する。

可能であればモデルのボリュームを増やしてapiのコード量を減らす。

## 環境構築手順

### 1. venvの作成（python仮想環境）と起動から終了まで

**任意のディレクトリで下記コマンドを使用して仮想環境を構築する。**
```bash
$ python3 -m venv [仮想環境名]
```

**venvのディレクトリ構成**
```
$ tree .venv -L 3 
.venv
├── bin
│   ├── Activate.ps1
│   ├── activate
│   ├── activate.csh
│   ├── activate.fish
│   ├── flask
│   ├── pip
│   ├── pip3
│   ├── pip3.9
│   ├── python -> python3.9
│   ├── python3 -> python3.9 
│   └── python3.9 -> /usr/local/opt/python@3.9/bin/python3.9 (*SDK対象ファイル)
├── include
│   └── site
│       └── python3.9
├── lib
│   └── python3.9
│       └── site-packages
└── pyvenv.cfg
```

**仮想環境の起動と終了(inteliJでSDKを選択している場合は恐らく不要)**

起動
```
$ . .venv/bin/activate
```

終了
```
$ deactivate
```

仮想環境自体を削除する
```
rm -rf ENV_NAME/
```

### 2. パッケージやライブラリの運用(pip)

インストール済ライブラリ一覧
```
$ pip list
```
```
$ pip freeze
```

仮想環境内パッケージを全てrequirements.txtへ書き出す
```
$ pip freeze > requirements.txt
```

仮想環境を初期状態に戻す
```
$ python3 -m venv —clear ENV_NAME
```

# SQLalchemy操作、概要

## セッティング

```
# flaskを起動した上でシェルに入る
$ FLASK_APP=main.py flask shell
```

```
# appilicationに取り込まれたdbを操作する
>> from main import db
# modelに定義したテーブルを作成する
>> db.create_all()
# データベース内のテーブルを全て削除する.
>> db.drop_all()
```

* 起動
```

root $ FLASK_APP=main.py flask run
```

## 初期データ（seed.py）
**実行**
```
※実行する前にモデルなどよく確認する。
$ FLASK_APP=main.py flask shell
>> from seed import main
>> main()
>> exit()
```

## SQLALchemy

### 1. Relationship

```python

```

### 2. filterメソッドの挙動について

比較したい項目を直接比較参照しなければ正しく挙動しない。
```
-省略-
.filter(Subject.created_at > (datetime.now() - timedelta(minutes=1)))
-省略-
```

## やるべきこと

* post,putメソッドのレスポンスを201に統一する
* swagger documentを強化する



