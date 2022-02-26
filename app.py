import logging
import os

from flask import Flask, make_response
from flask.logging import default_handler
from flask_jwt_extended import JWTManager
from flask_restx import Api, Resource
from flask_cors import CORS
from flask_migrate import Migrate
from api.auth.auth import auth_ns
from api.model.others import TokenBlocklist
from api.model.user import User
import config
from api.notifications import notification_ns
from api.questions import question_ns
from api.upload import upload_ns
from api.users import user_ns
from database import db

app = Flask(__name__)

# basic setting
app.config.from_object(config.config[os.getenv('FLASK_ENV', 'develop')])
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)
CORS(app, resources={r"/api/*": {"origins": f"{os.getenv('FRONT_URL', 'http://localhost:3000')}"}})

# logging (asctime display to cloudwatch. don't need)
formatter = logging.Formatter(
    '%(levelname)s %(process)d -- %(threadName)s '
    '%(module)s : %(funcName)s {%(pathname)s:%(lineno)d} %(message)s', '%Y-%m-%dT%H:%M:%SZ')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.removeHandler(default_handler)


# jwt settings
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


# while maintenance (https://hawksnowlog.blogspot.com/2020/12/flask-maintenance-mode.html)
@app.before_request
def check_under_maintenance():
    if os.getenv("MAINTENANCE") == "true":
        return make_response({"message": "Sorry, This service is under maintenance."}, 503)


@auth_ns.route('/maintenance')
class AuthMaintenance(Resource):
    """Check Maintenance(Very simple method.)"""

    @auth_ns.doc(
        description='Check maintenance.'
    )
    def get(self):
        return {"message": "This application is working correctly."}, 200


# Flask-rest setting.
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
    doc="/document",
    title='Enqueter API',
    version='1.0',
    license="SAMPLE license",
    description='the sample API',
    prefix='/api/v1',
    authorizations=authorizations
)
api.add_namespace(auth_ns, path='/auth')
api.add_namespace(user_ns, path='/users')
api.add_namespace(question_ns, path='/questions')
api.add_namespace(upload_ns, path='/upload')
api.add_namespace(notification_ns, path='/notifications')


def main():
    print(app.url_map)
    app.logger.info(f"Starting Enqueter API in {app.config['ENV']}")
    app.run(
        host=app.config['APP_HOST'],
        port=app.config['APP_PORT']
    )


if __name__ == '__main__':
    main()
