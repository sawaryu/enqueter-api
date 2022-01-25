import http
from datetime import datetime, timedelta

from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Resource, Namespace, fields
from sqlalchemy import func

from api.model.enum.enums import NotificationCategory
from api.model.others import SearchHistory, Question, bookmark, answer, Notification, user_relationship
from api.model.user import User
from database import db

user_ns = Namespace('/users')

userSearch = user_ns.model('UserSearch', {
    'search': fields.String(required=True),
})

userSearchHistory = user_ns.model('UserSearchHistory', {
    'user_id': fields.Integer(required=True),
})

createOrDeleteRelationship = user_ns.model('CreateOrDeleteRelationship', {
    'user_id': fields.Integer(required=True),
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

        user_dict = user.to_dict() | {
            "following_count": len(user.followings),
            "follower_count": len(user.follower),
            "questions_count": len(user.questions),
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
            .order_by(Question.created_at.desc()) \
            .join(User).all()
        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))


@user_ns.route('/<user_id>/questions/answered')
class UserQuestionsAnswered(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get answered questions by user_id'
    )
    @jwt_required()
    def get(self, user_id):
        objects = db.session.query(Question, User) \
            .join(answer, answer.c.question_id == Question.id) \
            .filter(answer.c.user_id == user_id) \
            .join(User, User.id == Question.user_id) \
            .order_by(answer.c.created_at.desc()) \
            .all()

        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))


@user_ns.route('/<user_id>/questions/bookmark')
class UserQuestionsBookmarked(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get bookmarked questions by user_id. (*only access for current_user)'
    )
    @jwt_required()
    def get(self, user_id):
        # path parameters are treated as 'string'. So it is needed to casting to 'int'.
        if not current_user.id == int(user_id):
            return {"status": 404, "message": "Not found."}, 404

        objects = db.session.query(Question, User) \
            .join(bookmark, bookmark.c.question_id == Question.id) \
            .filter(bookmark.c.user_id == user_id) \
            .join(User, User.id == Question.user_id) \
            .order_by(bookmark.c.created_at.desc()) \
            .all()

        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))


