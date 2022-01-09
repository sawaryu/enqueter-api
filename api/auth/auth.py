import http
import os
from datetime import datetime, timezone
from random import randrange

from flask import request, jsonify
from flask_jwt_extended import create_access_token, \
    current_user, jwt_required, create_refresh_token, get_jwt
from flask_restx import Resource, fields, Namespace
from werkzeug.security import check_password_hash, generate_password_hash
from api.model.models import User, db, TokenBlocklist
from api.upload import client

auth_ns = Namespace('/auth')

public_id_regex = r'\A[a-z\d]{1,15}\Z(?i)'
password_regex = r'\A[a-z\d]{8,72}\Z(?i)'

signup = auth_ns.model('AuthSignup', {
    'public_id': fields.String(pattern=public_id_regex, required=True),
    'name': fields.String(min_length=1, max_length=20, required=True),
    'password': fields.String(pattern=password_regex, required=True)
})

login = auth_ns.model('AuthLogin', {
    'public_id': fields.String(required=True),
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


@auth_ns.route('')
class AuthBasic(Resource):
    @auth_ns.doc(
        description='Create new user.',
        body=signup
    )
    def post(self):
        params = request.json

        if User.query.filter_by(public_id=params['public_id']).one_or_none():
            return {"status": 400, "message": "既に使用されているユーザーIDです。"}, 400

        hashed_password = generate_password_hash(params['password'], method='sha256')
        new_user = User(
            public_id=params['public_id'],
            name=params['name'],
            name_replaced=params['name'].replace(' ', '').replace('　', ''),
            avatar=f'egg_{randrange(1, 11)}.png',
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        return {"status": 201, 'message': 'registered successfully'}, 201

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
        user = User.query.filter_by(public_id=params['public_id']).one_or_none()

        if user and check_password_hash(user.password, params['password']):
            access_token = create_access_token(identity=user)
            refresh_token = create_refresh_token(identity=user)
            return jsonify(access_token=access_token, refresh_token=refresh_token)

        return {"status": 401, "message": "Incorrect user id or password."}, http.HTTPStatus.UNAUTHORIZED


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
        description='required access-token to change the password.',
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
        return jsonify(
            id=current_user.id,
            public_id=current_user.public_id,
            avatar=current_user.avatar,
            introduce=current_user.introduce,
            name=current_user.name,
            role=current_user.role,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )
