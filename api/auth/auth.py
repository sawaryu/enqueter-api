import os
import re
import traceback
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    current_user,
    jwt_required,
    create_refresh_token,
    get_jwt
)
from flask_restx import Resource, fields, Namespace
from werkzeug.security import check_password_hash, generate_password_hash

from api.model.confirmation import Confirmation, UpdateEmail
from api.model.others import TokenBlocklist
from api.model.user import User
from api.libs.mailgun import MailGunException
from database import db

auth_ns = Namespace('/auth', description="* Authentication")

username_regex = r'\A[a-z\d]{1,15}\Z(?i)'
email_regex = r"^(?!.*…)[a-zA-Z0-9_+-]+(.[a-zA-Z0-9_+-]+)*@([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.)+[a-zA-Z]{2,}$"
password_regex = r'\A[a-z\d]{8,72}\Z(?i)'
nickname_regex = r'\S'

signup = auth_ns.model('AuthSignup', {
    'username': fields.String(pattern=username_regex, required=True),
    'email': fields.String(pattern=email_regex, required=True),
    'password': fields.String(pattern=password_regex, required=True)
})

login = auth_ns.model('AuthLogin', {
    'username_or_email': fields.String(required=True),
    'password': fields.String(required=True),
})

update = auth_ns.model('AuthUpdate', {
    'username': fields.String(pattern=username_regex, required=True),
    'nickname': fields.String(min_length=1, max_length=20, pattern=nickname_regex, required=True),
    'introduce': fields.String(max_length=140, required=True)
})

updatePassword = auth_ns.model('AuthUpdatePassword', {
    'current_password': fields.String(pattern=password_regex, required=True),
    'new_password': fields.String(pattern=password_regex, required=True)
})

sendEmail = auth_ns.model('AuthSendEmail', {
    'email': fields.String(pattern=email_regex, max_length=255, required=True)
})

updateEmail = auth_ns.model('AuthUpdateEmail', {
    'code': fields.String(required=True, min_length=6, max_length=6)
})

resetPassword = auth_ns.model('AuthResetPassword', {
    'token': fields.String(max_length=50, required=True),
    'email': fields.String(pattern=email_regex, max_length=255, required=True),
    'password': fields.String(pattern=password_regex, required=True)
})


@auth_ns.route('')
class AuthBasic(Resource):
    """Basic auth CRUD functions"""

    @auth_ns.doc(
        description='Create new user.',
        body=signup
    )
    def post(self):
        params = request.json

        if User.query.filter_by(username=params['username']).one_or_none():
            return {"message": "user_id is already used."}, 400

        if User.query.filter_by(email=params['email']).one_or_none():
            return {"message": "Email is already used."}, 400

        user = User(
            username=params['username'],
            email=params["email"],
            password=params["password"],
        )

        try:
            user.save_to_db()
            confirmation = Confirmation(user.id)
            confirmation.save_to_db()
            user.send_confirmation_email()
            return {'message': 'Account created successfully. '
                               'an email with activation link has been sent to your email address, please check.'}, 201
        except MailGunException as e:
            user.delete_from_db()
            return {"message": str(e)}, 400
        except:
            traceback.print_exc()
            user.delete_from_db()
            return {"message": "Internal server error. Failed to create user."}, 500

    @auth_ns.doc(
        security='jwt_auth',
        description="Update user's profile.",
        body=update
    )
    @jwt_required()
    def put(self):
        params = request.json
        if not current_user.username == params['username'] \
                and User.query.filter_by(username=params['username']).one_or_none():
            return {'message': 'The username has been already used.'}, 400

        current_user.username = params['username']
        current_user.nickname = params['nickname']
        current_user.nickname_replaced = params['nickname'].replace(' ', '').replace('　', '')
        current_user.introduce = params['introduce']
        db.session.commit()

        return {'message': 'the user was successfully updated.'}, 201

    @auth_ns.doc(
        security='jwt_auth',
        description='Delete User, avatar from S3.'
    )
    @jwt_required()
    def delete(self):

        try:
            client = boto3.client("s3")
            # delete the avatar from aws s3
            if "egg" not in current_user.avatar:
                client.delete_object(
                    Bucket=os.getenv("AWS_BUCKET_NAME"),
                    Key=f'{os.getenv("AWS_PATH_KEY")}{current_user.avatar}'
                )
        except:
            return {"message": "Internal server error. Failed to delete the user."}, 500

        # change True the current_user deleted flag, and revoke jwt.
        current_user.is_deleted = True
        jti = get_jwt()["jti"]
        now = datetime.now(timezone.utc)
        db.session.add(TokenBlocklist(jti=jti, created_at=now))
        db.session.commit()

        return {'message': 'the user was successfully deleted. And token revoked'}, 200


