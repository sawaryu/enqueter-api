import http
from datetime import datetime, timedelta
from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource, fields
from sqlalchemy import func

from api.model.enums import PostFontId, PostColorId
from api.model.models import Post, db, Rate, Subject, Notification, NotificationCategory, User
from api.helpers.helper import return_posts_list, return_post

post_ns = Namespace('/posts')

postCreate = post_ns.model('PostCreate', {
    'subject_id': fields.String(required=True, pattern=r'[0-9]'),
    'content': fields.String(required=True, max_length=100, pattern=r'\S'),
    'color_id': fields.Integer(required=True,
                               min=min(PostColorId.get_value_list()),
                               max=max(PostColorId.get_value_list())),
    'font_id': fields.Integer(required=True,
                              min=min(PostFontId.get_value_list()),
                              max=max(PostFontId.get_value_list()))
})

postRate = post_ns.model('PostRate', {
    'rating': fields.Integer(required=True,
                             min=1,
                             max=3)
})


@post_ns.route('/<int:post_id>')
class PostShow(Resource):
    @post_ns.doc(
        security='jwt_auth',
        description='get a post.',
    )
    @jwt_required()
    def get(self, post_id):
        post = Post.query.filter_by(id=post_id).first()
        if not post:
            return {"status": 404, "message": "the page you want was not founded."}, 404

        return return_post(post)


@post_ns.route('/<int:post_id>/rates')
class PostRate(Resource):
    @post_ns.doc(
        security='jwt_auth',
        body=postRate,
        description='rate the post.',
        params={'post_id': 'post_id, you want to rate.'}
    )
    @jwt_required()
    def post(self, post_id):
        rating = request.json['rating']
        post = Post.query.filter_by(id=post_id).first()

        # 前提チェック
        if not post:
            return dict(status=404, messaeg="回答が既に削除されている可能性があります。"), 404

        # 評価作成
        rate = Rate.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        if rate:
            rate.rating = rating
        else:
            new_rate = Rate(
                rating=rating,
                user_id=current_user.id,
                post_id=post_id
            )
            db.session.add(new_rate)

            # 通知作成(既に同じ内容の通知がある場合はスルー)
            if not Notification.query.filter_by(passive_id=post.user_id,
                                                post_id=post.id,
                                                active_id=current_user.id,
                                                category=NotificationCategory.rated).first():
                new_notice = Notification(
                    category=NotificationCategory.rated,
                    passive_id=post.user_id,
                    active_id=current_user.id,
                    post_id=post.id
                )
                db.session.add(new_notice)

        db.session.commit()
        return dict(status=200, message="successfully rated.")

    @post_ns.doc(
        security='jwt_auth',
        description='delete the rate',
        params={'post_id': 'post_id, you want to rate.'}

    )
    @jwt_required()
    def delete(self, post_id):
        rate = Rate.query.filter_by(post_id=post_id, user_id=current_user.id).first()

        # 前提チェック
        if rate is None:
            return dict(status=400, message="bad request"), http.HTTPStatus.BAD_REQUEST

        db.session.delete(rate)
        db.session.commit()

        return dict(status=200, message="the rate had been successfully deleted.")


@post_ns.route('')
class PostsIndex(Resource):
    # create
    @post_ns.doc(
        security='jwt_auth',
        body=postCreate,
        description='create the post (*don`t create the post for my subject)'
    )
    @jwt_required()
    def post(self):
        # 前提チェック
        subject = Subject.query.filter_by(id=request.json['subject_id']).first()
        if not subject:
            return {"status": 409, "message": "質問が削除されている可能性があります。"}, 409
        elif subject.user_id == current_user.id:
            return {"status": 400, "message": "bad request."}, 400
        elif current_user.posts and (current_user.posts[0].created_at + timedelta(minutes=3)) > datetime.now():
            return {"status": 400, "message": "最新の回答からまだ３分が経過していません。"}, 400

        # 作成
        subject_id = request.json['subject_id']
        content = request.json['content']
        color_id = request.json['color_id']
        font_id = request.json['font_id']

        post = Post(
            user_id=current_user.id,
            subject_id=subject_id,
            content=content,
            color_id=color_id,
            font_id=font_id
        )

        # 同じユーザーが同じsubjectに対して複数回postすることも考えられるので通知作成をスルーしない。
        new_notice = Notification(
            category=NotificationCategory.posted,
            passive_id=subject.user_id,
            active_id=current_user.id,
            subject_id=subject.id
        )
        db.session.add(new_notice)

        db.session.add(post)
        db.session.commit()

        return return_post(post)


@post_ns.route('/contributors')
class PostsContributors(Resource):
    # index
    @post_ns.doc(
        security='jwt_auth',
        description='評価数の多いユーザーを返す',
        params={'period': {'type': 'str', 'description': 'week, month, all'}}
    )
    @jwt_required()
    def get(self):
        period = request.args.get("period")
        d = {}
        if period == "week":
            d = {"weeks": 1}
        elif period == "month":
            d = {"days": 30}
        elif period == "all":
            # 100年として全て取得する。
            d = {"days": 365 * 100}

        sql_objects = db.session.query(User, func.sum(Rate.rating).label("rating_count")) \
            .join(Post, Post.user_id == User.id).join(Rate, Rate.post_id == Post.id) \
            .filter(Rate.created_at > (datetime.now() - timedelta(**d))).group_by(User.id) \
            .order_by(func.sum(Rate.rating).desc()).limit(10).all()

        users = list(map(lambda x: x.User.to_dict() | {"rating_count": int(x.rating_count)}, sql_objects))

        return users


@post_ns.route('/latest')
class PostsLatest(Resource):
    @post_ns.doc(
        security='jwt_auth',
        description='postを新しい順で取得する。',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self):
        page = int(request.args.get('page'))
        posts = Post.query.order_by(Post.id.desc()) \
            .paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


@post_ns.route('/feed')
class PostsFeed(Resource):
    @post_ns.doc(
        security='jwt_auth',
        description='postのフィードを取得する。。',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self):
        page = int(request.args.get('page'))

        following_ids = [current_user.id]
        for user in current_user.followings:
            following_ids.append(user.id)

        posts = Post.query.filter(Post.user_id.in_(following_ids)) \
            .order_by(Post.id.desc()).paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


@post_ns.route('/popular/<string:period>')
class PostsPopular(Resource):
    @post_ns.doc(
        security='jwt_auth',
        description='人気順でpostを取得する。(週間、月間、全期間)',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, period):
        page = int(request.args.get('page'))
        if period == "week":
            d = {"weeks": 1}
        elif period == "month":
            d = {"days": 30}
        else:
            d = {"days": 365 * 100}

        items = db.session.query(Post, func.sum(Rate.rating)).join(Rate) \
            .filter(Post.created_at > (datetime.now() - timedelta(**d))) \
            .group_by(Post.id) \
            .order_by(func.sum(Rate.rating).desc()) \
            .paginate(page=page, per_page=20, error_out=False).items

        posts = []
        for item in items:
            posts.append(item.Post)

        return return_posts_list(posts)
