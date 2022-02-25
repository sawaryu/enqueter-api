from datetime import timedelta
import os

# determine which environment by 'FLASK_ENV'
config = {
    "production": "config.ProductionConfig",
    "develop": "config.DevelopConfig",
}


class BasicConfig(object):
    SECRET_KEY = os.getenv("SECRET_KEY", "779e66954b10ec490b90d29438044ae286842fd7f109d715")
    JWT_AUTH_URL_RULE = '/api/v1/auth'
    JWT_TOKEN_LOCATION = 'headers'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    MAX_CONTENT_LENGTH = 2 * 1000 * 1000
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI",
                                        'mysql+pymysql://python:python@localhost/python?charset=utf8mb4')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # required fields must needed
    RESTX_VALIDATE = True


class DevelopConfig(BasicConfig):
    ENV = 'develop'
    DEBUG = True
    APP_HOST = 'localhost'
    APP_PORT = 5000


class ProductionConfig(BasicConfig):
    ENV = 'production'
    DEBUG = False
    APP_HOST = '0.0.0.0'
    APP_PORT = 80

