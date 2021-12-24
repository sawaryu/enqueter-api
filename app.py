import os

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restx import Api
from flask_cors import CORS
from flask_migrate import Migrate

from api.auth.admin import admin_ns
from api.auth.auth import auth_ns
from api.model.models import db, User, TokenBlocklist
import config
from api.notifications import notification_ns
from api.posts import post_ns
from api.reports import report_ns
from api.tags import tag_ns
from api.upload import upload_ns
from api.subjects import subject_ns
from api.users import user_ns

app = Flask(__name__)
app.config.from_object(config.config[os.getenv('FLASK_CONFIGURATION', 'develop')])
db.init_app(app)
migrate = Migrate(app, db)

jwt = JWTManager(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.filter_by(id=identity).one_or_none()


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
    return token is not None


authorizations = {
    'jwt_auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': "Type below field 'Bearer [jwt_token]'"
    }
}

api = Api(
    app,
    title='SAMPLE API',
    version='1.0',
    license="SAMPLE license",
    description='the sample API for the front application.',
    prefix='/api/v1',
    authorizations=authorizations
)
api.add_namespace(auth_ns, path='/auth')
api.add_namespace(admin_ns, path='/admin')
api.add_namespace(user_ns, path='/users')
api.add_namespace(subject_ns, path='/subjects')
api.add_namespace(post_ns, path='/posts')
api.add_namespace(notification_ns, path='/notifications')
api.add_namespace(tag_ns, path='/tags')
api.add_namespace(report_ns, path='/reports')
api.add_namespace(upload_ns, path='/upload')


def main():
    print(app.url_map)
    print("starting API application...")
    app.run(
        host=app.config['APP_HOST'],
        port=app.config['APP_PORT']
    )


if __name__ == '__main__':
    main()
