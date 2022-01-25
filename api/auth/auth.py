import http
import os
import re
import traceback
from datetime import datetime, timezone
from random import randrange

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

from api.model.confirmation import Confirmation, UpdateConfirmation
from api.model.models import TokenBlocklist
from api.model.user import User
from api.upload import client
from api.libs.mailgun import MailGunException
from database import db

auth_ns = Namespace('/auth')

public_id_regex = r'\A[a-z\d]{1,15}\Z(?i)'
email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
password_regex = r'\A[a-z\d]{8,72}\Z(?i)'

signup = auth_ns.model('AuthSignup', {
    'public_id': fields.String(pattern=public_id_regex, required=True),
    'email': fields.String(pattern=email_regex, required=True),
    'name': fields.String(min_length=1, max_length=20, required=True),
    'password': fields.String(pattern=password_regex, required=True)
})

login = auth_ns.model('AuthLogin', {
    'public_id_or_email': fields.String(required=True),
    'password': fields.String(required=True),
})

update = auth_ns.model('AuthUpdate', {
    'public_id': fields.String(pattern=public_id_regex, required=True),
    'name': fields.String(min_length=1, max_length=20, pattern=r'\S', required=True),
    'introduce': fields.String(max_length=140, required=True)
})

updatePassword = auth_ns.model('AuthUpdatePassword', {
    'current_password': fields.String(pattern=password_regex, required=True),
    'new_password': fields.String(pattern=password_regex, required=True)
})

updateConfirmation = auth_ns.model('AuthUpdateConfirmation', {
    'email': fields.String(pattern=email_regex, required=True)
})

updateConfirmationConfirm = auth_ns.model('AuthUpdateConfirmationConfirm', {
    'token': fields.String(required=True, max_length=50)
})


@auth_ns.route('')
class AuthBasic(Resource):
    @auth_ns.doc(
        description='Create new user.',
        body=signup
    )
    def post(self):
        params = request.json

        if User.query.filter_by(public_id=params['public_id']).one_or_none():
            return {"status": 400, "message": "user_id is already used."}, 400

        if User.query.filter_by(email=params['email']).one_or_none():
            return {"status": 400, "message": "Email is already used."}, 400

        hashed_password = generate_password_hash(params['password'], method='sha256')
        user = User(
            public_id=params['public_id'],
            email=params["email"],
            name=params['name'],
            name_replaced=params['name'].replace(' ', '').replace('　', ''),
            avatar=f'egg_{randrange(1, 11)}.png',
            password=hashed_password
        )

        try:
            # create user
            db.session.add(user)
            db.session.commit()

            # create confirmation
            confirmation = Confirmation(user.id)
            db.session.add(confirmation)
            db.session.commit()

            # send an email with confirmation link
            user.send_confirmation_email()
            return {"status": 201, 'message': 'Account created successfully. an email with activation link '
                                              'has been sent to your email address, please check.'}, 201
        except MailGunException as e:
            # delete the user if any error happen.
            db.session.delete(user)
            db.session.commit()
            return {"message": str(e)}, 400
        except:
            # delete the user if any error happen.
            traceback.print_exc()
            db.session.delete(user)
            db.session.commit()
            return {"message": "Internal server error. Failed to create user."}, 500

    @auth_ns.doc(
        security='jwt_auth',
        description='Delete User, avatar from S3.'
    )
    @jwt_required()
    def delete(self):

        # delete the avatar from aws s3
        if "egg" not in current_user.avatar:
            client.delete_object(
                Bucket=os.getenv("AWS_BUCKET_NAME"),
                Key=f'{os.getenv("AWS_PATH_KEY")}{current_user.avatar}'
            )

        # delete the current_user
        db.session.delete(current_user)

        # current_user's jwt go to block lists.
        jti = get_jwt()["jti"]
        now = datetime.now(timezone.utc)
        db.session.add(TokenBlocklist(jti=jti, created_at=now))

        db.session.commit()

        return {
            'status': 200,
            'message': 'the user was successfully deleted. And token revoked'
        }

    @auth_ns.doc(
        security='jwt_auth',
        description="Update user's profile.",
        body=update
    )
    @jwt_required()
    def put(self):
        params = request.json

        if not current_user.public_id == params['public_id'] \
                and User.query.filter_by(public_id=params['public_id']).one_or_none():
            return {
                       'status': 400,
                       'message': 'the user id has been already used.'
                   }, 400

        current_user.public_id = params['public_id']
        current_user.name = params['name']
        current_user.name_replaced = params['name'].replace(' ', '').replace('　', '')
        current_user.introduce = params['introduce']
        db.session.commit()

        return {
                   'status': 201,
                   'message': 'the user was successfully updated.'
               }, 201


@auth_ns.route('/login')
class AuthLogin(Resource):
    @auth_ns.doc(
        description='Login',
        body=login
    )
    def post(self):
        params = request.json
        identify = params['public_id_or_email']

        user = None
        if re.fullmatch(public_id_regex, identify):
            user = User.query.filter_by(public_id=identify).one_or_none()
        elif re.fullmatch(email_regex, identify):
            user = User.query.filter_by(email=identify).one_or_none()

        if user and check_password_hash(user.password, params['password']):
            confirmation = user.most_recent_confirmation
            if confirmation and confirmation.confirmed:
                access_token = create_access_token(identity=user)
                refresh_token = create_refresh_token(identity=user)
                return jsonify(access_token=access_token, refresh_token=refresh_token)
            return {"message": "You have not confirmed registration.", "user_id_not_confirmed": user.id}, 400

        return {"status": 401, "message": "Incorrect user_id (email) or password.",
                "user_id_not_confirmed": None}, http.HTTPStatus.UNAUTHORIZED


