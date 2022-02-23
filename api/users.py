import http
from datetime import datetime, timedelta

from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Resource, Namespace, fields
from sqlalchemy import func

from api.model.aggregate import point
from api.model.enum.enums import NotificationCategory
from api.model.others import SearchHistory, Notification, user_relationship
from api.model.question import Question, answer, bookmark
from api.model.user import User, PointStats, ResponseStats
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
        user = User.find_by_id(user_id)
        if not user:
            return {'status': 404, 'message': 'the page you want was not found.'}, 404

        user_dict = user.to_dict() | {
            "following_count": len(user.followings),
            "follower_count": len(user.follower),
            "questions_count": len(user.questions.all()),
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
            .order_by(Question.id.desc()) \
            .join(User).all()
        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))


@user_ns.route('/<user_id>/questions/answered')
class UserQuestionsAnswered(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get answered questions by user_id',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page: int = int(request.args.get('page'))
        if not page:
            return {"message": "Bad Request."}, 400

        objects = db.session.query(Question, User) \
            .join(answer, answer.c.question_id == Question.id) \
            .filter(answer.c.user_id == user_id) \
            .join(User, User.id == Question.user_id) \
            .order_by(answer.c.created_at.desc()) \
            .paginate(page=page, per_page=15, error_out=False) \
            .items

        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))


@user_ns.route('/<user_id>/questions/bookmark')
class UserQuestionsBookmarked(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get bookmarked questions by user_id. (*only access for current_user)',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page: int = int(request.args.get('page'))
        if not page:
            return {"message": "Bad Request."}, 400

        # path parameters are treated as 'string'. So it is needed to casting to 'int'.
        if not current_user.id == int(user_id):
            return {"status": 404, "message": "Not found."}, 404

        objects = db.session.query(Question, User) \
            .join(bookmark, bookmark.c.question_id == Question.id) \
            .filter(bookmark.c.user_id == user_id) \
            .join(User, User.id == Question.user_id) \
            .order_by(bookmark.c.created_at.desc()) \
            .paginate(page=page, per_page=15, error_out=False) \
            .items

        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))


# Follow
@user_ns.route('/<user_id>/followings')
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


@user_ns.route('/<user_id>/followers')
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


@user_ns.route('/<target_id>/search/history')
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


@user_ns.route('/point_ranking')
class UserPointRanking(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get the users ranking top 50 (by pt).',
        params={'period': {'type': 'str', 'enum': ['week', 'month', 'total']}}
    )
    @jwt_required()
    def get(self):
        period = request.args.get("period")

        if period == "week":
            select_query = [PointStats.week_rank, PointStats.week_point]
            sub_query = PointStats.week_rank.asc()
        elif period == "month":
            select_query = [PointStats.month_rank, PointStats.month_point]
            sub_query = PointStats.month_rank.asc()
        else:  # all
            select_query = [PointStats.total_rank, PointStats.total_point]
            sub_query = PointStats.total_rank.asc()

        objects = db.session.query(select_query[0].label("rank"), select_query[1].label("point"), User) \
            .join(User, User.id == PointStats.user_id) \
            .order_by(sub_query) \
            .order_by(User.id.desc()) \
            .limit(30) \
            .all()

        return list(map(lambda x: x.User.to_dict() | {
            "rank": x.rank,
            "point": x.point
        }, objects))


@user_ns.route('/response_ranking')
class UserResponseRanking(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get the users ranking top 50 (by response).',
        params={'period': {'type': 'str', 'enum': ['week', 'month', 'total']}}
    )
    @jwt_required()
    def get(self):
        period = request.args.get("period")

        if period == "week":
            select_query = [ResponseStats.week_rank, ResponseStats.week_response]
            sub_query = ResponseStats.week_rank.asc()
        elif period == "month":
            select_query = [ResponseStats.month_rank, ResponseStats.month_response]
            sub_query = ResponseStats.month_rank.asc()
        else:  # all
            select_query = [ResponseStats.total_rank, ResponseStats.total_response]
            sub_query = ResponseStats.total_rank.asc()

        objects = db.session.query(select_query[0].label("rank"), select_query[1].label("response"), User) \
            .join(User, User.id == ResponseStats.user_id) \
            .order_by(sub_query) \
            .order_by(User.id.desc()) \
            .limit(30) \
            .all()

        return list(map(lambda x: x.User.to_dict() | {
            "rank": x.rank,
            "response": x.response
        }, objects))


@user_ns.route('/<user_id>/stats')
class UserStats(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='Get the user stats by user_id.',
        params={'period': {'type': 'str', 'enum': ['week', 'month', 'total']}}
    )
    @jwt_required()
    def get(self, user_id):
        user = User.find_by_id(user_id)
        if not user:
            return {"message": "Not Found."}, 404

        period = request.args.get("period")
        point_stats: PointStats = user.point_stats
        response_stats: ResponseStats = user.response_stats
        if period == "week":
            d = {"weeks": 1}
            if point_stats:
                point_stats: list = point_stats.get_week
            if response_stats:
                response_stats: list = response_stats.get_week
        elif period == "month":
            d = {"days": 30}
            if point_stats:
                point_stats: list = point_stats.get_month
            if response_stats:
                response_stats: list = response_stats.get_month
        else:  # all
            d = {"days": 365 * 100}
            if point_stats:
                point_stats: list = point_stats.get_total
            if response_stats:
                response_stats: list = response_stats.get_total

        objects = db.session.query(point.c.point.label("point")) \
            .filter(point.c.user_id == user_id) \
            .filter(point.c.created_at > (datetime.now() - timedelta(**d))) \
            .all()
        right_count = len(list(filter(lambda x: x.point == 3, objects)))
        first_count = len(list(filter(lambda x: x.point == 1, objects)))
        wrong_count = len(list(filter(lambda x: x.point == -3, objects)))
        even_count = len(list(filter(lambda x: x.point == 0, objects)))

        radar_data = [right_count, first_count, wrong_count, even_count]

        return {"radar_data": radar_data, "point_stats": point_stats, "response_stats": response_stats}, 200