@auth_ns.route('/login')
class AuthLogin(Resource):
    """Login"""

    @auth_ns.doc(
        description='Login',
        body=login
    )
    def post(self):
        params = request.json
        identify = params['username_or_email']

        user = None
        if re.fullmatch(username_regex, identify):
            user = User.query.filter_by(username=identify).one_or_none()
        elif re.fullmatch(email_regex, identify):
            user = User.query.filter_by(email=identify).one_or_none()

        if user and not user.is_deleted and check_password_hash(user.password, params['password']):
            confirmation = user.most_recent_confirmation
            if confirmation and confirmation.confirmed:
                access_token = create_access_token(identity=user)
                refresh_token = create_refresh_token(identity=user)
                return jsonify(access_token=access_token, refresh_token=refresh_token)
            return {"message": "You have not confirmed registration.", "user_id_not_confirmed": user.id}, 400

        return {"message": "Incorrect Username (E-mail) or Password.",
                "user_id_not_confirmed": None}, 401


@auth_ns.route('/logout')
class AuthLogout(Resource):
    """"Logout"""

    @auth_ns.doc(
        security='jwt_auth',
        description='logout and revoke jwt.',
    )
    @jwt_required()
    def delete(self):
        jti = get_jwt()["jti"]
        now = datetime.now(timezone.utc)
        db.session.add(TokenBlocklist(jti=jti, created_at=now))
        db.session.commit()
        return jsonify(message="Logged out completely.")


@auth_ns.route('/password')
class AuthPasswordUpdate(Resource):
    """Update Password"""

    @auth_ns.doc(
        security='jwt_auth',
        description='Update Password.',
        body=updatePassword
    )
    @jwt_required()
    def put(self):
        params = request.json
        if not check_password_hash(current_user.password, params['current_password']):
            return {"message": "Incorrect current password."}, 400

        current_user.password = generate_password_hash(params['new_password'], method='sha256')
        db.session.commit()
        return {"message": "The password was successfully updated."}, 200


@auth_ns.route('/refresh')
class AuthRefresh(Resource):
    """Token Refresh"""

    @auth_ns.doc(
        description='required refresh token to get new access-token',
        security='jwt_auth',
    )
    @jwt_required(refresh=True)
    def post(self):
        access_token = create_access_token(identity=current_user)
        return jsonify(access_token=access_token)


# confirm you can get the current_user info
@auth_ns.route('/protected')
class AuthProtected(Resource):
    """Get current user information"""

    @auth_ns.doc(
        security='jwt_auth',
        description='required access-token to get current_user info.'
    )
    @jwt_required()
    def get(self):
        return jsonify(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            avatar=current_user.avatar,
            introduce=current_user.introduce,
            nickname=current_user.nickname,
            role=current_user.role,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )


@auth_ns.route('/<string:confirmation_id>/confirm')
class AuthConfirmation(Resource):
    """When click the confirmation link"""

    @auth_ns.doc(
        description='Confirm the user is existing.'
    )
    def get(self, confirmation_id: str):
        confirmation = Confirmation.find_by_id(confirmation_id)
        if not confirmation:
            return {"message": "illegal"}, 401
        if confirmation.confirmed:
            return {"message": "already"}, 401
        if confirmation.is_expired:
            return {"message": "expired"}, 401

        confirmation.confirmed = True
        db.session.commit()

        # redirect to Frontend page.
        return {"message": "You are confirmed now."}, 200