@auth_ns.route('/logout')
class AuthLogout(Resource):
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
        return jsonify(msg="JWT revoked")


@auth_ns.route('/password')
class AuthPassword(Resource):

    @auth_ns.doc(
        security='jwt_auth',
        description='Update Password.',
        body=updatePassword
    )
    @jwt_required()
    def put(self):
        params = request.json
        if not check_password_hash(current_user.password, params['current_password']):
            return {
                       "status": 401,
                       "message": "Incorrect current password"
                   }, http.HTTPStatus.UNAUTHORIZED

        current_user.password = generate_password_hash(params['new_password'], method='sha256')
        db.session.commit()
        return {
            "status": 200,
            "message": "The password was successfully updated."
        }


@auth_ns.route('/refresh')
class RefreshApi(Resource):

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
class ProtectedApi(Resource):
    @auth_ns.doc(
        security='jwt_auth',
        description='required access-token to get current_user info.'
    )
    @jwt_required()
    def get(self):
        # TODO: review current_user information.
        return jsonify(
            id=current_user.id,
            public_id=current_user.public_id,
            email=current_user.email,
            avatar=current_user.avatar,
            introduce=current_user.introduce,
            name=current_user.name,
            role=current_user.role,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )


@auth_ns.route('/<string:confirmation_id>/confirm')
class AuthConfirm(Resource):
    """When click the confirmation link"""

    @auth_ns.doc(
        description='Confirm the user is existing.'
    )
    def get(self, confirmation_id: str):
        confirmation = Confirmation.query.filter_by(id=confirmation_id).first()
        if not confirmation:
            return {"message": "Not Found the resource you want."}, 404
        if confirmation.confirmed:
            return {"message": "You are already confirmed.", "type": "info"}, 200
        if confirmation.is_expired:
            return {"message": "That link is expired. If you need to resend E-mail, please login firstly.",
                    "type": "warning"}, 200

        confirmation.confirmed = True
        db.session.commit()

        # redirect to Frontend page.
        return {"message": "You are confirmed now. please login. ", "type": "success"}, 200


@auth_ns.route('/<int:user_id>/confirm/resend')
class AuthConfirmResent(Resource):
    """Resend the confirmation link"""

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

    # """For testing"""
    # @auth_ns.doc(
    #     security='jwt_auth',
    #     description='Confirmation testing (* should not be open to public.)'
    # )
    # @jwt_required()
    # def get(self, user_id):
    #     user = User.query.filter_by(id=user_id).first()
    #     if not user:
    #         return {"message": "Not found the resource you want."}, 404
    #
    #     objects = user.confirmations.order_by(Confirmation.expire_at).all()
    #
    #     # dump with scratch.
    #     confirmations = list(map(lambda x: x.to_dict(), objects))
    #
    #     return (
    #         {
    #             "current_time": int(time()),
    #             "confirmation": confirmations
    #         }
    #     )


@auth_ns.route('/update_confirmation')
class AuthUpdateConfirmation(Resource):
    """reconfirmation email"""

    @auth_ns.doc(
        security='jwt_auth',
        description='Send email with token to new E-mail.',
        body=updateConfirmation
    )
    @jwt_required()
    def post(self):
        if User.query.filter_by(email=request.json["email"]).first():
            return {"status": 400, "message": "E-mail is already used."}, 400

        try:
            old_update_confirmation = current_user.most_recent_update_confirmation
            if old_update_confirmation:
                old_update_confirmation.force_to_expire()
            new_update_confirmation = UpdateConfirmation(current_user.id, request.json["email"])
            db.session.add(new_update_confirmation)
            db.session.commit()
            current_user.send_update_confirmation_email()
            return {"status": 201, 'message': 'An email with token '
                                              'has been sent to your email address, please check.'}, 201
        except MailGunException as e:
            return {"message": str(e)}, 400
        except:
            traceback.print_exc()
            return {"message": "Internal server error. Failed to resend the email."}, 500

    @auth_ns.doc(
        security='jwt_auth',
        description='Confirm token and update the email.',
        body=updateConfirmationConfirm
    )
    @jwt_required()
    def put(self):
        token = request.json["token"]

        update_confirmation = UpdateConfirmation.query.filter_by(id=token).first()
        if not update_confirmation:
            return {"message": "The token is incorrect."}, 400
        if update_confirmation.is_expired:
            return {"message": "That token is expired already. please start over.",
                    "type": "danger"}, 400
        if not update_confirmation.user_id == current_user.id:
            return {"message": "Illegal operation found."}, 400

        # if the email is used while process of updating.
        if User.query.filter_by(email=update_confirmation.email).first():
            return {"status": 400, "message": "Sorry, E-mail is already used by someone."}, 400

        current_user.email = update_confirmation.email
        update_confirmation.force_to_expire()
        db.session.commit()

        return {"message": "Your email has been updated successfully."}, 200
