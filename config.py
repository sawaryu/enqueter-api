from datetime import timedelta
import os
from dotenv import load_dotenv

# determine which environment by 'FLASK_CONFIGURATION'
config = {
    "production": "config.ProductionConfig",
    "develop": "config.DevelopConfig",
}


class BasicConfig(object):
    # Secrete
    SECRET_KEY = os.getenv("SECRET_KEY", "779e66954b10ec490b90d29438044ae286842fd7f109d715")

    # Flask-restx
    # required fields must needed
    RESTX_VALIDATE = True
    # any methods disabled("try it out")
    # SWAGGER_SUPPORTED_SUBMIT_METHODS = []

    # jwt
    JWT_AUTH_URL_RULE = '/api/v1/auth'
    JWT_TOKEN_LOCATION = 'headers'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # max upload size (2mb)
    MAX_CONTENT_LENGTH = 2 * 1000 * 1000

    # sqlslcmey: 'mysql+pymysql://{user}:{password}@{host}/{database}?charset=utf8mb4'
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI",
                                        'mysql+pymysql://python:python@localhost/python?charset=utf8mb4')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False


class DevelopConfig(BasicConfig):
    # ローカル環境のみload_dotenvを行う
    # Bucket
    load_dotenv('.env')

    ENV = 'development'
    DEBUG = True
    APP_HOST = 'localhost'
    APP_PORT = 5000


class ProductionConfig(BasicConfig):
    ENV = 'production'
    DEBUG = False
    APP_HOST = '0.0.0.0'
    APP_PORT = 80
