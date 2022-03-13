from flask import request
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Namespace, Resource, fields
from werkzeug.security import generate_password_hash

from api.model.enum.enums import UserRole
from api.model.user import User
from database import db

"""
*For Admin
"""
admin_ns = Namespace("/admin", description="* Only for admin user.")

username_regex = r'\A[a-z\d]{1,15}\Z(?i)'
email_regex = r"^(?!.*…)[a-zA-Z0-9_+-]+(.[a-zA-Z0-9_+-]+)*@([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.)+[a-zA-Z]{2,}$"
password_regex = r'\A[a-z\d]{8,72}\Z(?i)'
updateUser = admin_ns.model('AdminUpdateUser', {
    'username': fields.String(pattern=username_regex, required=True),
    'email': fields.String(pattern=email_regex, required=True),
    'password': fields.String(pattern=password_regex, required=True),
})


@admin_ns.route('/users')
class AdminUsersIndex(Resource):
    @admin_ns.doc(
        security='jwt_auth',
        description='Get list of all users.'
    )
    @jwt_required()
    def get(self):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        users = User.query.all()
        return list(map(lambda x: x.to_dict(), users))


@admin_ns.route('/users/<user_id>')
class AdminUsersShow(Resource):
    @admin_ns.doc(
        security='jwt_auth',
        description='Get user info.'
    )
    @jwt_required()
    def get(self, user_id):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403
        user = User.find_by_id(user_id)
        if not user:
            return {"message": "Not found"}, 404
        return user.to_dict()

    @admin_ns.doc(
        security='jwt_auth',
        description='Update the user basic info.',
        body=updateUser
    )
    @jwt_required()
    def put(self, user_id):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        user = User.find_by_id(user_id)
        if not user:
            return {"message": "Not found"}, 404

        params = request.json

        if not user.username == params['username'] \
                and User.query.filter_by(username=params['username']).one_or_none():
            return {'message': 'The username has been already used.'}, 400
        user.username = params["username"]

        if not user.email == params['email'] \
                and User.query.filter_by(email=params['email']).one_or_none():
            return {'message': 'The email has been already used.'}, 400
        user.email = params["email"]

        user.password = generate_password_hash(params["password"], method='sha256')
        db.session.commit()
        return {"message": "Successfully updated the user's information"}, 200
