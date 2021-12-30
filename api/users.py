import http
from datetime import datetime

from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Resource, Namespace, fields
from sqlalchemy import func

from api.model.models import User, db, relationship, SearchHistory, Question

user_ns = Namespace('/users')

userSearch = user_ns.model('UserSearch', {
    'search': fields.String(required=True),
})

userSearchHistory = user_ns.model('UserSearchHistory', {
    'target_id': fields.Integer(required=True, pattern=r'[0-9]'),
})


# Basic
@user_ns.route('/<user_id>')
class UserShow(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='user find by id'
    )
    @jwt_required()
    def get(self, user_id):
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return {'status': 404, 'message': 'the page you want was not found.'}, 404

        is_following = True if current_user.is_following(user) else False

        user_dict = user.to_dict() | {
            "followings_count": len(user.followings),
            "follower_count": len(user.follower),
            "is_following": is_following
        }

        return user_dict


# Question
@user_ns.route('/<user_id>/questions')
class UserQuestions(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get questions by user_id'
    )
    @jwt_required()
    def get(self, user_id):
        objects = db.session.query(Question, User).filter(Question.user_id == user_id) \
            .join(User).all()
        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))


# Follow
@user_ns.route('/<int:user_id>/followings')
class UserFollowings(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='対象ユーザーがフォローしているユーザーを全て返す'
    )
    @jwt_required()
    def get(self, user_id):

        try:
            users = User.query.filter_by(id=user_id).first().followings
        except AttributeError:
            return {"status": 404, "message": "not found"}, http.HTTPStatus.NOT_FOUND

        users_dicts = []

        for user in users:
            is_following = True if current_user.is_following(user) else False
            user_dict = user.to_dict() | {"is_following": is_following}
            users_dicts.append(user_dict)

        return users_dicts


@user_ns.route('/<int:user_id>/followers')
class UserFollowers(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='対象ユーザーをフォローしているユーザーを全て返す'
    )
    @jwt_required()
    def get(self, user_id):

        try:
            users = User.query.filter_by(id=user_id).first().follower
        except AttributeError:
            return {"status": 404, "message": "not found"}, 404

        users_dicts = []

        for user in users:
            is_following = True if current_user.is_following(user) else False
            user_dict = user.to_dict() | {"is_following": is_following}
            users_dicts.append(user_dict)

        return users_dicts


@user_ns.route('/<int:followed_id>/relationships')
class Relationship(Resource):
    # follow
    @user_ns.doc(
        security='jwt_auth',
        description='現在ユーザーが対象ユーザーをフォローします。（followed_id）'
    )
    @jwt_required()
    def post(self, followed_id):
        if current_user.id == followed_id:
            return {"status": 400, "message": "bad request."}, http.HTTPStatus.BAD_REQUEST

        target_user = User.query.filter_by(id=followed_id).first()
        if not target_user:
            return {"status": 409, "message": "The user may has been deleted."}, 409
        current_user.follow(target_user)

        db.session.commit()
        return {"status": 200, "message": f"done successfully follow the user:{followed_id}"}

    # unfollow
    @user_ns.doc(
        security='jwt_auth',
        description='現在ユーザーが対象ユーザーをアンフォローします。(followed_id)'
    )
    @jwt_required()
    def delete(self, followed_id):
        target_user = User.query.filter_by(id=followed_id).first()
        if not target_user:
            return {"status": 409, "message": "The user may has been deleted."}, 409
        current_user.unfollow(target_user)
        db.session.commit()
        return {"status": 200, "message": f"done successfully unfollow user:{followed_id}"}


# Search
# todo(余裕があれば検索条件の強化)
@user_ns.route('/search')
class UsersSearch(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Search User（フォロワーの多いユーザーを上位へ）',
        body=userSearch
    )
    @jwt_required()
    def post(self):
        search = request.json["search"]
        search = "%{}%".format(search)
        users_objects = db.session.query(User, func.count(relationship.c.followed_id).label("follower_count")) \
            .outerjoin(relationship, relationship.c.followed_id == User.id) \
            .filter(User.id != current_user.id) \
            .filter((User.public_id + User.name_replaced).like(search)) \
            .order_by(func.count(relationship.c.followed_id).desc()) \
            .group_by(User.id) \
            .all()

        return list(map(lambda x: x.User.to_dict(), users_objects))


@user_ns.route('/search/history')
class UsersSearchHistory(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get the search history'
    )
    @jwt_required()
    def get(self):
        users_objects = db.session.query(SearchHistory, User) \
                .filter(SearchHistory.user_id == current_user.id) \
                .join(User, User.id == SearchHistory.target_id)\
                .order_by(SearchHistory.updated_at.desc()).all()
        return list(map(lambda x: x.User.to_dict(), users_objects))

    @user_ns.doc(
        security='jwt_auth',
        description='Create the search history',
        body=userSearchHistory
    )
    @jwt_required()
    def post(self):
        target_id = request.json["target_id"]
        history = SearchHistory.query.filter_by(user_id=current_user.id).filter_by(target_id=target_id).first()
        if history:
            history.updated_at = datetime.now()
            db.session.commit()
            return {
                "status": 200,
                "message": "there are already the history and updated it."
            }

        new_history = SearchHistory(
            user_id=current_user.id,
            target_id=target_id,
        )
        db.session.add(new_history)
        db.session.commit()
        return {
            "status": 200,
            "message": "New history has been created"
        }

    @user_ns.doc(
        security='jwt_auth',
        description='Delete all search histories the user has'
    )
    @jwt_required()
    def delete(self):
        SearchHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        return {
            "status": 200,
            "message": "all search histories were deleted."
        }


@user_ns.route('/<int:target_id>/search/history')
class UsersSearchHistoryShow(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Delete the one history'
    )
    @jwt_required()
    def delete(self, target_id):
        history = SearchHistory.query.filter_by(user_id=current_user.id)\
            .filter_by(target_id=target_id).first()
        db.session.delete(history)
        db.session.commit()

        return {
            "status": 200,
            "message": "The search history was deleted."
        }