@auth_ns.route('/<int:user_id>/confirm/resend')
class AuthConfirmationResend(Resource):
    """Resend the confirmation email"""

    @auth_ns.doc(
        description='Resend confirmation email.'
    )
    def post(self, user_id):
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return {"message": "Not found the resource you want."}, 404

        try:
            confirmation = user.most_recent_confirmation
            if confirmation:
                if confirmation.confirmed:
                    return {"message": "You had been already confirmed"}
                confirmation.force_to_expire()
            new_confirmation = Confirmation(user_id)
            db.session.add(new_confirmation)
            db.session.commit()
            user.send_confirmation_email()
            return {"message": "E-mail confirmation successfully re-sent. please check your email"
                               f" <{user.email}>"}
        except MailGunException as e:
            return {"message": str(e)}, 400
        except:
            traceback.print_exc()
            return {"message": "Internal server error. Failed to resend the email."}, 500


@auth_ns.route('/update_email')
class AuthUpdateEmail(Resource):
    """Update E-mail"""

    @auth_ns.doc(
        security='jwt_auth',
        description='Send email with code to new address.',
        body=sendEmail
    )
    @jwt_required()
    def post(self):
        if User.find_by_email(request.json["email"]):
            return {"message": "E-mail is already used."}, 400

        try:
            old_update_email_confirmation = current_user.most_recent_update_email_confirmation
            if old_update_email_confirmation:
                old_update_email_confirmation.force_to_expire()  # important
            new_update_email_confirmation = UpdateEmail(current_user.id, request.json["email"])
            new_update_email_confirmation.save_to_db()
            current_user.send_update_confirmation_email()
            return {'message': 'An email with code '
                               'has been sent to your email address, please check.'}, 201
        except MailGunException as e:
            return {"message": str(e)}, 400
        except:
            traceback.print_exc()
            return {"message": "Internal server error. Failed to resend the email."}, 500

    @auth_ns.doc(
        security='jwt_auth',
        description='Confirm code and update the E-mail.',
        body=updateEmail
    )
    @jwt_required()
    def put(self):
        code = request.json["code"]

        update_email = UpdateEmail.find_by_user_id_and_code(current_user.id, code)
        if not update_email:
            return {"message": "The code is incorrect."}, 401
        if update_email.is_expired:
            return {"message": "That code is expired already. please start over.",
                    "type": "danger"}, 401

        # if the email is used while process of updating.
        if User.find_by_email(update_email.email):
            return {"message": "Sorry, E-mail is already used by someone. please start over."}, 401

        current_user.email = update_email.email
        update_email.force_to_expire()  # important
        db.session.commit()

        return {"message": "Your email has been updated successfully."}, 200


@auth_ns.route('/password_reset')
class AuthPasswordReset(Resource):
    """Forgot Password"""

    @auth_ns.doc(
        description='Send password reset email.',
        body=sendEmail
    )
    def post(self):
        user = User.find_by_email(request.json["email"])
        if not user:
            return {"message": "An email is not registered."}, 400

        try:
            token = uuid4().hex
            user.create_reset_password_resource(token)
            user.send_reset_password_email(token)
            return {"message": "An email with link has been sent to your email address, please check."}, 200
        except MailGunException as e:
            return {"message": str(e)}, 400
        except:
            traceback.print_exc()
            return {"message": "Internal server error. Failed to resend the email."}, 500

    @auth_ns.doc(
        description='Check the link is valid and open reset page. (* very important.)',
        params={'token': {'type': 'str', 'required': True}, 'email': {'type': 'str', 'required': True}}
    )
    def get(self):
        token = request.args.get("token")
        email = request.args.get("email").replace("%40", "@")
        user = User.find_by_email(email)
        if not user or not check_password_hash(user.reset_digest, token):
            return {"message": "illegal"}, 401
        elif user.is_reset_expired:
            return {"message": "expired"}, 401

        return {"message": "ok"}, 200

    @auth_ns.doc(
        description='Actually update password.',
        body=resetPassword
    )
    def put(self):
        token = request.json["token"]
        email = request.json["email"]
        password = request.json["password"]
        user = User.find_by_email(email)
        if not user or not check_password_hash(user.reset_digest, token):
            return {"message": "illegal"}, 401
        elif user.is_reset_expired:
            return {"message": "expired"}, 401

        user.password = generate_password_hash(password, method='sha256')
        db.session.commit()
        user.force_to_expired()

        return {"message": "Reset a password successfully."}, 200