# Follow
@user_ns.route('/<int:user_id>/followings')
class UserFollowings(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get following user by user_id.'
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
        description='Get follower by user_id.'
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


@user_ns.route('/relationships')
class Relationship(Resource):
    # follow
    @user_ns.doc(
        security='jwt_auth',
        description='Follow the user.',
        body=createOrDeleteRelationship
    )
    @jwt_required()
    def post(self):
        user_id = request.json["user_id"]
        if current_user.id == user_id:
            return {"status": 400, "message": "bad request."}, http.HTTPStatus.BAD_REQUEST

        target_user = User.query.filter_by(id=user_id).first()
        if not target_user:
            return {"status": 409, "message": "The user may has been deleted."}, 409
        current_user.follow(target_user)
        current_user.create_follow_notification(target_user)

        db.session.commit()
        return {"status": 200, "message": f"done successfully follow the user:{user_id}"}

    # unfollow
    @user_ns.doc(
        security='jwt_auth',
        description='Unfollow the user.',
        body=createOrDeleteRelationship
    )
    @jwt_required()
    def delete(self):
        user_id = request.json["user_id"]

        # unfollow
        target_user = User.query.filter_by(id=user_id).first()
        if not target_user:
            return {"status": 409, "message": "The user may has been deleted."}, 409
        current_user.unfollow(target_user)

        # delete notification if exist
        Notification.query.filter_by(
            passive_id=user_id,
            active_id=current_user.id,
            category=NotificationCategory.follow
        ).delete()

        db.session.commit()
        return {"status": 200, "message": f"done successfully unfollow user:{user_id}"}


# Search
@user_ns.route('/search')
class UsersSearch(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Search User（Finally order by desc of follower count.）',
        body=userSearch
    )
    @jwt_required()
    def post(self):
        search = request.json["search"]
        search = "%{}%".format(search)
        users_objects = db.session.query(User, func.count(user_relationship.c.followed_id).label("follower_count")) \
            .outerjoin(user_relationship, user_relationship.c.followed_id == User.id) \
            .filter(User.id != current_user.id) \
            .filter((User.username + User.nickname_replaced).like(search)) \
            .order_by(func.count(user_relationship.c.followed_id).desc()) \
            .group_by(User.id) \
            .all()

        return list(map(lambda x: x.User.to_dict(), users_objects))


@user_ns.route('/search/history')
class UsersSearchHistory(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get the search history (Finally order_by desc of updated_at)'
    )
    @jwt_required()
    def get(self):
        users_objects = db.session.query(SearchHistory, User) \
            .filter(SearchHistory.user_id == current_user.id) \
            .join(User, User.id == SearchHistory.target_id) \
            .order_by(SearchHistory.updated_at.desc()).all()
        return list(map(lambda x: x.User.to_dict(), users_objects))

    @user_ns.doc(
        security='jwt_auth',
        description='Create the search history',
        body=userSearchHistory
    )
    @jwt_required()
    def post(self):
        user_id = request.json["user_id"]
        history = SearchHistory.query.filter_by(user_id=current_user.id).filter_by(target_id=user_id).first()
        if history:
            history.updated_at = datetime.now()
            db.session.commit()
            return {
                "status": 200,
                "message": "There are already the history and updated it."
            }

        new_history = SearchHistory(
            user_id=current_user.id,
            target_id=user_id,
        )
        db.session.add(new_history)
        db.session.commit()
        return {
                   "status": 201,
                   "message": "New history has been created"
               }, 201

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
        history = SearchHistory.query.filter_by(user_id=current_user.id) \
            .filter_by(target_id=target_id).first()
        db.session.delete(history)
        db.session.commit()

        return {
            "status": 200,
            "message": "The search history was deleted."
        }


@user_ns.route('/ranking')
class UserRanking(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get the users ranking top 10 (by pt) and current_user rank info',
        params={'period': {'type': 'str', 'enum': ['week', 'month', 'all'], 'required': True}}
    )
    @jwt_required()
    def get(self):
        # get query parameter.
        period = request.args.get("period")
        if period not in ["week", "month", "all"]:
            return {"status": 400, "message": "Bad request"}, 400
        d = {}
        if period == "week":
            d = {"days": 7}
        elif period == "month":
            d = {"days": 30}
        elif period == "all":
            d = {"days": 365 * 100}

        objects = db.session.query(User, func.sum(answer.c.result_point).label("total_point")) \
            .join(answer, answer.c.user_id == User.id) \
            .filter(answer.c.created_at > (datetime.now() - timedelta(**d))) \
            .group_by(User.id) \
            .order_by(func.sum(answer.c.result_point).desc()) \
            .all()

        users = list(map(lambda x: x.User.to_dict() | {
            "total_point": int(x[1])
        }, objects))

        target_user = None
        for (index, user) in enumerate(users):
            user["rank"] = index + 1
            if user["id"] == int(current_user.id):
                target_user = user
                break

        return {"users": users, "current_user": target_user}


# TODO
@user_ns.route('/<user_id>/stats')
class UserStats(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get the user stats by user_id.',
        params={'period': {'in': 'query', 'type': 'str', 'enum': ['week', 'month', 'all']}},
    )
    @jwt_required()
    def get(self, user_id):
        # get the user
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return {"status": 404, "message": "Not Found"}, 404

        # get query parameter.
        period = request.args.get("period")
        if period not in ["week", "month", "all"]:
            return {"status": 400, "message": "Bad request"}, 400
        d = {}
        if period == "week":
            d = {"days": 7}
        elif period == "month":
            d = {"days": 30}
        elif period == "all":
            d = {"days": 365 * 100}

        # execute sql
        objects = db.session.query(User, func.sum(answer.c.result_point).label("total_point")) \
            .join(answer, answer.c.user_id == User.id) \
            .filter(answer.c.created_at > (datetime.now() - timedelta(**d))) \
            .group_by(User.id) \
            .order_by(func.sum(answer.c.result_point).desc()) \
            .all()

        users = list(map(lambda x: x.User.to_dict() | {
            "total_point": int(x[1])
        }, objects))

        target_user = None
        for (index, user) in enumerate(users):
            user["rank"] = index + 1
            if user["id"] == int(user_id):
                target_user = user
                break

        if target_user:
            return {"total_point": target_user["total_point"], "rank": target_user["rank"]}
        else:
            return {"total_point": 0, "rank": None}
