# Enqueter API

## 概要
EnqueterプロジェクトのAPI

`開発環境`
* MacOS (Bigsur)
* InteliJ IDEA (python community edition)
* python3.9.6 (flask)

## 環境構築
<u>1. venvの作成</u>
```bash
# 作成
$ python3 -m venv [ENV_NAME]
# 起動
$ . .venv/bin/activate
# 終了
$ deactivate
# 削除
$ rm -rf ENV_NAME/
# 仮想環境を初期状態に戻す
$ python3 -m venv -clear ENV_NAME
```

<u>2. pip</u>
```bash
# ライブラリのインストール
$ pip install --upgrade pip
$ pip install -r requirements.txt
# インストール済みライブラリ
$ pip list
$ pip freeze
# requirements.txtへ書き出し
$ pip freeze > requirements.txt
```

## DB structure
![image](images/db-structure.png)


## 注意事項
*　import補完が効かない事象が発生

`.venv`を除外フォルダーとして指定することで解決

![image](images/import-problem.png)