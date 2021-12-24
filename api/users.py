import http
from datetime import datetime, timedelta

from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Resource, Namespace, fields
from sqlalchemy import func

from api.model.models import User, Subject, Post, Rate, db, Notification, NotificationCategory, relationship, SearchHistory
from api.helpers.helper import return_subjects_list, return_posts_list

user_ns = Namespace('/users')

userSearch = user_ns.model('UserSearch', {
    'search': fields.String(required=True),
})

userSearchHistory = user_ns.model('UserSearchHistory', {
    'target_id': fields.Integer(required=True, pattern=r'[0-9]'),
})


@user_ns.route('/<user_id>')
class UserShow(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='ユーザー情報を返す。'
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
            "tags_count": len(user.tags),
            "is_following": is_following
        }

        return user_dict


@user_ns.route('/<int:user_id>/posts')
class UserPosts(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='ユーザーのポストを返す。',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page = int(request.args.get('page'))

        posts = Post.query.filter_by(user_id=user_id) \
            .order_by(Post.id.desc()) \
            .paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


@user_ns.route('/<int:user_id>/posts/rated')
class UserPostsRated(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='評価順でかえす',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page = int(request.args.get('page'))

        posts = Post.query \
            .filter_by(user_id=user_id) \
            .join(Rate, Rate.post_id == Post.id) \
            .order_by(func.sum(Rate.rating).desc()) \
            .group_by(Post.id) \
            .paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


@user_ns.route('/<int:user_id>/subjects')
class UserSubjects(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='ユーザーのサブジェクト一覧を返す。(新しい順)',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page = int(request.args.get('page'))

        subjects = Subject.query.filter_by(user_id=user_id) \
            .order_by(Subject.id.desc()) \
            .paginate(page=page, per_page=20, error_out=False).items

        return return_subjects_list(subjects)


@user_ns.route('/<int:user_id>/subjects/responded')
class UserSubjectsResponded(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='ユーザーのサブジェクト一覧を返す。(評価順)',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page = int(request.args.get('page'))

        subjects = Subject.query.filter_by(user_id=user_id).join(Post) \
            .order_by(func.count(Post.id).desc()).group_by(Subject.id) \
            .paginate(page=page, per_page=20, error_out=False).items

        return return_subjects_list(subjects)


@user_ns.route('/<int:user_id>/ratings/high')
class UserRatingsHigh(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='評価している一定件数ずつ評価した順で返す。(high)',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page = int(request.args.get('page'))

        posts = Post.query.join(Rate, Post.id == Rate.post_id).filter(Rate.user_id == user_id) \
            .filter(Rate.rating == 3) \
            .order_by(Rate.id.desc()).paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


@user_ns.route('/<int:user_id>/ratings/middle')
class UserRatingsMiddle(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='評価している一定件数ずつ評価した順で返す。(middle)',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page = int(request.args.get('page'))

        posts = Post.query.join(Rate, Post.id == Rate.post_id).filter(Rate.user_id == user_id) \
            .filter(Rate.rating == 2) \
            .order_by(Rate.id.desc()).paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


@user_ns.route('/<int:user_id>/ratings/low')
class UserRatingsLow(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='評価している一定件数ずつ評価した順で返す。(low)',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, user_id):
        page = int(request.args.get('page'))

        posts = Post.query.join(Rate, Post.id == Rate.post_id).filter(Rate.user_id == user_id) \
            .filter(Rate.rating == 1) \
            .order_by(Rate.id.desc()).paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


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
            return {"status": 404, "message": "ユーザーが見つかりません。"}, http.HTTPStatus.NOT_FOUND

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
            return {"status": 404, "message": "ユーザーが見つかりません。"}, 404

        users_dicts = []

        for user in users:
            is_following = True if current_user.is_following(user) else False
            user_dict = user.to_dict() | {"is_following": is_following}
            users_dicts.append(user_dict)

        return users_dicts


@user_ns.route('/<int:user_id>/tags')
class UserTags(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='対象ユーザーがフォローしているタグを全て返す'
    )
    @jwt_required()
    def get(self, user_id):

        try:
            tags = User.query.filter_by(id=user_id).first().tags
        except AttributeError:
            return {"status": 404, "message": "ユーザーが見つかりません。"}, 404

        tags_list = []
        for tag in tags:
            is_following = True if current_user.is_following_tag(tag) else False
            tags_list.append(tag.to_dict() | {"follower_count": len(tag.users), "is_following": is_following})

        return tags_list


@user_ns.route('/ranking/posts/get')
class UserRankingGetPosts(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='回答獲得数ランキングを返す(過去一週間)'
    )
    @jwt_required()
    def get(self):
        sql_objects = db.session.query(User, func.count(Post.id).label("total_post_count")) \
            .join(Subject, Subject.user_id == User.id).join(Post, Post.subject_id == Subject.id) \
            .group_by(User.id).filter((datetime.now() - Subject.created_at) < timedelta(weeks=1)) \
            .order_by(func.count(Subject.id).desc()).limit(10).all()

        users_list = []
        for sql_object in sql_objects:
            users_list.append(sql_object.User.to_dict() | {
                "total_count": sql_object.total_post_count
            })

        return users_list


@user_ns.route('/ranking/subjects/count')
class UserRankingSubjectsCount(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='質問回答数ランキングを返す。(過去一週間)'
    )
    @jwt_required()
    def get(self):
        # todo 現在は10件
        sql_objects = db.session.query(User, func.count(Subject.id).label("subject_count")).join(Subject) \
            .group_by(User.id).filter((datetime.now() - Subject.created_at) < timedelta(weeks=1)) \
            .order_by(func.count(Subject.id).desc()).limit(10).all()

        users_list = []
        for sql_object in sql_objects:
            users_list.append(sql_object.User.to_dict() | {
                "total_count": sql_object.subject_count
            })

        return users_list


@user_ns.route('/ranking/rating/get')
class UserRankingRatingGet(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='評価獲得順のランキングを返す。(過去一週間)'
    )
    @jwt_required()
    def get(self):
        # todo 現在は10件
        sql_objects = db.session.query(User, func.sum(Rate.rating).label("rating_count")) \
            .join(Post, Post.user_id == User.id).join(Rate, Rate.post_id == Post.id).group_by(User.id) \
            .filter((datetime.now() - Post.created_at) < timedelta(weeks=1)).order_by(func.sum(Rate.rating).desc()) \
            .limit(10).all()

        print(sql_objects)

        users_list = []
        for sql_object in sql_objects:
            users_list.append(sql_object.User.to_dict() | {
                "total_count": int(sql_object.rating_count)
            })

        return users_list


@user_ns.route('/ranking/posts/count')
class UserRankingPostsCount(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='回答数の多い順でユーザー取得。(過去一週間)'
    )
    @jwt_required()
    def get(self):
        # todo 現在は10件
        sql_objects = db.session.query(User, func.count(Post.id).label("posts_count")) \
            .join(Post, Post.user_id == User.id).group_by(User.id) \
            .filter((datetime.now() - Post.created_at) < timedelta(weeks=1)) \
            .order_by(func.count(Post.id).desc()).limit(10).all()

        print(sql_objects)

        users_list = []
        for sql_object in sql_objects:
            users_list.append(sql_object.User.to_dict() | {
                "total_count": int(sql_object.posts_count)
            })

        return users_list


@user_ns.route('/<int:user_id>/analytics')
class UserAnalytics(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='ユーザーのアナリティクスを取得する（週間、月間、全期間）',
        params={'period': {'type': 'str', 'description': 'week, month, all'}}
    )
    @jwt_required()
    def get(self, user_id):
        period = int(request.args.get('period'))
        d = {}
        if period == 1:
            d = {"weeks": 1}
        elif period == 2:
            d = {"days": 30}

        analytics = [0, 0, 0, 0]

        rating = db.session.query(User, func.sum(Rate.rating).label("rating_count")) \
            .join(Post, Post.user_id == User.id).join(Rate, Rate.post_id == Post.id).group_by(User.id) \
            .filter(User.id == user_id) \
            .filter(Rate.created_at > (datetime.now() - timedelta(**d))).first()

        response = db.session.query(User, func.count(Post.id).label("response_count")) \
            .join(Subject, Subject.user_id == User.id).join(Post, Post.subject_id == Subject.id) \
            .group_by(User.id).filter(User.id == user_id) \
            .filter(Post.created_at > (datetime.now() - timedelta(**d))).first()

        posts = db.session.query(User, func.count(Post.id).label("posts_count")).join(Post) \
            .group_by(User.id).filter(User.id == user_id) \
            .filter(Post.created_at > (datetime.now() - timedelta(**d))).first()

        subjects = db.session.query(User, func.count(Subject.id).label("subjects_count")).join(Subject) \
            .group_by(User.id).filter(User.id == user_id) \
            .filter(Subject.created_at > (datetime.now() - timedelta(**d))).first()

        analytics[0] = int(rating.rating_count) if rating else 0
        analytics[1] = int(response.response_count) if response else 0
        analytics[2] = int(posts.posts_count) if posts else 0
        analytics[3] = int(subjects.subjects_count) if subjects else 0

        return analytics


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
            return {"status": 400, "message": "自分自身をフォローすることはできません。"}, http.HTTPStatus.BAD_REQUEST

        target_user = User.query.filter_by(id=followed_id).first()
        if not target_user:
            return {"status": 409, "message": "対象のユーザーは既に削除されている可能性があります。"}, 409
        current_user.follow(target_user)

        # 同じ内容の通知が既にある場合は通知作成をスルーする。
        if not Notification.query \
                .filter_by(passive_id=target_user.id, active_id=current_user.id,
                           category=NotificationCategory.followed) \
                .first():
            new_notice = Notification(
                category=NotificationCategory.followed,
                passive_id=target_user.id,
                active_id=current_user.id
            )
            db.session.add(new_notice)

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
            return {"status": 409, "message": "対象のユーザーは既に削除されている可能性があります。"}, 409
        current_user.unfollow(target_user)
        db.session.commit()
        return {"status": 200, "message": f"done successfully unfollow user:{followed_id}"}


# todo(余裕があれば検索条件の強化)
@user_ns.route('/search')
class UsersSearch(Resource):
    @user_ns.doc(
        security='jwt_auth',
        description='全てのユーザーを検索する（フォロワーの多いユーザーを上位へ）',
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
        description='検索履歴を取得する'
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
        description='検索履歴を作成する',
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
        description='検索履歴を全て削除する。'
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
        description='検索履歴を一件削除する。'
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

